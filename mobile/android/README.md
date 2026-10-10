# Masum AI Agent Mobile v5.0

Native Android companion for Cirilla / Geralt voice control.

## One-time setup

1. Install the APK.
2. Allow microphone access.
3. Set **Masum AI Agent** as the device's **Default Assistant**.
4. Optional: enable **Masum AI Voice Control** in Accessibility for system-wide UI navigation.

Android requires these approvals; the app does not attempt to bypass them.

## Voice commands

- Open Chrome / YouTube / Gmail / WhatsApp / Maps / GitHub / ChatGPT / Camera
- Open Settings / Wi-Fi Settings / Bluetooth Settings
- Volume up / down / mute / unmute
- Switch to Cirilla / Geralt
- Dial a number (opens dialer for user confirmation)
- With Accessibility enabled: Home, Back, Recent Apps, Scroll Up/Down, Click/Tap visible text, Type/Write into the focused field

## Notes

The service prefers Android's on-device speech recognizer when the device provides one; otherwise Android may use its configured speech recognition service.

This is a debug-signed sideload build for testing. Production distribution should use a private release-signing key.
