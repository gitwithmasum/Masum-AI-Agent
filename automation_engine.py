import asyncio
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Awaitable, Callable


def local_now() -> datetime:
    return datetime.now().astimezone()


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=local_now().tzinfo)
    return dt


def _parse_once(value: str) -> datetime:
    dt = datetime.strptime(value, "%Y-%m-%d %H:%M")
    return dt.replace(tzinfo=local_now().tzinfo)


def _next_daily(time_value: str, after: datetime | None = None) -> datetime:
    base = after or local_now()
    hour, minute = (int(part) for part in time_value.split(":", 1))
    candidate = base.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )
    if candidate <= base:
        candidate += timedelta(days=1)
    return candidate


class AutomationStore:
    def __init__(self, tasks_path: Path, log_path: Path):
        self.tasks_path = Path(tasks_path)
        self.log_path = Path(log_path)
        self.tasks_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict]:
        if not self.tasks_path.exists():
            return []

        try:
            data = json.loads(
                self.tasks_path.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            return []

        return data if isinstance(data, list) else []

    def _save(self, tasks: list[dict]) -> None:
        temp_path = self.tasks_path.with_suffix(
            self.tasks_path.suffix + ".tmp"
        )
        temp_path.write_text(
            json.dumps(
                tasks,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temp_path.replace(self.tasks_path)

    def list_tasks(self) -> list[dict]:
        return self._load()

    def get(self, task_id: str) -> dict | None:
        task_id = task_id.strip()
        for task in self._load():
            if task.get("id") == task_id:
                return task
        return None

    def _new_task(
        self,
        schedule_type: str,
        schedule_value: str,
        action: str,
        next_run: datetime,
    ) -> dict:
        action = action.strip()
        if not action:
            raise ValueError("Automation action cannot be empty.")

        task = {
            "id": uuid.uuid4().hex[:8],
            "schedule_type": schedule_type,
            "schedule_value": schedule_value,
            "action": action,
            "enabled": True,
            "created_at": local_now().isoformat(),
            "last_run": None,
            "next_run": next_run.isoformat(),
            "last_status": None,
        }

        tasks = self._load()
        tasks.append(task)
        self._save(tasks)
        return task

    def add_daily(self, time_value: str, action: str) -> dict:
        try:
            hour, minute = (
                int(part)
                for part in time_value.strip().split(":", 1)
            )
        except (ValueError, TypeError):
            raise ValueError("Daily time must use HH:MM format.")

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Daily time must be a valid 24-hour HH:MM.")

        normalized = f"{hour:02d}:{minute:02d}"
        return self._new_task(
            "daily",
            normalized,
            action,
            _next_daily(normalized),
        )

    def add_interval(self, minutes: int, action: str) -> dict:
        minutes = int(minutes)
        if minutes < 1:
            raise ValueError("Interval must be at least 1 minute.")

        return self._new_task(
            "interval",
            str(minutes),
            action,
            local_now() + timedelta(minutes=minutes),
        )

    def add_once(self, when_value: str, action: str) -> dict:
        try:
            run_at = _parse_once(when_value.strip())
        except ValueError:
            raise ValueError(
                "One-time schedule must use YYYY-MM-DD HH:MM format."
            )

        if run_at <= local_now():
            raise ValueError("One-time schedule must be in the future.")

        return self._new_task(
            "once",
            run_at.strftime("%Y-%m-%d %H:%M"),
            action,
            run_at,
        )

    def set_enabled(self, task_id: str, enabled: bool) -> dict | None:
        tasks = self._load()
        changed = None

        for task in tasks:
            if task.get("id") != task_id.strip():
                continue

            task["enabled"] = bool(enabled)
            if enabled:
                schedule_type = task.get("schedule_type")
                if schedule_type == "daily":
                    task["next_run"] = _next_daily(
                        task["schedule_value"]
                    ).isoformat()
                elif schedule_type == "interval":
                    task["next_run"] = (
                        local_now()
                        + timedelta(
                            minutes=int(task["schedule_value"])
                        )
                    ).isoformat()
                elif schedule_type == "once":
                    run_at = _parse_once(task["schedule_value"])
                    if run_at <= local_now():
                        raise ValueError(
                            "Cannot enable a one-time task whose time has passed."
                        )
                    task["next_run"] = run_at.isoformat()

            changed = task
            break

        if changed is not None:
            self._save(tasks)

        return changed

    def remove(self, task_id: str) -> bool:
        tasks = self._load()
        filtered = [
            task
            for task in tasks
            if task.get("id") != task_id.strip()
        ]

        if len(filtered) == len(tasks):
            return False

        self._save(filtered)
        return True

    def due_tasks(self, now: datetime | None = None) -> list[dict]:
        now = now or local_now()
        due = []

        for task in self._load():
            if not task.get("enabled", True):
                continue

            next_run = task.get("next_run")
            if not next_run:
                continue

            try:
                run_at = _parse_iso(next_run)
            except ValueError:
                continue

            if run_at <= now:
                due.append(task)

        return due

    def mark_result(
        self,
        task_id: str,
        status: str,
        result: str,
    ) -> None:
        now = local_now()
        tasks = self._load()
        updated_task = None

        for task in tasks:
            if task.get("id") != task_id:
                continue

            task["last_run"] = now.isoformat()
            task["last_status"] = status

            schedule_type = task.get("schedule_type")
            if schedule_type == "daily":
                task["next_run"] = _next_daily(
                    task["schedule_value"],
                    after=now,
                ).isoformat()
            elif schedule_type == "interval":
                task["next_run"] = (
                    now
                    + timedelta(
                        minutes=int(task["schedule_value"])
                    )
                ).isoformat()
            elif schedule_type == "once":
                task["enabled"] = False
                task["next_run"] = None

            updated_task = task
            break

        if updated_task is not None:
            self._save(tasks)

        record = {
            "time": now.isoformat(),
            "task_id": task_id,
            "status": status,
            "action": (
                updated_task.get("action")
                if updated_task
                else None
            ),
            "result": result[:6000],
        }

        with self.log_path.open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    def format_tasks(self) -> str:
        tasks = self._load()
        if not tasks:
            return "No automation tasks configured."

        lines = ["Automation tasks:"]
        for task in tasks:
            enabled = "ON" if task.get("enabled", True) else "OFF"
            next_run = task.get("next_run") or "—"
            lines.append(
                f"[{task.get('id')}] {enabled} | "
                f"{task.get('schedule_type')} "
                f"{task.get('schedule_value')} | "
                f"next: {next_run} | "
                f"action: {task.get('action')}"
            )

        return "\n".join(lines)

    def format_log(self, limit: int = 20) -> str:
        if not self.log_path.exists():
            return "No automation runs logged yet."

        try:
            lines = self.log_path.read_text(
                encoding="utf-8"
            ).splitlines()
        except OSError:
            return "Could not read automation log."

        records = []
        for line in lines[-max(1, min(limit, 100)):]:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        if not records:
            return "No valid automation log entries found."

        output = ["Recent automation runs:"]
        for item in records:
            output.append(
                f"[{item.get('time')}] "
                f"{item.get('task_id')} | "
                f"{item.get('status')} | "
                f"{item.get('action')}"
            )

        return "\n".join(output)


async def automation_loop(
    store: AutomationStore,
    execute_action: Callable[[str], Awaitable[str]],
    check_seconds: int = 30,
) -> None:
    interval = max(5, int(check_seconds))

    while True:
        due = store.due_tasks()

        for task in due:
            task_id = task.get("id") or "unknown"
            action = task.get("action") or ""

            print(
                f"\n\n⚙️ Automation [{task_id}] running: {action}"
            )

            try:
                result = await execute_action(action)
                status = "success"
            except asyncio.CancelledError:
                raise
            except Exception as error:
                result = f"Automation failed: {error}"
                status = "error"

            store.mark_result(
                task_id,
                status,
                str(result),
            )

            preview = str(result)
            if len(preview) > 3500:
                preview = preview[:3500].rstrip() + "\n[output truncated]"

            print(
                f"\n⚙️ Automation [{task_id}] {status}:\n{preview}\n"
            )

        await asyncio.sleep(interval)
