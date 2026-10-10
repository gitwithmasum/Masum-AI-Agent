from __future__ import annotations

import asyncio
import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Literal

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import main as core
from automation_engine import AutomationStore, automation_loop
from multi_agent import AGENT_DESCRIPTIONS, normalize_agent_name


DASHBOARD_DIR = Path(__file__).resolve().parent / "dashboard"
HOST = os.getenv("DASHBOARD_HOST", "127.0.0.1").strip() or "127.0.0.1"
PORT = int(os.getenv("DASHBOARD_PORT", "8765"))
STT_SERVICE_URL = os.getenv(
    "STT_SERVICE_URL",
    "http://127.0.0.1:8766",
).strip().rstrip("/")
STT_PROXY_TIMEOUT = int(os.getenv("STT_PROXY_TIMEOUT", "120"))
AUTO_OPEN = os.getenv(
    "DASHBOARD_AUTO_OPEN",
    "true",
).strip().lower() in {"1", "true", "yes", "on"}

app = FastAPI(
    title="Masum AI Agent Dashboard",
    version="4.2.0",
    docs_url=None,
    redoc_url=None,
)

app.mount(
    "/static",
    StaticFiles(directory=str(DASHBOARD_DIR)),
    name="static",
)

automation_store = AutomationStore(
    core.AUTOMATION_TASKS_PATH,
    core.AUTOMATION_LOG_PATH,
)

_runtime_lock = asyncio.Lock()
_chat_lock = asyncio.Lock()
_runtime: dict | None = None
_scheduler_task: asyncio.Task | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    agent: str = "auto"
    team_review: bool = False


class AutomationCreateRequest(BaseModel):
    schedule_type: Literal["daily", "interval", "once"]
    schedule_value: str = Field(min_length=1, max_length=40)
    action: str = Field(min_length=1, max_length=4000)


async def get_runtime() -> dict:
    global _runtime

    if _runtime is not None:
        return _runtime

    async with _runtime_lock:
        if _runtime is not None:
            return _runtime

        try:
            coordinator, team, provider, model_name = await asyncio.to_thread(
                core.build_agent
            )
            session = core.build_memory_session()
        except Exception as error:
            raise RuntimeError(str(error)) from error

        _runtime = {
            "coordinator": coordinator,
            "team": team,
            "provider": provider,
            "model": model_name,
            "session": session,
        }
        return _runtime


async def scheduler_execute(action: str) -> str:
    runtime = await get_runtime()
    return await core.execute_automation_action(
        runtime["coordinator"],
        action,
    )


def ollama_status() -> tuple[bool, str]:
    model_name = os.getenv(
        "OLLAMA_MODEL",
        "qwen3:1.7b",
    ).strip()

    try:
        core.check_ollama(model_name)
        return True, model_name
    except Exception as error:
        return False, str(error)


def stt_request(method: str, path: str, body: bytes | None = None, content_type: str = "application/json") -> tuple[dict | None, str | None]:
    url = f"{STT_SERVICE_URL}{path}"
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=STT_PROXY_TIMEOUT) as response:
            payload = response.read().decode("utf-8", errors="replace")
            return json.loads(payload) if payload else {}, None
    except urllib.error.HTTPError as error:
        try:
            payload = json.loads(error.read().decode("utf-8", errors="replace"))
            detail = payload.get("detail") or payload.get("error") or str(error)
        except Exception:
            detail = str(error)
        return None, f"Local STT error {error.code}: {detail}"
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return None, f"Local STT service unavailable: {error}"
    except json.JSONDecodeError as error:
        return None, f"Local STT returned invalid JSON: {error}"


def stt_status_data() -> dict:
    data, error = stt_request("GET", "/status")
    if error:
        return {"online": False, "service_url": STT_SERVICE_URL, "detail": error}
    return {"online": True, "service_url": STT_SERVICE_URL, **(data or {})}

def safe_report_path(file_name: str) -> Path:
    core.ensure_research_report_dir()
    root = core.RESEARCH_REPORT_DIR.resolve()
    target = (root / file_name.strip()).resolve()

    if root not in target.parents:
        raise HTTPException(
            status_code=400,
            detail="Invalid report path.",
        )

    if (
        not target.exists()
        or not target.is_file()
        or target.suffix.lower() != ".md"
    ):
        raise HTTPException(
            status_code=404,
            detail="Report not found.",
        )

    return target


