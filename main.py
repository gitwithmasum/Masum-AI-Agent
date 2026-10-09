import asyncio
import base64
import html as html_lib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from automation_engine import AutomationStore, automation_loop
from multi_agent import (
    format_agent_catalog,
    normalize_agent_name,
    route_agent_names,
)

from ddgs import DDGS
from ddgs.exceptions import DDGSException
from docx import Document
from dotenv import load_dotenv
from pypdf import PdfReader
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build as google_api_build
from googleapiclient.errors import HttpError
from agents import (
    Agent,
    AsyncOpenAI,
    OpenAIChatCompletionsModel,
    Runner,
    SQLiteSession,
    function_tool,
    set_tracing_disabled,
)

load_dotenv(override=True)

AGENT_TIMEOUT_SECONDS = int(os.getenv("AGENT_TIMEOUT_SECONDS", "120"))
MEMORY_SESSION_ID = os.getenv("MEMORY_SESSION_ID", "masum-main").strip()
MEMORY_DB_PATH = Path(os.getenv("MEMORY_DB_PATH", "data/memory.db"))

WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))
WEB_SEARCH_TIMEOUT = int(os.getenv("WEB_SEARCH_TIMEOUT", "10"))

KNOWLEDGE_DIR = Path(os.getenv("KNOWLEDGE_DIR", "knowledge"))
FILE_MAX_BYTES = int(os.getenv("FILE_MAX_BYTES", str(15 * 1024 * 1024)))
FILE_PREVIEW_CHARS = int(os.getenv("FILE_PREVIEW_CHARS", "12000"))
FILE_CHUNK_CHARS = int(os.getenv("FILE_CHUNK_CHARS", "3500"))
FILE_MAX_CHUNKS = int(os.getenv("FILE_MAX_CHUNKS", "4"))

ACADEMIC_SEARCH_MAX_RESULTS = int(os.getenv("ACADEMIC_SEARCH_MAX_RESULTS", "6"))
OPENALEX_TIMEOUT = int(os.getenv("OPENALEX_TIMEOUT", "20"))
RESEARCH_TIMEOUT_SECONDS = int(os.getenv("RESEARCH_TIMEOUT_SECONDS", "240"))
RESEARCH_REPORT_DIR = Path(os.getenv("RESEARCH_REPORT_DIR", "research_reports"))

