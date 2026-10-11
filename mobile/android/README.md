# Masum AI Agent Mobile v6.3 RC

v6.3 is the final release-candidate phase before stable installation.

The Android pipeline now builds:
- an installable debug QA APK
- a release APK
- SHA-256 checksums

If permanent release-signing secrets are configured, the release APK is signed and verified with Android apksigner. If signing secrets are absent, the release variant is intentionally unsigned while the debug APK remains installable for QA.

No release keystore or password is stored in Git. See `ANDROID_RELEASE_SIGNING.md`.

The RC keeps all v5.x/v6.x phone features, unified Windows AI brain routing, Security Center, Reliability Center, and protected sensitive-field behavior.

Do not treat the unsigned release APK as the final stable distribution build.
