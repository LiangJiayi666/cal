from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from cal_app.application.service import CalendarService
from cal_app.domain.date_utils import format_date
from cal_app.domain.errors import DomainError
from cal_app.domain.models import Schedule


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cal",
        description="Task pool + schedule pool calendar CLI.",
    )
    subparsers = parser.add_subparsers(dest="command")

    add_one_time = subparsers.add_parser("task-add-once", help="Create a one-time task.")
    add_one_time.add_argument("--name", required=True)
    add_one_time.add_argument("--description", default="")
    add_one_time.add_argument("--start", required=True, help="YYYY-MM-DD")
    add_one_time.add_argument("--end", required=True, help="YYYY-MM-DD")
    add_one_time.add_argument("--test", action="store_true")

    update_one_time = subparsers.add_parser("task-update-once", help="Update a one-time task.")
    update_one_time.add_argument("--id", required=True, dest="task_id")
    update_one_time.add_argument("--name")
    update_one_time.add_argument("--description")
    update_one_time.add_argument("--start", dest="start_date")
    update_one_time.add_argument("--end", dest="end_date")

    add_recurring = subparsers.add_parser("task-add-recurring", help="Create a recurring task.")
    add_recurring.add_argument("--name", required=True)
    add_recurring.add_argument("--description", default="")
    add_recurring.add_argument("--first-start", required=True)
    add_recurring.add_argument("--first-end", required=True)
    add_recurring.add_argument("--task-start")
    add_recurring.add_argument("--task-end")
    add_recurring.add_argument("--repeat", required=True, choices=["day", "week", "month", "year"])
    add_recurring.add_argument("--n", type=int, default=1)
    add_recurring.add_argument("--test", action="store_true")

    update_recurring = subparsers.add_parser("task-update-recurring", help="Update a recurring task.")
    update_recurring.add_argument("--id", required=True, dest="task_id")
    update_recurring.add_argument("--name")
    update_recurring.add_argument("--description")
    update_recurring.add_argument("--first-start")
    update_recurring.add_argument("--first-end")
    update_recurring.add_argument("--task-start")
    update_recurring.add_argument("--task-end")
    update_recurring.add_argument("--repeat", choices=["day", "week", "month", "year"])
    update_recurring.add_argument("--n", type=int)

    delete_task = subparsers.add_parser("task-delete", help="Delete a task (test tasks only).")
    delete_task.add_argument("--id", required=True, dest="task_id")

    subparsers.add_parser("task-list", help="List all tasks.")

    set_status = subparsers.add_parser("schedule-set-status", help="Set a schedule status.")
    set_status.add_argument("--task-id", required=True)
    set_status.add_argument("--schedule-id", required=True, type=int)
    set_status.add_argument("--status", required=True, choices=["todo", "doing", "done"])

    list_schedule = subparsers.add_parser("schedule-list", help="List schedules.")
    list_schedule.add_argument("--task-id")

    calendar_view = subparsers.add_parser("calendar-view", help="View schedules grouped by day.")
    calendar_view.add_argument("--from", dest="from_date")
    calendar_view.add_argument("--to", dest="to_date")
    calendar_view.add_argument("--filter", choices=["todo", "active", "all"], default="active")

    subparsers.add_parser("maintenance-run", help="Force run daily maintenance now.")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return

    project_root = Path(__file__).resolve().parents[1]
    service = CalendarService.default(project_root=project_root)

    try:
        if args.command == "maintenance-run":
            maintenance = service.run_daily_maintenance(force=True)
            _print_maintenance(maintenance)
            return

        maintenance = service.run_daily_maintenance_if_needed()
        _print_maintenance(maintenance)

        if args.command == "task-add-once":
            result = service.create_one_time_task(
                name=args.name,
                description=args.description,
                start_date_text=args.start,
                end_date_text=args.end,
                is_test=args.test,
            )
            print(f"Created one-time task: {result['task_id']}")
            _print_notes(result["notes"])
            return

        if args.command == "task-update-once":
            notes = service.update_one_time_task(
                task_id=args.task_id,
                name=args.name,
                description=args.description,
                start_date_text=args.start_date,
                end_date_text=args.end_date,
            )
            print(f"Updated one-time task: {args.task_id}")
            _print_notes(notes)
            return

        if args.command == "task-add-recurring":
            result = service.create_recurring_task(
                name=args.name,
                description=args.description,
                first_start_text=args.first_start,
                first_end_text=args.first_end,
                task_start_text=args.task_start,
                task_end_text=args.task_end,
                repeat_unit=args.repeat,
                n=args.n,
                is_test=args.test,
            )
            print(f"Created recurring task: {result['task_id']}")
            _print_notes(result["notes"])
            return

        if args.command == "task-update-recurring":
            notes = service.update_recurring_task(
                task_id=args.task_id,
                name=args.name,
                description=args.description,
                first_start_text=args.first_start,
                first_end_text=args.first_end,
                task_start_text=args.task_start,
                task_end_text=args.task_end,
                repeat_unit=args.repeat,
                n=args.n,
            )
            print(f"Updated recurring task: {args.task_id}")
            _print_notes(notes)
            return

        if args.command == "task-delete":
            service.delete_task(args.task_id)
            print(f"Deleted task: {args.task_id}")
            return

        if args.command == "task-list":
            tasks = service.list_tasks()
            if not tasks:
                print("No tasks found.")
                return
            for item in tasks:
                repeat_text = ""
                if item["kind"] == "recurring":
                    repeat_text = f", repeat={item['n']} {item['repeat_unit']}"
                print(
                    f"[{item['kind']}] {item['task_id']} | {item['name']} | "
                    f"{format_date(item['start_date'])} -> {format_date(item['end_date'])}"
                    f"{repeat_text} | test={item['is_test']}"
                )
            return

        if args.command == "schedule-set-status":
            service.set_schedule_status(
                task_id=args.task_id,
                schedule_id=args.schedule_id,
                status=args.status,
            )
            print(f"Updated schedule status: {args.task_id}#{args.schedule_id} -> {args.status}")
            return

        if args.command == "schedule-list":
            schedules = service.list_schedules(task_id=args.task_id)
            if not schedules:
                print("No schedules found.")
                return
            for item in schedules:
                print(_format_schedule_line(item))
            return

        if args.command == "calendar-view":
            view = service.view_calendar(
                from_date_text=args.from_date,
                to_date_text=args.to_date,
                filter_mode=args.filter,
            )
            _print_calendar(view)
            return

        raise DomainError(f"Unsupported command: {args.command}")
    except DomainError as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


