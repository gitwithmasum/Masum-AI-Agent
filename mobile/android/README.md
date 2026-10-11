# Masum AI Agent Mobile v5.5

Native Android Cirilla / Geralt companion with voice productivity actions.

## Alarm and timer

```text
Hey Cirilla, set alarm for 7 AM
Hey Cirilla, set a 25 minute timer

হেই সিরিলা, সকাল ৭টায় অ্যালার্ম দাও
হেই সিরিলা, ২৫ মিনিটের টাইমার দাও
```

Alarm and timer commands use Android's system AlarmClock intents.

## Local reminders

```text
Hey Cirilla, remind me in 20 minutes to submit assignment
হেই সিরিলা, ২০ মিনিট পরে অ্যাসাইনমেন্ট জমা দিতে মনে করিয়ে দিও
```

Reminders are stored locally, delivered as Android notifications, and future reminders are re-scheduled after a device reboot. Android power management may make delivery slightly inexact.

Enable **Reminder Notifications** in the app on Android 13+.

## Notes

```text
Hey Cirilla, take note buy perfume samples
Hey Cirilla, read my notes

হেই সিরিলা, নোট করো কাল research paper দেখব
হেই সিরিলা, নোটগুলো পড়ো
```

Notes stay in the app's private local storage.

## Calendar

```text
Hey Cirilla, calendar event BUBT assignment review
হেই সিরিলা, ক্যালেন্ডারে BUBT assignment review যোগ করো
```

Calendar commands open a pre-filled event in the user's calendar app for review/save.

All earlier call, notification, messaging, Bangla voice and mobile↔laptop bridge features remain available.
