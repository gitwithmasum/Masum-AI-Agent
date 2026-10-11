# Masum AI Agent Mobile v5.9

Native Android Cirilla / Geralt companion with on-device camera OCR and basic visual labeling.

## Camera voice commands

```text
Hey Cirilla, scan this document
Hey Cirilla, read text with camera
Hey Cirilla, what do you see?
Hey Cirilla, describe with camera

হেই সিরিলা, ডকুমেন্ট স্ক্যান করো
হেই সিরিলা, ক্যামেরা দিয়ে লেখা পড়ো
হেই সিরিলা, ক্যামেরা দিয়ে কী দেখছ বলো
```

The user explicitly captures each photo in the Android camera UI.

## On-device analysis

- Text recognition uses the bundled ML Kit Latin-script OCR model.
- Basic visual description uses the bundled ML Kit image-labeling model.
- Captures are written only to a temporary app cache file and deleted on activity cleanup.
- Photos are not uploaded to Masum AI Agent servers.
- Obvious OTP / verification / security-code text is not spoken aloud.

The image-labeling mode provides general labels rather than full generative visual reasoning. It does not identify people.

Bangla voice commands are supported, but the bundled OCR recognizer is for Latin-script text; Bengali-script document OCR is not claimed as reliable in this phase.

All earlier v5.x features remain available.
