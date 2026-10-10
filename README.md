# Masum AI Agent

## v5.1 — Universal Call Voice Control

Android mobile companion now supports explicit voice control for incoming calls:

```text
Hey Cirilla, answer the call
Hey Cirilla, reject the call
Hey Cirilla, who is calling?
Hey Cirilla, answer WhatsApp call
Hey Cirilla, reject WhatsApp call
Hey Cirilla, answer Messenger call
Hey Cirilla, reject Messenger call
```

Normal SIM calls use Android Telecom with user-granted phone permissions. WhatsApp and Messenger use Android Notification Access and only trigger an Answer / Decline PendingIntent that the incoming-call notification actually exposes.

No call is auto-answered. v5.1 requires the user's explicit voice command and does not guess unknown notification buttons.

Android source: `mobile/android/`

GitHub Actions artifact: `Masum-AI-Agent-Android-APK-v5.1`

---

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

Local-first personal AI system with Ollama, multi-agent routing, automation, Gmail intelligence, research, GitHub inspection, optional Supabase, Windows desktop companion and Android voice companion.

## Current version

**v5.1 — Universal Call Voice Control**

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
- v4.6 — Install-and-Run Windows Companion ✅
- v5.0 — Android Cirilla / Geralt Companion ✅
- **v5.1 — Universal Call Voice Control ✅**

## Author

**Masum Billah**  
GitHub: [@gitwithmasum](https://github.com/gitwithmasum)
