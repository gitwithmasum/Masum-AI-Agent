from __future__ import annotations

import py_compile
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "release-qa-report.txt"
EXPECTED = "1.0.0"


def read(path: str) -> str:
    return (ROOT / path).read_text(
        encoding="utf-8",
        errors="replace",
    )


def check(condition: bool, message: str, rows: list[str]) -> None:
    rows.append(("PASS " if condition else "FAIL ") + message)
    if not condition:
        raise AssertionError(message)


def main() -> None:
    rows: list[str] = ["Masum AI Agent 1.0.0 Release QA", ""]

    desktop = read("desktop_companion.py")
    dashboard = read("dashboard.py")
    gradle = read("mobile/android/app/build.gradle")
    installer = read("installer/MasumAI.iss")
    gitignore = read(".gitignore")
    android_workflow = read(".github/workflows/android-companion.yml")

    check(
        'VERSION = "1.0.2-rc1"' in desktop,
        "Windows companion is 1.0.2 RC1",
        rows,
    )
    check(
        f'version="{EXPECTED}"' in dashboard,
        "Bundled AI brain version matches 1.0.0",
        rows,
    )
    check(
        "'1.0.0'" in gradle and
        "'1.0.2-rc1'" in gradle and
        "stableReleaseBuild" in gradle and
        "10004" in gradle,
        "Android RC 1.0.2 uses newer versionCode while stable 1.0.0 remains available",
        rows,
    )
    check(
        '#define MyAppVersion "1.0.2-rc2"' in installer,
        "Windows installer is 1.0.2 RC2",
        rows,
    )
    check(
        "masum-discover-v1" in desktop and
        "private-mobile-pairing-qr.png" in desktop and
        "BridgeDiscovery.find" in read("mobile/android/app/src/main/java/com/gitwithmasum/masumai/BridgeClient.java") and
        "SCAN LAPTOP PAIRING QR" in read("mobile/android/app/src/main/java/com/gitwithmasum/masumai/MainActivity.java"),
        "Smart Bridge Discovery and QR pairing hooks exist",
        rows,
    )
    check(
        "ACCESS_WIFI_STATE" in read("mobile/android/app/src/main/AndroidManifest.xml"),
        "Android can inspect Wi-Fi broadcast details",
        rows,
    )
    check(
        "127.0.0.1" in dashboard,
        "Dashboard retains localhost default",
        rows,
    )
    check(
        "http://127.0.0.1:8765" in desktop,
        "Windows unified brain defaults to localhost",
        rows,
    )
    check(
        "shell=True" not in desktop,
        "Desktop companion has no shell=True execution",
        rows,
    )
    check(
        "ANDROID_KEYSTORE_PASSWORD" in gradle and
        "System.getenv" in gradle,
        "Android release signing reads environment variables",
        rows,
    )
    check(
        'storePassword "' not in gradle and
        'keyPassword "' not in gradle,
        "No Android signing password is hard-coded",
        rows,
    )
    check(
        "ANDROID_RELEASE_KEYSTORE_BASE64" in android_workflow,
        "Android CI supports secret-backed release signing",
        rows,
    )

    for pattern in (
        "*.jks",
        "*.keystore",
        "keystore.properties",
        "release-signing.properties",
    ):
        check(
            pattern in gitignore,
            f"Git ignores {pattern}",
            rows,
        )

    leaked_key_files = [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and path.suffix.lower() in {".jks", ".keystore"}
    ]
    check(
        not leaked_key_files,
        "No Android keystore file is present in the checkout",
        rows,
    )

    secrets_dir = ROOT / "secrets"
    if secrets_dir.exists():
        unexpected = [
            path.name
            for path in secrets_dir.iterdir()
            if path.name != ".gitkeep"
        ]
        check(
            not unexpected,
            "No Gmail OAuth secret/token file is committed",
            rows,
        )

    python_files = [
        "desktop_companion.py",
        "dashboard.py",
        "main.py",
        "multi_agent.py",
        "automation_engine.py",
    ]
    for name in python_files:
        py_compile.compile(
            str(ROOT / name),
            doraise=True,
        )
        rows.append(f"PASS Python syntax: {name}")

    rows.append("")
    rows.append("RESULT: PASS")
    REPORT.write_text(
        "\n".join(rows) + "\n",
        encoding="utf-8",
    )
    print("\n".join(rows))


if __name__ == "__main__":
    main()
