# Masum AI Agent Mobile v5.1

Native Android Cirilla / Geralt companion with universal voice call control.

## One-time setup

1. Install the APK.
2. Allow microphone access.
3. Set **Masum AI Agent** as the device's **Default Assistant**.
4. Allow **SIM Call Control** for normal incoming phone calls.
5. Enable **Masum AI Call Control** under Notification Access for WhatsApp / Messenger call actions.
6. Optional: enable **Masum AI Voice Control** in Accessibility for system-wide UI navigation.

Android requires these approvals. The app does not silently grant itself permissions.

## Call voice commands

```text
Hey Cirilla, answer the call
Hey Cirilla, receive the call
Hey Cirilla, reject the call
Hey Cirilla, who is calling?

Hey Cirilla, answer WhatsApp call
Hey Cirilla, reject WhatsApp call

Hey Cirilla, answer Messenger call
Hey Cirilla, reject Messenger call
```

### How it works

- **SIM / normal phone calls:** uses Android Telecom APIs only while the phone is actually ringing and only after the user grants phone-call permissions.
- **WhatsApp / Messenger:** uses Android Notification Access and triggers the call notification's own Answer / Decline PendingIntent when the app exposes one.
- **Caller identification:** uses visible incoming-call notification text when available.

WhatsApp and Messenger are best-effort integrations because their notification labels and behavior can change between app versions. v5.1 never guesses an unlabeled notification action.

## Safety

- Calls are never auto-answered.
- A call action requires an explicit voice command.
- Rejecting a SIM call checks that the phone is actually ringing before using Telecom; it will not intentionally terminate an already active call.
- Passwords, banking approvals, lock-screen bypasses and arbitrary shell commands remain unsupported.

## Other mobile commands

- Open Chrome / YouTube / Gmail / WhatsApp / Maps / GitHub / ChatGPT / Camera
- Open Settings / Wi-Fi Settings / Bluetooth Settings
- Volume up / down / mute / unmute
- Switch to Cirilla / Geralt
- Dial a number (opens dialer for user confirmation)
- With Accessibility enabled: Home, Back, Recent Apps, Scroll Up/Down, Click/Tap visible text, Type/Write into the focused field

The APK produced by GitHub Actions is debug-signed for sideload testing.
