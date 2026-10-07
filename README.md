# Masum AI Agent

A modular, local-first AI Agent built with Python and the OpenAI Agents SDK. It can run **completely free on your own computer with Ollama**, while keeping optional OpenAI API support for later.

## Current version

**v1.0 — Local/Free Mode + Tool Calling**

### Current capabilities

- Local AI through Ollama — no OpenAI API credits required
- Optional OpenAI provider
- OpenAI Agents SDK orchestration
- Interactive terminal chat
- Function/tool calling
- Current-time tool
- Bangla-friendly behavior
- Environment-based provider switching
- OpenAI tracing disabled in local mode

## Default local model

```text
qwen3:4b
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
ollama pull qwen3:4b
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

For free local mode, use:

```env
AI_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen3:4b
```

No OpenAI API key is required.

### 7. Run

```powershell
python main.py
```

Expected startup:

```text
🤖 MASUM AI AGENT v1.0 — LOCAL/FREE MODE
Provider : ollama
Model    : qwen3:4b
```

Try:

```text
Hello, who are you?
```

Then test the tool:

```text
এখন কয়টা বাজে?
```

## Optional OpenAI mode

Later, if you add API credits:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your_real_api_key
```

Then run `python main.py`.

## Switching local models

For a stronger local model:

```powershell
ollama pull qwen3:8b
```

Then change:

```env
OLLAMA_MODEL=qwen3:8b
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
Provider Router
  ├── Ollama (default / local / free)
  │      ↓
  │   Qwen3
  │
  └── OpenAI (optional)
         ↓
      OpenAI API

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
- Local Ollama mode runs the model on your computer.
- OpenAI mode remains optional.

## Author

**Masum Billah**  
GitHub: [@gitwithmasum](https://github.com/gitwithmasum)
