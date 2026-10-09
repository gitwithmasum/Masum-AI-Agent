# Masum AI Agent

A local-first modular AI Agent built with Python, OpenAI Agents SDK, Ollama, web search, OpenAlex, local document intelligence, GitHub intelligence, Gmail read-only access, and Supabase read-only database access.

## Current version

**v1.7 — Supabase / Database Agent (Read-Only)**

### What v1.7 adds

- Connect to a Supabase project using the project URL and anon key
- Detect accessible REST tables
- Read rows from tables
- Filter rows using one equality condition
- Ask the local model to summarize/analyze a small row sample
- Respect Supabase Row Level Security (RLS)
- Optional table allowlist
- No insert, update, delete, SQL execution, or schema modification

## Update

```powershell
git pull origin main
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

v1.7 uses Python's built-in HTTP libraries, so no new Supabase Python package is required.

## Configure Supabase

In Supabase Dashboard, copy:

- **Project URL**
- **anon / publishable key** suitable for client-side access

Put them only in your local `.env`:

```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your_real_anon_key
SUPABASE_SCHEMA=public
SUPABASE_TIMEOUT=20
SUPABASE_MAX_ROWS=20
SUPABASE_PREVIEW_CHARS=16000
SUPABASE_ALLOWED_TABLES=
```

Do not paste a service-role/secret key into this project. v1.7 is designed around the anon/publishable client key and RLS.

### Optional table allowlist

To make the agent see only selected tables even if the anon key can access more:

```env
SUPABASE_ALLOWED_TABLES=profiles,products,orders
```

Leave it blank to allow all tables that are already permitted by the anon key and RLS.

## Run

```powershell
python main.py
```

Startup header includes:

```text
🤖 MASUM AI AGENT v1.7 — SUPABASE / DATABASE AGENT
Database : Supabase read-only | configured
```

## Database commands

Check configuration and connection:

```text
/db-status
```

Discover visible tables:

```text
/db-tables
```

Read rows:

```text
/db-read profiles
```

or limit the sample:

```text
/db-read profiles 5
```

Filter one column:

```text
/db-filter profiles :: status=active
```

Analyze a small sample with the local model:

```text
/db-analyze profiles 10
```

## Security model

The database layer is intentionally read-only:

- Only HTTP GET requests are implemented.
- No database write tools exist.
- No raw SQL execution exists.
- Table/column identifiers are validated.
- Supabase RLS remains authoritative.
- An optional table allowlist adds another local restriction.
- Never use a Supabase service-role key in this local agent.

## Existing capabilities

- Local Ollama AI
- Persistent memory
- Web search
- PDF/DOCX/TXT/Markdown intelligence
- Academic research agent
- GitHub read-only agent
- Gmail read-only agent
- Supabase/database read-only agent

## Main commands

```text
/db-status
/db-tables
/db-read <table> [limit]
/db-filter <table> :: <column>=<value>
/db-analyze <table> [limit]

/gmail-status
/gmail-auth
/gmail-inbox [count]
/gmail-search <query>
/gmail-read <message-id>
/gmail-summary [query]

/repo [owner/repo]
/repo-files [owner/repo] :: [path]
/repo-read <owner/repo> :: <path>
/repo-commits [owner/repo]
/repo-issues [owner/repo]
/repo-analyze [owner/repo]

/papers <topic>
/research <topic>

/files
/read <filename>
/ask-file <filename> :: <question>

/search <query>
/memory
/clear-memory
exit
```

## Roadmap

- v1.0 — Local/Free AI Brain + Tool Calling ✅
- v1.1 — Persistent Conversation Memory ✅
- v1.2 — Web Search ✅
- v1.3 — File/PDF Intelligence ✅
- v1.4 — Research Agent ✅
- v1.5 — GitHub Agent ✅
- v1.6 — Gmail Agent ✅
- v1.7 — Supabase / Database Agent ✅
- v1.8 — Automation
- v2.0 — Multi-Agent System
- v3.0 — Web Dashboard
- v4.0 — Voice Agent

## Security

- `.env` is ignored by Git.
- Gmail and GitHub integrations remain read-only.
- Supabase access is read-only and RLS-respecting.
- Never publish OAuth tokens, GitHub tokens, database secrets, or API keys.

## Author

**Masum Billah**  
GitHub: [@gitwithmasum](https://github.com/gitwithmasum)