@app.on_event("startup")
async def startup_event() -> None:
    global _scheduler_task

    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(
            automation_loop(
                automation_store,
                scheduler_execute,
                core.AUTOMATION_CHECK_SECONDS,
            )
        )


@app.on_event("shutdown")
async def shutdown_event() -> None:
    global _scheduler_task

    if _scheduler_task is not None:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
        _scheduler_task = None


@app.get("/")
async def dashboard_index():
    return FileResponse(DASHBOARD_DIR / "index.html")


@app.get("/api/status")
async def api_status():
    ollama_ok, ollama_detail = await asyncio.to_thread(
        ollama_status
    )

    reports = []
    core.ensure_research_report_dir()
    try:
        reports = list(core.RESEARCH_REPORT_DIR.glob("*.md"))
    except OSError:
        reports = []

    gmail_authorized = core.GMAIL_TOKEN_PATH.exists()
    tasks = automation_store.list_tasks()
    enabled_tasks = sum(
        1
        for task in tasks
        if task.get("enabled", True)
    )

    local_stt = await asyncio.to_thread(stt_status_data)

    return {
        "version": "v4.2",
        "name": "Masum AI Agent",
        "ollama": {
            "online": ollama_ok,
            "detail": ollama_detail,
        },
        "provider": os.getenv("AI_PROVIDER", "ollama"),
        "model": os.getenv("OLLAMA_MODEL", "qwen3:1.7b"),
        "gmail": {
            "authorized": gmail_authorized,
            "mode": "read-only",
        },
        "supabase": {
            "configured": core.supabase_configured(),
            "mode": "read-only",
        },
        "automation": {
            "total": len(tasks),
            "enabled": enabled_tasks,
            "check_seconds": core.AUTOMATION_CHECK_SECONDS,
        },
        "reports": len(reports),
        "auto_route": core.MULTI_AGENT_AUTO_ROUTE,
        "local_stt": local_stt,
        "local_time": datetime.now().astimezone().isoformat(),
    }


@app.get("/api/agents")
async def api_agents():
    return {
        "agents": [
            {
                "id": name,
                "description": description,
            }
            for name, description in AGENT_DESCRIPTIONS.items()
        ]
    }


@app.post("/api/chat")
async def api_chat(payload: ChatRequest):
    message = payload.message.strip()
    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    try:
        runtime = await get_runtime()
    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error

    async with _chat_lock:
        if payload.team_review:
            selected, output = await core.run_team_review(
                runtime["team"],
                message,
            )
            return {
                "mode": "team-review",
                "agents": selected,
                "answer": output,
            }

        requested = payload.agent.strip().lower()
        if requested in {"", "auto"}:
            selected, output = await core.run_team_route(
                runtime["team"],
                message,
                session=runtime["session"],
            )
            return {
                "mode": "auto",
                "agents": [selected],
                "answer": output,
            }

        selected = normalize_agent_name(requested)
        if selected not in runtime["team"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown agent: {payload.agent}",
            )

        output = await core.run_named_agent(
            runtime["team"],
            selected,
            message,
            session=runtime["session"],
        )
        return {
            "mode": "manual",
            "agents": [selected],
            "answer": output,
        }


@app.get("/api/stt/status")
async def api_stt_status():
    return await asyncio.to_thread(stt_status_data)


@app.post("/api/stt/transcribe")
async def api_stt_transcribe(request: Request, language: str = "bn"):
    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=400, detail="Audio body is empty.")
    if len(audio) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio is too large.")
    safe_language = language.strip().lower()
    if safe_language not in {"bn", "en", "auto"}:
        safe_language = "auto"
    path = "/transcribe?" + urllib.parse.urlencode({"language": safe_language})
    content_type = request.headers.get("content-type", "audio/webm")
    data, error = await asyncio.to_thread(stt_request, "POST", path, audio, content_type)
    if error:
        raise HTTPException(status_code=503, detail=error)
    return data or {}

