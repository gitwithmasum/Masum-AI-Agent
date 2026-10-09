# Masum AI Agent

Local-first personal AI system with Ollama, multi-agent routing, automation, Gmail intelligence, research, GitHub inspection, optional Supabase and a futuristic local web dashboard.

## Current version

**v3.0 — Web Dashboard**

### v3.0 adds

- Futuristic responsive browser control center
- Multi-agent chat with Auto Router
- Manual General / Research / Developer / Gmail / Data selection
- Team Review mode
- Live Ollama, Gmail, automation and research status
- Automation create / run / pause / resume / delete controls
- Research report browser and preview
- Gmail status and GitHub quick diagnostics
- Mobile-responsive layout
- Dashboard starts its own automation scheduler
- Local-only network binding by default

The original CLI remains available through `python main.py`.

## Update local copy

```powershell
git pull origin main
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Dashboard configuration

Add to local `.env`:

```env
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=8765
DASHBOARD_AUTO_OPEN=true
```

Keep `DASHBOARD_HOST=127.0.0.1` unless you intentionally add authentication and secure network exposure.

## Start Web Dashboard

Make sure Ollama is running, then:

```powershell
python dashboard.py
```

The browser opens automatically at:

```text
http://127.0.0.1:8765
```

If auto-open is disabled, open that address manually.

## Dashboard areas

### Overview

Shows:

- Ollama/local model status
- Gmail authorization state
- Active automation count
- Saved research-report count
- agent matrix
- Gmail and GitHub quick diagnostics

### Neural Chat

Use:

- Auto Router
- General Agent
- Research Agent
- Developer Agent
- Gmail Agent
- Data Agent
- Team Review

Normal multi-agent routing and persistent conversation memory are reused from the CLI core.

### Automation Center

Create:

- daily tasks,
- interval tasks,
- one-time tasks.

From the dashboard you can also run, pause, enable and delete tasks.

Automation state remains stored locally in:

```text
data/automations.json
data/automation_log.jsonl
```

### Research Vault

Browse and preview Markdown reports already created in:

```text
research_reports/
```

## Security model

The dashboard has **no public-user authentication in v3.0**. Therefore:

- default host is `127.0.0.1`,
- do not expose port 8765 directly to the public internet,
- Gmail remains read-only,
- GitHub agent tools remain read-only,
- Supabase remains read-only and optional,
- automation still cannot execute arbitrary PowerShell/CMD/shell commands,
- secrets remain local in `.env` and `secrets/`.

## Run modes

CLI:

```powershell
python main.py
```

Web Dashboard:

```powershell
python dashboard.py
```

You normally need only one of them running at a time. Both use the same local data files.

## Main architecture

```text
Browser
   |
   v
FastAPI Dashboard (localhost)
   |
   +-- Multi-Agent Router
   |     +-- General
   |     +-- Research
   |     +-- Developer
   |     +-- Gmail
   |     +-- Data
   |
   +-- Automation Engine
   +-- Research Vault
   +-- Gmail Read-Only
   +-- GitHub Read-Only
   +-- Optional Supabase Read-Only
   |
   v
Ollama / qwen3:1.7b
```

## Roadmap

- v1.0 — Local AI + Tool Calling ✅
- v1.1 — Persistent Memory ✅
- v1.2 — Web Search ✅
- v1.3 — File/PDF Intelligence ✅
- v1.4 — Research Agent ✅
- v1.5 — GitHub Agent ✅
- v1.6 — Gmail Agent ✅
- v1.7 — Supabase / Database Agent ✅ (optional setup)
- v1.8 — Automation ✅
- v2.0 — Multi-Agent System ✅
- **v3.0 — Web Dashboard ✅**
- v4.0 — Voice Agent

## Author

**Masum Billah**  
GitHub: [@gitwithmasum](https://github.com/gitwithmasum)
