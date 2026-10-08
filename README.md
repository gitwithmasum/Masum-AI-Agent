# Masum AI Agent

A local-first AI Agent built with Python, OpenAI Agents SDK, Ollama, DDGS, and OpenAlex.

## Current version

**v1.4 — Research Agent**

The project runs locally without OpenAI API credits and now supports academic literature search plus structured research-report generation.

## Capabilities

- Local AI through Ollama
- Persistent SQLite conversation memory
- Live web search
- Local PDF/TXT/Markdown/DOCX intelligence
- OpenAlex scholarly-paper search
- Academic metadata: title, authors, year, citations, DOI, abstract when available
- Structured research planning reports
- Candidate research-gap generation with evidence safeguards
- Markdown report saving
- Bangla-friendly interaction

## Update

```powershell
git pull origin main
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

No new Python package is required specifically for OpenAlex because v1.4 uses Python's built-in HTTP libraries.

## .env

Keep your existing settings and add:

```env
ACADEMIC_SEARCH_MAX_RESULTS=6
OPENALEX_TIMEOUT=20
RESEARCH_TIMEOUT_SECONDS=240
RESEARCH_REPORT_DIR=research_reports
```

A complete local setup can look like:

```env
AI_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen3:1.7b
AGENT_TIMEOUT_SECONDS=120

MEMORY_SESSION_ID=masum-main
MEMORY_DB_PATH=data/memory.db

WEB_SEARCH_MAX_RESULTS=5
WEB_SEARCH_TIMEOUT=10

KNOWLEDGE_DIR=knowledge
FILE_MAX_BYTES=15728640
FILE_PREVIEW_CHARS=12000
FILE_CHUNK_CHARS=3500
FILE_MAX_CHUNKS=4

ACADEMIC_SEARCH_MAX_RESULTS=6
OPENALEX_TIMEOUT=20
RESEARCH_TIMEOUT_SECONDS=240
RESEARCH_REPORT_DIR=research_reports
```

## Run

```powershell
python main.py
```

Expected startup:

```text
🤖 MASUM AI AGENT v1.4 — RESEARCH AGENT
Provider : ollama
Model    : qwen3:1.7b
Academic : OpenAlex (6 papers)
Reports  : research_reports
```

## Academic-paper search

```text
/papers machine learning for early diabetes prediction
```

The agent returns relevant scholarly works with available authors, year, citation count, DOI, source, abstract excerpt, and access link.

## Build a research report

```text
/research machine learning for early diabetes prediction
```

The Research Agent gathers:

1. scholarly evidence from OpenAlex,
2. current web evidence,
3. then asks the local model to create a structured planning report.

The report includes:

- Executive Summary
- Key Findings
- Literature Snapshot
- Potential Research Gaps
- Candidate Research Questions
- Methodology Options
- Possible Data / Dataset Sources
- Risks and Limitations
- Practical Next Steps
- Sources

Reports are saved locally:

```text
research_reports/
└── machine-learning-for-early-diabetes-prediction-YYYYMMDD-HHMMSS.md
```

Research reports are ignored by Git by default.

## Report commands

```text
/reports
/read-report <filename>
```

## Other commands

```text
/papers <topic>
/research <topic>
/reports
/read-report <filename>
/files
/read <filename>
/ask-file <filename> :: <question>
/search <query>
/memory
/clear-memory
exit
```

## Research safeguards

- Factual claims in generated research reports should be tied to collected evidence markers such as `[P1]` or `[W1]`.
- Candidate research gaps are explicitly treated as ideas that must be validated, not automatically as proven gaps.
- A machine-collected source appendix is added to each report.
- If the local model times out, the evidence bundle is still saved as a Markdown report instead of being lost.

## OpenAlex

v1.4 uses OpenAlex for academic literature search. Basic API searches can work without an API key, which keeps the default project local/free-friendly.

## Architecture

```text
User
  ↓
Masum AI Agent
  ↓
Research layer
  ├── OpenAlex → scholarly works
  ├── DDGS → web evidence
  ├── Local documents → knowledge/
  └── Ollama → synthesis
          ↓
   Markdown research report
          ↓
   research_reports/
```

## Roadmap

- v1.0 — Local/Free AI Brain + Tool Calling ✅
- v1.1 — Persistent Conversation Memory ✅
- v1.2 — Web Search ✅
- v1.3 — File/PDF Intelligence ✅
- v1.4 — Research Agent ✅
- v1.5 — GitHub Agent
- v1.6 — Gmail Agent
- v1.7 — Database / Supabase
- v1.8 — Automation
- v2.0 — Multi-Agent System
- v3.0 — Web Dashboard
- v4.0 — Voice Agent

## Security

- `.env` is ignored by Git.
- `data/`, `knowledge/`, and `research_reports/` contents are ignored by Git.
- The default local setup requires no OpenAI API key.

## Author

**Masum Billah**  
GitHub: [@gitwithmasum](https://github.com/gitwithmasum)
