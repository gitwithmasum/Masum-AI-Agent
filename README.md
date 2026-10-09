# Masum AI Agent

A local-first modular AI Agent built with Python, OpenAI Agents SDK, Ollama, web search, academic research, local file intelligence, GitHub, Gmail, optional Supabase access, and persistent automation.

## Current version

**v1.8 — Automation**

### What Automation means

v1.8 adds a persistent local scheduler. You can tell the agent to run supported tasks:

- once at a specific local date/time,
- every N minutes,
- every day at a specific local time.

Automation tasks are stored locally in `data/automations.json`, so they survive an app restart. Run history is stored in `data/automation_log.jsonl`.

### Supported automated actions

```text
search <query>
gmail-summary [gmail query]
gmail-search <gmail query>
repo-analyze [owner/repo]
repo-commits [owner/repo]
papers <topic>
research <topic>
db-analyze <table> [limit]
ask <prompt>
```

The `db-analyze` action only works if Supabase is configured. Supabase can remain skipped and all other automation features still work.

## Important runtime limitation

This is a **local scheduler**. The Masum AI Agent process must be running:

```powershell
python main.py
```

If the app/computer is off, scheduled tasks cannot execute at that moment. The task definitions stay saved. When the app starts again, an overdue enabled task is detected by the scheduler and can run on the next scheduler check.

For true always-on automation later, the project can be extended with Windows Task Scheduler, a background service, or a cloud worker.

## Update

```powershell
git pull origin main
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

v1.8 uses only Python standard-library scheduling/storage code, so no new automation package is required.

## .env settings

Add:

```env
AUTOMATION_TASKS_PATH=data/automations.json
AUTOMATION_LOG_PATH=data/automation_log.jsonl
AUTOMATION_CHECK_SECONDS=30
```

The `data/` folder is already ignored by Git.

## Run

```powershell
python main.py
```

The startup banner includes:

```text
🤖 MASUM AI AGENT v1.8 — AUTOMATION
Automation: local scheduler | check every 30s
```

## Automation commands

Show help:

```text
/auto-help
```

Show all tasks:

```text
/auto-list
```

### Daily automation

Every day at 9:00 AM, summarize unread/recent Gmail:

```text
/auto-add-daily 09:00 :: gmail-summary is:unread newer_than:1d
```

Every day at 8:00 PM, search latest AI news:

```text
/auto-add-daily 20:00 :: search latest AI news
```

### Interval automation

Check recent commits every 60 minutes:

```text
/auto-add-every 60 :: repo-commits gitwithmasum/Masum-AI-Agent
```

Search AI news every 120 minutes:

```text
/auto-add-every 120 :: search latest artificial intelligence news
```

### One-time automation

```text
/auto-add-once 2026-10-10 18:30 :: papers retrieval augmented generation
```

The date/time uses the computer's local timezone.

## Manage tasks

Each automation gets an 8-character ID.

Run immediately:

```text
/auto-run <id>
```

Pause:

```text
/auto-disable <id>
```

Resume:

```text
/auto-enable <id>
```

Delete:

```text
/auto-remove <id>
```

See recent automation runs:

```text
/auto-log
```

or:

```text
/auto-log 50
```

## Useful setups

### Morning Gmail brief

Requires Gmail OAuth to be authorized:

```text
/auto-add-daily 09:00 :: gmail-summary is:unread newer_than:1d
```

### GitHub project watch

```text
/auto-add-every 60 :: repo-commits gitwithmasum/Masum-AI-Agent
```

### Daily research discovery

```text
/auto-add-daily 19:00 :: papers machine learning artificial intelligence
```

### Generate a recurring research report

```text
/auto-add-daily 21:00 :: research retrieval augmented generation
```

This creates Markdown reports in `research_reports/`, so do not schedule it too frequently unless you want many files.

### General AI prompt

```text
/auto-add-daily 08:00 :: ask Give me a short study plan for today
```

## Safety

v1.8 automation dispatches only a fixed allowlist of project actions. It does **not** execute arbitrary PowerShell, CMD, shell, or Python code.

Existing GitHub, Gmail, and Supabase integrations remain read-only.

## Architecture

```text
Masum AI Agent
    |
    +-- interactive chat
    |
    +-- AutomationStore
          |
          +-- data/automations.json
          +-- data/automation_log.jsonl
          |
          +-- background scheduler
                 |
                 +-- web search
                 +-- Gmail read/summary
                 +-- GitHub read/analyze
                 +-- paper/research workflow
                 +-- optional DB analysis
                 +-- local AI prompt
```

## Roadmap

- v1.0 — Local/Free AI Brain + Tool Calling ✅
- v1.1 — Persistent Conversation Memory ✅
- v1.2 — Web Search ✅
- v1.3 — File/PDF Intelligence ✅
- v1.4 — Research Agent ✅
- v1.5 — GitHub Agent ✅
- v1.6 — Gmail Agent ✅
- v1.7 — Supabase / Database Agent ✅ (optional setup)
- v1.8 — Automation ✅
- v2.0 — Multi-Agent System
- v3.0 — Web Dashboard
- v4.0 — Voice Agent

## Security

- Automation files stay in the ignored `data/` directory.
- No arbitrary operating-system command execution.
- Gmail remains read-only.
- GitHub remains read-only.
- Supabase remains read-only and optional.
- Never commit OAuth tokens, API keys, or database secrets.

## Author

**Masum Billah**  
GitHub: [@gitwithmasum](https://github.com/gitwithmasum)
