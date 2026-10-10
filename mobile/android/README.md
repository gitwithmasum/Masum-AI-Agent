# Masum AI Agent Mobile v5.3

Native Android Cirilla / Geralt companion with Bangla voice mode and paired laptop control.

## Bangla voice

The app now has three speech-recognition modes:

- AUTO
- বাংলা — forces `bn-BD`
- ENGLISH — forces `en-US`

Tap the Voice Language button inside the app to switch modes. Bangla command aliases are included for calls, notifications, replies, app controls, volume, navigation and laptop bridge actions.

Examples:

```text
হেই সিরিলা, সর্বশেষ নোটিফিকেশন পড়ো
হেই সিরিলা, কল ধরো
হেই সিরিলা, ভলিউম বাড়াও
হেই সিরিলা, হোয়াটসঅ্যাপে রিপ্লাই দাও আমি পরে কল করব
```

## Mobile ↔ Laptop bridge

Windows Masum AI Agent v5.3 exposes a local allowlisted bridge on port 8767.

Pair once:

1. Install/update the Windows companion.
2. From the Windows tray choose **Open Mobile Pairing Info**.
3. Keep phone and laptop on the same trusted private Wi-Fi.
4. In the Android app enter the Bridge URL and Pairing Key.
5. Tap **Save + Test Laptop Pairing**.
6. If Windows Firewall prompts, allow the app on **Private networks only**.

Examples:

```text
Hey Cirilla, open VS Code on laptop
Hey Cirilla, open Chrome on laptop
Hey Cirilla, open GitHub on laptop
Hey Cirilla, laptop status

হেই সিরিলা, ল্যাপটপে ভিএস কোড খোলো
হেই সিরিলা, ল্যাপটপে ক্রোম খোলো
হেই সিরিলা, ল্যাপটপে গিটহাব খোলো
হেই সিরিলা, ল্যাপটপ স্ট্যাটাস
```

Bridge requests use HMAC-SHA256, timestamps and one-time nonces. The pairing key itself is not sent over the network and replayed requests are rejected. The transport is local HTTP, so command contents are not encrypted; use only a trusted private Wi-Fi network.

All earlier v5.1 call controls and v5.2 notification/smart-reply features remain available.
