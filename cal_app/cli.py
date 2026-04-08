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

    once = subparsers.add_parser("once", help="Create a one-time task.")
    once.add_argument("shortcut", nargs="?", choices=["today"], help="use 'today' for sd=ed=today")
    once.add_argument("--nm", required=True, help="name")
    once.add_argument("--ds", default="", help="description")
    once.add_argument("--sd", help="start date: YYYY-MM-DD")
    once.add_argument("--ed", help="end date: YYYY-MM-DD")
    once.add_argument("--tt", action="store_true", help="test task")

    onceupd = subparsers.add_parser("onceupd", help="Update a one-time task.")
    onceupd.add_argument("shortcut", nargs="?", choices=["today"], help="use 'today' for sd=ed=today")
    onceupd.add_argument("--id", required=True, dest="task_id")
    onceupd.add_argument("--nm")
    onceupd.add_argument("--ds")
    onceupd.add_argument("--sd", dest="start_date")
    onceupd.add_argument("--ed", dest="end_date")

    rec = subparsers.add_parser("rec", help="Create a recurring task.")
    rec.add_argument("shortcut", nargs="?", choices=["today"], help="use 'today' for fs=fe=today")
    rec.add_argument("--nm", required=True, help="name")
    rec.add_argument("--ds", default="", help="description")
    rec.add_argument("--fs", help="first start date")
    rec.add_argument("--fe", help="first end date")
    rec.add_argument("--ts", help="task start date")
    rec.add_argument("--te", help="task end date")
    rec.add_argument("--rp", required=True, choices=["d", "w", "m", "y", "day", "week", "month", "year"])
    rec.add_argument("--iv", type=int, default=1, help="interval n")
    rec.add_argument("--tt", action="store_true", help="test task")

    recupd = subparsers.add_parser("recupd", help="Update a recurring task.")
    recupd.add_argument("shortcut", nargs="?", choices=["today"], help="use 'today' for fs=fe=today")
    recupd.add_argument("--id", required=True, dest="task_id")
    recupd.add_argument("--nm")
    recupd.add_argument("--ds")
    recupd.add_argument("--fs")
    recupd.add_argument("--fe")
    recupd.add_argument("--ts")
    recupd.add_argument("--te")
    recupd.add_argument("--rp", choices=["d", "w", "m", "y", "day", "week", "month", "year"])
    recupd.add_argument("--iv", type=int)

    delete_task = subparsers.add_parser("del", help="Delete test tasks.")
    delete_task.add_argument("target", nargs="?", help="task id or 'all'")
    delete_task.add_argument("--id", dest="task_id")

    subparsers.add_parser("list", help="List all tasks.")

    for status_cmd in ("todo", "doing", "done"):
        status_parser = subparsers.add_parser(status_cmd, help=f"Set schedule status to {status_cmd}.")
        status_parser.add_argument("target", nargs="?", help="task id, or 'all' for done command")
        status_parser.add_argument("--id", dest="task_id")
        status_parser.add_argument("--sid", type=int, dest="schedule_id")

    list_schedule = subparsers.add_parser("schlist", help="List schedules.")
    list_schedule.add_argument("--id", dest="task_id")

    view = subparsers.add_parser("view", help="View schedules grouped by day.")
    view.add_argument("target", nargs="?", choices=["today"], help="use 'today' to view only today")
    view.add_argument("--fd", dest="from_date")
    view.add_argument("--td", dest="to_date")
    view.add_argument("--m", choices=["t", "a", "l", "todo", "active", "all"], default="a")

    subparsers.add_parser(
        "delay",
        help="Delay overdue unfinished one-time tasks so their end date becomes today.",
    )

    subparsers.add_parser("maint", help="Force run daily maintenance now.")
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
        if args.command == "maint":
            maintenance = service.run_daily_maintenance(force=True)
            _print_maintenance(maintenance)
            return

        maintenance = service.run_daily_maintenance_if_needed()
        _print_maintenance(maintenance)

        if args.command == "once":
            start_date_text, end_date_text = _resolve_today_pair(
                shortcut=args.shortcut,
                today=service.today_provider(),
                start_value=args.sd,
                end_value=args.ed,
                command_name="once",
                start_option="--sd",
                end_option="--ed",
            )
            if start_date_text is None or end_date_text is None:
                raise DomainError("Please provide --sd and --ed, or use 'once today'.")
            result = service.create_one_time_task(
                name=args.nm,
                description=args.ds,
                start_date_text=start_date_text,
                end_date_text=end_date_text,
                is_test=args.tt,
            )
            print(f"Created one-time task: {result['task_id']}")
            _print_notes(result["notes"])
            return

        if args.command == "onceupd":
            start_date_text, end_date_text = _resolve_today_pair(
                shortcut=args.shortcut,
                today=service.today_provider(),
                start_value=args.start_date,
                end_value=args.end_date,
                command_name="onceupd",
                start_option="--sd",
                end_option="--ed",
            )
            notes = service.update_one_time_task(
                task_id=args.task_id,
                name=args.nm,
                description=args.ds,
                start_date_text=start_date_text,
                end_date_text=end_date_text,
            )
            print(f"Updated one-time task: {args.task_id}")
            _print_notes(notes)
            return

        if args.command == "rec":
            first_start_text, first_end_text = _resolve_today_pair(
                shortcut=args.shortcut,
                today=service.today_provider(),
                start_value=args.fs,
                end_value=args.fe,
                command_name="rec",
                start_option="--fs",
                end_option="--fe",
            )
            if first_start_text is None or first_end_text is None:
                raise DomainError("Please provide --fs and --fe, or use 'rec today'.")
            result = service.create_recurring_task(
                name=args.nm,
                description=args.ds,
                first_start_text=first_start_text,
                first_end_text=first_end_text,
                task_start_text=args.ts,
                task_end_text=args.te,
                repeat_unit=_normalize_repeat(args.rp),
                n=args.iv,
                is_test=args.tt,
            )
            print(f"Created recurring task: {result['task_id']}")
            _print_notes(result["notes"])
            return

        if args.command == "recupd":
            first_start_text, first_end_text = _resolve_today_pair(
                shortcut=args.shortcut,
                today=service.today_provider(),
                start_value=args.fs,
                end_value=args.fe,
                command_name="recupd",
                start_option="--fs",
                end_option="--fe",
            )
            notes = service.update_recurring_task(
                task_id=args.task_id,
                name=args.nm,
                description=args.ds,
                first_start_text=first_start_text,
                first_end_text=first_end_text,
                task_start_text=args.ts,
                task_end_text=args.te,
                repeat_unit=_normalize_repeat(args.rp) if args.rp else None,
                n=args.iv,
            )
            print(f"Updated recurring task: {args.task_id}")
            _print_notes(notes)
            return

        if args.command == "del":
            target = _resolve_target(args.task_id, args.target)
            if not target:
                raise DomainError("Please provide a task id, or use 'del all'.")
            if target == "all":
                deleted = service.delete_all_test_tasks()
                print(
                    "Deleted all test tasks: "
                    f"one_time={deleted['one_time']}, "
                    f"recurring={deleted['recurring']}, "
                    f"schedules={deleted['schedules']}"
                )
                return
            service.delete_task(target)
            print(f"Deleted task: {target}")
            return

        if args.command == "list":
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

        if args.command in {"todo", "doing", "done"}:
            target = _resolve_target(args.task_id, args.target)
            if not target:
                raise DomainError("Please provide a task id, or use 'done all'.")

            if target == "all":
                if args.command != "done":
                    raise DomainError("'all' is only supported by the done command.")
                updated = service.mark_overdue_schedules_done()
                print(f"Marked overdue schedules as done: {updated}")
                return

            resolved_schedule_id = service.set_schedule_status(
                task_id=target,
                schedule_id=args.schedule_id,
                status=args.command,
            )
            print(f"Updated schedule status: {target}#{resolved_schedule_id} -> {args.command}")
            return

        if args.command == "schlist":
            schedules = service.list_schedules(task_id=args.task_id)
            if not schedules:
                print("No schedules found.")
                return
            for item in schedules:
                print(_format_schedule_line(item))
            return

        if args.command == "view":
            from_date_text, to_date_text = _resolve_view_range(
                target=args.target,
                today=service.today_provider(),
                from_date_text=args.from_date,
                to_date_text=args.to_date,
            )
            view = service.view_calendar(
                from_date_text=from_date_text,
                to_date_text=to_date_text,
                filter_mode=_normalize_view_mode(args.m),
            )
            _print_calendar(view)
            return

        if args.command == "delay":
            updated = service.delay_overdue_one_time_tasks_to_today()
            print(f"Delayed overdue one-time tasks to today: {updated}")
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


