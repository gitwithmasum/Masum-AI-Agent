# Masum AI Agent

A modular, local-first AI Agent built with Python, OpenAI Agents SDK, and Ollama. It runs locally without OpenAI API credits and includes persistent memory, live web search, and local File/PDF Intelligence.

## Current version

**v1.3 — File/PDF Intelligence**

### Current capabilities

- Local AI through Ollama
- No OpenAI API credits required
- Persistent SQLite conversation memory
- Live public web search
- Local PDF reading
- Local TXT and Markdown reading
- Local DOCX reading
- Keyword-based document excerpt retrieval
- Direct file commands for reliable use with small local models
- Current-time tool
- Bangla-friendly behavior
- Clean timeout and Ctrl+C handling

## Update an existing installation

From the project folder:

```powershell
git pull origin main
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Your local `.env` is not overwritten by Git. Add these settings if they are missing:

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
```

## Add documents

Put documents inside:

```text
Masum-AI-Agent/
└── knowledge/
    ├── notes.txt
    ├── research-paper.pdf
    ├── assignment.docx
    └── roadmap.md
```

Supported formats:

- PDF
- TXT
- Markdown
- DOCX

The contents of `knowledge/` are ignored by Git, so private documents are not uploaded to GitHub.

## Run

```powershell
python main.py
```

Expected startup:

```text
🤖 MASUM AI AGENT v1.3 — FILE/PDF INTELLIGENCE
Provider : ollama
Model    : qwen3:1.7b
Memory   : masum-main
Web      : enabled (5 results)
Files    : knowledge (PDF/TXT/MD/DOCX)
```

## File commands

List available documents:

```text
/files
```

Preview a file:

```text
/read research-paper.pdf
```

Ask a question about a file:

```text
/ask-file research-paper.pdf :: এই paper-এর main objective কী?
```

Another example:

```text
/ask-file assignment.docx :: এখানে blockchain-এর কী কী advantage বলা হয়েছে?
```

The agent retrieves relevant excerpts first and answers from those excerpts instead of sending the entire document to the local model.

## Natural-language file tools

You can also ask:

```text
knowledge folder-এ কী কী file আছে?
```

or:

```text
research-paper.pdf থেকে methodology সম্পর্কে বলো
```

For the smallest local model, the direct commands are generally more reliable.

## Existing commands

```text
/files
/read <filename>
/ask-file <filename> :: <question>
/search <query>
/memory
/clear-memory
exit
```

## Important PDF limitation

Text-based PDFs work directly. Scanned/image-only PDFs may return no extractable text because OCR is intentionally not enabled in this version.

## Architecture

```text
User
  ↓
Masum AI Agent
  ↓
OpenAI Agents SDK
  ├── SQLiteSession → data/memory.db
  ├── Current Time Tool
  ├── Web Search Tool → DDGS
  └── File Intelligence
       ├── PDF → pypdf
       ├── DOCX → python-docx
       ├── TXT / MD → Python
       └── Chunk + keyword retrieval
  ↓
Ollama (local / free)
  ↓
Qwen3
```

## Roadmap

- v1.0 — Local/Free AI Brain + Tool Calling ✅
- v1.1 — Persistent Conversation Memory ✅
- v1.2 — Web Search ✅
- v1.3 — File/PDF Intelligence ✅
- v1.4 — Research Agent
- v1.5 — GitHub Agent
- v1.6 — Gmail Agent
- v1.7 — Database / Supabase
- v1.8 — Automation
- v2.0 — Multi-Agent System
- v3.0 — Web Dashboard
- v4.0 — Voice Agent

## Security

- `.env` is ignored by Git.
- `data/` is ignored by Git.
- `knowledge/` document contents are ignored by Git.
- File access is restricted to the configured knowledge directory.
- The default local setup requires no OpenAI API key.

## Author

**Masum Billah**  
GitHub: [@gitwithmasum](https://github.com/gitwithmasum)
