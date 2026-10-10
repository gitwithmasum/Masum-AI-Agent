# Masum AI Agent

## v4.6 — Install-and-Run Windows Companion

The Windows companion is designed for this end-user flow:

```text
Install Masum AI Agent once
→ sign in to Windows
→ Cirilla starts automatically in the system tray
→ say “Hey Cirilla”
→ use safe desktop voice commands
```

After the standalone installer is built and installed, VS Code, PowerShell, `python dashboard.py`, and a manually started STT server are not required for the desktop-launcher experience.

Safe commands include:

```text
Hey Cirilla, open VS Code
Hey Cirilla, open Masum AI Agent project
Hey Cirilla, open Chrome
Hey Cirilla, open GitHub
Hey Cirilla, open Gmail
Hey Cirilla, open ChatGPT
Hey Cirilla, open Downloads
Hey Cirilla, open Documents
Hey Cirilla, switch to Geralt
```

Chrome profile launch is supported without storing passwords:

```text
Hey Cirilla, open Chrome profile <profile name>
Hey Cirilla, open Gmail with <profile name or signed-in account>
```

The app reads Chrome's local profile metadata only to select an already signed-in profile. It never stores or types Google passwords.

### First run

The app automatically downloads its local Faster-Whisper models on first use and caches them under the user's local app-data folder. After the models are cached, wake detection and desktop command transcription stay local.

### Windows startup

The installer enables **Start Cirilla automatically when I sign in to Windows** by default. It installs for the current user and does not require administrator privileges.

### Build locally

```powershell
.\build_windows_app.ps1
```

Output:

```text
installer-output\Masum-AI-Agent-Setup.exe
```

A GitHub Actions workflow also builds the same Windows installer artifact automatically when desktop-companion files change.

Security: desktop actions use an explicit allowlist. Arbitrary voice text is never executed as PowerShell/CMD, and v4.6 does not perform destructive system actions.

---

## v4.5 — Voice Actions + Smart Confirmation

v4.5 extends Cirilla/Geralt from navigation commands into safe voice actions with confirmation.

### Smart confirmation

Impactful automation actions require an explicit confirmation:

```text
Hey Cirilla, run automation 1
Cirilla: Confirm run automation 1 ...? Say yes or no.
You: Yes
```

Supported automation voice actions:

```text
List automations
Run automation 1
Pause automation 1
Enable automation 1
Delete automation 1
```

Automation actions can also be referenced by a unique task ID prefix or unique text from the action.

Recovery commands:

```text
Yes
No
Cancel
Repeat
What did you hear?
```

Read-only/intelligence shortcuts do not require confirmation:

```text
Gmail summary
Research <topic>
GitHub summary
Gmail status
```

After asking for confirmation, the system automatically opens a short local Whisper confirmation window, so you do not need to repeat the wake phrase before saying Yes or No.

---

## v4.4 — Hands-Free Voice Command Center

v4.4 adds deterministic local voice controls on top of the existing Cirilla/Geralt wake system.

Examples:

```text
Hey Cirilla, open Research
Hey Geralt, open Automation
Switch to Geralt
Switch to Cirilla
Wake mode on
Wake mode off
Speak replies on
Speak replies off
Auto send on
Auto send off
Gmail status
GitHub summary
Voice commands
```

Dashboard-control commands are handled locally in the browser and do not need to be routed through the AI model. Anything that is not a dashboard-control command still goes through the normal Masum AI Agent routing and tool system.

The Voice Commands panel inside Neural Chat shows the currently supported shortcuts.

---

## v4.3 — Dual Voice Personas

Masum AI Agent now has two selectable voice personas:

- **Female — Cirilla**
- **Male — Geralt**

The selected persona controls:

- spoken reply profile,
- wake word,
- wake status badge,
- wake acknowledgment,
- saved browser voice preference.

Wake phrases:

```text
Female mode:
Hey Cirilla
Cirilla

Male mode:
Hey Geralt
Geralt
```

