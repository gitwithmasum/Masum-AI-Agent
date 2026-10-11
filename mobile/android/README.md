# Masum AI Agent Mobile v6.0

v6.0 introduces the Unified Personal AI Brain.

Android and Windows share the laptop's existing local multi-agent core and SQLite conversation memory when paired.

Flow: Android voice → HMAC-authenticated bridge → Windows companion → localhost-only dashboard API → Ollama / multi-agent core → shared session → answer to Android TTS.

Examples:
- Hey Cirilla, brain status
- Hey Cirilla, ask AI explain machine learning simply
- Hey Cirilla, explain polymorphism in Bangla
- Hey Cirilla, summarize my Gmail
- Hey Cirilla, analyze my GitHub repository
- হেই সিরিলা, এআইকে জিজ্ঞেস করো machine learning কী

Unknown non-device commands can fall back to the unified AI brain. Device actions remain platform-specific and safe: Android actions run on Android; Windows actions run on Windows. The AI brain has no arbitrary shell execution.

The Windows companion can start the existing project dashboard silently on demand using the project's local Python environment. Ollama must be available for local AI mode.

All earlier v5.x Android features remain available.
