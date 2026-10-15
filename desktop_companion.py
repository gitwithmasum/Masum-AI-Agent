from __future__ import annotations

import ctypes
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import wave
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import numpy as np
import pystray
import pyttsx3
import sounddevice as sd
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from PIL import Image, ImageDraw

load_dotenv(override=True)

APP_NAME = "Masum AI Agent"
VERSION = "1.0.3-rc1"
LOCAL_APP_DATA = Path(
    os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
)
APP_DATA_DIR = LOCAL_APP_DATA / "MasumAI"
MODEL_DIR = APP_DATA_DIR / "models"
CONFIG_PATH = APP_DATA_DIR / "companion-config.json"
LOG_PATH = APP_DATA_DIR / "companion.log"

APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

SAMPLE_RATE = int(os.getenv("DESKTOP_SAMPLE_RATE", "16000"))
WAKE_SECONDS = float(os.getenv("DESKTOP_WAKE_SECONDS", "5"))
COMMAND_SECONDS = float(os.getenv("DESKTOP_COMMAND_SECONDS", "7"))
WAKE_MODEL_NAME = os.getenv("DESKTOP_WAKE_MODEL", "small").strip() or "small"
COMMAND_MODEL_NAME = (
    os.getenv("DESKTOP_COMMAND_MODEL", "small").strip() or "small"
)
COMPUTE_TYPE = os.getenv("DESKTOP_COMPUTE_TYPE", "int8").strip() or "int8"
BRIDGE_PORT = int(os.getenv("DESKTOP_BRIDGE_PORT", "8767"))
BRAIN_URL = os.getenv("MASUM_BRAIN_URL", "http://127.0.0.1:8765").strip().rstrip("/")
BRAIN_START_TIMEOUT = float(os.getenv("MASUM_BRAIN_START_TIMEOUT", "20"))
BRAIN_REPLY_TIMEOUT = float(os.getenv("MASUM_BRAIN_REPLY_TIMEOUT", "150"))

DEFAULT_CONFIG = {
    "persona": "cirilla",
    "wake_enabled": True,
    "project_path": os.getenv("MASUM_AI_PROJECT_PATH", "").strip(),
    "bridge_enabled": True,
    "bridge_port": BRIDGE_PORT,
    "bridge_secret": "",
}

CIRILLA_WAKE_PHRASES = [
    "hey cirilla",
    "cirilla",
    "hey sirilla",
    "sirilla",
    "cirila",
    "সিরিলা",
    "হেই সিরিলা",
]
GERALT_WAKE_PHRASES = [
    "hey geralt",
    "geralt",
    "hey gerald",
    "gerald",
    "গেরাল্ট",
    "হেই গেরাল্ট",
]

STOP_EVENT = threading.Event()
CONFIG_LOCK = threading.RLock()
TTS_LOCK = threading.Lock()
MODEL_LOCK = threading.Lock()
BRIDGE_NONCE_LOCK = threading.Lock()
BRIDGE_NONCES: dict[str, int] = {}
BRAIN_PROCESS_LOCK = threading.Lock()
brain_process: subprocess.Popen | None = None
BRIDGE_STATE_LOCK = threading.Lock()
bridge_state = "starting"
bridge_restart_count = 0
bridge_last_error = ""
listener_last_error = ""
VOICE_STATE_LOCK = threading.Lock()
VOICE_TEST_LOCK = threading.Lock()
VOICE_TEST_ACTIVE = threading.Event()
voice_last_text = ""
voice_last_detected = False
voice_last_level = 0.0
voice_last_time = 0.0
voice_last_status = "Waiting for microphone"
diagnostics_open = threading.Event()


def update_voice_state(text: str | None = None, level: float | None = None,
                       detected: bool | None = None, status: str | None = None) -> None:
    global voice_last_text, voice_last_level, voice_last_detected
    global voice_last_time, voice_last_status
    with VOICE_STATE_LOCK:
        if text is not None:
            voice_last_text = text[:200]
            voice_last_time = time.time()
        if level is not None:
            voice_last_level = level
        if detected is not None:
            voice_last_detected = detected
        if status is not None:
            voice_last_status = status


def voice_state_snapshot() -> dict[str, Any]:
    with VOICE_STATE_LOCK:
        return {
            "text": voice_last_text,
            "level": voice_last_level,
            "detected": voice_last_detected,
            "time": voice_last_time,
            "status": voice_last_status,
            "error": listener_last_error,
        }


wake_model: WhisperModel | None = None
command_model: WhisperModel | None = None
tts_engine: Any = None
tray_icon: pystray.Icon | None = None


def ensure_single_instance() -> None:
    if os.name != "nt":
        return
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(
        None,
        False,
        "MasumAIAgentDesktopCompanion-v4",
    )
    if handle and kernel32.GetLastError() == 183:
        raise SystemExit(0)


