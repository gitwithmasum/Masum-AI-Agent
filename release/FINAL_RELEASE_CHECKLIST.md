# Masum AI Agent 1.0.0 — Final Release Checklist

The final stable release is intentionally blocked until every required gate is true.

## Required gates

- Release Candidate QA workflow passes.
- Android release keystore is permanent and backed up securely.
- GitHub Actions release-signing secrets are configured.
- Android signed release passes `apksigner verify --verbose`.
- Windows self-contained installer build passes.
- Real Android phone QA has been completed for wake recognition, Default Assistant behavior, background/battery behavior, SIM call control, notification access, Accessibility commands, camera vision, reminders, bridge pairing and unified AI responses.
- Android and Windows first-run readiness checks are reviewed.
- Final SHA-256 checksums are generated.

## Signing secrets

Configure these in GitHub repository Actions secrets. Never paste their values into source code, commits, issues, README files, or chat:

- `ANDROID_RELEASE_KEYSTORE_BASE64`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS`
- `ANDROID_KEY_PASSWORD`

## Stable build rule

The manual Final Stable Release workflow requires a confirmation that real-device QA was completed. It also fails if release-signing secrets are unavailable.

Default Android CI remains an RC build with version `1.0.0-rc1`. The final workflow passes `-PstableRelease=true` and produces version `1.0.0` with a higher versionCode.
