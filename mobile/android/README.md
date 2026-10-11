# Masum AI Agent Mobile v5.7

Native Android Cirilla / Geralt companion with screen-aware accessibility intelligence.

## Screen-aware commands

```text
Hey Cirilla, what is on my screen?
Hey Cirilla, read this screen
Hey Cirilla, find Submit
Hey Cirilla, scroll until you find Settings

হেই সিরিলা, স্ক্রিনে কী আছে?
হেই সিরিলা, এই স্ক্রিনটা পড়ো
হেই সিরিলা, Submit খুঁজে বের করো
হেই সিরিলা, Settings পাওয়া পর্যন্ত স্ক্রল করো
```

Cirilla reads a compact summary of useful visible labels instead of dumping the full accessibility tree.

## Privacy and safety

Screen-aware mode intentionally filters:

- password/passcode fields
- PIN fields
- OTP / verification-code fields
- CVV/security-code fields
- text-entry into protected/password fields

Obvious OTP/security-code text is replaced with protected information instead of being spoken aloud.

`scroll until you find X` searches the visible screen, scrolls in short asynchronous steps, and stops when the target is found, scrolling ends, or the bounded search limit is reached.

Accessibility Voice Control must be enabled for these features.

All earlier calls, messaging, notifications, Bangla voice, mobile↔laptop bridge, productivity and phone controls remain available.
