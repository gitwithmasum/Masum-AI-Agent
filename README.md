# Masum AI Agent

A modular, local-first AI Agent built with Python and the OpenAI Agents SDK. The default setup runs **completely free on your own computer with Ollama** and does not require an OpenAI API key.

## Current version

**v1.0 — Local/Free Mode + Tool Calling**

### Current capabilities

- Local AI through Ollama — no API credits required
- OpenAI Agents SDK orchestration
- Interactive terminal chat
- Function/tool calling
- Current-time tool
- Bangla-friendly behavior
- Fast local mode for smaller models
- Clean timeout and Ctrl+C handling
- OpenAI tracing disabled in local mode

## Default local model

```text
qwen3:1.7b
```

## Windows setup — Free local mode

### 1. Install Ollama

Open PowerShell:

```powershell
irm https://ollama.com/install.ps1 | iex
```

Reopen the terminal and verify:

```powershell
ollama --version
```

### 2. Download the local model

```powershell
ollama pull qwen3:1.7b
```

Check it:

```powershell
ollama list
```

Ollama normally serves its local API at `http://localhost:11434`. If necessary:

```powershell
ollama serve
```

### 3. Update this repository

```powershell
git pull origin main
```

### 4. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 5. Install/update dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Configure local mode

If you do not already have a `.env` file:

```powershell
Copy-Item .env.example .env
```

Use this local configuration:

```env
AI_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen3:1.7b
AGENT_TIMEOUT_SECONDS=120
```

**No OpenAI API key is required for the default local setup.**

### 7. Run

```powershell
python main.py
```

Expected startup:

```text
🤖 MASUM AI AGENT v1.0 — LOCAL/FREE MODE
Provider : ollama
Model    : qwen3:1.7b
Fast mode: enabled
Timeout  : 120s
```

Try:

```text
Hello, who are you?
```

Then test the tool:

```text
এখন কয়টা বাজে?
```

## Switching local models

For a stronger local model:

```powershell
ollama pull qwen3:4b
```

Then change:

```env
OLLAMA_MODEL=qwen3:4b
```

Larger models usually improve quality but require more RAM/GPU memory.

## Architecture

```text
User
  ↓
Masum AI Agent
  ↓
OpenAI Agents SDK
  ↓
Ollama (local / free)
  ↓
Qwen3

Tools
  └── Current Time
```

## Roadmap

- v1.0 — Local/Free AI Brain + Tool Calling ✅
- v1.1 — Conversation Memory
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
- Never publish real API keys.
- The default local setup requires no OpenAI API key.
- Local Ollama mode runs the model on your computer.

## Author

**Masum Billah**  
GitHub: [@gitwithmasum](https://github.com/gitwithmasum)
