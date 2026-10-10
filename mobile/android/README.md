# Masum AI Agent Mobile v5.2

Native Android Cirilla / Geralt companion with call control, notification intelligence and confirmed smart replies.

## One-time setup

1. Install the APK.
2. Allow microphone access.
3. Set **Masum AI Agent** as the device's **Default Assistant**.
4. Allow **SIM Call Control** for normal incoming phone calls.
5. Enable **Masum AI Call + Message Access** under Notification Access.
6. Optional: enable **Masum AI Voice Control** in Accessibility.

## Voice notifications

```text
Hey Cirilla, read latest notification
Hey Cirilla, list notifications
Hey Cirilla, read latest WhatsApp message
Hey Cirilla, read latest Messenger message
```

## Confirmed smart reply

```text
Hey Cirilla, reply WhatsApp I will call you later
Cirilla: Send reply ...? Say yes or no.
You: Yes
```

Direct reply only works when the target notification exposes Android RemoteInput / direct reply. Unknown notification actions are never guessed.

For privacy, obvious OTP / verification-code notifications are not read aloud.

## Call controls

```text
Hey Cirilla, answer the call
Hey Cirilla, reject the call
Hey Cirilla, who is calling?
Hey Cirilla, answer WhatsApp call
Hey Cirilla, reject WhatsApp call
Hey Cirilla, answer Messenger call
Hey Cirilla, reject Messenger call
```

No call is auto-answered and no message is sent without an explicit confirmation.

The GitHub Actions APK is debug-signed for sideload testing.
