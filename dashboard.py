from __future__ import annotations

import asyncio
import os
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Literal

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import main as core
from automation_engine import AutomationStore, automation_loop
from multi_agent import AGENT_DESCRIPTIONS, normalize_agent_name


DASHBOARD_DIR = Path(__file__).resolve().parent / "dashboard"
HOST = os.getenv("DASHBOARD_HOST", "127.0.0.1").strip() or "127.0.0.1"
PORT = int(os.getenv("DASHBOARD_PORT", "8765"))
AUTO_OPEN = os.getenv(
    "DASHBOARD_AUTO_OPEN",
    "true",
).strip().lower() in {"1", "true", "yes", "on"}

app = FastAPI(
    title="Masum AI Agent Dashboard",
    version="4.0.0",
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

    return {
        "version": "v4.0",
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
    print("🤖 MASUM AI AGENT v4.0 — VOICE AGENT + WEB DASHBOARD")
    print(f"Dashboard: http://{HOST}:{PORT}")
    print("Security : local-only is recommended (127.0.0.1)")
    print("Stop     : Ctrl + C")
    print("=" * 64)

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="warning",
    )
