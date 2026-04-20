from __future__ import annotations

import argparse
import json
from datetime import date
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cal_app.application.service import CalendarService
from cal_app.domain.date_utils import format_date
from cal_app.domain.errors import DomainError
from cal_app.domain.models import Schedule


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = Path(__file__).resolve().parent / "web_static"


def _json_error(message: str, *, code: int = HTTPStatus.BAD_REQUEST) -> tuple[int, dict[str, str]]:
    return code, {"error": message}


def _serialize_task(task: dict[str, Any]) -> dict[str, Any]:
    output = dict(task)
    output["start_date"] = format_date(task["start_date"])
    output["end_date"] = format_date(task["end_date"])
    return output


def _serialize_schedule(item: Schedule) -> dict[str, Any]:
    return item.to_dict()


def _view_overview(service: CalendarService) -> dict[str, Any]:
    service.run_daily_maintenance_if_needed()
    tasks = [_serialize_task(task) for task in service.list_tasks()]
    schedules = [_serialize_schedule(item) for item in service.list_schedules()]
    overdue = [_serialize_schedule(item) for item in service.view_calendar(
        from_date_text=None,
        to_date_text=None,
        filter_mode="all",
    )["overdue"]]
    return {
        "today": format_date(service.today_provider()),
        "tasks": tasks,
        "schedules": schedules,
        "overdue": overdue,
        "counts": {
            "tasks": len(tasks),
            "schedules": len(schedules),
            "overdue": len(overdue),
        },
    }


def _run_action(service: CalendarService, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if path == "/api/tasks/one-time":
        result = service.create_one_time_task(
            name=str(payload.get("name", "")),
            description=str(payload.get("description", "")),
            start_date_text=str(payload.get("start_date", "")),
            end_date_text=str(payload.get("end_date", "")),
            is_test=bool(payload.get("is_test", False)),
        )
        return HTTPStatus.OK, {"ok": True, "result": result}

    if path == "/api/tasks/recurring":
        result = service.create_recurring_task(
            name=str(payload.get("name", "")),
            description=str(payload.get("description", "")),
            first_start_text=str(payload.get("first_start_date", "")),
            first_end_text=str(payload.get("first_end_date", "")),
            task_start_text=payload.get("task_start_date"),
            task_end_text=payload.get("task_end_date"),
            repeat_unit=str(payload.get("repeat_unit", "")),
            n=int(payload.get("n", 1)),
            is_test=bool(payload.get("is_test", False)),
        )
        return HTTPStatus.OK, {"ok": True, "result": result}

    if path == "/api/schedules/status":
        schedule_id = payload.get("schedule_id")
        resolved_schedule_id = service.set_schedule_status(
            task_id=str(payload.get("task_id", "")),
            schedule_id=int(schedule_id) if schedule_id is not None else None,
            status=str(payload.get("status", "")),
        )
        return HTTPStatus.OK, {"ok": True, "schedule_id": resolved_schedule_id}

    if path == "/api/schedules/done-overdue":
        updated = service.mark_overdue_schedules_done()
        return HTTPStatus.OK, {"ok": True, "updated": updated}

    if path == "/api/tasks/delay-overdue":
        updated = service.delay_overdue_one_time_tasks_to_today()
        return HTTPStatus.OK, {"ok": True, "updated": updated}

    if path == "/api/tasks/delay-one-time":
        service.delay_one_time_task_to_today(str(payload.get("task_id", "")))
        return HTTPStatus.OK, {"ok": True}

    if path == "/api/maintenance":
        result = service.run_daily_maintenance(force=True)
        return HTTPStatus.OK, {"ok": True, "result": result}

    return _json_error("Unsupported API endpoint.", code=HTTPStatus.NOT_FOUND)


class CalWebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def _service(self) -> CalendarService:
        return CalendarService.default(project_root=PROJECT_ROOT)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _load_json_body(self) -> dict[str, Any]:
        length_text = self.headers.get("Content-Length", "0")
        try:
            length = int(length_text)
        except ValueError:
            raise DomainError("Invalid Content-Length.")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as error:
            raise DomainError("Request body must be valid JSON.") from error
        if not isinstance(parsed, dict):
            raise DomainError("Request body must be a JSON object.")
        return parsed

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/overview":
            try:
                payload = _view_overview(self._service())
            except DomainError as error:
                self._send_json(*_json_error(str(error)))
                return
            self._send_json(HTTPStatus.OK, payload)
            return
        if parsed.path.startswith("/api/"):
            self._send_json(*_json_error("API not found.", code=HTTPStatus.NOT_FOUND))
            return
        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self._send_json(*_json_error("Only /api endpoints support POST.", code=HTTPStatus.NOT_FOUND))
            return

        try:
            payload = self._load_json_body()
            service = self._service()
            service.run_daily_maintenance_if_needed()
            status, body = _run_action(service, parsed.path, payload)
        except DomainError as error:
            status, body = _json_error(str(error))
        except ValueError as error:
            status, body = _json_error(f"Invalid value: {error}")
        self._send_json(status, body)

    def log_message(self, format_string: str, *args: Any) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Run cal web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), CalWebHandler)
    today_text = format_date(date.today())
    print(f"cal web UI is running at http://{args.host}:{args.port} (today: {today_text})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