def save_config(config_data: dict[str, Any]) -> None:
    with CONFIG_LOCK:
        CONFIG_PATH.write_text(
            json.dumps(config_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def load_config() -> dict[str, Any]:
    with CONFIG_LOCK:
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                merged = {**DEFAULT_CONFIG, **data}
                if merged.get("persona") not in {"cirilla", "geralt"}:
                    merged["persona"] = "cirilla"
                return merged
            except Exception:
                logging.exception("Could not read companion config.")

        initial = DEFAULT_CONFIG.copy()
        save_config(initial)
        return initial


config = load_config()
if not str(config.get("bridge_secret") or "").strip():
    config["bridge_secret"] = secrets.token_hex(32)
    save_config(config)


def set_config_value(key: str, value: Any) -> None:
    config[key] = value
    save_config(config)
    if tray_icon is not None:
        try:
            tray_icon.update_menu()
        except Exception:
            pass


def persona_name() -> str:
    return "Geralt" if config.get("persona") == "geralt" else "Cirilla"


def wake_phrases() -> list[str]:
    return (
        GERALT_WAKE_PHRASES
        if config.get("persona") == "geralt"
        else CIRILLA_WAKE_PHRASES
    )


def normalize_text(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^\w\s@.+-]+", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def get_tts_engine() -> Any:
    global tts_engine
    if tts_engine is None:
        tts_engine = pyttsx3.init()
        tts_engine.setProperty("rate", 175)
        tts_engine.setProperty("volume", 1.0)
    return tts_engine


def choose_voice(engine: Any) -> None:
    target = config.get("persona", "cirilla")
    female_hints = ("zira", "aria", "jenny", "susan", "hazel", "female")
    male_hints = ("david", "mark", "guy", "george", "daniel", "male")
    hints = male_hints if target == "geralt" else female_hints

    for voice in engine.getProperty("voices") or []:
        haystack = (
            f"{getattr(voice, 'name', '')} "
            f"{getattr(voice, 'id', '')}"
        ).lower()
        if any(hint in haystack for hint in hints):
            engine.setProperty("voice", voice.id)
            return


def speak(message: str) -> None:
    if not message:
        return

    logging.info("TTS: %s", message)
    try:
        with TTS_LOCK:
            engine = get_tts_engine()
            choose_voice(engine)
            engine.setProperty(
                "rate",
                165 if config.get("persona") == "geralt" else 178,
            )
            engine.say(message)
            engine.runAndWait()
    except Exception:
        logging.exception("TTS failed.")


def get_model(kind: str) -> WhisperModel:
    global wake_model, command_model

    with MODEL_LOCK:
        if kind == "wake":
            if wake_model is None:
                logging.info("Loading wake model: %s", WAKE_MODEL_NAME)
                wake_model = WhisperModel(
                    WAKE_MODEL_NAME,
                    device="cpu",
                    compute_type=COMPUTE_TYPE,
                    download_root=str(MODEL_DIR),
                )
            return wake_model

        if command_model is None:
            logging.info("Loading command model: %s", COMMAND_MODEL_NAME)
            command_model = WhisperModel(
                COMMAND_MODEL_NAME,
                device="cpu",
                compute_type=COMPUTE_TYPE,
                download_root=str(MODEL_DIR),
            )
        return command_model


def record_wav(seconds: float) -> Path:
    frames = max(1, int(SAMPLE_RATE * seconds))
    # The diagnostic microphone test and wake listener must never
    # record from the same microphone simultaneously.
    with VOICE_TEST_LOCK:
        audio = sd.rec(
            frames,
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )
        sd.wait()

    level = float(np.sqrt(np.mean(np.square(audio[:, 0], dtype=np.float64))))
    update_voice_state(level=level, status="Captured audio")
    pcm = np.clip(audio[:, 0], -1.0, 1.0)
    pcm = (pcm * 32767).astype(np.int16)

    handle = tempfile.NamedTemporaryFile(
        prefix="masum-ai-",
        suffix=".wav",
        delete=False,
    )
    path = Path(handle.name)
    handle.close()

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm.tobytes())

    return path


def transcribe(path: Path, kind: str) -> str:
    model = get_model(kind)
    is_wake = kind == "wake"
    # Small model + wake-phrase context improves recognition of the
    # uncommon assistant names. Preserve command-language auto-detection.
    wake_prompt = (
        "The assistant's name is Geralt. Wake phrase: Hey Geralt."
        if config.get("persona") == "geralt"
        else "The assistant's name is Cirilla. Wake phrase: Hey Cirilla."
    )
    segments, _info = model.transcribe(
        str(path),
        language="en" if is_wake else None,
        beam_size=5 if is_wake else 4,
        vad_filter=not is_wake,
        condition_on_previous_text=False,
        initial_prompt=wake_prompt if is_wake else None,
    )
    return " ".join(
        (segment.text or "").strip()
        for segment in segments
        if (segment.text or "").strip()
    ).strip()


def listen(seconds: float, kind: str) -> str:
    path: Path | None = None
    try:
        path = record_wav(seconds)
        if kind == "wake" and voice_state_snapshot()["level"] < 0.003:
            update_voice_state(text="", detected=False, status="Quiet audio skipped")
            return ""
        result = transcribe(path, kind)
        if kind == "wake":
            # Whisper can echo initial_prompt on silent/ambiguous audio.
            normalized = normalize_text(result)
            if normalized.startswith("the assistant s name is") or normalized in {
                "wake phrase", "the assistant s name is cirilla wake phrase",
                "the assistant s name is geralt wake phrase",
            }:
                return ""
        return result
    except Exception as error:
        logging.exception("Microphone/transcription failed.")
        global listener_last_error
        listener_last_error = str(error)[:300]
        return ""
    finally:
        if path is not None:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def extract_wake_command(text: str) -> tuple[bool, str]:
    normalized = normalize_text(text)
    for phrase in wake_phrases():
        normalized_phrase = normalize_text(phrase)
        position = normalized.find(normalized_phrase)
        if position >= 0:
            command = normalized[position + len(normalized_phrase):].strip()
            return True, command
    return False, ""


def find_vscode() -> str | None:
    candidates = [
        LOCAL_APP_DATA / "Programs" / "Microsoft VS Code" / "Code.exe",
        Path(os.getenv("ProgramFiles", "C:/Program Files"))
        / "Microsoft VS Code"
        / "Code.exe",
        Path(os.getenv("ProgramFiles(x86)", "C:/Program Files (x86)"))
        / "Microsoft VS Code"
        / "Code.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return shutil.which("code")


def find_chrome() -> str | None:
    candidates = [
        Path(os.getenv("ProgramFiles", "C:/Program Files"))
        / "Google"
        / "Chrome"
        / "Application"
        / "chrome.exe",
        Path(os.getenv("ProgramFiles(x86)", "C:/Program Files (x86)"))
        / "Google"
        / "Chrome"
        / "Application"
        / "chrome.exe",
        LOCAL_APP_DATA
        / "Google"
        / "Chrome"
        / "Application"
        / "chrome.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return shutil.which("chrome")


def discover_project_path() -> Path | None:
    configured = str(config.get("project_path") or "").strip()
    if configured:
        candidate = Path(configured)
        if candidate.exists():
            return candidate

    candidates = [
        Path("D:/OneDrive/Web Development/Masum-AI-Agent"),
        Path.home() / "OneDrive" / "Web Development" / "Masum-AI-Agent",
        Path.home() / "Documents" / "Masum-AI-Agent",
        Path.home() / "Desktop" / "Masum-AI-Agent",
    ]
    for candidate in candidates:
        if candidate.exists():
            set_config_value("project_path", str(candidate))
            return candidate

    return None


def chrome_profiles() -> list[dict[str, str]]:
    state_path = (
        LOCAL_APP_DATA
        / "Google"
        / "Chrome"
        / "User Data"
        / "Local State"
    )
    if not state_path.exists():
        return []

    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        info_cache = payload.get("profile", {}).get("info_cache", {})
    except Exception:
        logging.exception("Could not read Chrome profile metadata.")
        return []

    profiles: list[dict[str, str]] = []
    for directory, meta in info_cache.items():
        profiles.append(
            {
                "directory": directory,
                "name": str(meta.get("name") or ""),
                "shortcut_name": str(meta.get("shortcut_name") or ""),
                "user_name": str(meta.get("user_name") or ""),
            }
        )

    return profiles


def resolve_chrome_profile(query: str) -> str | None:
    target = normalize_text(query)
    if not target:
        return None

    exact: list[str] = []
    partial: list[str] = []

    for profile in chrome_profiles():
        aliases = [
            profile["directory"],
            profile["name"],
            profile["shortcut_name"],
            profile["user_name"],
        ]
        normalized_aliases = [normalize_text(alias) for alias in aliases if alias]

        if target in normalized_aliases:
            exact.append(profile["directory"])
        elif any(target in alias for alias in normalized_aliases):
            partial.append(profile["directory"])

    choices = list(dict.fromkeys(exact or partial))
    return choices[0] if len(choices) == 1 else None


def open_chrome(
    url: str | None = None,
    profile_query: str | None = None,
) -> bool:
    chrome = find_chrome()
    if not chrome:
        return False

    args = [chrome]

    if profile_query:
        profile = resolve_chrome_profile(profile_query)
        if not profile:
            speak("I could not uniquely find that Chrome profile.")
            return True
        args.append(f"--profile-directory={profile}")

    if url:
        args.append(url)

    subprocess.Popen(args)
    return True


def open_vscode(project: Path | None = None) -> bool:
    executable = find_vscode()
    if not executable:
        return False

    args = [executable]
    if project is not None:
        args.append(str(project))

    if executable.lower().endswith((".cmd", ".bat")):
        subprocess.Popen(["cmd.exe", "/c", *args])
    else:
        subprocess.Popen(args)

    return True


def open_folder(folder: Path) -> bool:
    try:
        if os.name == "nt":
            os.startfile(str(folder))
        else:
            webbrowser.open(folder.as_uri())
        return True
    except Exception:
        logging.exception("Could not open folder: %s", folder)
        return False


def handle_command(raw_text: str) -> None:
    command = normalize_text(raw_text)
    logging.info("Command: %s", command)

    if re.search(r"\b(switch to|use) geralt\b", command) or command in {"গেরাল্ট মোড", "গেরাল্ট চালু করো"}:
        set_config_value("persona", "geralt")
        speak("Geralt mode active.")
        return

    if re.search(r"\b(switch to|use) cirilla\b", command) or command in {"সিরিলা মোড", "সিরিলা চালু করো"}:
        set_config_value("persona", "cirilla")
        speak("Cirilla mode active.")
        return

    if command in {
        "open vs code",
        "open vscode",
        "vs code open",
        "vscode open",
        "ভিএস কোড খোলো",
    }:
        speak(
            "Opening VS Code."
            if open_vscode()
            else "VS Code was not found."
        )
        return

    if any(
        phrase in command
        for phrase in (
            "open masum ai agent",
            "open masum ai agent project",
            "open my ai agent project",
            "মাসুম এআই এজেন্ট প্রজেক্ট খোলো",
            "আমার এআই প্রজেক্ট খোলো",
        )
    ):
        project = discover_project_path()
        if project is None:
            speak("I could not find the Masum AI Agent project folder.")
            return

        speak(
            "Opening Masum AI Agent project."
            if open_vscode(project)
            else "VS Code was not found."
        )
        return

    profile_match = re.match(
        r"open (chrome|gmail) (?:with |profile )(.+)$",
        command,
    )
    if profile_match:
        target = profile_match.group(1)
        profile_query = profile_match.group(2)
        url = "https://mail.google.com/" if target == "gmail" else None

        if open_chrome(url, profile_query):
            speak(f"Opening {target} with that Chrome profile.")
        else:
            speak("Google Chrome was not found.")
        return

    if command in {"open chrome", "chrome open", "ক্রোম খোলো"}:
        speak(
            "Opening Chrome."
            if open_chrome()
            else "Google Chrome was not found."
        )
        return

    sites = {
        "open github": "https://github.com/",
        "গিটহাব খোলো": "https://github.com/",
        "open gmail": "https://mail.google.com/",
        "জিমেইল খোলো": "https://mail.google.com/",
        "open chatgpt": "https://chatgpt.com/",
        "চ্যাটজিপিটি খোলো": "https://chatgpt.com/",
        "open youtube": "https://www.youtube.com/",
        "ইউটিউব খোলো": "https://www.youtube.com/",
    }
    if command in sites:
        if not open_chrome(sites[command]):
            webbrowser.open(sites[command])
        speak(command.replace("open ", "Opening ") + ".")
        return

    if command in {"open downloads", "downloads open", "ডাউনলোডস খোলো"}:
        speak(
            "Opening Downloads."
            if open_folder(Path.home() / "Downloads")
            else "I could not open Downloads."
        )
        return

    if command in {"open documents", "documents open", "ডকুমেন্টস খোলো"}:
        speak(
            "Opening Documents."
            if open_folder(Path.home() / "Documents")
            else "I could not open Documents."
        )
        return

    if command in {"go to sleep", "stop listening", "wake mode off"}:
        speak("Wake listening is off.")
        set_config_value("wake_enabled", False)
        return

    ok, answer, _agents = ask_unified_brain(raw_text)
    if ok:
        speak(answer)
    else:
        speak("Unified AI brain is unavailable. " + answer)



def lan_ip_address() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return str(sock.getsockname()[0])
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        sock.close()


def bridge_pairing_path() -> Path:
    return APP_DATA_DIR / "mobile-bridge-pairing.txt"


def write_bridge_pairing_info() -> Path:
    port = int(config.get("bridge_port") or BRIDGE_PORT)
    path = bridge_pairing_path()
    path.write_text(
        "Masum AI Agent Mobile ↔ Laptop Pairing\n"
        f"Bridge URL: http://{lan_ip_address()}:{port}\n"
        f"Pairing Key: {config.get('bridge_secret', '')}\n\n"
        "Use only on a trusted private Wi-Fi network. "
        "The key authenticates commands with HMAC-SHA256 and is never sent directly.\n"
        "Unified Brain: Android questions can route through this bridge to the "
        "laptop local Ollama multi-agent core.\n",
        encoding="utf-8",
    )
    return path



def brain_status() -> tuple[bool, str]:
    try:
        request = urllib.request.Request(
            f"{BRAIN_URL}/api/status",
            headers={"Accept": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(
                response.read().decode("utf-8", errors="replace")
            )
        model = (
            payload.get("ollama", {}).get("detail")
            or payload.get("model")
            or "local AI"
        )
        return True, f"Unified brain online with {model}."
    except Exception as error:
        return False, str(error)


def installed_brain_executable() -> Path | None:
    candidates: list[Path] = []

    if getattr(sys, "frozen", False):
        candidates.append(
            Path(sys.executable).resolve().parent /
            "MasumAIBrain.exe"
        )

    candidates.append(
        Path(__file__).resolve().parent /
        "MasumAIBrain.exe"
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def packaged_brain_environment() -> tuple[dict[str, str], Path]:
    runtime_root = APP_DATA_DIR / "brain-data"
    data_dir = runtime_root / "data"
    knowledge_dir = runtime_root / "knowledge"
    reports_dir = runtime_root / "research_reports"
    secrets_dir = runtime_root / "secrets"

    for path in (
        runtime_root,
        data_dir,
        knowledge_dir,
        reports_dir,
        secrets_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["DASHBOARD_HOST"] = "127.0.0.1"
    env["DASHBOARD_PORT"] = "8765"
    env["DASHBOARD_AUTO_OPEN"] = "false"
    env.setdefault(
        "MEMORY_DB_PATH",
        str(data_dir / "memory.db"),
    )
    env.setdefault(
        "KNOWLEDGE_DIR",
        str(knowledge_dir),
    )
    env.setdefault(
        "RESEARCH_REPORT_DIR",
        str(reports_dir),
    )
    env.setdefault(
        "GMAIL_CREDENTIALS_PATH",
        str(secrets_dir / "gmail_credentials.json"),
    )
    env.setdefault(
        "GMAIL_TOKEN_PATH",
        str(secrets_dir / "gmail_token.json"),
    )
    env.setdefault(
        "AUTOMATION_TASKS_PATH",
        str(data_dir / "automations.json"),
    )
    env.setdefault(
        "AUTOMATION_LOG_PATH",
        str(data_dir / "automation_log.jsonl"),
    )
    env["MASUM_AI_PACKAGED_BRAIN"] = "1"

    return env, runtime_root


def project_python(project: Path) -> str | None:
    candidates = [
        project / ".venv" / "Scripts" / "python.exe",
        project / ".venv" / "Scripts" / "pythonw.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    for command in ("python", "py"):
        found = shutil.which(command)
        if found:
            return found

    return None


def start_brain_server() -> tuple[bool, str]:
    global brain_process

    online, detail = brain_status()
    if online:
        return True, detail

    packaged_brain = installed_brain_executable()
    project = None
    dashboard = None
    python_exe = None

    if packaged_brain is None:
        project = discover_project_path()
        if project is None:
            return False, (
                "Bundled AI brain was not found, and the Masum AI Agent "
                "development project folder was not found."
            )

        dashboard = project / "dashboard.py"
        if not dashboard.exists():
            return False, "dashboard.py was not found in the project."

        python_exe = project_python(project)
        if not python_exe:
            return False, (
                "Bundled AI brain was not found, and a Python runtime "
                "for the development project was not found."
            )

    with BRAIN_PROCESS_LOCK:
        online, detail = brain_status()
        if online:
            return True, detail

        if brain_process is None or brain_process.poll() is not None:
            creationflags = 0
            if os.name == "nt":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

            try:
                if packaged_brain is not None:
                    env, runtime_root = packaged_brain_environment()
                    args = [str(packaged_brain)]
                    cwd = runtime_root
                else:
                    env = os.environ.copy()
                    env["DASHBOARD_HOST"] = "127.0.0.1"
                    env["DASHBOARD_PORT"] = "8765"
                    env["DASHBOARD_AUTO_OPEN"] = "false"

                    if Path(python_exe).name.lower() == "py.exe":
                        args = [python_exe, "-3.14", str(dashboard)]
                    else:
                        args = [python_exe, str(dashboard)]

                    cwd = project

                brain_process = subprocess.Popen(
                    args,
                    cwd=str(cwd),
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creationflags,
                )
            except Exception as error:
                logging.exception("Could not start unified brain server.")
                return False, f"Could not start the local AI brain: {error}"

    deadline = time.time() + BRAIN_START_TIMEOUT
    while time.time() < deadline:
        online, detail = brain_status()
        if online:
            return True, detail
        time.sleep(0.7)

    return False, (
        "The local AI brain did not become ready in time. "
        "Check Ollama and the project Python environment."
    )


def clean_spoken_answer(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[*_#>]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 1800:
        text = text[:1797].rstrip() + "..."
    return text


def ask_unified_brain(prompt: str) -> tuple[bool, str, list[str]]:
    question = str(prompt or "").strip()
    if not question:
        return False, "The AI prompt is empty.", []

    online, detail = start_brain_server()
    if not online:
        return False, detail, []

    payload = json.dumps(
        {
            "message": question,
            "agent": "auto",
            "team_review": False,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{BRAIN_URL}/api/chat",
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=BRAIN_REPLY_TIMEOUT,
        ) as response:
            result = json.loads(
                response.read().decode("utf-8", errors="replace")
            )

        answer = clean_spoken_answer(result.get("answer") or "")
        agents = [
            str(item)
            for item in result.get("agents", [])
            if item
        ]
        if not answer:
            return False, "The unified brain returned an empty answer.", agents
        return True, answer, agents
    except urllib.error.HTTPError as error:
        try:
            body = json.loads(
                error.read().decode("utf-8", errors="replace")
            )
            detail = body.get("detail") or str(error)
        except Exception:
            detail = str(error)
        return False, f"Unified brain error: {detail}", []
    except Exception as error:
        logging.exception("Unified brain request failed.")
        return False, f"Unified brain unavailable: {error}", []




def first_run_guide_text() -> str:
    return "\n".join(
        [
            "Masum AI Agent 1.0.0 — First Run Guide",
            "",
            "1. Keep Ollama installed and make sure the selected local model is available.",
            "2. Start Masum AI Agent; Cirilla runs from the Windows tray.",
            "3. Open Mobile Pairing Info and pair the Android app on the same trusted private Wi-Fi.",
            "4. On Android, complete the Security + Permission Center setup.",
            "5. Run the Android First-Run Readiness Check.",
            "6. Test: brain status, open VS Code on laptop, flashlight on phone, and one safe AI question.",
            "",
            "Security: no arbitrary voice-to-PowerShell/CMD execution. The AI brain remains localhost-only.",
            "If Windows SmartScreen warns, verify the installer came from the official project release and checksum before continuing.",
        ]
    )


def write_first_run_guide() -> Path:
    path = APP_DATA_DIR / "first-run-guide.txt"
    path.write_text(
        first_run_guide_text() + "\n",
        encoding="utf-8",
    )
    return path


def open_first_run_guide(
    _icon=None,
    _item=None,
) -> None:
    path = write_first_run_guide()
    try:
        os.startfile(str(path))
    except Exception:
        logging.exception(
            "Could not open first run guide."
        )


def security_health_text() -> str:
    project = discover_project_path()
    brain_ok, brain_detail = brain_status()
    secret_ready = bool(
        str(config.get("bridge_secret") or "").strip()
    )
    bridge_enabled = bool(
        config.get("bridge_enabled", True)
    )
    brain_local = (
        BRAIN_URL.startswith("http://127.0.0.1")
        or BRAIN_URL.startswith("http://localhost")
    )

    lines = [
        f"Masum AI Agent Windows Security Health v{VERSION}",
        f"Wake listening: {'ON' if config.get('wake_enabled', True) else 'OFF'}",
        f"Bridge enabled: {'YES' if bridge_enabled else 'NO'}",
        f"Bridge HMAC key configured: {'YES' if secret_ready else 'NO'}",
        "Replay protection: timestamp + one-time nonce",
        f"Unified brain URL local-only: {'YES' if brain_local else 'CHECK CONFIG'}",
        f"Bundled AI brain: {'FOUND' if installed_brain_executable() is not None else 'NOT FOUND'}",
        f"Development project fallback: {'FOUND' if project is not None else 'NOT FOUND'}",
        f"Unified brain: {'ONLINE' if brain_ok else 'OFFLINE / ON-DEMAND'}",
        f"Brain detail: {brain_detail if brain_ok else 'Starts on demand when local runtime and Ollama are available.'}",
        "OS actions: explicit allowlist only",
        "Arbitrary voice-to-PowerShell/CMD: DISABLED",
        "Bridge transport: authenticated local HTTP; use trusted private Wi-Fi",
    ]
    return "\n".join(lines)


def write_security_health_report() -> Path:
    path = APP_DATA_DIR / "security-health.txt"
    path.write_text(
        security_health_text() + "\n",
        encoding="utf-8",
    )
    return path


def open_security_health_report(
    _icon=None,
    _item=None,
) -> None:
    path = write_security_health_report()
    try:
        os.startfile(str(path))
    except Exception:
        logging.exception(
            "Could not open security health report."
        )



def set_bridge_runtime_state(
    state: str,
    error: str = "",
) -> None:
    global bridge_state, bridge_last_error

    with BRIDGE_STATE_LOCK:
        bridge_state = state
        bridge_last_error = str(error or "").strip()


def reliability_health_text() -> str:
    with BRIDGE_STATE_LOCK:
        current_state = bridge_state
        restarts = bridge_restart_count
        last_error = bridge_last_error

    project = discover_project_path()
    brain_ok, _brain_detail = brain_status()

    lines = [
        f"Masum AI Agent Windows Reliability v{VERSION}",
        f"Bridge runtime: {current_state.upper()}",
        f"Bridge recoveries: {restarts}",
        f"Bridge last error: {last_error or 'none'}",
        f"Wake listener: {'ENABLED' if config.get('wake_enabled', True) else 'PAUSED'}",
        f"Listener last error: {listener_last_error or 'none'}",
        f"Project folder: {'FOUND' if project is not None else 'NOT FOUND'}",
        f"Unified brain: {'ONLINE' if brain_ok else 'OFFLINE / ON-DEMAND'}",
        "Bridge server: retry-on-failure enabled",
        "Voice listener: exception recovery enabled",
        "Startup: Windows sign-in shortcut supported by installer",
    ]
    return "\n".join(lines)


def write_reliability_report() -> Path:
    path = APP_DATA_DIR / "reliability-health.txt"
    path.write_text(
        reliability_health_text() + "\n",
        encoding="utf-8",
    )
    return path


def open_reliability_report(
    _icon=None,
    _item=None,
) -> None:
    path = write_reliability_report()

    try:
        os.startfile(str(path))
    except Exception:
        logging.exception(
            "Could not open reliability report."
        )


def bridge_action(action: str) -> tuple[bool, str]:
    action = str(action or "").strip().lower()

    if action == "status":
        brain_ok, _brain_detail = brain_status()
        brain_text = "brain online" if brain_ok else "brain available on demand"
        return True, (
            f"Laptop bridge online. {persona_name()} is active; "
            f"{brain_text}."
        )

    if action == "brain_status":
        ok, detail = start_brain_server()
        return ok, detail

    if action == "security_status":
        return True, security_health_text()

    if action == "reliability_status":
        return True, reliability_health_text()

    if action == "open_vscode":
        ok = open_vscode()
        return ok, "Opening VS Code on the laptop." if ok else "VS Code was not found."

    if action == "open_project":
        project = discover_project_path()
        if project is None:
            return False, "Masum AI Agent project folder was not found."
        ok = open_vscode(project)
        return ok, "Opening Masum AI Agent project." if ok else "VS Code was not found."

    if action == "open_chrome":
        ok = open_chrome()
        return ok, "Opening Chrome on the laptop." if ok else "Chrome was not found."

    if action == "open_github":
        ok = open_chrome("https://github.com/")
        return ok, "Opening GitHub on the laptop." if ok else "Chrome was not found."

    if action == "open_gmail":
        ok = open_chrome("https://mail.google.com/")
        return ok, "Opening Gmail on the laptop." if ok else "Chrome was not found."

    if action == "open_chatgpt":
        ok = open_chrome("https://chatgpt.com/")
        return ok, "Opening ChatGPT on the laptop." if ok else "Chrome was not found."

    if action == "open_downloads":
        ok = open_folder(Path.home() / "Downloads")
        return ok, "Opening laptop Downloads." if ok else "Downloads could not be opened."

    return False, "That laptop action is not on the bridge allowlist."


def verify_bridge_request(
    timestamp: str,
    nonce: str,
    signature: str,
    body: bytes,
) -> bool:
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False

    now = int(time.time())
    if abs(now - ts) > 60:
        return False

    if not re.fullmatch(r"[A-Za-z0-9-]{16,80}", nonce or ""):
        return False

    with BRIDGE_NONCE_LOCK:
        expired = [key for key, value in BRIDGE_NONCES.items() if now - value > 120]
        for key in expired:
            BRIDGE_NONCES.pop(key, None)
        if nonce in BRIDGE_NONCES:
            return False

    canonical = (
        str(ts).encode("utf-8")
        + b"\n"
        + nonce.encode("utf-8")
        + b"\n"
        + body
    )
    expected = hmac.new(
        str(config.get("bridge_secret") or "").encode("utf-8"),
        canonical,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature or ""):
        return False

    with BRIDGE_NONCE_LOCK:
        BRIDGE_NONCES[nonce] = now
    return True


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "MasumBridge/1.0"

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:
        if self.path not in {"/action", "/brain"}:
            self._json(404, {"ok": False, "message": "Not found."})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0

        if length <= 0 or length > 4096:
            self._json(400, {"ok": False, "message": "Invalid request size."})
            return

        body = self.rfile.read(length)
        if not verify_bridge_request(
            self.headers.get("X-Masum-Timestamp", ""),
            self.headers.get("X-Masum-Nonce", ""),
            self.headers.get("X-Masum-Signature", ""),
            body,
        ):
            self._json(401, {"ok": False, "message": "Bridge authentication failed."})
            return

        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            self._json(400, {"ok": False, "message": "Invalid JSON."})
            return

        if self.path == "/brain":
            prompt = str(payload.get("prompt") or "").strip()
            if not prompt:
                self._json(400, {"ok": False, "message": "Brain prompt is empty."})
                return

            ok, message, agents = ask_unified_brain(prompt)
            self._json(
                200 if ok else 503,
                {"ok": ok, "message": message, "agents": agents},
            )
            return

        ok, message = bridge_action(str(payload.get("action") or ""))
        self._json(200 if ok else 400, {"ok": ok, "message": message})

    def log_message(self, format: str, *args: Any) -> None:
        logging.info("Bridge: " + format, *args)


class ResilientBridgeServer(
    ThreadingHTTPServer
):
    allow_reuse_address = True


def bridge_server_loop() -> None:
    global bridge_restart_count

    if not config.get("bridge_enabled", True):
        set_bridge_runtime_state("disabled")
        return

    port = int(
        config.get("bridge_port") or
        BRIDGE_PORT
    )
    write_bridge_pairing_info()

    delay = 1.0

    while not STOP_EVENT.is_set():
        server = None

        try:
            server = ResilientBridgeServer(
                ("0.0.0.0", port),
                BridgeHandler,
            )
            server.daemon_threads = True

            set_bridge_runtime_state("online")
            logging.info(
                "Mobile bridge listening on port %s",
                port,
            )

            server.serve_forever(
                poll_interval=0.8
            )

            if STOP_EVENT.is_set():
                break

            raise RuntimeError(
                "Bridge server stopped unexpectedly."
            )
        except Exception as error:
            bridge_restart_count += 1
            set_bridge_runtime_state(
                "recovering",
                str(error),
            )
            logging.exception(
                "Mobile bridge failure on port %s; retrying.",
                port,
            )

            if STOP_EVENT.wait(delay):
                break

            delay = min(
                delay * 2.0,
                30.0,
            )
        finally:
            if server is not None:
                try:
                    server.server_close()
                except Exception:
                    pass

    set_bridge_runtime_state("stopped")

def open_pairing_info(_icon=None, _item=None) -> None:
    path = write_bridge_pairing_info()
    try:
        os.startfile(str(path))
    except Exception:
        logging.exception("Could not open bridge pairing info.")



DISCOVERY_PORT = 8768


def discovery_server_loop() -> None:
    """Reply to paired local clients, never broadcasting the pairing key."""
    while not STOP_EVENT.is_set():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", DISCOVERY_PORT))
            sock.settimeout(1.0)
            while not STOP_EVENT.is_set():
                try:
                    raw, address = sock.recvfrom(1024)
                except socket.timeout:
                    continue
                try:
                    probe = json.loads(raw.decode("utf-8"))
                    nonce = str(probe.get("nonce", ""))
                    if probe.get("type") != "masum-discover-v1" or not re.fullmatch(r"[0-9a-f]{32}", nonce):
                        continue
                    port = int(config.get("bridge_port") or BRIDGE_PORT)
                    interface = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    try:
                        interface.connect((address[0], address[1]))
                        url = f"http://{interface.getsockname()[0]}:{port}"
                    finally:
                        interface.close()
                    signature = hmac.new(
                        str(config.get("bridge_secret", "")).encode("utf-8"),
                        (nonce + "\n" + url).encode("utf-8"),
                        hashlib.sha256,
                    ).hexdigest()
                    sock.sendto(json.dumps({
                        "type": "masum-discover-reply-v1",
                        "nonce": nonce,
                        "url": url,
                        "signature": signature,
                    }).encode("utf-8"), address)
                except Exception:
                    logging.debug("Ignored invalid discovery probe", exc_info=True)
        except OSError as error:
            logging.warning("LAN discovery unavailable: %s", error)
            STOP_EVENT.wait(5)
        finally:
            sock.close()


def open_pairing_qr(_icon=None, _item=None) -> None:
    """Show a private QR; it contains the shared key and must not be shared."""
    try:
        import qrcode
        payload = json.dumps({
            "type": "masum-pair-v1",
            "url": f"http://{lan_ip_address()}:{int(config.get('bridge_port') or BRIDGE_PORT)}",
            "key": str(config.get("bridge_secret", "")),
        })
        path = APP_DATA_DIR / "private-mobile-pairing-qr.png"
        qrcode.make(payload).save(path)
        os.startfile(str(path))
    except Exception:
        logging.exception("Unable to show private mobile pairing QR")


def listener_loop() -> None:
    global listener_last_error

    time.sleep(2.0)
    logging.info(
        "%s desktop companion started. Wake listening: %s",
        APP_NAME,
        "ON" if config.get("wake_enabled", True) else "OFF",
    )

    recovery_delay = 1.0

    while not STOP_EVENT.is_set():
        try:
            if VOICE_TEST_ACTIVE.is_set() or not config.get(
                "wake_enabled",
                True,
            ):
                STOP_EVENT.wait(0.5)
                recovery_delay = 1.0
                continue

            text = listen(
                WAKE_SECONDS,
                "wake",
            )
            if text:
                logging.info("Wake transcription: %s", text[:160])
            update_voice_state(text=text, detected=False,
                               status="Recognized speech" if text else "No recognized speech")
            if not text:
                recovery_delay = 1.0
                continue

            (
                detected,
                inline_command,
            ) = extract_wake_command(text)

            if not detected:
                recovery_delay = 1.0
                continue

            logging.info(
                "Wake detected: %s",
                text,
            )
            update_voice_state(detected=True, status="Wake phrase detected")

            if inline_command:
                handle_command(
                    inline_command
                )
                recovery_delay = 1.0
                continue

            speak("Yes?")

            command = listen(
                COMMAND_SECONDS,
                "command",
            )

            if command:
                handle_command(command)
            else:
                speak(
                    "I did not hear a command."
                )

            listener_last_error = ""
            recovery_delay = 1.0
        except Exception as error:
            listener_last_error = str(error)
            logging.exception(
                "Voice listener recovered from an unexpected error."
            )

            if STOP_EVENT.wait(
                recovery_delay
            ):
                break

            recovery_delay = min(
                recovery_delay * 2.0,
                20.0,
            )


def open_voice_diagnostics(_icon=None, _item=None) -> None:
    """Keep the tray responsive while a separate thread owns the Tk UI."""
    if diagnostics_open.is_set():
        return
    diagnostics_open.set()

    def show() -> None:
        try:
            import tkinter as tk
            from tkinter import ttk
            root = tk.Tk()
            root.title("Masum AI Agent — Voice Diagnostics")
            root.geometry("620x420")
            root.configure(bg="#0b1222")
            heading = tk.Label(root, text="CIRILLA // VOICE DIAGNOSTICS",
                               bg="#0b1222", fg="#65e7ff",
                               font=("Segoe UI", 16, "bold"))
            heading.pack(pady=14)
            status = tk.StringVar(value="Starting diagnostics...")
            heard = tk.StringVar(value="Last transcription: none")
            level = tk.StringVar(value="Microphone level: waiting")
            error = tk.StringVar(value="Listener error: none")
            for value in (status, heard, level, error):
                tk.Label(root, textvariable=value, bg="#0b1222", fg="#d9e7ff",
                         font=("Segoe UI", 10), wraplength=560,
                         justify="left").pack(anchor="w", padx=24, pady=6)
            meter = ttk.Progressbar(root, maximum=100, length=540)
            meter.pack(pady=10)
            result = tk.StringVar(value="Microphone test temporarily pauses wake listening.")
            tk.Label(root, textvariable=result, bg="#0b1222", fg="#65e7ff",
                     wraplength=560).pack(pady=12)
            buttons = tk.Frame(root, bg="#0b1222")
            buttons.pack()

            def microphone_test() -> None:
                if VOICE_TEST_ACTIVE.is_set():
                    return
                VOICE_TEST_ACTIVE.set()
                result.set("Waiting for listener to finish its current recording...")
                def worker():
                    # Wait for the current recording to finish before testing.
                    with VOICE_TEST_LOCK:
                        try:
                            time.sleep(WAKE_SECONDS + 0.5)
                            audio = sd.rec(int(3 * SAMPLE_RATE),
                                           samplerate=SAMPLE_RATE, channels=1,
                                           dtype="float32")
                            sd.wait()
                            rms = float(np.sqrt(np.mean(np.square(
                                audio[:, 0], dtype=np.float64))))
                            result.set("Microphone test: RMS {:.4f} ({})".format(
                                rms, "signal received" if rms > 0.005 else
                                "quiet input; check input device"))
                        except Exception as exc:
                            logging.exception("Diagnostic microphone test failed.")
                            result.set("Microphone test failed: " + str(exc)[:150])
                        finally:
                            VOICE_TEST_ACTIVE.clear()
                threading.Thread(target=worker, daemon=True).start()

            def speaker_test() -> None:
                result.set("Playing test voice...")
                threading.Thread(
                    target=lambda: speak("Hello. I am Cirilla. Can you hear me clearly?"),
                    daemon=True,
                ).start()

            tk.Button(buttons, text="TEST MICROPHONE", command=microphone_test,
                      bg="#12334a", fg="white", padx=12).pack(side="left", padx=8)
            tk.Button(buttons, text="TEST CIRILLA VOICE", command=speaker_test,
                      bg="#12334a", fg="white", padx=12).pack(side="left", padx=8)

            def refresh() -> None:
                if not root.winfo_exists():
                    return
                data = voice_state_snapshot()
                status.set("Wake listening: {} | {}".format(
                    "ON" if config.get("wake_enabled", True) else "OFF",
                    data["status"]))
                heard.set("Last wake transcription: " + (data["text"] or "(none)"))
                level.set("Last recorded microphone RMS: {:.4f}".format(data["level"]))
                error.set("Listener last error: " + (data["error"] or "none"))
                meter["value"] = min(100, data["level"] * 1200)
                root.after(750, refresh)

            def close() -> None:
                diagnostics_open.clear()
                root.destroy()
            root.protocol("WM_DELETE_WINDOW", close)
            refresh()
            root.mainloop()
        except Exception:
            logging.exception("Voice diagnostics window failed.")
        finally:
            diagnostics_open.clear()

    threading.Thread(target=show, name="MasumVoiceDiagnostics",
                     daemon=True).start()


def make_tray_image() -> Image.Image:
    image = Image.new("RGB", (64, 64), (4, 10, 20))
    draw = ImageDraw.Draw(image)
    draw.ellipse((6, 6, 58, 58), outline=(90, 220, 255), width=4)
    draw.rectangle((20, 20, 44, 44), outline=(150, 120, 255), width=3)
    draw.ellipse((25, 28, 29, 32), fill=(90, 220, 255))
    draw.ellipse((35, 28, 39, 32), fill=(90, 220, 255))
    return image


def toggle_wake(_icon=None, _item=None) -> None:
    enabled = not bool(config.get("wake_enabled", True))
    set_config_value("wake_enabled", enabled)
    speak("Wake listening on." if enabled else "Wake listening off.")


def set_cirilla(_icon=None, _item=None) -> None:
    set_config_value("persona", "cirilla")
    speak("Cirilla mode active.")


def set_geralt(_icon=None, _item=None) -> None:
    set_config_value("persona", "geralt")
    speak("Geralt mode active.")


def open_project_from_tray(_icon=None, _item=None) -> None:
    project = discover_project_path()
    if project is None:
        speak("Project folder was not found.")
        return
    if not open_vscode(project):
        speak("VS Code was not found.")


def exit_app(icon, _item=None) -> None:
    STOP_EVENT.set()
    icon.stop()


def build_menu() -> pystray.Menu:
    return pystray.Menu(
        pystray.MenuItem(
            lambda _item: f"{persona_name()} // v{VERSION}",
            None,
            enabled=False,
        ),
        pystray.MenuItem(
            "Wake listening",
            toggle_wake,
            checked=lambda _item: bool(config.get("wake_enabled", True)),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Use Cirilla",
            set_cirilla,
            checked=lambda _item: config.get("persona") == "cirilla",
            radio=True,
        ),
        pystray.MenuItem(
            "Use Geralt",
            set_geralt,
            checked=lambda _item: config.get("persona") == "geralt",
            radio=True,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Open Masum AI Agent project",
            open_project_from_tray,
        ),
        pystray.MenuItem(
            "Open GitHub",
            lambda _icon, _item: open_chrome("https://github.com/"),
        ),
        pystray.MenuItem(
            "Open Mobile Pairing Info",
            open_pairing_info,
        ),
        pystray.MenuItem(
            "Show Private Pairing QR",
            open_pairing_qr,
        ),
        pystray.MenuItem(
            "Open First Run Guide",
            open_first_run_guide,
        ),
        pystray.MenuItem(
            "Open Security Health Report",
            open_security_health_report,
        ),
        pystray.MenuItem(
            "Open Reliability Report",
            open_reliability_report,
        ),
        pystray.MenuItem(
            "Open Voice Diagnostics",
            open_voice_diagnostics,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", exit_app),
    )


def main() -> None:
    global tray_icon

    ensure_single_instance()

    listener = threading.Thread(
        target=listener_loop,
        name="CirillaListener",
        daemon=True,
    )
    listener.start()

    bridge_thread = threading.Thread(
        target=bridge_server_loop,
        name="MasumMobileBridge",
        daemon=True,
    )
    bridge_thread.start()

    discovery_thread = threading.Thread(
        target=discovery_server_loop,
        name="MasumLANDiscovery",
        daemon=True,
    )
    discovery_thread.start()

    tray_icon = pystray.Icon(
        "MasumAIAgent",
        make_tray_image(),
        "Masum AI Agent — Cirilla",
        build_menu(),
    )

    try:
        tray_icon.run()
    finally:
        STOP_EVENT.set()


if __name__ == "__main__":
    main()
