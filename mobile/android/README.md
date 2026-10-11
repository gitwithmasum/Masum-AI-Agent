# Masum AI Agent Mobile v5.6

Native Android Cirilla / Geralt companion with expanded safe phone controls.

## System voice controls

```text
Hey Cirilla, flashlight on
Hey Cirilla, flashlight off
Hey Cirilla, battery status

Hey Cirilla, brightness 60 percent
Hey Cirilla, brightness up
Hey Cirilla, brightness down

Hey Cirilla, do not disturb on
Hey Cirilla, do not disturb off

Hey Cirilla, auto rotate on
Hey Cirilla, auto rotate off

Hey Cirilla, play music
Hey Cirilla, pause music
Hey Cirilla, next song
Hey Cirilla, previous song

Hey Cirilla, take screenshot
Hey Cirilla, hotspot settings
```

Bangla aliases are included, for example:

```text
হেই সিরিলা, টর্চ চালু করো
হেই সিরিলা, ব্যাটারি কত
হেই সিরিলা, ব্রাইটনেস ৬০ পারসেন্ট করো
হেই সিরিলা, ডিএনডি চালু করো
হেই সিরিলা, অটো রোটেট বন্ধ করো
হেই সিরিলা, পরের গান চালাও
হেই সিরিলা, স্ক্রিনশট নাও
হেই সিরিলা, হটস্পট সেটিংস খোলো
```

## Android permission boundaries

- Flashlight uses Android CameraManager and needs the app's one-time **Flashlight access** permission.
- Brightness and rotation require Android's **Modify system settings** approval once.
- DND requires Android's **Do Not Disturb access** approval once.
- Screenshot uses Accessibility global screenshot and therefore needs Accessibility Voice Control enabled.
- Hotspot is intentionally opened as settings instead of silently toggled because modern Android restricts direct hotspot control for ordinary third-party apps.
- Media control sends standard Android media key events.

All earlier calls, messaging, notifications, Bangla voice, laptop bridge, alarms, reminders, calendar and notes remain available.