def _resolve_target(named_target: str | None, positional_target: str | None) -> str | None:
    if named_target and positional_target and named_target != positional_target:
        raise DomainError(f"Conflicting task id values: {named_target} vs {positional_target}.")
    return named_target or positional_target


def _resolve_today_pair(
    *,
    shortcut: str | None,
    today: date,
    start_value: str | None,
    end_value: str | None,
    command_name: str,
    start_option: str,
    end_option: str,
) -> tuple[str | None, str | None]:
    if shortcut is None:
        return start_value, end_value
    if start_value is not None or end_value is not None:
        raise DomainError(f"'{command_name} today' cannot be combined with {start_option} or {end_option}.")
    today_text = format_date(today)
    return today_text, today_text


def _resolve_view_range(
    *,
    target: str | None,
    today: date,
    from_date_text: str | None,
    to_date_text: str | None,
) -> tuple[str | None, str | None]:
    if target is None:
        return from_date_text, to_date_text
    if from_date_text is not None or to_date_text is not None:
        raise DomainError("'view today' cannot be combined with --fd or --td.")
    today_text = format_date(today)
    return today_text, today_text


def _normalize_repeat(repeat_arg: str) -> str:
    mapping = {"d": "day", "w": "week", "m": "month", "y": "year"}
    return mapping.get(repeat_arg, repeat_arg)


def _normalize_view_mode(mode_arg: str) -> str:
    mapping = {"t": "todo", "a": "active", "l": "all"}
    return mapping.get(mode_arg, mode_arg)


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