The dashboard uses the browser/Windows voices that are actually installed on the computer. It scores available voices by language and common male/female voice-name hints, then applies persona-specific pitch/rate tuning. Because browser speech APIs do not expose a guaranteed gender field, the exact voice can vary by Windows/browser.

Wake detection remains local through Faster-Whisper.

---

## v4.2 — Cirilla Wake Mode

The project brand remains **Masum AI Agent**, while the hands-free voice persona/wake name is **Cirilla**.

Wake phrases:

```text
Hey Cirilla
Cirilla
সিরিলা
হেই সিরিলা
```

Wake Mode is **OFF by default**. Turn on **Wake: Cirilla** in Neural Chat when you want continuous local listening.

Examples:

```text
Hey Cirilla, আমার GitHub recent commit দেখাও
Cirilla, find recent AI agent papers
```

If you say only `Hey Cirilla`, Cirilla wakes and automatically records your next command for about 7 seconds.

Wake detection uses the local Faster-Whisper service. A lightweight `tiny` model is used for wake detection, while the `small` multilingual model remains the main speech-to-text model.

### Run v4.2

Terminal 1:

```powershell
.\.venv-stt\Scripts\python.exe local_stt_server.py
```

Terminal 2:

```powershell
.\.venv\Scripts\Activate.ps1
python dashboard.py
```

Then open Neural Chat, select **Local Whisper**, and enable **Wake: Cirilla**.

Wake Mode continuously samples microphone audio locally while enabled, so it uses more CPU than manual MIC mode. Turn it off when you do not need hands-free listening.

---

<p align="center"><img src="dashboard/masum-ai-agent-logo.webp" alt="Masum AI Agent Logo" width="220"></p>

## v4.1 — Fully Local Speech-to-Text

v4.1 adds a local Faster-Whisper speech-to-text service for better Bangla/English voice input. Browser Speech remains available as a fallback.

### Setup

```powershell
py -0p
```

If Python 3.12 is missing:

```powershell
winget install -e --id Python.Python.3.12
```

Then:

```powershell
.\setup_local_stt.ps1
```

Start Local Whisper in Terminal 1:

```powershell
.\.venv-stt\Scripts\python.exe local_stt_server.py
```

Start the dashboard in Terminal 2:

```powershell
.\.venv\Scripts\Activate.ps1
python dashboard.py
```

In Neural Chat select **Local Whisper**. Click MIC once to start recording and click MIC again when finished. The multilingual `small` model is downloaded once into `data/stt_models`, then reused locally.

The main Python 3.14 environment stays separate from the STT Python 3.12 environment.

---

## v4.0 — Voice Agent

v4.0 adds microphone input and spoken replies to the local Web Dashboard while preserving all v3.0 features.

Voice features:
- Bangla (bn-BD), English US and English UK recognition modes
- Voice Link / MIC controls inside Neural Chat
- optional automatic submit after recognition
- browser text-to-speech for AI replies
- Ctrl + Space microphone shortcut
- browser-saved voice preferences
- graceful typed-chat fallback

Privacy: Ollama/agent processing stays on the configured AI stack, but browser speech recognition may use an online speech service depending on the browser. Do not assume speech-to-text is fully offline.

Update and run from PowerShell:
    git pull origin main
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python dashboard.py

Then open http://127.0.0.1:8765, enter Neural Chat, allow microphone permission, choose Bangla or English, and click MIC.

---

Local-first personal AI system with Ollama, multi-agent routing, automation, Gmail intelligence, research, GitHub inspection, optional Supabase and a futuristic local web dashboard.

## Current version

**v4.6 — Install-and-Run Windows Companion**

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
- v3.0 — Web Dashboard ✅
- v4.0 — Voice Agent ✅
- v4.1 — Local Faster-Whisper STT ✅
- v4.2 — Wake Word Mode ✅
- v4.3 — Cirilla / Geralt Dual Voice Personas ✅
- v4.4 — Hands-Free Voice Command Center ✅
- v4.5 — Voice Actions + Smart Confirmation ✅
- **v4.6 — Install-and-Run Windows Companion ✅**

## Author

**Masum Billah**  
GitHub: [@gitwithmasum](https://github.com/gitwithmasum)
