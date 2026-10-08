# Masum AI Agent

A modular, local-first AI Agent built with Python, the OpenAI Agents SDK, and Ollama. The default setup runs **completely free on your own computer** and now includes persistent conversation memory.

## Current version

**v1.1 — Persistent Conversation Memory**

### Current capabilities

- Local AI through Ollama — no API credits required
- Persistent SQLite conversation memory
- Memory survives closing and reopening the app
- OpenAI Agents SDK orchestration
- Interactive terminal chat
- Function/tool calling
- Current-time tool
- Bangla-friendly behavior
- Fast local mode
- Clean timeout and Ctrl+C handling

## Default local model

```text
qwen3:1.7b
```

## Update an existing installation

From the project folder:

```powershell
git pull origin main
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Sync dependencies:

```powershell
pip install -r requirements.txt
```

Your local `.env` is not overwritten by Git. Add these memory settings if they are missing:

```env
AI_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen3:1.7b
AGENT_TIMEOUT_SECONDS=120

MEMORY_SESSION_ID=masum-main
MEMORY_DB_PATH=data/memory.db
```

Then run:

```powershell
python main.py
```

Expected startup:

```text
🤖 MASUM AI AGENT v1.1 — PERSISTENT MEMORY
Provider : ollama
Model    : qwen3:1.7b
Memory   : masum-main
Database : data\memory.db
```

## Test persistent memory

First tell the agent:

```text
আমার favourite programming language Python.
```

Then ask:

```text
আমার favourite programming language কী?
```

Now type:

```text
exit
```

Run the app again:

```powershell
python main.py
```

Ask again:

```text
আমার favourite programming language কী?
```

The agent should use the stored conversation history.

## Memory commands

Show memory status:

```text
/memory
```

Clear the current conversation memory:

```text
/clear-memory
```

The local memory database is stored at:

```text
data/memory.db
```

The `data/` directory is ignored by Git, so private conversation memory is not uploaded to the repository.

## Fresh Windows setup

Install Ollama:

```powershell
irm https://ollama.com/install.ps1 | iex
```

Download the default model:

```powershell
ollama pull qwen3:1.7b
```

Create and activate the Python environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create local configuration:

```powershell
Copy-Item .env.example .env
```

Run:

```powershell
python main.py
```

## Architecture

```text
User
  ↓
Masum AI Agent
  ↓
OpenAI Agents SDK
  ├── SQLiteSession → data/memory.db
  ├── Tools
  │    └── Current Time
  ↓
Ollama (local / free)
  ↓
Qwen3
```

## Roadmap

- v1.0 — Local/Free AI Brain + Tool Calling ✅
- v1.1 — Persistent Conversation Memory ✅
- v1.2 — Web Search
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

## Author

**Masum Billah**  
GitHub: [@gitwithmasum](https://github.com/gitwithmasum)