@app.post("/api/stt/wake")
async def api_stt_wake(request: Request, language: str = "auto"):
    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=400, detail="Audio body is empty.")
    if len(audio) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio is too large.")

    safe_language = language.strip().lower()
    if safe_language not in {"bn", "en", "auto"}:
        safe_language = "auto"

    path = "/wake-detect?" + urllib.parse.urlencode(
        {"language": safe_language}
    )
    content_type = request.headers.get(
        "content-type",
        "audio/webm",
    )
    data, error = await asyncio.to_thread(
        stt_request,
        "POST",
        path,
        audio,
        content_type,
    )
    if error:
        raise HTTPException(status_code=503, detail=error)
    return data or {}


@app.get("/api/gmail/status")
async def api_gmail_status():
    return {
        "text": await asyncio.to_thread(
            core.gmail_status_text
        )
    }


@app.get("/api/automations")
async def api_automations():
    return {
        "tasks": automation_store.list_tasks(),
    }


@app.post("/api/automations")
async def api_create_automation(payload: AutomationCreateRequest):
    try:
        if payload.schedule_type == "daily":
            task = automation_store.add_daily(
                payload.schedule_value,
                payload.action,
            )
        elif payload.schedule_type == "interval":
            task = automation_store.add_interval(
                int(payload.schedule_value),
                payload.action,
            )
        else:
            task = automation_store.add_once(
                payload.schedule_value,
                payload.action,
            )
    except (ValueError, TypeError) as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return {
        "ok": True,
        "task": task,
    }


@app.post("/api/automations/{task_id}/run")
async def api_run_automation(task_id: str):
    try:
        runtime = await get_runtime()
    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error

    result = await core.run_automation_task_now(
        automation_store,
        runtime["coordinator"],
        task_id,
    )
    return {
        "ok": True,
        "result": result,
    }


@app.post("/api/automations/{task_id}/enable")
async def api_enable_automation(task_id: str):
    try:
        task = automation_store.set_enabled(
            task_id,
            True,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Automation task not found.",
        )

    return {
        "ok": True,
        "task": task,
    }


@app.post("/api/automations/{task_id}/disable")
async def api_disable_automation(task_id: str):
    task = automation_store.set_enabled(
        task_id,
        False,
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Automation task not found.",
        )

    return {
        "ok": True,
        "task": task,
    }


@app.delete("/api/automations/{task_id}")
async def api_delete_automation(task_id: str):
    if not automation_store.remove(task_id):
        raise HTTPException(
            status_code=404,
            detail="Automation task not found.",
        )

    return {"ok": True}


@app.get("/api/automation-log")
async def api_automation_log(limit: int = 20):
    return {
        "text": automation_store.format_log(
            max(1, min(limit, 100))
        )
    }


@app.get("/api/reports")
async def api_reports():
    core.ensure_research_report_dir()

    reports = []
    for path in sorted(
        core.RESEARCH_REPORT_DIR.glob("*.md"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    ):
        reports.append(
            {
                "name": path.name,
                "size": path.stat().st_size,
                "modified": datetime.fromtimestamp(
                    path.stat().st_mtime
                ).astimezone().isoformat(),
            }
        )

    return {"reports": reports}


@app.get("/api/reports/{file_name}")
async def api_report(file_name: str):
    path = safe_report_path(file_name)
    return {
        "name": path.name,
        "content": path.read_text(
            encoding="utf-8",
            errors="replace",
        ),
    }


@app.get("/api/github/summary")
async def api_github_summary():
    return {
        "text": await asyncio.to_thread(
            core.github_repo_summary_text
        )
    }


def open_dashboard() -> None:
    browser_host = (
        "127.0.0.1"
        if HOST in {"0.0.0.0", "::"}
        else HOST
    )
    webbrowser.open(
        f"http://{browser_host}:{PORT}"
    )


if __name__ == "__main__":
    if AUTO_OPEN:
        threading.Timer(
            1.2,
            open_dashboard,
        ).start()

    print("=" * 64)
    print("🤖 MASUM AI AGENT v4.2 — CIRILLA WAKE MODE")
    print(f"Dashboard: http://{HOST}:{PORT}")
    print(f"Local STT: {STT_SERVICE_URL}")
    print("Security : local-only is recommended (127.0.0.1)")
    print("Stop     : Ctrl + C")
    print("=" * 64)

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="warning",
    )
