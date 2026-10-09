# Masum AI Agent

A local-first modular AI Agent built with Python, OpenAI Agents SDK, Ollama, web search, OpenAlex, local document intelligence, GitHub intelligence, and Gmail read-only access.

## Current version

**v1.6 — Gmail Agent (Read-Only)**

### What v1.6 adds

- Gmail OAuth login using Google's official desktop-app flow
- Read-only Gmail scope: `gmail.readonly`
- Recent inbox listing
- Gmail search using normal Gmail search syntax
- Read individual messages by message ID
- Local AI summary of recent/search-matched messages
- OAuth token stored only in the local `secrets/` folder
- No send, delete, archive, label, or other mailbox modification capability

## Update

```powershell
git pull origin main
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Google Cloud setup — first time only

1. Open Google Cloud Console and create/select a project.
2. Enable **Gmail API**.
3. Configure the OAuth consent screen.
4. Create an OAuth Client ID with application type **Desktop app**.
5. Download the OAuth JSON file.
6. Rename/save it as:

```text
Masum-AI-Agent/
└── secrets/
    └── gmail_credentials.json
```

If your OAuth app is still in testing mode, add your own Google account as a test user.

The `secrets/` folder contents are ignored by Git.

## .env additions

```env
GMAIL_CREDENTIALS_PATH=secrets/gmail_credentials.json
GMAIL_TOKEN_PATH=secrets/gmail_token.json
GMAIL_MAX_RESULTS=8
GMAIL_BODY_PREVIEW_CHARS=12000
```

## Authorize Gmail

Run:

```powershell
python main.py
```

Then:

```text
/gmail-status
/gmail-auth
```

The first authorization opens a browser. Sign in to the Gmail account you want the local agent to read and approve the read-only permission.

After successful OAuth, the local token is stored at:

```text
secrets/gmail_token.json
```

Do not share or commit this file.

## Gmail commands

Recent inbox:

```text
/gmail-inbox
```

Choose how many:

```text
/gmail-inbox 10
```

Search using Gmail syntax:

```text
/gmail-search is:unread
```

```text
/gmail-search from:github.com newer_than:30d
```

```text
/gmail-search subject:interview
```

The results include Gmail message IDs. Read one message:

```text
/gmail-read <message-id>
```

Summarize recent inbox messages:

```text
/gmail-summary
```

Or summarize a Gmail search:

```text
/gmail-summary is:unread newer_than:7d
```

## Privacy

- Gmail scope is read-only.
- The agent cannot send or modify email in v1.6.
- OAuth credentials and tokens stay in the local `secrets/` folder.
- Direct Gmail commands do not upload your Gmail OAuth token anywhere.
- Natural-language agent runs can be recorded in the project's local SQLite conversation memory, so use `/clear-memory` if you do not want those local chat/tool records retained.

## Existing capabilities

- Local Ollama AI
- Persistent memory
- Web search
- PDF/DOCX/TXT/Markdown intelligence
- Academic research agent
- GitHub read-only agent
- Gmail read-only agent

## Main commands

```text
/gmail-status
/gmail-auth
/gmail-inbox [count]
/gmail-search <gmail query>
/gmail-read <message-id>
/gmail-summary [gmail query]

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
- v1.7 — Database / Supabase
- v1.8 — Automation
- v2.0 — Multi-Agent System
- v3.0 — Web Dashboard
- v4.0 — Voice Agent

## Security

- `.env`, `data/`, `knowledge/`, `research_reports/`, and `secrets/` contents are protected from Git where applicable.
- Gmail access is read-only.
- Never commit OAuth credentials, OAuth tokens, GitHub tokens, or API keys.

## Author

**Masum Billah**  
GitHub: [@gitwithmasum](https://github.com/gitwithmasum)
