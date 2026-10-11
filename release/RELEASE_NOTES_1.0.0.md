# Masum AI Agent 1.0.0

Masum AI Agent 1.0.0 is the first stable unified Android + Windows release.

## Highlights

- Cirilla / Geralt voice personas
- Android voice assistant controls and bilingual Bangla/English commands
- SIM/WhatsApp/Messenger call-control paths with explicit user action
- notifications and safe smart reply
- contacts, SMS and WhatsApp compose flows
- alarms, timers, reminders, notes and calendar helpers
- flashlight, brightness, DND, media, screenshot and settings controls
- screen-aware Accessibility navigation with protected sensitive fields
- smart YouTube, Chrome, Maps, GitHub, Play Store and WhatsApp actions
- on-device camera OCR and basic image labeling
- authenticated Android ↔ Windows bridge
- shared local Ollama + multi-agent AI brain
- security/permission and reliability centers
- self-contained Windows AI brain executable
- signed Android stable build gate and SHA-256 release manifest

## Security

Passwords, PINs, OTPs, CVV/security codes and sensitive confirmation flows remain protected. Outgoing call/message/reply actions require explicit confirmation where designed. Arbitrary voice-to-PowerShell/CMD execution is disabled. The unified AI dashboard stays localhost-only.

## Runtime notes

Ollama and the configured local model are still required for the full local unified AI brain. Android behavior can vary by OEM battery/background policy. Windows binaries are not Authenticode code-signed in 1.0.0, so SmartScreen can warn; verify the official SHA-256 checksum before installation.

## Installation order

Install Windows first, start Masum AI Agent, open Mobile Pairing Info, then install the signed Android APK and complete the Android first-run checklist.
