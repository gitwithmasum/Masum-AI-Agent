# Masum AI Agent

A modular AI Agent built with Python and the OpenAI Agents SDK, designed for intelligent conversations, tool calling, memory, research, automation, GitHub, Gmail, and future multi-agent workflows.

## Current version

**v1.0 — AI Brain + Tool Calling**

Current capabilities:

- Interactive terminal chat
- OpenAI Agents SDK integration
- Environment-variable based API key handling
- Local current-time tool
- Bangla-friendly assistant behavior
- Extensible architecture for future tools and agents

## Setup

### 1. Clone the repository

```powershell
git clone https://github.com/gitwithmasum/Masum-AI-Agent.git
cd Masum-AI-Agent
```

### 2. Create a virtual environment

```powershell
py -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure the API key

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` and replace:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

with your real OpenAI API key.

> Never commit the `.env` file.

### 5. Run

```powershell
python main.py
```

Try:

```text
Hello, who are you?
```

or:

```text
এখন কয়টা বাজে?
```

## Roadmap

- v1.0 — AI Brain + Tool Calling
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

Secrets must stay in local environment files. The repository intentionally ignores `.env`, virtual environments, Python cache files, and local VS Code settings.

## Author

**Masum Billah**  
GitHub: [@gitwithmasum](https://github.com/gitwithmasum)
