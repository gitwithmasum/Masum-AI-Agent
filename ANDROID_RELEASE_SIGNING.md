# Android Release Signing

Masum AI Agent v6.3 RC supports optional release signing without storing private signing material in Git.

## Permanent signing identity

Use one long-lived Android release keystore for all stable versions. Keep secure backups of the keystore and its passwords. Do not commit the keystore or passwords to this repository.

The Gradle release build reads only these environment variables:

- ANDROID_KEYSTORE_PATH
- ANDROID_KEYSTORE_PASSWORD
- ANDROID_KEY_ALIAS
- ANDROID_KEY_PASSWORD

The GitHub Actions RC workflow can decode a keystore from the repository secret:

- ANDROID_RELEASE_KEYSTORE_BASE64

along with the three password/alias secrets above.

If the secrets are absent, CI still builds:

- a normal installable debug APK for QA
- an unsigned release APK for release-build verification

The unsigned release APK is not the final stable distribution artifact.

## Local key creation

Create the permanent keystore on a trusted local machine using Java keytool or Android Studio's Generate Signed Bundle / APK flow. Keep the keystore outside the repository.

Never paste the keystore, password, alias password, or private key into chat, source code, README files, issues, or commits.

## Verification

A signed release APK should pass:

```text
apksigner verify --verbose <release.apk>
```

The same signing identity must be retained for future APK updates.
