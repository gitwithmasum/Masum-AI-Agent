# Masum AI Agent Mobile — 1.0 Release Gate

Default CI builds Android version `1.0.0-rc1`. The final stable workflow builds `1.0.0` with a higher versionCode only after permanent release signing and explicit real-device QA confirmation.

The setup screen contains **RUN FIRST-RUN READINESS CHECK**, combining local security/reliability state with the unified brain test when the Windows bridge is paired.

For the cleanest update path, do not install the debug RC if you intend to install only the final stable signed APK.

See:
- `ANDROID_RELEASE_SIGNING.md`
- `release/FINAL_RELEASE_CHECKLIST.md`
- `release/FIRST_RUN_GUIDE.md`
