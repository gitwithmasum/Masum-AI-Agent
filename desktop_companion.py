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
import tempfile
import threading
import time
import wave
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
VERSION = "5.3.0"
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
WAKE_SECONDS = float(os.getenv("DESKTOP_WAKE_SECONDS", "3.5"))
COMMAND_SECONDS = float(os.getenv("DESKTOP_COMMAND_SECONDS", "7"))
WAKE_MODEL_NAME = os.getenv("DESKTOP_WAKE_MODEL", "tiny").strip() or "tiny"
COMMAND_MODEL_NAME = (
    os.getenv("DESKTOP_COMMAND_MODEL", "small").strip() or "small"
)
COMPUTE_TYPE = os.getenv("DESKTOP_COMPUTE_TYPE", "int8").strip() or "int8"
BRIDGE_PORT = int(os.getenv("DESKTOP_BRIDGE_PORT", "8767"))

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
    audio = sd.rec(
        frames,
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
    )
    sd.wait()

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
    segments, _info = model.transcribe(
        str(path),
        language=None,
        beam_size=1 if kind == "wake" else 4,
        vad_filter=True,
        condition_on_previous_text=False,
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
        return transcribe(path, kind)
    except Exception:
        logging.exception("Microphone/transcription failed.")
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

    speak(
        "I heard the command, but this desktop action is not on my safe allowlist yet."
    )



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
        "The key authenticates commands with HMAC-SHA256 and is never sent directly.\n",
        encoding="utf-8",
    )
    return path


def bridge_action(action: str) -> tuple[bool, str]:
    action = str(action or "").strip().lower()

    if action == "status":
        return True, f"Laptop bridge online. {persona_name()} is active."

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
    server_version = "MasumBridge/5.3"

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:
        if self.path != "/action":
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

        ok, message = bridge_action(str(payload.get("action") or ""))
        self._json(200 if ok else 400, {"ok": ok, "message": message})

    def log_message(self, format: str, *args: Any) -> None:
        logging.info("Bridge: " + format, *args)


def bridge_server_loop() -> None:
    if not config.get("bridge_enabled", True):
        return

    port = int(config.get("bridge_port") or BRIDGE_PORT)
    write_bridge_pairing_info()

    try:
        server = ThreadingHTTPServer(("0.0.0.0", port), BridgeHandler)
        server.daemon_threads = True
        logging.info("Mobile bridge listening on port %s", port)
        server.serve_forever()
    except OSError:
        logging.exception("Mobile bridge could not bind to port %s", port)


def open_pairing_info(_icon=None, _item=None) -> None:
    path = write_bridge_pairing_info()
    try:
        os.startfile(str(path))
    except Exception:
        logging.exception("Could not open bridge pairing info.")


def listener_loop() -> None:
    time.sleep(2.0)
    logging.info("%s desktop companion started.", APP_NAME)

    while not STOP_EVENT.is_set():
        if not config.get("wake_enabled", True):
            STOP_EVENT.wait(0.5)
            continue

        text = listen(WAKE_SECONDS, "wake")
        if not text:
            continue

        detected, inline_command = extract_wake_command(text)
        if not detected:
            continue

        logging.info("Wake detected: %s", text)

        if inline_command:
            handle_command(inline_command)
            continue

        speak("Yes?")
        command = listen(COMMAND_SECONDS, "command")
        if command:
            handle_command(command)
        else:
            speak("I did not hear a command.")


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
