import asyncio
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from ddgs import DDGS
from ddgs.exceptions import DDGSException
from docx import Document
from dotenv import load_dotenv
from pypdf import PdfReader
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

SUPPORTED_FILE_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}


@function_tool
def get_current_time() -> str:
    """Return the computer's current local date and time."""
    return datetime.now().astimezone().strftime(
        "%A, %d %B %Y - %I:%M:%S %p %Z"
    )


def search_web(query: str, max_results: int | None = None) -> str:
    """Run a key-free web search and return compact source results."""
    query = query.strip()
    if not query:
        return "Search query is empty."

    limit = max_results or WEB_SEARCH_MAX_RESULTS
    limit = max(1, min(limit, 8))

    try:
        results = DDGS(timeout=WEB_SEARCH_TIMEOUT).text(
            query,
            max_results=limit,
        )
    except DDGSException as error:
        return f"Web search failed: {error}"
    except Exception as error:
        return f"Web search failed unexpectedly: {error}"

    if not results:
        return f"No web results found for: {query}"

    lines = [f"Live web results for: {query}"]
    for index, item in enumerate(results, start=1):
        title = (item.get("title") or "Untitled").strip()
        url = (item.get("href") or "").strip()
        body = (item.get("body") or "").strip()

        lines.append(f"\n[{index}] {title}")
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
    may require up-to-date information. Return sources with the result.
    """
    return search_web(query, max_results=max_results)


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
    """
    List PDF, TXT, Markdown, and DOCX files available in the local knowledge folder.
    """
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
    """
    Read text from a PDF, TXT, Markdown, or DOCX file in the local knowledge folder.
    Use file_search for targeted questions about long files.
    """
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
                end = start + split_at + (2 if chunk[split_at:split_at + 2] == ". " else 0)
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
        selected = [(0, index, chunk) for index, chunk in enumerate(chunks[:limit])]

    lines = [
        f"Relevant excerpts from: {file_name}",
        f"Question: {query}",
    ]

    for rank, (score, index, chunk) in enumerate(selected, start=1):
        lines.append(
            f"\n--- Excerpt {rank} | chunk {index + 1} | keyword score {score} ---\n{chunk}"
        )

    return "\n".join(lines)


@function_tool
def file_search(file_name: str, query: str, max_chunks: int = 4) -> str:
    """
    Search a local document for excerpts relevant to a question.

    The file must be inside the knowledge folder. Use this for questions
    about long PDF, TXT, Markdown, or DOCX files.
    """
    return search_file_text(file_name, query, max_chunks=max_chunks)


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
- For questions about local documents, use list_local_files, read_local_file, or file_search.
- Only claim facts about a local file when supported by text returned from a file tool.
"""

LOCAL_FAST_INSTRUCTIONS = INSTRUCTIONS + """
- You are running on a small local model. Prefer short, direct answers.
- For simple tool requests, call the required tool immediately without lengthy reasoning.
- If the user asks for the current date or time, call get_current_time immediately.
- If the user asks to search the web, find current information, or asks for latest/recent information, call web_search immediately.
- If the user asks what files are available, call list_local_files immediately.
- If the user asks about a named local document, prefer file_search with the user's question.
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


def build_agent() -> tuple[Agent, str, str]:
    provider = os.getenv("AI_PROVIDER", "ollama").strip().lower()
    tools = [
        get_current_time,
        web_search,
        list_local_files,
        read_local_file,
        file_search,
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
        local_model = OpenAIChatCompletionsModel(
            model=model_name,
            openai_client=local_client,
        )

        agent = Agent(
            name="Masum AI Agent",
            instructions=LOCAL_FAST_INSTRUCTIONS,
            model=local_model,
            tools=tools,
        )
        return agent, provider, model_name

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or "your_openai_api_key_here" in api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is missing or still contains the placeholder value."
            )

        model_name = os.getenv("OPENAI_MODEL", "").strip()
        kwargs = {
            "name": "Masum AI Agent",
            "instructions": INSTRUCTIONS,
            "tools": tools,
        }
        if model_name:
            kwargs["model"] = model_name

        agent = Agent(**kwargs)
        return agent, provider, model_name or "OpenAI SDK default"

    raise RuntimeError(
        f"Unsupported AI_PROVIDER='{provider}'. Use 'ollama' or 'openai'."
    )


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


async def main() -> None:
    ensure_knowledge_dir()

    try:
        agent, provider, model_name = build_agent()
        session = build_memory_session()
    except RuntimeError as error:
        print(f"\n❌ Startup error: {error}\n")
        return

    print("=" * 60)
    print("🤖 MASUM AI AGENT v1.3 — FILE/PDF INTELLIGENCE")
    print(f"Provider : {provider}")
    print(f"Model    : {model_name}")
    if provider == "ollama":
        print("Fast mode: enabled")
    print(f"Memory   : {MEMORY_SESSION_ID}")
    print(f"Web      : enabled ({WEB_SEARCH_MAX_RESULTS} results)")
    print(f"Files    : {KNOWLEDGE_DIR} (PDF/TXT/MD/DOCX)")
    print(f"Timeout  : {AGENT_TIMEOUT_SECONDS}s")
    print(
        "Commands : /files, /read <file>, /ask-file <file> :: <question>, "
        "/search <query>, /memory, /clear-memory, exit"
    )
    print("=" * 60)

    while True:
        user_input = input("\nMasum: ").strip()

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

            file_name, question = (part.strip() for part in payload.split("::", 1))
            await answer_file_question(agent, session, file_name, question)
            continue

        if user_input.lower().startswith("/search"):
            query = user_input[len("/search"):].strip()
            await run_direct_search(query)
            continue

        if not user_input:
            continue

        try:
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
                "\n⏱️ Response timed out. Try a shorter prompt, "
                "/search for direct web results, or /ask-file for documents."
            )
        except Exception as error:
            print(f"\n❌ Error: {error}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nAgent stopped cleanly. 👋")
