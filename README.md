# Masum AI Agent

A local-first personal AI system built with Python, OpenAI Agents SDK, Ollama, web search, research tools, local document intelligence, GitHub, Gmail, optional Supabase, persistent automation, and specialist-agent routing.

## Current version

**v2.0 — Multi-Agent System**

### Agent team

- **General Coordinator** — mixed questions, planning, explanations
- **Research Agent** — papers, thesis, literature review, datasets, methods, evidence
- **Developer Agent** — code, debugging, GitHub, repositories, commits, issues, architecture
- **Gmail Agent** — read-only Gmail search/read/summary
- **Data Agent** — optional read-only Supabase access

The project still uses the same local Ollama model by default. Specialist agents share the model but receive different instructions and tool permissions.

## Why this helps

Instead of exposing every tool to every task, v2.0 narrows the toolset by role. A Gmail question is routed to the Gmail specialist, a research question to Research, and GitHub/code work to Developer. This makes the small local model more predictable.

## Update local VS Code copy

```powershell
git pull origin main
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

No new Python package is required for v2.0.

## .env

Optional settings:

```env
MULTI_AGENT_AUTO_ROUTE=true
MULTI_AGENT_MAX_COLLABORATORS=2
MULTI_AGENT_TIMEOUT_SECONDS=180
```

- `MULTI_AGENT_AUTO_ROUTE=true` automatically selects a specialist for normal chat.
- `MULTI_AGENT_MAX_COLLABORATORS=2` limits multi-agent review cost/latency.
- `MULTI_AGENT_TIMEOUT_SECONDS=180` is the per-agent timeout.

## Commands

Show team:

```text
/agents
```

Auto-route a request:

```text
/team Find recent research papers on retrieval augmented generation
```

Call a specific specialist:

```text
/agent research :: Find papers on RAG and suggest a research gap
/agent developer :: Analyze the architecture of gitwithmasum/Masum-AI-Agent
/agent gmail :: Summarize my unread emails
/agent data :: Show accessible Supabase tables
```

Ask multiple agents to review a request and let the coordinator synthesize:

```text
/team-review Review my AI research project from both research and software-engineering perspectives
```

## Natural auto-routing

With:

```env
MULTI_AGENT_AUTO_ROUTE=true
```

normal prompts are automatically routed.

Examples:

```text
Masum: find recent papers on AI agents
🧭 research agent

Masum: check my GitHub repo architecture
🧭 developer agent

Masum: summarize unread Gmail
🧭 gmail agent
```

## Existing automation

v1.8 remains available:

```text
/auto-help
/auto-list
/auto-add-daily HH:MM :: <action>
/auto-add-every MINUTES :: <action>
/auto-add-once YYYY-MM-DD HH:MM :: <action>
/auto-run <id>
/auto-disable <id>
/auto-enable <id>
/auto-remove <id>
/auto-log
```

The automation engine is local, so `python main.py` must be running for scheduled execution.

## Existing direct tools

```text
/gmail-status
/gmail-auth
/gmail-inbox
/gmail-search <query>
/gmail-summary [query]

/repo [owner/repo]
/repo-files [repo] :: [path]
/repo-read <repo> :: <path>
/repo-commits [repo]
/repo-issues [repo]
/repo-analyze [repo]

/papers <topic>
/research <topic>
/reports

/files
/read <file>
/ask-file <file> :: <question>

/search <query>

/db-status
/db-tables
/db-read <table> [limit]
/db-filter <table> :: <column>=<value>
/db-analyze <table> [limit]

/memory
/clear-memory
```

Supabase remains optional. Leaving it unconfigured does not affect the rest of the system.

## Security

- Gmail is read-only.
- GitHub agent tools are read-only.
- Supabase tools are read-only and optional.
- Automation cannot execute arbitrary PowerShell/CMD/shell commands.
- Secrets remain in local `.env` / `secrets/` and are ignored by Git.
- Specialist agents receive only the tools relevant to their role.

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
- **v2.0 — Multi-Agent System ✅**
- v3.0 — Web Dashboard
- v4.0 — Voice Agent

## Author

**Masum Billah**  
GitHub: [@gitwithmasum](https://github.com/gitwithmasum)
