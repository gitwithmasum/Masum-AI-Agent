# Masum AI Agent Mobile v5.4

Native Android Cirilla / Geralt companion with contact-aware outgoing calls and messaging.

## Contacts permission

v5.4 can resolve a spoken contact name from Android Contacts. The app requests:

- READ_CONTACTS — only when you enable Contacts support
- CALL_PHONE — for direct outgoing calls after voice confirmation

If CALL_PHONE is not granted, Cirilla falls back to opening the dialer.

## Voice examples

```text
Hey Cirilla, call Rahim
Cirilla: Call Rahim? Say yes or no.
You: Yes

Hey Cirilla, send SMS to Rahim saying I am coming
Cirilla: Prepare SMS to Rahim ...? Say yes or no.
You: Yes

Hey Cirilla, WhatsApp Rahim saying I will call later
Cirilla: Prepare WhatsApp message to Rahim ...? Say yes or no.
You: Yes
```

Bangla:

```text
হেই সিরিলা, রহিমকে কল করো
হেই সিরিলা, রহিমকে এসএমএস করো আমি আসছি
হেই সিরিলা, রহিমকে হোয়াটসঅ্যাপ করো আমি পরে কল করব
```

SMS and WhatsApp are intentionally opened as a pre-filled compose screen instead of silently sending. With Accessibility Voice Control enabled, say:

```text
Hey Cirilla, click Send
```

to press a visible Send button.

If multiple contacts match the same spoken name, Cirilla asks for a more specific contact name instead of guessing.

All v5.1 call receiving, v5.2 notification/smart reply, and v5.3 Bangla + laptop bridge features remain available.