GITHUB_API_BASE = os.getenv("GITHUB_API_BASE", "https://api.github.com").rstrip("/")
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "gitwithmasum").strip()
GITHUB_DEFAULT_REPO = os.getenv("GITHUB_DEFAULT_REPO", "Masum-AI-Agent").strip()
GITHUB_TIMEOUT = int(os.getenv("GITHUB_TIMEOUT", "20"))
GITHUB_MAX_ITEMS = int(os.getenv("GITHUB_MAX_ITEMS", "8"))
GITHUB_FILE_PREVIEW_CHARS = int(os.getenv("GITHUB_FILE_PREVIEW_CHARS", "16000"))

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
GMAIL_CREDENTIALS_PATH = Path(
    os.getenv("GMAIL_CREDENTIALS_PATH", "secrets/gmail_credentials.json")
)
GMAIL_TOKEN_PATH = Path(
    os.getenv("GMAIL_TOKEN_PATH", "secrets/gmail_token.json")
)
GMAIL_MAX_RESULTS = int(os.getenv("GMAIL_MAX_RESULTS", "8"))
GMAIL_BODY_PREVIEW_CHARS = int(os.getenv("GMAIL_BODY_PREVIEW_CHARS", "12000"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
SUPABASE_SCHEMA = os.getenv("SUPABASE_SCHEMA", "public").strip() or "public"
SUPABASE_TIMEOUT = int(os.getenv("SUPABASE_TIMEOUT", "20"))
SUPABASE_MAX_ROWS = int(os.getenv("SUPABASE_MAX_ROWS", "20"))
SUPABASE_PREVIEW_CHARS = int(os.getenv("SUPABASE_PREVIEW_CHARS", "16000"))
SUPABASE_ALLOWED_TABLES = {
    item.strip()
    for item in os.getenv("SUPABASE_ALLOWED_TABLES", "").split(",")
    if item.strip()
}

AUTOMATION_TASKS_PATH = Path(
    os.getenv("AUTOMATION_TASKS_PATH", "data/automations.json")
)
AUTOMATION_LOG_PATH = Path(
    os.getenv("AUTOMATION_LOG_PATH", "data/automation_log.jsonl")
)
AUTOMATION_CHECK_SECONDS = int(
    os.getenv("AUTOMATION_CHECK_SECONDS", "30")
)

MULTI_AGENT_AUTO_ROUTE = os.getenv(
    "MULTI_AGENT_AUTO_ROUTE",
    "true",
).strip().lower() in {"1", "true", "yes", "on"}
MULTI_AGENT_MAX_COLLABORATORS = max(
    1,
    min(
        int(os.getenv("MULTI_AGENT_MAX_COLLABORATORS", "2")),
        3,
    ),
)
MULTI_AGENT_TIMEOUT_SECONDS = int(
    os.getenv("MULTI_AGENT_TIMEOUT_SECONDS", "180")
)

SUPPORTED_FILE_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}


@function_tool
def get_current_time() -> str:
    """Return the computer's current local date and time."""
    return datetime.now().astimezone().strftime(
        "%A, %d %B %Y - %I:%M:%S %p %Z"
    )


def search_web_data(query: str, max_results: int | None = None) -> list[dict]:
    query = query.strip()
    if not query:
        return []

    limit = max_results or WEB_SEARCH_MAX_RESULTS
    limit = max(1, min(limit, 8))

    try:
        results = DDGS(timeout=WEB_SEARCH_TIMEOUT).text(
            query,
            max_results=limit,
        )
    except DDGSException:
        return []
    except Exception:
        return []

    return list(results or [])


def search_web(query: str, max_results: int | None = None) -> str:
    """Run a key-free web search and return compact source results."""
    query = query.strip()
    if not query:
        return "Search query is empty."

    results = search_web_data(query, max_results=max_results)
    if not results:
        return f"No web results found for: {query}"

    lines = [f"Live web results for: {query}"]
    for index, item in enumerate(results, start=1):
        title = (item.get("title") or "Untitled").strip()
        url = (item.get("href") or "").strip()
        body = (item.get("body") or "").strip()

        lines.append(f"\n[W{index}] {title}")
        if body:
            lines.append(body)
        if url:
            lines.append(f"Source: {url}")

    return "\n".join(lines)


@function_tool
def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the live public web.

    Use this for current information, recent events, documentation,
    changing facts, websites, products, releases, or anything that
    may require up-to-date information.
    """
    return search_web(query, max_results=max_results)


def reconstruct_abstract(inverted_index: dict | None) -> str:
    if not inverted_index:
        return ""

    positions = []
    for word, indexes in inverted_index.items():
        for position in indexes:
            positions.append((position, word))

    positions.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positions)


def search_academic_papers_data(
    query: str,
    max_results: int | None = None,
) -> list[dict]:
    query = query.strip()
    if not query:
        return []

    limit = max_results or ACADEMIC_SEARCH_MAX_RESULTS
    limit = max(1, min(limit, 10))

    params = urllib.parse.urlencode(
        {
            "search": query,
            "per_page": limit,
            "select": (
                "id,title,publication_year,cited_by_count,doi,authorships,"
                "abstract_inverted_index,open_access,primary_location"
            ),
        }
    )
    url = f"https://api.openalex.org/works?{params}"

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Masum-AI-Agent/1.4 (local research assistant)",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=OPENALEX_TIMEOUT) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return []

    papers = []
    for item in payload.get("results", []):
        authors = []
        for authorship in item.get("authorships") or []:
            author = (authorship.get("author") or {}).get("display_name")
            if author:
                authors.append(author)

        location = item.get("primary_location") or {}
        source = location.get("source") or {}
        open_access = item.get("open_access") or {}

        papers.append(
            {
                "id": item.get("id") or "",
                "title": item.get("title") or "Untitled",
                "year": item.get("publication_year"),
                "citations": item.get("cited_by_count") or 0,
                "doi": item.get("doi") or "",
                "authors": authors[:6],
                "abstract": reconstruct_abstract(
                    item.get("abstract_inverted_index")
                ),
                "source_name": source.get("display_name") or "",
                "landing_page": location.get("landing_page_url") or "",
                "is_open_access": bool(open_access.get("is_oa")),
                "oa_url": open_access.get("oa_url") or "",
            }
        )

    return papers


def render_academic_papers(
    query: str,
    papers: list[dict],
    abstract_limit: int = 700,
) -> str:
    if not papers:
        return f"No academic papers found for: {query}"

    lines = [f"Academic papers for: {query}"]
    for index, paper in enumerate(papers, start=1):
        authors = ", ".join(paper["authors"]) or "Authors not listed"
        abstract = paper["abstract"].strip()
        if len(abstract) > abstract_limit:
            abstract = abstract[:abstract_limit].rstrip() + "..."

        lines.append(f"\n[P{index}] {paper['title']}")
        lines.append(
            f"Year: {paper['year'] or 'N/A'} | Citations: {paper['citations']} | "
            f"Open access: {'Yes' if paper['is_open_access'] else 'No'}"
        )
        lines.append(f"Authors: {authors}")
        if paper["source_name"]:
            lines.append(f"Source: {paper['source_name']}")
        if abstract:
            lines.append(f"Abstract: {abstract}")
        if paper["doi"]:
            lines.append(f"DOI: {paper['doi']}")
        if paper["oa_url"]:
            lines.append(f"Open access URL: {paper['oa_url']}")
        elif paper["landing_page"]:
            lines.append(f"URL: {paper['landing_page']}")
        elif paper["id"]:
            lines.append(f"OpenAlex: {paper['id']}")

    return "\n".join(lines)


def search_academic_papers(query: str, max_results: int | None = None) -> str:
    papers = search_academic_papers_data(query, max_results=max_results)
    return render_academic_papers(query, papers)


@function_tool
def academic_search(query: str, max_results: int = 6) -> str:
    """
    Search scholarly literature using OpenAlex.

    Use this for academic papers, literature review, authors, citations,
    publication years, DOI links, research topics, and evidence gathering.
    """
    return search_academic_papers(query, max_results=max_results)


def ensure_knowledge_dir() -> None:
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)


def resolve_knowledge_file(file_name: str) -> Path:
    ensure_knowledge_dir()

    file_name = file_name.strip().strip('"').strip("'")
    if not file_name:
        raise ValueError("File name is empty.")

    root = KNOWLEDGE_DIR.resolve()
    target = (root / file_name).resolve()

    if target != root and root not in target.parents:
        raise ValueError("Access denied: files must stay inside the knowledge folder.")

    if not target.exists() or not target.is_file():
        raise FileNotFoundError(
            f"File not found: {file_name}. Put it inside '{KNOWLEDGE_DIR}'."
        )

    if target.suffix.lower() not in SUPPORTED_FILE_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_FILE_EXTENSIONS))
        raise ValueError(f"Unsupported file type. Supported: {supported}")

    if target.stat().st_size > FILE_MAX_BYTES:
        raise ValueError(
            f"File is too large ({target.stat().st_size / 1024 / 1024:.1f} MB). "
            f"Current limit is {FILE_MAX_BYTES / 1024 / 1024:.1f} MB."
        )

    return target


def extract_file_text(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")

    if suffix == ".pdf":
        reader = PdfReader(str(path))
        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"--- Page {page_number} ---\n{text.strip()}")
        return "\n\n".join(pages)

    if suffix == ".docx":
        document = Document(str(path))
        paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    raise ValueError(f"Unsupported file type: {suffix}")


def list_knowledge_files_text() -> str:
    ensure_knowledge_dir()

    files = sorted(
        path
        for path in KNOWLEDGE_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_FILE_EXTENSIONS
    )

    if not files:
        return (
            f"No supported files found in '{KNOWLEDGE_DIR}'. "
            "Add PDF, TXT, MD, or DOCX files there."
        )

    lines = [f"Files in {KNOWLEDGE_DIR}:"]
    for index, path in enumerate(files, start=1):
        relative = path.relative_to(KNOWLEDGE_DIR)
        size_kb = path.stat().st_size / 1024
        lines.append(f"[{index}] {relative} ({size_kb:.1f} KB)")

    return "\n".join(lines)


@function_tool
def list_local_files() -> str:
    """List supported files in the local knowledge folder."""
    return list_knowledge_files_text()


def read_file_text(file_name: str, max_chars: int | None = None) -> str:
    try:
        path = resolve_knowledge_file(file_name)
        text = extract_file_text(path).strip()
    except (ValueError, FileNotFoundError) as error:
        return str(error)
    except Exception as error:
        return f"Could not read '{file_name}': {error}"

    if not text:
        return (
            f"No extractable text found in '{file_name}'. "
            "Scanned/image-only PDFs may require OCR, which is not enabled yet."
        )

    limit = max_chars or FILE_PREVIEW_CHARS
    if len(text) > limit:
        text = text[:limit].rstrip() + (
            f"\n\n[Preview truncated at {limit} characters. "
            "Use file_search for targeted excerpts.]"
        )

    return f"File: {file_name}\n\n{text}"


@function_tool
def read_local_file(file_name: str) -> str:
    """Read text from a supported file in the local knowledge folder."""
    return read_file_text(file_name)


def chunk_text(text: str, chunk_size: int) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []

    chunks = []
    start = 0
    overlap = min(500, max(100, chunk_size // 7))

    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end]

        if end < len(text):
            split_at = max(chunk.rfind("\n\n"), chunk.rfind(". "))
            if split_at > chunk_size // 2:
                end = start + split_at + (
                    2 if chunk[split_at:split_at + 2] == ". " else 0
                )
                chunk = text[start:end]

        chunks.append(chunk.strip())
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)

    return [chunk for chunk in chunks if chunk]


def query_terms(query: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[\w\-]+", query, flags=re.UNICODE)
        if len(token) >= 2
    }


def search_file_text(file_name: str, query: str, max_chunks: int | None = None) -> str:
    query = query.strip()
    if not query:
        return "Question/search query is empty."

    try:
        path = resolve_knowledge_file(file_name)
        text = extract_file_text(path).strip()
    except (ValueError, FileNotFoundError) as error:
        return str(error)
    except Exception as error:
        return f"Could not read '{file_name}': {error}"

    if not text:
        return (
            f"No extractable text found in '{file_name}'. "
            "Scanned/image-only PDFs may require OCR, which is not enabled yet."
        )

    chunks = chunk_text(text, FILE_CHUNK_CHARS)
    if not chunks:
        return f"No readable text chunks found in '{file_name}'."

    terms = query_terms(query)
    scored = []

    for index, chunk in enumerate(chunks):
        lowered = chunk.lower()
        score = sum(lowered.count(term) for term in terms)
        scored.append((score, index, chunk))

    scored.sort(key=lambda item: (item[0], -item[1]), reverse=True)

    limit = max_chunks or FILE_MAX_CHUNKS
    limit = max(1, min(limit, 6))
    selected = scored[:limit]

    if terms and selected and selected[0][0] == 0:
        selected = [
            (0, index, chunk)
            for index, chunk in enumerate(chunks[:limit])
        ]

    lines = [
        f"Relevant excerpts from: {file_name}",
        f"Question: {query}",
    ]

    for rank, (score, index, chunk) in enumerate(selected, start=1):
        lines.append(
            f"\n--- Excerpt {rank} | chunk {index + 1} | "
            f"keyword score {score} ---\n{chunk}"
        )

    return "\n".join(lines)


@function_tool
def file_search(file_name: str, query: str, max_chunks: int = 4) -> str:
    """Search a local document for excerpts relevant to a question."""
    return search_file_text(file_name, query, max_chunks=max_chunks)


def ensure_research_report_dir() -> None:
    RESEARCH_REPORT_DIR.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    value = re.sub(r"[^\w\-]+", "-", text.lower(), flags=re.UNICODE)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value[:70] or "research"


def list_research_reports_text() -> str:
    ensure_research_report_dir()
    reports = sorted(
        RESEARCH_REPORT_DIR.glob("*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not reports:
        return f"No research reports found in '{RESEARCH_REPORT_DIR}'."

    lines = [f"Research reports in {RESEARCH_REPORT_DIR}:"]
    for index, path in enumerate(reports, start=1):
        stamp = datetime.fromtimestamp(path.stat().st_mtime).strftime(
            "%Y-%m-%d %H:%M"
        )
        lines.append(f"[{index}] {path.name} ({stamp})")

    return "\n".join(lines)


def read_research_report(file_name: str) -> str:
    ensure_research_report_dir()
    root = RESEARCH_REPORT_DIR.resolve()
    target = (root / file_name.strip()).resolve()

    if target != root and root not in target.parents:
        return "Access denied: report must stay inside the research report folder."

    if not target.exists() or not target.is_file() or target.suffix.lower() != ".md":
        return f"Research report not found: {file_name}"

    return target.read_text(encoding="utf-8", errors="replace")


def build_research_source_bundle(topic: str) -> tuple[str, list[dict], list[dict]]:
    papers = search_academic_papers_data(
        topic,
        max_results=ACADEMIC_SEARCH_MAX_RESULTS,
    )
    web_results = search_web_data(
        topic,
        max_results=WEB_SEARCH_MAX_RESULTS,
    )

    academic_text = render_academic_papers(
        topic,
        papers,
        abstract_limit=650,
    )

    if web_results:
        web_lines = [f"Web evidence for: {topic}"]
        for index, item in enumerate(web_results, start=1):
            title = (item.get("title") or "Untitled").strip()
            body = (item.get("body") or "").strip()
            url = (item.get("href") or "").strip()
            web_lines.append(f"\n[W{index}] {title}")
            if body:
                web_lines.append(body[:700])
            if url:
                web_lines.append(f"Source: {url}")
        web_text = "\n".join(web_lines)
    else:
        web_text = f"No web results found for: {topic}"

    bundle = (
        "=== ACADEMIC EVIDENCE ===\n"
        f"{academic_text}\n\n"
        "=== WEB EVIDENCE ===\n"
        f"{web_text}"
    )
    return bundle, papers, web_results


def research_source_appendix(
    papers: list[dict],
    web_results: list[dict],
) -> str:
    lines = ["\n\n## Machine-collected source appendix"]

    if papers:
        lines.append("\n### Academic papers")
        for index, paper in enumerate(papers, start=1):
            link = (
                paper["doi"]
                or paper["oa_url"]
                or paper["landing_page"]
                or paper["id"]
            )
            lines.append(
                f"- [P{index}] {paper['title']} "
                f"({paper['year'] or 'N/A'}) — {link}"
            )

    if web_results:
        lines.append("\n### Web sources")
        for index, item in enumerate(web_results, start=1):
            title = (item.get("title") or "Untitled").strip()
            url = (item.get("href") or "").strip()
            lines.append(f"- [W{index}] {title} — {url}")

    return "\n".join(lines)


async def create_research_report(
    agent: Agent,
    topic: str,
) -> tuple[str, Path | None]:
    topic = topic.strip()
    if not topic:
        return "Research topic is empty.", None

    evidence, papers, web_results = await asyncio.to_thread(
        build_research_source_bundle,
        topic,
    )

    prompt = f"""
Act as a careful academic research assistant.

Create a concise Markdown research planning report for this topic:

{topic}

Use ONLY the evidence bundle below for factual claims. Cite factual claims
with the supplied markers such as [P1] or [W1]. If evidence is weak or
missing, say so. Never invent paper findings, authors, datasets, or citations.

Required sections:
# Research Report: <topic>
## Executive Summary
## Key Findings from Existing Literature
## Literature Snapshot
## Potential Research Gaps
## Candidate Research Questions
## Methodology Options
## Possible Data / Dataset Sources
## Risks and Limitations
## Practical Next Steps
## Sources Used

Important:
- Research gaps should be framed as candidate gaps to validate, not proven gaps.
- Distinguish evidence from your proposed research ideas.
- Keep the report useful for a student planning a real paper.

EVIDENCE BUNDLE:
{evidence}
""".strip()

    try:
        result = await asyncio.wait_for(
            Runner.run(agent, prompt),
            timeout=RESEARCH_TIMEOUT_SECONDS,
        )
        report_text = str(result.final_output).strip()
    except asyncio.TimeoutError:
        report_text = (
            f"# Research Evidence Bundle: {topic}\n\n"
            "The local model timed out while synthesizing the report. "
            "The collected evidence is preserved below so you can retry.\n\n"
            f"{evidence}"
        )
    except Exception as error:
        report_text = (
            f"# Research Evidence Bundle: {topic}\n\n"
            f"Report synthesis failed: {error}\n\n{evidence}"
        )

    report_text += research_source_appendix(papers, web_results)

    ensure_research_report_dir()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = RESEARCH_REPORT_DIR / f"{slugify(topic)}-{timestamp}.md"
    report_path.write_text(report_text, encoding="utf-8")

    return report_text, report_path



def normalize_github_repo(repo_name: str = "") -> str:
    value = (repo_name or "").strip().strip("/")

    if not value:
        return f"{GITHUB_OWNER}/{GITHUB_DEFAULT_REPO}"

    if value.startswith("https://github.com/"):
        value = value[len("https://github.com/"):].strip("/")

    if value.endswith(".git"):
        value = value[:-4]

    parts = [part for part in value.split("/") if part]
    if len(parts) == 1:
        return f"{GITHUB_OWNER}/{parts[0]}"
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"

    return f"{GITHUB_OWNER}/{GITHUB_DEFAULT_REPO}"


def github_api_request(endpoint: str, params: dict | None = None):
    url = f"{GITHUB_API_BASE}{endpoint}"

    if params:
        query = urllib.parse.urlencode(
            {key: value for key, value in params.items() if value is not None}
        )
        if query:
            url = f"{url}?{query}"

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Masum-AI-Agent/1.5",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=GITHUB_TIMEOUT) as response:
            return json.load(response), None
    except urllib.error.HTTPError as error:
        try:
            body = json.loads(error.read().decode("utf-8", errors="replace"))
            message = body.get("message") or str(error)
        except Exception:
            message = str(error)

        if error.code == 403 and "rate limit" in message.lower():
            message += (
                " Public GitHub API rate limit may be exhausted. "
                "Wait for reset or optionally configure a GitHub token locally."
            )
        return None, f"GitHub API error {error.code}: {message}"
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return None, f"GitHub request failed: {error}"


def github_repo_summary_text(repo_name: str = "") -> str:
    repo = normalize_github_repo(repo_name)
    data, error = github_api_request(f"/repos/{repo}")
    if error:
        return error

    owner = (data.get("owner") or {}).get("login") or "Unknown"
    license_name = ((data.get("license") or {}).get("spdx_id")) or "Not specified"

    return "\n".join(
        [
            f"GitHub repository: {data.get('full_name') or repo}",
            f"Description: {data.get('description') or 'No description'}",
            f"Owner: {owner}",
            f"Visibility: {'Private' if data.get('private') else 'Public'}",
            f"Default branch: {data.get('default_branch') or 'N/A'}",
            f"Language: {data.get('language') or 'Not detected'}",
            f"Stars: {data.get('stargazers_count', 0)}",
            f"Forks: {data.get('forks_count', 0)}",
            f"Open issues: {data.get('open_issues_count', 0)}",
            f"License: {license_name}",
            f"Created: {data.get('created_at') or 'N/A'}",
            f"Updated: {data.get('updated_at') or 'N/A'}",
            f"URL: {data.get('html_url') or f'https://github.com/{repo}'}",
        ]
    )


@function_tool
def github_repo_info(repo_name: str = "") -> str:
    """Get read-only metadata for a public GitHub repository."""
    return github_repo_summary_text(repo_name)


def github_list_files_text(repo_name: str = "", path: str = "", ref: str = "") -> str:
    repo = normalize_github_repo(repo_name)
    clean_path = path.strip().strip("/")
    encoded_path = urllib.parse.quote(clean_path, safe="/")
    endpoint = f"/repos/{repo}/contents"
    if encoded_path:
        endpoint += f"/{encoded_path}"

    data, error = github_api_request(endpoint, {"ref": ref.strip() or None})
    if error:
        return error

    if isinstance(data, dict) and data.get("type") == "file":
        return (
            f"{repo}/{clean_path} is a file, not a directory. "
            "Use github_read_file to read it."
        )

    if not isinstance(data, list):
        return f"Unexpected GitHub contents response for {repo}/{clean_path}"

    location = clean_path or "/"
    lines = [f"Files in {repo}:{location}"]
    for item in data[:50]:
        item_type = item.get("type") or "unknown"
        item_path = item.get("path") or item.get("name") or "unknown"
        size = item.get("size")
        suffix = f" ({size} bytes)" if item_type == "file" and size is not None else ""
        lines.append(f"- [{item_type}] {item_path}{suffix}")

    if len(data) > 50:
        lines.append(f"... {len(data) - 50} more entries not shown")

    return "\n".join(lines)


@function_tool
def github_list_files(repo_name: str = "", path: str = "", ref: str = "") -> str:
    """List files/directories from a public GitHub repository."""
    return github_list_files_text(repo_name, path, ref)


def github_read_file_text(repo_name: str, path: str, ref: str = "") -> str:
    repo = normalize_github_repo(repo_name)
    clean_path = path.strip().strip("/")
    if not clean_path:
        return "GitHub file path is empty."

    encoded_path = urllib.parse.quote(clean_path, safe="/")
    data, error = github_api_request(
        f"/repos/{repo}/contents/{encoded_path}",
        {"ref": ref.strip() or None},
    )
    if error:
        return error

    if not isinstance(data, dict) or data.get("type") != "file":
        return f"Not a readable file: {repo}/{clean_path}"

    encoding = data.get("encoding")
    content = data.get("content") or ""

    if encoding == "base64":
        try:
            raw = base64.b64decode(content)
            text = raw.decode("utf-8", errors="replace")
        except Exception as error:
            return f"Could not decode GitHub file: {error}"
    else:
        text = str(content)

    if len(text) > GITHUB_FILE_PREVIEW_CHARS:
        text = text[:GITHUB_FILE_PREVIEW_CHARS].rstrip() + (
            f"\n\n[Preview truncated at {GITHUB_FILE_PREVIEW_CHARS} characters.]"
        )

    return (
        f"GitHub file: {repo}/{clean_path}\n"
        f"URL: {data.get('html_url') or ''}\n\n{text}"
    )


@function_tool
def github_read_file(repo_name: str, path: str, ref: str = "") -> str:
    """Read a text-like file from a public GitHub repository."""
    return github_read_file_text(repo_name, path, ref)


def github_recent_commits_text(repo_name: str = "", max_items: int | None = None) -> str:
    repo = normalize_github_repo(repo_name)
    limit = max_items or GITHUB_MAX_ITEMS
    limit = max(1, min(limit, 20))

    data, error = github_api_request(f"/repos/{repo}/commits", {"per_page": limit})
    if error:
        return error

    if not isinstance(data, list) or not data:
        return f"No commits found for {repo}."

    lines = [f"Recent commits for {repo}:"]
    for index, item in enumerate(data, start=1):
        commit = item.get("commit") or {}
        author = commit.get("author") or {}
        message = (commit.get("message") or "").splitlines()[0]
        sha = (item.get("sha") or "")[:7]
        lines.append(
            f"[{index}] {sha} | {author.get('date') or 'N/A'} | "
            f"{author.get('name') or 'Unknown'} | {message}"
        )

    return "\n".join(lines)


@function_tool
def github_recent_commits(repo_name: str = "", max_items: int = 8) -> str:
    """List recent commits from a public GitHub repository."""
    return github_recent_commits_text(repo_name, max_items)


def github_open_issues_text(repo_name: str = "", max_items: int | None = None) -> str:
    repo = normalize_github_repo(repo_name)
    limit = max_items or GITHUB_MAX_ITEMS
    limit = max(1, min(limit, 20))

    data, error = github_api_request(
        f"/repos/{repo}/issues",
        {"state": "open", "per_page": min(limit * 2, 40)},
    )
    if error:
        return error

    if not isinstance(data, list):
        return f"Unexpected GitHub issues response for {repo}."

    issues = [item for item in data if "pull_request" not in item][:limit]
    if not issues:
        return f"No open issues found for {repo}."

    lines = [f"Open issues for {repo}:"]
    for item in issues:
        labels = ", ".join(label.get("name", "") for label in item.get("labels", []))
        suffix = f" | labels: {labels}" if labels else ""
        lines.append(
            f"#{item.get('number')} | {item.get('title') or 'Untitled'}"
            f"{suffix}\n  {item.get('html_url') or ''}"
        )

    return "\n".join(lines)


@function_tool
def github_open_issues(repo_name: str = "", max_items: int = 8) -> str:
    """List open issues from a public GitHub repository."""
    return github_open_issues_text(repo_name, max_items)


def github_owner_repos_text(owner: str = "") -> str:
    target_owner = owner.strip() or GITHUB_OWNER
    data, error = github_api_request(
        f"/users/{urllib.parse.quote(target_owner)}/repos",
        {
            "sort": "updated",
            "direction": "desc",
            "per_page": min(max(GITHUB_MAX_ITEMS, 1), 20),
        },
    )
    if error:
        return error

    if not isinstance(data, list) or not data:
        return f"No public repositories found for {target_owner}."

    lines = [f"Recent public repositories for {target_owner}:"]
    for index, item in enumerate(data, start=1):
        lines.append(
            f"[{index}] {item.get('name')} | "
            f"{item.get('language') or 'N/A'} | ⭐ {item.get('stargazers_count', 0)} | "
            f"{item.get('html_url') or ''}"
        )

    return "\n".join(lines)


@function_tool
def github_owner_repos(owner: str = "") -> str:
    """List recently updated public repositories for a GitHub user."""
    return github_owner_repos_text(owner)


def build_github_analysis_bundle(repo_name: str = "") -> str:
    repo = normalize_github_repo(repo_name)
    sections = [
        github_repo_summary_text(repo),
        github_list_files_text(repo),
        github_recent_commits_text(repo, max_items=6),
        github_open_issues_text(repo, max_items=6),
    ]
    return "\n\n=== NEXT SECTION ===\n\n".join(sections)


async def analyze_github_repo(agent: Agent, repo_name: str = "") -> str:
    repo = normalize_github_repo(repo_name)
    bundle = await asyncio.to_thread(build_github_analysis_bundle, repo)

    prompt = f"""
Act as a careful software repository reviewer.

Review this GitHub repository snapshot:

{repo}

Using ONLY the repository data below, produce a concise assessment with:
## Repository Snapshot
## What Looks Good
## Potential Problems / Risks
## Next 5 Recommended Actions

Do not invent files, issues, commits, tests, or CI status that are not shown.
If the evidence is insufficient for a claim, say so.

REPOSITORY DATA:
{bundle}
""".strip()

    try:
        result = await asyncio.wait_for(
            Runner.run(agent, prompt),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
        return str(result.final_output)
    except asyncio.TimeoutError:
        return (
            "GitHub analysis timed out in the local model. "
            "Raw repository snapshot:\n\n" + bundle
        )
    except Exception as error:
        return f"GitHub analysis failed: {error}\n\n{bundle}"



def save_gmail_token(creds: Credentials) -> None:
    GMAIL_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    GMAIL_TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")


def load_gmail_credentials(interactive: bool = False) -> Credentials:
    creds = None

    if GMAIL_TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                str(GMAIL_TOKEN_PATH),
                GMAIL_SCOPES,
            )
        except Exception as error:
            raise RuntimeError(
                f"Could not read Gmail token: {error}. "
                "Delete the local token and run /gmail-auth again."
            ) from error

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(GoogleAuthRequest())
            save_gmail_token(creds)
        except Exception as error:
            if not interactive:
                raise RuntimeError(
                    "Gmail authorization expired or was revoked. "
                    "Run /gmail-auth again."
                ) from error
            creds = None

    if creds and creds.valid:
        return creds

    if not interactive:
        raise RuntimeError(
            "Gmail is not authorized yet. Run /gmail-auth first."
        )

    if not GMAIL_CREDENTIALS_PATH.exists():
        raise RuntimeError(
            f"Gmail OAuth client file not found: {GMAIL_CREDENTIALS_PATH}. "
            "Download a Desktop app OAuth client JSON from Google Cloud "
            "and save it at that path."
        )

    GMAIL_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(GMAIL_CREDENTIALS_PATH),
            GMAIL_SCOPES,
        )
        creds = flow.run_local_server(port=0)
        save_gmail_token(creds)
        return creds
    except Exception as error:
        raise RuntimeError(f"Gmail OAuth failed: {error}") from error


def gmail_service(interactive: bool = False):
    creds = load_gmail_credentials(interactive=interactive)
    return google_api_build(
        "gmail",
        "v1",
        credentials=creds,
        cache_discovery=False,
    )


def gmail_status_text() -> str:
    lines = [
        "Gmail Agent: read-only",
        f"Credentials file: {GMAIL_CREDENTIALS_PATH}",
        f"Token file: {GMAIL_TOKEN_PATH}",
        f"OAuth scope: {GMAIL_SCOPES[0]}",
    ]

    if not GMAIL_CREDENTIALS_PATH.exists():
        lines.append("OAuth client: missing")
    else:
        lines.append("OAuth client: found")

    try:
        creds = load_gmail_credentials(interactive=False)
        lines.append(f"Authorized: {'Yes' if creds.valid else 'No'}")
    except RuntimeError as error:
        lines.append("Authorized: No")
        lines.append(f"Status: {error}")

    return "\n".join(lines)


def gmail_header(payload: dict, name: str) -> str:
    for header in payload.get("headers", []):
        if (header.get("name") or "").lower() == name.lower():
            return header.get("value") or ""
    return ""


def decode_gmail_body_data(data: str) -> str:
    if not data:
        return ""

    padding = "=" * (-len(data) % 4)
    try:
        raw = base64.urlsafe_b64decode(data + padding)
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def html_to_plain_text(value: str) -> str:
    value = re.sub(
        r"(?is)<(script|style).*?>.*?</\1>",
        " ",
        value,
    )
    value = re.sub(r"(?i)<br\s*/?>", "\n", value)
    value = re.sub(r"(?i)</p\s*>", "\n\n", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = html_lib.unescape(value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def extract_gmail_body(payload: dict) -> str:
    plain_parts = []
    html_parts = []

    def walk(part: dict) -> None:
        mime_type = (part.get("mimeType") or "").lower()
        body_data = (part.get("body") or {}).get("data") or ""

        if body_data:
            decoded = decode_gmail_body_data(body_data)
            if mime_type == "text/plain":
                plain_parts.append(decoded)
            elif mime_type == "text/html":
                html_parts.append(decoded)

        for child in part.get("parts") or []:
            walk(child)

    walk(payload)

    if plain_parts:
        return "\n\n".join(part.strip() for part in plain_parts if part.strip()).strip()

    if html_parts:
        return html_to_plain_text(
            "\n\n".join(part for part in html_parts if part.strip())
        )

    body_data = (payload.get("body") or {}).get("data") or ""
    return decode_gmail_body_data(body_data).strip()


def gmail_message_metadata(message: dict) -> dict:
    payload = message.get("payload") or {}
    return {
        "id": message.get("id") or "",
        "thread_id": message.get("threadId") or "",
        "from": gmail_header(payload, "From"),
        "to": gmail_header(payload, "To"),
        "subject": gmail_header(payload, "Subject") or "(No subject)",
        "date": gmail_header(payload, "Date"),
        "snippet": message.get("snippet") or "",
        "labels": message.get("labelIds") or [],
    }


def gmail_list_messages_data(
    query: str = "in:inbox",
    max_results: int | None = None,
) -> list[dict]:
    limit = max_results or GMAIL_MAX_RESULTS
    limit = max(1, min(limit, 25))

    try:
        service = gmail_service(interactive=False)
        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query.strip() or None,
                maxResults=limit,
            )
            .execute()
        )

        messages = response.get("messages", [])
        results = []

        for item in messages:
            full = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=item["id"],
                    format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"],
                )
                .execute()
            )
            results.append(gmail_message_metadata(full))

        return results
    except HttpError as error:
        raise RuntimeError(f"Gmail API error: {error}") from error


def render_gmail_messages(
    messages: list[dict],
    title: str,
) -> str:
    if not messages:
        return f"{title}\nNo matching messages found."

    lines = [title]
    for index, item in enumerate(messages, start=1):
        unread = "UNREAD" if "UNREAD" in item["labels"] else "read"
        lines.append(
            f"\n[G{index}] ID: {item['id']}\n"
            f"From: {item['from'] or 'Unknown'}\n"
            f"Subject: {item['subject']}\n"
            f"Date: {item['date'] or 'N/A'}\n"
            f"State: {unread}\n"
            f"Snippet: {item['snippet']}"
        )

    return "\n".join(lines)


def gmail_inbox_text(max_results: int | None = None) -> str:
    try:
        messages = gmail_list_messages_data(
            "in:inbox",
            max_results=max_results,
        )
        return render_gmail_messages(messages, "Recent Gmail inbox messages:")
    except RuntimeError as error:
        return str(error)


@function_tool
def gmail_inbox(max_results: int = 8) -> str:
    """List recent Gmail inbox messages using read-only access."""
    return gmail_inbox_text(max_results)


def gmail_search_text(
    query: str,
    max_results: int | None = None,
) -> str:
    query = query.strip()
    if not query:
        return "Gmail search query is empty."

    try:
        messages = gmail_list_messages_data(
            query,
            max_results=max_results,
        )
        return render_gmail_messages(
            messages,
            f"Gmail search results for: {query}",
        )
    except RuntimeError as error:
        return str(error)


@function_tool
def gmail_search(query: str, max_results: int = 8) -> str:
    """
    Search Gmail using the same query syntax as the Gmail search box.

    Examples: is:unread, from:example@example.com, newer_than:7d.
    This tool is read-only.
    """
    return gmail_search_text(query, max_results)


def gmail_read_message_text(message_id: str) -> str:
    message_id = message_id.strip()
    if not message_id:
        return "Gmail message ID is empty."

    try:
        service = gmail_service(interactive=False)
        message = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="full",
            )
            .execute()
        )
    except HttpError as error:
        return f"Gmail API error: {error}"
    except RuntimeError as error:
        return str(error)

    meta = gmail_message_metadata(message)
    body = extract_gmail_body(message.get("payload") or {})

    if not body:
        body = meta["snippet"] or "[No readable text body found]"

    if len(body) > GMAIL_BODY_PREVIEW_CHARS:
        body = body[:GMAIL_BODY_PREVIEW_CHARS].rstrip() + (
            f"\n\n[Body truncated at {GMAIL_BODY_PREVIEW_CHARS} characters.]"
        )

    return (
        f"Gmail message ID: {meta['id']}\n"
        f"Thread ID: {meta['thread_id']}\n"
        f"From: {meta['from'] or 'Unknown'}\n"
        f"To: {meta['to'] or 'Unknown'}\n"
        f"Subject: {meta['subject']}\n"
        f"Date: {meta['date'] or 'N/A'}\n\n"
        f"{body}"
    )


@function_tool
def gmail_read_message(message_id: str) -> str:
    """Read one Gmail message by message ID. Read-only."""
    return gmail_read_message_text(message_id)


async def gmail_summary_text(
    agent: Agent,
    query: str = "in:inbox newer_than:7d",
    max_results: int | None = None,
) -> str:
    try:
        messages = await asyncio.to_thread(
            gmail_list_messages_data,
            query,
            max_results or GMAIL_MAX_RESULTS,
        )
    except RuntimeError as error:
        return str(error)

    if not messages:
        return f"No Gmail messages found for: {query}"

    evidence = render_gmail_messages(
        messages,
        f"Gmail messages for summary: {query}",
    )

    prompt = f"""
Summarize the Gmail message metadata/snippets below.

Rules:
- Do not invent message content.
- Separate urgent/action-needed items from informational messages.
- Mention sender, subject, and useful dates when available.
- If the snippets are insufficient, say so.
- Reply mainly in Bangla.

EMAIL DATA:
{evidence}
""".strip()

    try:
        result = await asyncio.wait_for(
            Runner.run(agent, prompt),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
        return str(result.final_output)
    except asyncio.TimeoutError:
        return "Gmail summary timed out.\n\n" + evidence
    except Exception as error:
        return f"Gmail summary failed: {error}\n\n{evidence}"



def supabase_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY)


def validate_db_identifier(value: str, label: str = "identifier") -> str:
    value = value.strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(
            f"Invalid database {label}: {value!r}. "
            "Use only letters, numbers, and underscores."
        )
    return value


def ensure_allowed_table(table_name: str) -> str:
    table = validate_db_identifier(table_name, "table")
    if SUPABASE_ALLOWED_TABLES and table not in SUPABASE_ALLOWED_TABLES:
        allowed = ", ".join(sorted(SUPABASE_ALLOWED_TABLES))
        raise ValueError(
            f"Table '{table}' is not in SUPABASE_ALLOWED_TABLES. "
            f"Allowed tables: {allowed}"
        )
    return table


def supabase_headers() -> dict:
    if not supabase_configured():
        raise RuntimeError(
            "Supabase is not configured. Add SUPABASE_URL and "
            "SUPABASE_ANON_KEY to your local .env file."
        )

    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Accept": "application/json",
        "Accept-Profile": SUPABASE_SCHEMA,
        "Content-Profile": SUPABASE_SCHEMA,
        "User-Agent": "Masum-AI-Agent/1.7",
    }


def supabase_get(
    endpoint: str,
    params: dict | None = None,
):
    url = f"{SUPABASE_URL}/rest/v1{endpoint}"

    if params:
        query = urllib.parse.urlencode(
            {key: value for key, value in params.items() if value is not None}
        )
        if query:
            url = f"{url}?{query}"

    try:
        request = urllib.request.Request(
            url,
            headers=supabase_headers(),
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=SUPABASE_TIMEOUT) as response:
            body = response.read().decode("utf-8", errors="replace")
            if not body:
                return None, None
            return json.loads(body), None
    except ValueError as error:
        return None, str(error)
    except RuntimeError as error:
        return None, str(error)
    except urllib.error.HTTPError as error:
        try:
            body = json.loads(error.read().decode("utf-8", errors="replace"))
            message = (
                body.get("message")
                or body.get("hint")
                or body.get("details")
                or str(error)
            )
        except Exception:
            message = str(error)

        if error.code in {401, 403}:
            message += (
                " Check the anon key and Supabase Row Level Security policies."
            )

        return None, f"Supabase REST error {error.code}: {message}"
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return None, f"Supabase request failed: {error}"
    except json.JSONDecodeError as error:
        return None, f"Supabase returned invalid JSON: {error}"


def supabase_status_text() -> str:
    lines = [
        "Supabase Agent: read-only",
        f"Configured: {'Yes' if supabase_configured() else 'No'}",
        f"Schema: {SUPABASE_SCHEMA}",
        f"Default max rows: {SUPABASE_MAX_ROWS}",
    ]

    if SUPABASE_URL:
        project_host = urllib.parse.urlparse(SUPABASE_URL).netloc or SUPABASE_URL
        lines.append(f"Project host: {project_host}")
    else:
        lines.append("Project host: not configured")

    if SUPABASE_ALLOWED_TABLES:
        lines.append(
            "Allowed tables: " + ", ".join(sorted(SUPABASE_ALLOWED_TABLES))
        )
    else:
        lines.append(
            "Allowed tables: all tables permitted by the anon key and RLS"
        )

    if not supabase_configured():
        lines.append(
            "Status: add SUPABASE_URL and SUPABASE_ANON_KEY to .env"
        )
        return "\n".join(lines)

    _, error = supabase_get("/")
    if error:
        lines.append(f"Connection: failed — {error}")
    else:
        lines.append("Connection: OK")

    return "\n".join(lines)


def supabase_tables_text() -> str:
    if not supabase_configured():
        return (
            "Supabase is not configured. Add SUPABASE_URL and "
            "SUPABASE_ANON_KEY to .env."
        )

    data, error = supabase_get("/")
    if error:
        return error

    tables = set()

    if isinstance(data, dict):
        for path in (data.get("paths") or {}):
            name = path.strip("/")
            if name and "/" not in name:
                tables.add(name)

        for name in (data.get("definitions") or {}):
            if name:
                tables.add(name)

    if SUPABASE_ALLOWED_TABLES:
        tables = {table for table in tables if table in SUPABASE_ALLOWED_TABLES}

    if not tables:
        return (
            "No accessible tables were discovered. This can happen when "
            "the REST schema is hidden or RLS/API exposure blocks access."
        )

    lines = [f"Accessible Supabase tables in schema '{SUPABASE_SCHEMA}':"]
    for index, table in enumerate(sorted(tables), start=1):
        lines.append(f"[{index}] {table}")

    return "\n".join(lines)


@function_tool
def supabase_tables() -> str:
    """List Supabase tables visible through the read-only REST API."""
    return supabase_tables_text()


def supabase_read_rows_data(
    table_name: str,
    limit: int | None = None,
) -> tuple[list[dict] | None, str | None]:
    try:
        table = ensure_allowed_table(table_name)
    except ValueError as error:
        return None, str(error)

    row_limit = limit or SUPABASE_MAX_ROWS
    row_limit = max(1, min(row_limit, 100))

    data, error = supabase_get(
        f"/{urllib.parse.quote(table)}",
        {
            "select": "*",
            "limit": row_limit,
        },
    )
    if error:
        return None, error

    if not isinstance(data, list):
        return None, f"Unexpected Supabase response for table '{table}'."

    return data, None


def format_supabase_rows(
    table_name: str,
    rows: list[dict],
    heading: str | None = None,
) -> str:
    if not rows:
        return heading or f"No visible rows found in '{table_name}'."

    title = heading or f"Rows from Supabase table '{table_name}':"
    payload = json.dumps(
        rows,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    if len(payload) > SUPABASE_PREVIEW_CHARS:
        payload = payload[:SUPABASE_PREVIEW_CHARS].rstrip() + (
            f"\n\n[Preview truncated at {SUPABASE_PREVIEW_CHARS} characters.]"
        )

    return f"{title}\n{payload}"


def supabase_read_table_text(
    table_name: str,
    limit: int | None = None,
) -> str:
    rows, error = supabase_read_rows_data(table_name, limit)
    if error:
        return error
    return format_supabase_rows(table_name, rows or [])


@function_tool
def supabase_read_table(table_name: str, limit: int = 20) -> str:
    """
    Read rows from a Supabase table using the anon key and current RLS policies.

    This tool is strictly read-only.
    """
    return supabase_read_table_text(table_name, limit)


def supabase_filter_rows_text(
    table_name: str,
    column_name: str,
    value: str,
    limit: int | None = None,
) -> str:
    try:
        table = ensure_allowed_table(table_name)
        column = validate_db_identifier(column_name, "column")
    except ValueError as error:
        return str(error)

    row_limit = limit or SUPABASE_MAX_ROWS
    row_limit = max(1, min(row_limit, 100))

    data, error = supabase_get(
        f"/{urllib.parse.quote(table)}",
        {
            "select": "*",
            column: f"eq.{value}",
            "limit": row_limit,
        },
    )
    if error:
        return error

    if not isinstance(data, list):
        return f"Unexpected Supabase response for table '{table}'."

    return format_supabase_rows(
        table,
        data,
        heading=(
            f"Rows from '{table}' where {column} == {value!r}:"
            if data
            else f"No visible rows in '{table}' where {column} == {value!r}."
        ),
    )


@function_tool
def supabase_filter_rows(
    table_name: str,
    column_name: str,
    value: str,
    limit: int = 20,
) -> str:
    """Filter a Supabase table by one equality condition. Read-only."""
    return supabase_filter_rows_text(
        table_name,
        column_name,
        value,
        limit,
    )


async def supabase_analyze_table_text(
    agent: Agent,
    table_name: str,
    limit: int | None = None,
) -> str:
    rows, error = await asyncio.to_thread(
        supabase_read_rows_data,
        table_name,
        limit,
    )
    if error:
        return error

    if not rows:
        return f"No visible rows found in '{table_name}'."

    evidence = json.dumps(
        rows,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    if len(evidence) > SUPABASE_PREVIEW_CHARS:
        evidence = evidence[:SUPABASE_PREVIEW_CHARS]

    prompt = f"""
Analyze the following Supabase rows from table '{table_name}'.

Rules:
- Use ONLY the supplied rows.
- Do not invent missing fields or database schema.
- Mention that the sample may be incomplete.
- Identify useful patterns, counts, missing values, or anomalies only when
  visible from the supplied rows.
- Reply mainly in Bangla.

ROWS:
{evidence}
""".strip()

    try:
        result = await asyncio.wait_for(
            Runner.run(agent, prompt),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
        return str(result.final_output)
    except asyncio.TimeoutError:
        return (
            "Database analysis timed out in the local model.\n\n"
            + format_supabase_rows(table_name, rows)
        )
    except Exception as error:
        return (
            f"Database analysis failed: {error}\n\n"
            + format_supabase_rows(table_name, rows)
        )


INSTRUCTIONS = """
You are Masum AI Agent, a modular personal AI assistant.

Core responsibilities:
- Help with programming and software development.
- Help with AI, machine learning, and research.
- Explain technical topics clearly and practically.
- Use available tools when they are useful.
- Never claim that a tool was used unless it was actually used.
- Respond mainly in Bangla when the user speaks Bangla.
- Keep useful English technical terms where they improve clarity.
- Use conversation memory naturally when it is relevant.
- For current, latest, recent, changing, or web-specific information, use web_search.
- When using web_search, mention useful source URLs in the final answer.
- Do not invent search results or sources.
- For scholarly literature, use academic_search.
- Treat possible research gaps as hypotheses to verify, not established facts.
- For questions about local documents, use list_local_files, read_local_file, or file_search.
- Only claim facts about a local file when supported by text returned from a file tool.
- For GitHub repository questions, use the GitHub read-only tools.
- Never claim to have changed a GitHub repository; GitHub tools are read-only.
- Gmail access is read-only. Use Gmail tools only to list, search, or read messages.
- Never claim to send, delete, archive, label, or modify email.
- Supabase/database access is read-only. Use database tools only for listing,
  reading, filtering, or analyzing visible rows.
- Never claim to insert, update, delete, or alter database data or schema.
"""

LOCAL_FAST_INSTRUCTIONS = INSTRUCTIONS + """
- You are running on a small local model. Prefer short, direct answers.
- For simple tool requests, call the required tool immediately without lengthy reasoning.
- If the user asks for the current date or time, call get_current_time immediately.
- If the user asks to search the web or asks for latest/recent information, call web_search immediately.
- If the user asks for academic papers or literature, call academic_search immediately.
- If the user asks what files are available, call list_local_files immediately.
- If the user asks about a named local document, prefer file_search with the user's question.
- If the user asks about a GitHub repository, use the relevant GitHub tool immediately.
- If the user asks about Gmail, use the relevant Gmail read-only tool immediately.
- If the user asks about Supabase or database data, use the relevant read-only database tool immediately.
/no_think
"""


def check_ollama(model_name: str) -> None:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=4) as response:
            data = json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise RuntimeError(
            "Ollama is not reachable. Install/start Ollama first, then run "
            f"'ollama pull {model_name}'. Expected server: {host}"
        ) from error

    installed_models = {
        item.get("name") or item.get("model")
        for item in data.get("models", [])
        if item.get("name") or item.get("model")
    }

    if model_name not in installed_models:
        raise RuntimeError(
            f"Local model '{model_name}' is not installed. "
            f"Run: ollama pull {model_name}"
        )


def build_agent() -> tuple[Agent, dict[str, Agent], str, str]:
    provider = os.getenv("AI_PROVIDER", "ollama").strip().lower()

    general_tools = [
        get_current_time,
        web_search,
        academic_search,
        list_local_files,
        read_local_file,
        file_search,
        github_repo_info,
        github_list_files,
        github_read_file,
        github_recent_commits,
        github_open_issues,
        github_owner_repos,
        gmail_inbox,
        gmail_search,
        gmail_read_message,
        supabase_tables,
        supabase_read_table,
        supabase_filter_rows,
    ]

    research_tools = [
        get_current_time,
        web_search,
        academic_search,
        list_local_files,
        read_local_file,
        file_search,
    ]

    developer_tools = [
        get_current_time,
        web_search,
        list_local_files,
        read_local_file,
        file_search,
        github_repo_info,
        github_list_files,
        github_read_file,
        github_recent_commits,
        github_open_issues,
        github_owner_repos,
    ]

    gmail_tools = [
        get_current_time,
        gmail_inbox,
        gmail_search,
        gmail_read_message,
    ]

    data_tools = [
        get_current_time,
        supabase_tables,
        supabase_read_table,
        supabase_filter_rows,
    ]

    if provider == "ollama":
        model_name = os.getenv("OLLAMA_MODEL", "qwen3:1.7b").strip()
        base_url = os.getenv(
            "OLLAMA_BASE_URL",
            "http://localhost:11434/v1",
        ).rstrip("/")

        check_ollama(model_name)
        set_tracing_disabled(True)

        local_client = AsyncOpenAI(base_url=base_url, api_key="ollama")
        shared_model = OpenAIChatCompletionsModel(
            model=model_name,
            openai_client=local_client,
        )

        def make_agent(
            name: str,
            instructions: str,
            tools: list,
        ) -> Agent:
            return Agent(
                name=name,
                instructions=instructions + "\n/no_think",
                model=shared_model,
                tools=tools,
            )

        general = make_agent(
            "Masum AI Coordinator",
            LOCAL_FAST_INSTRUCTIONS,
            general_tools,
        )

    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or "your_openai_api_key_here" in api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is missing or still contains the placeholder value."
            )

        model_name = os.getenv("OPENAI_MODEL", "").strip()

        def make_agent(
            name: str,
            instructions: str,
            tools: list,
        ) -> Agent:
            kwargs = {
                "name": name,
                "instructions": instructions,
                "tools": tools,
            }
            if model_name:
                kwargs["model"] = model_name
            return Agent(**kwargs)

        general = make_agent(
            "Masum AI Coordinator",
            INSTRUCTIONS,
            general_tools,
        )

    else:
        raise RuntimeError(
            f"Unsupported AI_PROVIDER='{provider}'. Use 'ollama' or 'openai'."
        )

    research = make_agent(
        "Masum Research Agent",
        """You are the Research specialist inside Masum AI Agent.
Focus on academic research, web evidence, papers, literature reviews,
research questions, methods, datasets, and evidence-backed synthesis.
Use academic_search for scholarly literature and web_search for fresh public
information. Use local-file tools when the user refers to local documents.
Do not invent papers, citations, sources, or research findings.
Respond mainly in Bangla when the user speaks Bangla.""",
        research_tools,
    )

    developer = make_agent(
        "Masum Developer Agent",
        """You are the Developer/GitHub specialist inside Masum AI Agent.
Focus on programming, debugging, architecture, GitHub repository inspection,
commits, issues, source files, deployment reasoning, and developer workflows.
Use GitHub tools for repository facts and web_search when current documentation
is needed. GitHub access in this agent is read-only; never claim that you
changed a repository through these tools.
Respond mainly in Bangla when the user speaks Bangla.""",
        developer_tools,
    )

    gmail_agent = make_agent(
        "Masum Gmail Agent",
        """You are the Gmail specialist inside Masum AI Agent.
Use Gmail read-only tools to list, search, read, and summarize messages.
Never claim to send, delete, archive, label, forward, or modify email.
Do not invent message content. Keep summaries concise and privacy-conscious.
Respond mainly in Bangla when the user speaks Bangla.""",
        gmail_tools,
    )

    data_agent = make_agent(
        "Masum Data Agent",
        """You are the Database/Data specialist inside Masum AI Agent.
Use the Supabase read-only tools only when Supabase is configured.
You may inspect visible tables, read rows, filter rows, and analyze returned
data. Never claim to insert, update, delete, execute SQL, or alter schema.
Respect RLS and the local table allowlist.
Respond mainly in Bangla when the user speaks Bangla.""",
        data_tools,
    )

    team = {
        "general": general,
        "research": research,
        "developer": developer,
        "gmail": gmail_agent,
        "data": data_agent,
    }

    display_model = (
        model_name
        if model_name
        else "OpenAI SDK default"
    )
    return general, team, provider, display_model


def build_memory_session() -> SQLiteSession:
    MEMORY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return SQLiteSession(
        MEMORY_SESSION_ID,
        str(MEMORY_DB_PATH),
    )


async def print_memory_info(session: SQLiteSession) -> None:
    items = await session.get_items()
    print(f"\n🧠 Memory session : {MEMORY_SESSION_ID}")
    print(f"🗄️ Memory database: {MEMORY_DB_PATH}")
    print(f"💬 Stored items   : {len(items)}")


async def run_direct_search(query: str) -> None:
    if not query:
        print("\nUsage: /search <your query>")
        return

    print("\n🌐 Searching the web...")
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(search_web, query),
            timeout=WEB_SEARCH_TIMEOUT + 10,
        )
        print(f"\n{result}")
    except asyncio.TimeoutError:
        print("\n⏱️ Web search timed out. Try again with a shorter query.")


async def run_direct_paper_search(query: str) -> None:
    if not query:
        print("\nUsage: /papers <research topic>")
        return

    print("\n📚 Searching academic literature...")
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(search_academic_papers, query),
            timeout=OPENALEX_TIMEOUT + 10,
        )
        print(f"\n{result}")
    except asyncio.TimeoutError:
        print("\n⏱️ Academic search timed out. Try again.")


async def answer_file_question(
    agent: Agent,
    session: SQLiteSession,
    file_name: str,
    question: str,
) -> None:
    if not file_name or not question:
        print("\nUsage: /ask-file <filename> :: <question>")
        return

    excerpts = await asyncio.to_thread(search_file_text, file_name, question)

    if (
        excerpts.startswith("File not found:")
        or excerpts.startswith("Unsupported file type")
        or excerpts.startswith("Could not read")
        or excerpts.startswith("No extractable text")
    ):
        print(f"\n{excerpts}")
        return

    prompt = (
        "Answer the user's question using ONLY the document excerpts below. "
        "If the excerpts do not contain enough evidence, say that clearly. "
        "Do not invent details.\n\n"
        f"{excerpts}\n\n"
        f"User question: {question}"
    )

    try:
        result = await asyncio.wait_for(
            Runner.run(agent, prompt, session=session),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
        print(f"\nAgent: {result.final_output}")
    except asyncio.TimeoutError:
        print("\n⏱️ File question timed out. Try a shorter question or smaller file.")




def multi_agent_status_text() -> str:
    mode = "ON" if MULTI_AGENT_AUTO_ROUTE else "OFF"
    return (
        f"Multi-Agent System: enabled\n"
        f"Auto-route natural chat: {mode}\n"
        f"Max collaboration agents: {MULTI_AGENT_MAX_COLLABORATORS}\n\n"
        f"{format_agent_catalog()}"
    )


async def run_named_agent(
    team: dict[str, Agent],
    agent_name: str,
    prompt: str,
    session: SQLiteSession | None = None,
) -> str:
    normalized = normalize_agent_name(agent_name)
    specialist = team.get(normalized)

    if specialist is None:
        return (
            f"Unknown agent: {agent_name}\n\n"
            + format_agent_catalog()
        )

    if not prompt.strip():
        return "Prompt is empty."

    kwargs = {}
    if session is not None:
        kwargs["session"] = session

    try:
        result = await asyncio.wait_for(
            Runner.run(
                specialist,
                prompt.strip(),
                **kwargs,
            ),
            timeout=MULTI_AGENT_TIMEOUT_SECONDS,
        )
        return str(result.final_output)
    except asyncio.TimeoutError:
        return (
            f"{normalized} agent timed out after "
            f"{MULTI_AGENT_TIMEOUT_SECONDS}s."
        )
    except Exception as error:
        return f"{normalized} agent error: {error}"


async def run_team_route(
    team: dict[str, Agent],
    prompt: str,
    session: SQLiteSession | None = None,
) -> tuple[str, str]:
    names = route_agent_names(prompt, max_agents=1)
    selected = names[0] if names else "general"
    output = await run_named_agent(
        team,
        selected,
        prompt,
        session=session,
    )
    return selected, output


async def run_team_review(
    team: dict[str, Agent],
    prompt: str,
) -> tuple[list[str], str]:
    selected = route_agent_names(
        prompt,
        max_agents=MULTI_AGENT_MAX_COLLABORATORS,
    )

    selected = [
        name
        for name in selected
        if name in team and name != "general"
    ]

    if not selected:
        selected = ["general"]
    elif len(selected) == 1 and MULTI_AGENT_MAX_COLLABORATORS >= 2:
        selected.append("general")

    contributions = []

    for name in selected[:MULTI_AGENT_MAX_COLLABORATORS]:
        specialist_prompt = (
            "Act as a specialist contributor. Analyze the request from "
            f"your role's perspective. Do not assume another agent will "
            f"correct unsupported claims.\n\nUser request:\n{prompt}"
        )

        output = await run_named_agent(
            team,
            name,
            specialist_prompt,
            session=None,
        )
        contributions.append(
            f"=== {name.upper()} AGENT ===\n{output}"
        )

    if len(contributions) == 1:
        return selected, contributions[0].split("\n", 1)[-1]

    synthesis_prompt = (
        "You are the coordinator. Synthesize the specialist responses below "
        "into one accurate, practical answer for the user. Resolve conflicts "
        "conservatively, do not invent facts, and keep useful source URLs or "
        "evidence references that specialists supplied. Reply mainly in Bangla "
        "when appropriate.\n\n"
        + "\n\n".join(contributions)
        + f"\n\nOriginal user request:\n{prompt}"
    )

    final_output = await run_named_agent(
        team,
        "general",
        synthesis_prompt,
        session=None,
    )
    return selected, final_output


def automation_help_text() -> str:
    return """Automation actions supported:
- search <query>
- gmail-summary [gmail query]
- gmail-search <gmail query>
- repo-analyze [owner/repo]
- repo-commits [owner/repo]
- papers <topic>
- research <topic>
- db-analyze <table> [limit]   (only if Supabase is configured)
- ask <prompt>

Schedule commands:
- /auto-add-daily HH:MM :: <action>
- /auto-add-every MINUTES :: <action>
- /auto-add-once YYYY-MM-DD HH:MM :: <action>
- /auto-list
- /auto-run <id>
- /auto-enable <id>
- /auto-disable <id>
- /auto-remove <id>
- /auto-log

Examples:
- /auto-add-daily 09:00 :: gmail-summary is:unread newer_than:1d
- /auto-add-every 60 :: repo-commits gitwithmasum/Masum-AI-Agent
- /auto-add-daily 20:00 :: search latest AI news
- /auto-add-once 2026-10-10 18:30 :: papers retrieval augmented generation
"""


async def execute_automation_action(
    agent: Agent,
    action: str,
) -> str:
    action = action.strip()
    lower = action.lower()

    if lower.startswith("search "):
        query = action[len("search "):].strip()
        return await asyncio.to_thread(search_web, query)

    if lower == "gmail-summary":
        return await gmail_summary_text(agent)

    if lower.startswith("gmail-summary "):
        query = action[len("gmail-summary "):].strip()
        return await gmail_summary_text(agent, query)

    if lower.startswith("gmail-search "):
        query = action[len("gmail-search "):].strip()
        return await asyncio.to_thread(gmail_search_text, query)

    if lower == "repo-analyze":
        return await analyze_github_repo(agent)

    if lower.startswith("repo-analyze "):
        repo_name = action[len("repo-analyze "):].strip()
        return await analyze_github_repo(agent, repo_name)

    if lower == "repo-commits":
        return await asyncio.to_thread(github_recent_commits_text)

    if lower.startswith("repo-commits "):
        repo_name = action[len("repo-commits "):].strip()
        return await asyncio.to_thread(
            github_recent_commits_text,
            repo_name,
        )

    if lower.startswith("papers "):
        topic = action[len("papers "):].strip()
        return await asyncio.to_thread(
            search_academic_papers,
            topic,
        )

    if lower.startswith("research "):
        topic = action[len("research "):].strip()
        report_text, report_path = await create_research_report(
            agent,
            topic,
        )
        suffix = (
            f"\\n\\nSaved report: {report_path}"
            if report_path
            else ""
        )
        return report_text + suffix

    if lower.startswith("db-analyze "):
        payload = action[len("db-analyze "):].strip()
        parts = payload.split()
        if not parts:
            return "Usage: db-analyze <table> [limit]"

        table_name = parts[0]
        limit = None

        if len(parts) >= 2:
            try:
                limit = int(parts[1])
            except ValueError:
                return "Usage: db-analyze <table> [limit]"

        return await supabase_analyze_table_text(
            agent,
            table_name,
            limit,
        )

    if lower.startswith("ask "):
        prompt = action[len("ask "):].strip()
        if not prompt:
            return "Automation ask prompt is empty."

        result = await asyncio.wait_for(
            Runner.run(agent, prompt),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
        return str(result.final_output)

    return (
        "Unsupported automation action. Use /auto-help to see "
        "the allowed actions."
    )


async def run_automation_task_now(
    store: AutomationStore,
    agent: Agent,
    task_id: str,
) -> str:
    task = store.get(task_id)
    if not task:
        return f"Automation task not found: {task_id}"

    action = task.get("action") or ""
    try:
        result = await execute_automation_action(agent, action)
        store.mark_result(task_id, "manual-success", str(result))
        return str(result)
    except Exception as error:
        message = f"Automation failed: {error}"
        store.mark_result(task_id, "manual-error", message)
        return message


async def main() -> None:
    ensure_knowledge_dir()
    ensure_research_report_dir()

    try:
        agent, agent_team, provider, model_name = build_agent()
        session = build_memory_session()
        automation_store = AutomationStore(
            AUTOMATION_TASKS_PATH,
            AUTOMATION_LOG_PATH,
        )
    except RuntimeError as error:
        print(f"\n❌ Startup error: {error}\n")
        return

    print("=" * 64)
    print("🤖 MASUM AI AGENT v4.0 — VOICE-READY MULTI-AGENT CORE")
    print(f"Provider : {provider}")
    print(f"Model    : {model_name}")
    if provider == "ollama":
        print("Fast mode: enabled")
    print(f"Memory   : {MEMORY_SESSION_ID}")
    print(f"Web      : enabled ({WEB_SEARCH_MAX_RESULTS} results)")
    print(f"Academic : OpenAlex ({ACADEMIC_SEARCH_MAX_RESULTS} papers)")
    print(f"Files    : {KNOWLEDGE_DIR} (PDF/TXT/MD/DOCX)")
    print(f"Reports  : {RESEARCH_REPORT_DIR}")
    print(f"GitHub   : read-only | default {GITHUB_OWNER}/{GITHUB_DEFAULT_REPO}")
    gmail_ready = GMAIL_TOKEN_PATH.exists()
    print(f"Gmail    : read-only | {'authorized' if gmail_ready else 'setup required'}")
    print(f"Database : Supabase read-only | {'configured' if supabase_configured() else 'setup required'}")
    print(f"Automation: local scheduler | check every {AUTOMATION_CHECK_SECONDS}s")
    print(
        "Agents   : general | research | developer | gmail | data "
        f"| auto-route {'ON' if MULTI_AGENT_AUTO_ROUTE else 'OFF'}"
    )
    print(f"Timeout  : chat {AGENT_TIMEOUT_SECONDS}s | research {RESEARCH_TIMEOUT_SECONDS}s")
    print(
        "Commands : /agents, /team <prompt>, /team-review <prompt>, "
        "/agent <name> :: <prompt>, /auto-help, /auto-list, /auto-add-daily, /auto-add-every, "
        "/auto-add-once, /auto-run, /auto-enable, /auto-disable, /auto-remove, /auto-log, "
        "/db-status, /db-tables, /db-read <table> [limit], "
        "/db-filter <table> :: <column>=<value>, /db-analyze <table> [limit], "
        "/gmail-status, /gmail-auth, /gmail-inbox [count], "
        "/gmail-search <query>, /gmail-read <message-id>, /gmail-summary [query], "
        "/repo [owner/repo], /repos [owner], /repo-files [repo] :: [path], "
        "/repo-read <repo> :: <path>, /repo-commits [repo], /repo-issues [repo], "
        "/repo-analyze [repo], /papers <topic>, /research <topic>, /reports, "
        "/read-report <file>, /files, /read <file>, "
        "/ask-file <file> :: <question>, /search <query>, "
        "/memory, /clear-memory, exit"
    )
    print("=" * 64)

    scheduler_task = asyncio.create_task(
        automation_loop(
            automation_store,
            lambda action: execute_automation_action(agent, action),
            AUTOMATION_CHECK_SECONDS,
        )
    )

    while True:
        user_input = (
            await asyncio.to_thread(input, "\nMasum: ")
        ).strip()

        if user_input.lower() in {"exit", "quit"}:
            print("\nAgent: Goodbye Masum 👋")
            break

        if user_input.lower() == "/memory":
            await print_memory_info(session)
            continue

        if user_input.lower() == "/clear-memory":
            await session.clear_session()
            print("\n🧠 Conversation memory cleared.")
            continue

        if user_input.lower() == "/files":
            print(f"\n{list_knowledge_files_text()}")
            continue

        if user_input.lower() == "/reports":
            print(f"\n{list_research_reports_text()}")
            continue

        if user_input.lower().startswith("/read-report "):
            file_name = user_input[len("/read-report "):].strip()
            print(f"\n{read_research_report(file_name)}")
            continue

        if user_input.lower().startswith("/read "):
            file_name = user_input[len("/read "):].strip()
            result = await asyncio.to_thread(read_file_text, file_name)
            print(f"\n{result}")
            continue

        if user_input.lower().startswith("/ask-file "):
            payload = user_input[len("/ask-file "):].strip()
            if "::" not in payload:
                print("\nUsage: /ask-file <filename> :: <question>")
                continue

            file_name, question = (
                part.strip()
                for part in payload.split("::", 1)
            )
            await answer_file_question(agent, session, file_name, question)
            continue

        if user_input.lower().startswith("/papers"):
            query = user_input[len("/papers"):].strip()
            await run_direct_paper_search(query)
            continue

        if user_input.lower().startswith("/research"):
            topic = user_input[len("/research"):].strip()
            if not topic:
                print("\nUsage: /research <research topic>")
                continue

            print("\n🔬 Gathering academic + web evidence and building report...")
            report_text, report_path = await create_research_report(agent, topic)
            print(f"\n{report_text}")
            if report_path:
                print(f"\n💾 Report saved: {report_path}")
            continue






        if user_input.lower() == "/agents":
            print(f"\n{multi_agent_status_text()}")
            continue

        if user_input.lower().startswith("/agent "):
            payload = user_input[len("/agent "):].strip()
            if "::" not in payload:
                print(
                    "\nUsage: /agent <name> :: <prompt>\n"
                    "Example: /agent research :: Find papers on RAG"
                )
                continue

            agent_name, prompt = (
                part.strip()
                for part in payload.split("::", 1)
            )
            normalized = normalize_agent_name(agent_name)

            print(f"\n🧩 Agent: {normalized}")
            print(
                f"\n{await run_named_agent(
                    agent_team,
                    normalized,
                    prompt,
                    session=session,
                )}"
            )
            continue

        if user_input.lower().startswith("/team-review "):
            prompt = user_input[len("/team-review "):].strip()
            if not prompt:
                print("\nUsage: /team-review <prompt>")
                continue

            print("\n🤝 Multi-agent review running...")
            selected, output = await run_team_review(
                agent_team,
                prompt,
            )
            print(
                "\nAgents used: "
                + ", ".join(selected)
            )
            print(f"\nAgent: {output}")
            continue

        if user_input.lower().startswith("/team "):
            prompt = user_input[len("/team "):].strip()
            if not prompt:
                print("\nUsage: /team <prompt>")
                continue

            selected, output = await run_team_route(
                agent_team,
                prompt,
                session=session,
            )
            print(f"\n🧭 Routed to: {selected}")
            print(f"\nAgent: {output}")
            continue

        if user_input.lower() == "/auto-help":
            print(f"\n{automation_help_text()}")
            continue

        if user_input.lower() == "/auto-list":
            print(f"\n{automation_store.format_tasks()}")
            continue

        if user_input.lower().startswith("/auto-add-daily "):
            payload = user_input[len("/auto-add-daily "):].strip()
            if "::" not in payload:
                print(
                    "\nUsage: /auto-add-daily HH:MM :: <action>"
                )
                continue

            time_value, action = (
                part.strip()
                for part in payload.split("::", 1)
            )

            try:
                task = automation_store.add_daily(
                    time_value,
                    action,
                )
                print(
                    f"\n✅ Automation created: {task['id']} | "
                    f"next run {task['next_run']}"
                )
            except ValueError as error:
                print(f"\n❌ {error}")
            continue

        if user_input.lower().startswith("/auto-add-every "):
            payload = user_input[len("/auto-add-every "):].strip()
            if "::" not in payload:
                print(
                    "\nUsage: /auto-add-every MINUTES :: <action>"
                )
                continue

            minutes_text, action = (
                part.strip()
                for part in payload.split("::", 1)
            )

            try:
                task = automation_store.add_interval(
                    int(minutes_text),
                    action,
                )
                print(
                    f"\n✅ Automation created: {task['id']} | "
                    f"next run {task['next_run']}"
                )
            except (ValueError, TypeError) as error:
                print(f"\n❌ {error}")
            continue

        if user_input.lower().startswith("/auto-add-once "):
            payload = user_input[len("/auto-add-once "):].strip()
            if "::" not in payload:
                print(
                    "\nUsage: /auto-add-once "
                    "YYYY-MM-DD HH:MM :: <action>"
                )
                continue

            when_value, action = (
                part.strip()
                for part in payload.split("::", 1)
            )

            try:
                task = automation_store.add_once(
                    when_value,
                    action,
                )
                print(
                    f"\n✅ Automation created: {task['id']} | "
                    f"next run {task['next_run']}"
                )
            except ValueError as error:
                print(f"\n❌ {error}")
            continue

        if user_input.lower().startswith("/auto-run "):
            task_id = user_input[len("/auto-run "):].strip()
            if not task_id:
                print("\nUsage: /auto-run <id>")
                continue

            print(f"\n⚙️ Running automation {task_id} now...")
            print(
                f"\n{await run_automation_task_now(
                    automation_store,
                    agent,
                    task_id,
                )}"
            )
            continue

        if user_input.lower().startswith("/auto-enable "):
            task_id = user_input[len("/auto-enable "):].strip()
            try:
                task = automation_store.set_enabled(
                    task_id,
                    True,
                )
                if task:
                    print(
                        f"\n✅ Automation {task_id} enabled. "
                        f"Next run: {task.get('next_run')}"
                    )
                else:
                    print(f"\nAutomation task not found: {task_id}")
            except ValueError as error:
                print(f"\n❌ {error}")
            continue

        if user_input.lower().startswith("/auto-disable "):
            task_id = user_input[len("/auto-disable "):].strip()
            task = automation_store.set_enabled(
                task_id,
                False,
            )
            if task:
                print(f"\n⏸️ Automation {task_id} disabled.")
            else:
                print(f"\nAutomation task not found: {task_id}")
            continue

        if user_input.lower().startswith("/auto-remove "):
            task_id = user_input[len("/auto-remove "):].strip()
            if automation_store.remove(task_id):
                print(f"\n🗑️ Automation {task_id} removed.")
            else:
                print(f"\nAutomation task not found: {task_id}")
            continue

        if user_input.lower() == "/auto-log":
            print(f"\n{automation_store.format_log()}")
            continue

        if user_input.lower().startswith("/auto-log "):
            raw_limit = user_input[len("/auto-log "):].strip()
            try:
                log_limit = int(raw_limit)
            except ValueError:
                print("\nUsage: /auto-log [count]")
                continue
            print(
                f"\n{automation_store.format_log(log_limit)}"
            )
            continue

        if user_input.lower() == "/db-status":
            print(f"\n{supabase_status_text()}")
            continue

        if user_input.lower() == "/db-tables":
            print(f"\n{supabase_tables_text()}")
            continue

        if user_input.lower().startswith("/db-read "):
            payload = user_input[len("/db-read "):].strip()
            parts = payload.split()
            if not parts:
                print("\nUsage: /db-read <table> [limit]")
                continue

            table_name = parts[0]
            limit = None
            if len(parts) >= 2:
                try:
                    limit = int(parts[1])
                except ValueError:
                    print("\nUsage: /db-read <table> [limit]")
                    continue

            print(
                f"\n{await asyncio.to_thread(
                    supabase_read_table_text,
                    table_name,
                    limit,
                )}"
            )
            continue

        if user_input.lower().startswith("/db-filter "):
            payload = user_input[len("/db-filter "):].strip()
            if "::" not in payload:
                print("\nUsage: /db-filter <table> :: <column>=<value>")
                continue

            table_name, condition = (
                part.strip()
                for part in payload.split("::", 1)
            )

            if "=" not in condition:
                print("\nUsage: /db-filter <table> :: <column>=<value>")
                continue

            column_name, value = (
                part.strip()
                for part in condition.split("=", 1)
            )

            print(
                f"\n{await asyncio.to_thread(
                    supabase_filter_rows_text,
                    table_name,
                    column_name,
                    value,
                    None,
                )}"
            )
            continue

        if user_input.lower().startswith("/db-analyze "):
            payload = user_input[len("/db-analyze "):].strip()
            parts = payload.split()
            if not parts:
                print("\nUsage: /db-analyze <table> [limit]")
                continue

            table_name = parts[0]
            limit = None
            if len(parts) >= 2:
                try:
                    limit = int(parts[1])
                except ValueError:
                    print("\nUsage: /db-analyze <table> [limit]")
                    continue

            print(f"\n📊 Analyzing Supabase table: {table_name}")
            print(
                f"\n{await supabase_analyze_table_text(
                    agent,
                    table_name,
                    limit,
                )}"
            )
            continue

        if user_input.lower() == "/gmail-status":
            print(f"\n{gmail_status_text()}")
            continue

        if user_input.lower() == "/gmail-auth":
            print("\n📧 Starting Gmail read-only OAuth...")
            try:
                await asyncio.to_thread(load_gmail_credentials, True)
                print(
                    "\n✅ Gmail authorization complete. "
                    f"Token saved locally at: {GMAIL_TOKEN_PATH}"
                )
            except RuntimeError as error:
                print(f"\n❌ Gmail authorization error: {error}")
            continue

        if user_input.lower() == "/gmail-inbox":
            print(f"\n{await asyncio.to_thread(gmail_inbox_text)}")
            continue

        if user_input.lower().startswith("/gmail-inbox "):
            raw_count = user_input[len("/gmail-inbox "):].strip()
            try:
                count = int(raw_count)
            except ValueError:
                print("\nUsage: /gmail-inbox [count]")
                continue
            print(f"\n{await asyncio.to_thread(gmail_inbox_text, count)}")
            continue

        if user_input.lower().startswith("/gmail-search "):
            query = user_input[len("/gmail-search "):].strip()
            print(f"\n{await asyncio.to_thread(gmail_search_text, query)}")
            continue

        if user_input.lower().startswith("/gmail-read "):
            message_id = user_input[len("/gmail-read "):].strip()
            print(f"\n{await asyncio.to_thread(gmail_read_message_text, message_id)}")
            continue

        if user_input.lower() == "/gmail-summary":
            print("\n📨 Summarizing recent inbox messages...")
            print(f"\n{await gmail_summary_text(agent)}")
            continue

        if user_input.lower().startswith("/gmail-summary "):
            query = user_input[len("/gmail-summary "):].strip()
            print(f"\n📨 Summarizing Gmail search: {query}")
            print(f"\n{await gmail_summary_text(agent, query)}")
            continue

        if user_input.lower() == "/repo":
            print(f"\n{github_repo_summary_text()}")
            continue

        if user_input.lower().startswith("/repo "):
            repo_name = user_input[len("/repo "):].strip()
            print(f"\n{github_repo_summary_text(repo_name)}")
            continue

        if user_input.lower() == "/repos":
            print(f"\n{github_owner_repos_text()}")
            continue

        if user_input.lower().startswith("/repos "):
            owner = user_input[len("/repos "):].strip()
            print(f"\n{github_owner_repos_text(owner)}")
            continue

        if user_input.lower().startswith("/repo-files"):
            payload = user_input[len("/repo-files"):].strip()
            if "::" in payload:
                repo_name, path = (
                    part.strip()
                    for part in payload.split("::", 1)
                )
            else:
                repo_name, path = payload, ""
            print(f"\n{github_list_files_text(repo_name, path)}")
            continue

        if user_input.lower().startswith("/repo-read "):
            payload = user_input[len("/repo-read "):].strip()
            if "::" not in payload:
                print("\nUsage: /repo-read <owner/repo> :: <path>")
                continue
            repo_name, path = (
                part.strip()
                for part in payload.split("::", 1)
            )
            print(f"\n{github_read_file_text(repo_name, path)}")
            continue

        if user_input.lower() == "/repo-commits":
            print(f"\n{github_recent_commits_text()}")
            continue

        if user_input.lower().startswith("/repo-commits "):
            repo_name = user_input[len("/repo-commits "):].strip()
            print(f"\n{github_recent_commits_text(repo_name)}")
            continue

        if user_input.lower() == "/repo-issues":
            print(f"\n{github_open_issues_text()}")
            continue

        if user_input.lower().startswith("/repo-issues "):
            repo_name = user_input[len("/repo-issues "):].strip()
            print(f"\n{github_open_issues_text(repo_name)}")
            continue

        if user_input.lower() == "/repo-analyze":
            print("\n🐙 Analyzing default GitHub repository...")
            print(f"\n{await analyze_github_repo(agent)}")
            continue

        if user_input.lower().startswith("/repo-analyze "):
            repo_name = user_input[len("/repo-analyze "):].strip()
            print(f"\n🐙 Analyzing {normalize_github_repo(repo_name)}...")
            print(f"\n{await analyze_github_repo(agent, repo_name)}")
            continue

        if user_input.lower().startswith("/search"):
            query = user_input[len("/search"):].strip()
            await run_direct_search(query)
            continue

        if not user_input:
            continue

        try:
            if MULTI_AGENT_AUTO_ROUTE:
                selected, output = await run_team_route(
                    agent_team,
                    user_input,
                    session=session,
                )
                print(f"\n🧭 {selected} agent")
                print(f"\nAgent: {output}")
            else:
                result = await asyncio.wait_for(
                    Runner.run(
                        agent,
                        user_input,
                        session=session,
                    ),
                    timeout=AGENT_TIMEOUT_SECONDS,
                )
                print(f"\nAgent: {result.final_output}")
        except asyncio.TimeoutError:
            print(
                "\n⏱️ Response timed out. Try /team, /agent, or a direct "
                "command such as /auto-list, /gmail-inbox, /repo, /papers, "
                "/research, /search, or /ask-file."
            )
        except Exception as error:
            print(f"\n❌ Error: {error}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nAgent stopped cleanly. 👋")
