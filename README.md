# Masum AI Agent

A modular, local-first AI Agent built with Python, OpenAI Agents SDK, and Ollama. It runs locally without OpenAI API credits and now includes persistent memory plus live key-free web search.

## Current version

**v1.2 — Persistent Memory + Web Search**

### Current capabilities

- Local AI through Ollama
- No OpenAI API credits required
- Persistent SQLite conversation memory
- Live public web search
- Direct `/search` command
- Agent-controlled `web_search` tool
- Current-time tool
- Bangla-friendly behavior
- Fast local mode
- Clean timeout and Ctrl+C handling

## Update an existing installation

```powershell
git pull origin main
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Your local `.env` is not overwritten by Git. Add these settings if missing:

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
```

Run:

```powershell
python main.py
```

Expected startup:

```text
🤖 MASUM AI AGENT v1.2 — MEMORY + WEB SEARCH
Provider : ollama
Model    : qwen3:1.7b
Memory   : masum-main
Web      : enabled (5 results)
```

## Test web search

### Direct search — fastest and easiest to debug

```text
/search latest Python 3.14 news
```

This prints live result titles, snippets, and source URLs directly without waiting for the model to decide whether to call a tool.

### Agent-controlled search

Ask naturally:

```text
আজকের AI news web থেকে search করে বলো
```

or:

```text
Search the web for the latest Ollama release and summarize it.
```

The agent can call the `web_search` tool and use the returned sources.

## Memory test

```text
আমার favourite programming language Python.
আমার favourite programming language কী?
```

Commands:

```text
/memory
/clear-memory
/search <query>
exit
```

## Local model

Default:

```text
qwen3:1.7b
```

For better tool-use quality, if your computer can handle it:

```powershell
ollama pull qwen3:4b
```

Then set:

```env
OLLAMA_MODEL=qwen3:4b
```

## Architecture

```text
User
  ↓
Masum AI Agent
  ↓
OpenAI Agents SDK
  ├── SQLiteSession → data/memory.db
  ├── Current Time Tool
  └── Web Search Tool → DDGS metasearch
  ↓
Ollama (local / free)
  ↓
Qwen3
```

## Roadmap

- v1.0 — Local/Free AI Brain + Tool Calling ✅
- v1.1 — Persistent Conversation Memory ✅
- v1.2 — Web Search ✅
- v1.3 — File/PDF Intelligence
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
- Local conversation memory stays on your computer.
- The default local setup requires no OpenAI API key.

## Notes

Web search uses the `ddgs` metasearch package. Search availability can vary when upstream search providers rate-limit or block requests.

## Author

**Masum Billah**  
GitHub: [@gitwithmasum](https://github.com/gitwithmasum)
