# Masum AI Agent

A local-first modular AI Agent built with Python, OpenAI Agents SDK, Ollama, web search, OpenAlex research tools, local document intelligence, and GitHub repository intelligence.

## Current version

**v1.5 — GitHub Agent (Read-Only)**

### What v1.5 adds

- Inspect public GitHub repositories
- Repository metadata and health snapshot
- Browse repository files/folders
- Read text/code files directly from GitHub
- View recent commits
- View open issues
- List a user's recently updated public repositories
- Generate a local-model repository assessment
- Default repository: `gitwithmasum/Masum-AI-Agent`
- No GitHub token required for basic public-repository reads

The GitHub Agent is intentionally **read-only** in v1.5. It does not push commits, create issues, change files, or modify repositories.

## Update

```powershell
git pull origin main
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

No new Python dependency is required for v1.5.

## .env additions

```env
GITHUB_API_BASE=https://api.github.com
GITHUB_OWNER=gitwithmasum
GITHUB_DEFAULT_REPO=Masum-AI-Agent
GITHUB_TIMEOUT=20
GITHUB_MAX_ITEMS=8
GITHUB_FILE_PREVIEW_CHARS=16000
```

For public repositories, no token is required. An optional local `GITHUB_TOKEN` can later be used for private-repository access or higher API limits; never commit it to GitHub.

## Run

```powershell
python main.py
```

Expected header includes:

```text
🤖 MASUM AI AGENT v1.5 — GITHUB AGENT
GitHub   : read-only | default gitwithmasum/Masum-AI-Agent
```

## GitHub commands

Default repository summary:

```text
/repo
```

Another repository:

```text
/repo gitwithmasum/Aurora-Essence
```

List your public repositories:

```text
/repos
```

List another user's public repositories:

```text
/repos openai
```

Browse root files:

```text
/repo-files gitwithmasum/Masum-AI-Agent
```

Browse a folder:

```text
/repo-files gitwithmasum/Masum-AI-Agent :: knowledge
```

Read a GitHub file:

```text
/repo-read gitwithmasum/Masum-AI-Agent :: README.md
```

Recent commits:

```text
/repo-commits
```

Open issues:

```text
/repo-issues
```

Repository assessment:

```text
/repo-analyze
```

or:

```text
/repo-analyze gitwithmasum/Aurora-Essence
```

## Natural-language use

The agent also has GitHub read-only tools, so you can try:

```text
আমার Masum-AI-Agent repo-এর recent commits দেখাও
```

or:

```text
Aurora-Essence repo-এর root files কী কী?
```

Direct commands are more reliable with small local models.

## Existing major commands

```text
/repo [owner/repo]
/repos [owner]
/repo-files [owner/repo] :: [path]
/repo-read <owner/repo> :: <path>
/repo-commits [owner/repo]
/repo-issues [owner/repo]
/repo-analyze [owner/repo]

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

## GitHub API note

Unauthenticated GitHub API requests have a lower rate limit. If you hit a rate-limit message, wait for reset or later configure a GitHub token locally. The token must stay in `.env`, which is ignored by Git.

## Roadmap

- v1.0 — Local/Free AI Brain + Tool Calling ✅
- v1.1 — Persistent Conversation Memory ✅
- v1.2 — Web Search ✅
- v1.3 — File/PDF Intelligence ✅
- v1.4 — Research Agent ✅
- v1.5 — GitHub Agent ✅
- v1.6 — Gmail Agent
- v1.7 — Database / Supabase
- v1.8 — Automation
- v2.0 — Multi-Agent System
- v3.0 — Web Dashboard
- v4.0 — Voice Agent

## Security

- `.env` is ignored by Git.
- GitHub v1.5 actions are read-only.
- No GitHub token is required for normal public-repository use.
- Never publish GitHub or OpenAI secrets.

## Author

**Masum Billah**  
GitHub: [@gitwithmasum](https://github.com/gitwithmasum)
