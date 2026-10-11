from __future__ import annotations

import py_compile
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "release-qa-report.txt"
EXPECTED = "6.3.0"


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
    rows: list[str] = ["Masum AI Agent v6.3 Release QA", ""]

    desktop = read("desktop_companion.py")
    dashboard = read("dashboard.py")
    gradle = read("mobile/android/app/build.gradle")
    installer = read("installer/MasumAI.iss")
    gitignore = read(".gitignore")
    android_workflow = read(".github/workflows/android-companion.yml")

    check(
        f'VERSION = "{EXPECTED}"' in desktop,
        "Windows companion version matches 6.3.0",
        rows,
    )
    check(
        'version="6.3.0"' in dashboard,
        "Bundled AI brain version matches 6.3.0",
        rows,
    )
    check(
        "versionName '6.3.0'" in gradle,
        "Android versionName matches 6.3.0",
        rows,
    )
    check(
        '#define MyAppVersion "6.3.0"' in installer,
        "Windows installer version matches 6.3.0",
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