def _print_maintenance(maintenance: dict[str, object]) -> None:
    if not maintenance.get("ran"):
        return
    removed_one_time = maintenance.get("removed_one_time", 0)
    removed_recurring = maintenance.get("removed_recurring", 0)
    delta = maintenance.get("delta", {})
    added = delta.get("added", 0) if isinstance(delta, dict) else 0
    removed = delta.get("removed", 0) if isinstance(delta, dict) else 0
    print(
        "Daily maintenance: "
        f"removed_one_time={removed_one_time}, "
        f"removed_recurring={removed_recurring}, "
        f"schedule_added={added}, schedule_removed={removed}"
    )


def _print_notes(notes: list[str]) -> None:
    for note in notes:
        print(f"Note: {note}")


def _weekday_name(value: date) -> str:
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return names[value.weekday()]


def _format_schedule_line(item: Schedule) -> str:
    return (
        f"- [{item.status}] {item.name} (ID: {item.task_id}, S#{item.schedule_id}) - "
        f"{item.description} [{format_date(item.start_date)} -> {format_date(item.end_date)}]"
    )


def _print_calendar(view: dict[str, object]) -> None:
    grouped = view["grouped"]
    assert isinstance(grouped, dict)

    for day in sorted(grouped.keys()):
        print(f"{format_date(day)} ({_weekday_name(day)}):")
        entries = grouped[day]
        assert isinstance(entries, list)
        if not entries:
            print("  (no schedules)")
            continue
        for entry in entries:
            assert isinstance(entry, Schedule)
            print(f"  {_format_schedule_line(entry)}")

    overdue = view["overdue"]
    assert isinstance(overdue, list)
    print("Past unfinished schedules:")
    if not overdue:
        print("  (none)")
    else:
        for item in overdue:
            assert isinstance(item, Schedule)
            print(f"  {_format_schedule_line(item)}")
