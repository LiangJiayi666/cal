from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from cal_app.application.scheduler_engine import generate_schedules_for_task
from cal_app.domain.constants import (
    DEFAULT_RECURRING_END,
    ID_ALPHABET,
    ID_LENGTH,
    STATUS_DONE,
    TASK_KIND_ONE_TIME,
    TASK_KIND_RECURRING,
)
from cal_app.domain.date_utils import add_months, format_date, parse_date
from cal_app.domain.errors import DomainError
from cal_app.domain.models import OneTimeTask, RecurringTask, Schedule, Task, task_from_dict
from cal_app.domain.rules import (
    normalize_one_time_dates,
    normalize_recurring_dates,
    validate_repeat,
    validate_required_name,
    validate_status,
)
from cal_app.infrastructure.repository import JsonRepository


class CalendarService:
    def __init__(self, repository: JsonRepository, today_provider: Any = date.today) -> None:
        self.repository = repository
        self.today_provider = today_provider
        self.meta: dict[str, Any] = {}
        self.one_time_tasks: dict[str, OneTimeTask] = {}
        self.recurring_tasks: dict[str, RecurringTask] = {}
        self.schedules: list[Schedule] = []
        self._load()

    @classmethod
    def default(cls, project_root: Path | None = None) -> "CalendarService":
        if project_root is None:
            project_root = Path(__file__).resolve().parents[2]
        return cls(JsonRepository(project_root))

    def _load(self) -> None:
        state = self.repository.load()
        self.meta = state.get("meta", {"last_maintenance": ""})

        self.one_time_tasks = {}
        for item in state.get("tasks", {}).get("one_time", []):
            task = task_from_dict(item)
            if isinstance(task, OneTimeTask):
                self.one_time_tasks[task.task_id] = task

        self.recurring_tasks = {}
        for item in state.get("tasks", {}).get("recurring", []):
            task = task_from_dict(item)
            if isinstance(task, RecurringTask):
                self.recurring_tasks[task.task_id] = task

        self.schedules = [Schedule.from_dict(item) for item in state.get("schedules", [])]

    def _save(self) -> None:
        state = {
            "meta": self.meta,
            "tasks": {
                "one_time": [task.to_dict() for task in self.one_time_tasks.values()],
                "recurring": [task.to_dict() for task in self.recurring_tasks.values()],
            },
            "schedules": [schedule.to_dict() for schedule in self.schedules],
        }
        self.repository.save(state)

    def _all_tasks(self) -> list[Task]:
        return list(self.one_time_tasks.values()) + list(self.recurring_tasks.values())

    def _all_task_ids(self) -> set[str]:
        return set(self.one_time_tasks.keys()) | set(self.recurring_tasks.keys())

    def _new_task_id(self) -> str:
        existing = self._all_task_ids()
        while True:
            candidate = "".join(random.choice(ID_ALPHABET) for _ in range(ID_LENGTH))
            if candidate not in existing:
                return candidate

    def _find_task_kind(self, task_id: str) -> str:
        if task_id in self.one_time_tasks:
            return TASK_KIND_ONE_TIME
        if task_id in self.recurring_tasks:
            return TASK_KIND_RECURRING
        raise DomainError(f"Task not found: {task_id}")

    def _sync_task_schedules(self, task_id: str) -> None:
        status_map = {
            schedule.schedule_id: schedule.status
            for schedule in self.schedules
            if schedule.task_id == task_id
        }
        self.schedules = [schedule for schedule in self.schedules if schedule.task_id != task_id]

        task: Task | None = None
        if task_id in self.one_time_tasks:
            task = self.one_time_tasks[task_id]
        if task_id in self.recurring_tasks:
            task = self.recurring_tasks[task_id]
        if task is None:
            return

        generated = generate_schedules_for_task(task, self.today_provider())
        for schedule in generated:
            if schedule.schedule_id in status_map:
                schedule.status = status_map[schedule.schedule_id]
        self.schedules.extend(generated)

    def _regen_all_schedules(self) -> dict[str, Any]:
        old_schedules = list(self.schedules)
        status_map = {
            (schedule.task_id, schedule.schedule_id): schedule.status for schedule in old_schedules
        }
        regenerated: list[Schedule] = []
        for task in self._all_tasks():
            generated = generate_schedules_for_task(task, self.today_provider())
            for schedule in generated:
                key = (schedule.task_id, schedule.schedule_id)
                if key in status_map:
                    schedule.status = status_map[key]
            regenerated.extend(generated)
        self.schedules = regenerated
        return self._compare_schedule_shapes(old_schedules, regenerated)

    def _compare_schedule_shapes(
        self, old_schedules: list[Schedule], new_schedules: list[Schedule]
    ) -> dict[str, int]:
        old_keys = {(item.task_id, item.schedule_id) for item in old_schedules}
        new_keys = {(item.task_id, item.schedule_id) for item in new_schedules}
        return {
            "added": len(new_keys - old_keys),
            "removed": len(old_keys - new_keys),
        }

    def _find_schedule(self, task_id: str, schedule_id: int) -> Schedule:
        for schedule in self.schedules:
            if schedule.task_id == task_id and schedule.schedule_id == schedule_id:
                return schedule
        raise DomainError(f"Schedule not found: {task_id}#{schedule_id}")

    def run_daily_maintenance(self, *, force: bool = False) -> dict[str, Any]:
        today = self.today_provider()
        today_text = format_date(today)
        if not force and self.meta.get("last_maintenance") == today_text:
            return {"ran": False, "removed_one_time": 0, "removed_recurring": 0, "delta": {}}

        cutoff = add_months(today, -1)
        removed_one_time = 0
        removed_recurring = 0

        one_time_to_remove: list[str] = []
        for task in self.one_time_tasks.values():
            try:
                schedule = self._find_schedule(task.task_id, 1)
            except DomainError:
                continue
            if schedule.status == STATUS_DONE and task.end_date <= cutoff:
                one_time_to_remove.append(task.task_id)

        for task_id in one_time_to_remove:
            removed_one_time += 1
            self.one_time_tasks.pop(task_id, None)
            self.schedules = [item for item in self.schedules if item.task_id != task_id]

        recurring_to_remove: list[str] = []
        for task in self.recurring_tasks.values():
            if task.task_end_date > cutoff:
                continue
            task_schedules = [item for item in self.schedules if item.task_id == task.task_id]
            if task_schedules and all(item.status == STATUS_DONE for item in task_schedules):
                recurring_to_remove.append(task.task_id)

        for task_id in recurring_to_remove:
            removed_recurring += 1
            self.recurring_tasks.pop(task_id, None)
            self.schedules = [item for item in self.schedules if item.task_id != task_id]

        delta = self._regen_all_schedules()
        self.meta["last_maintenance"] = today_text
        self._save()
        return {
            "ran": True,
            "removed_one_time": removed_one_time,
            "removed_recurring": removed_recurring,
            "delta": delta,
        }

    def run_daily_maintenance_if_needed(self) -> dict[str, Any]:
        return self.run_daily_maintenance(force=False)

    def create_one_time_task(
        self,
        *,
        name: str,
        description: str,
        start_date_text: str,
        end_date_text: str,
        is_test: bool,
    ) -> dict[str, Any]:
        validate_required_name(name)
        start_date = parse_date(start_date_text, "start_date")
        end_date = parse_date(end_date_text, "end_date")
        start_date, end_date, notes = normalize_one_time_dates(start_date, end_date)

        task = OneTimeTask(
            task_id=self._new_task_id(),
            name=name.strip(),
            description=description.strip(),
            start_date=start_date,
            end_date=end_date,
            is_test=is_test,
            created_date=self.today_provider(),
        )
        self.one_time_tasks[task.task_id] = task
        self._sync_task_schedules(task.task_id)
        self._save()
        return {"task_id": task.task_id, "notes": notes}

    def update_one_time_task(
        self,
        *,
        task_id: str,
        name: str | None,
        description: str | None,
        start_date_text: str | None,
        end_date_text: str | None,
    ) -> list[str]:
        if task_id not in self.one_time_tasks:
            raise DomainError(f"One-time task not found: {task_id}")
        task = self.one_time_tasks[task_id]

        if name is not None:
            validate_required_name(name)
            task.name = name.strip()
        if description is not None:
            task.description = description.strip()
        if start_date_text is not None:
            task.start_date = parse_date(start_date_text, "start_date")
        if end_date_text is not None:
            task.end_date = parse_date(end_date_text, "end_date")

        task.start_date, task.end_date, notes = normalize_one_time_dates(task.start_date, task.end_date)
        self._sync_task_schedules(task.task_id)
        self._save()
        return notes

    def create_recurring_task(
        self,
        *,
        name: str,
        description: str,
        first_start_text: str,
        first_end_text: str,
        task_start_text: str | None,
        task_end_text: str | None,
        repeat_unit: str,
        n: int,
        is_test: bool,
    ) -> dict[str, Any]:
        validate_required_name(name)
        validate_repeat(repeat_unit, n)

        first_start = parse_date(first_start_text, "first_start_date")
        first_end = parse_date(first_end_text, "first_end_date")
        task_start = parse_date(task_start_text, "task_start_date") if task_start_text else first_start
        task_end = parse_date(task_end_text, "task_end_date") if task_end_text else DEFAULT_RECURRING_END

        first_start, first_end, task_start, task_end, notes = normalize_recurring_dates(
            first_start, first_end, task_start, task_end
        )

        task = RecurringTask(
            task_id=self._new_task_id(),
            name=name.strip(),
            description=description.strip(),
            first_start_date=first_start,
            first_end_date=first_end,
            task_start_date=task_start,
            task_end_date=task_end,
            repeat_unit=repeat_unit,
            n=n,
            is_test=is_test,
            created_date=self.today_provider(),
        )
        self.recurring_tasks[task.task_id] = task
        self._sync_task_schedules(task.task_id)
        self._save()
        return {"task_id": task.task_id, "notes": notes}

    def update_recurring_task(
        self,
        *,
        task_id: str,
        name: str | None,
        description: str | None,
        first_start_text: str | None,
        first_end_text: str | None,
        task_start_text: str | None,
        task_end_text: str | None,
        repeat_unit: str | None,
        n: int | None,
    ) -> list[str]:
        if task_id not in self.recurring_tasks:
            raise DomainError(f"Recurring task not found: {task_id}")
        task = self.recurring_tasks[task_id]

        if name is not None:
            validate_required_name(name)
            task.name = name.strip()
        if description is not None:
            task.description = description.strip()
        if first_start_text is not None:
            task.first_start_date = parse_date(first_start_text, "first_start_date")
        if first_end_text is not None:
            task.first_end_date = parse_date(first_end_text, "first_end_date")
        if task_start_text is not None:
            task.task_start_date = parse_date(task_start_text, "task_start_date")
        if task_end_text is not None:
            task.task_end_date = parse_date(task_end_text, "task_end_date")
        if repeat_unit is not None:
            task.repeat_unit = repeat_unit
        if n is not None:
            task.n = n

        validate_repeat(task.repeat_unit, task.n)
        (
            task.first_start_date,
            task.first_end_date,
            task.task_start_date,
            task.task_end_date,
            notes,
        ) = normalize_recurring_dates(
            task.first_start_date,
            task.first_end_date,
            task.task_start_date,
            task.task_end_date,
        )

        self._sync_task_schedules(task.task_id)
        self._save()
        return notes

    def delete_task(self, task_id: str) -> None:
        kind = self._find_task_kind(task_id)
        if kind == TASK_KIND_ONE_TIME:
            if not self.one_time_tasks[task_id].is_test:
                raise DomainError("Only test tasks can be deleted.")
            self.one_time_tasks.pop(task_id, None)
        else:
            if not self.recurring_tasks[task_id].is_test:
                raise DomainError("Only test tasks can be deleted.")
            self.recurring_tasks.pop(task_id, None)
        self.schedules = [item for item in self.schedules if item.task_id != task_id]
        self._save()

    def delete_all_test_tasks(self) -> dict[str, int]:
        one_time_ids = [task_id for task_id, task in self.one_time_tasks.items() if task.is_test]
        recurring_ids = [task_id for task_id, task in self.recurring_tasks.items() if task.is_test]
        deleted_ids = set(one_time_ids) | set(recurring_ids)

        for task_id in one_time_ids:
            self.one_time_tasks.pop(task_id, None)
        for task_id in recurring_ids:
            self.recurring_tasks.pop(task_id, None)

        before = len(self.schedules)
        self.schedules = [item for item in self.schedules if item.task_id not in deleted_ids]
        removed_schedules = before - len(self.schedules)

        self._save()
        return {
            "one_time": len(one_time_ids),
            "recurring": len(recurring_ids),
            "schedules": removed_schedules,
        }

    def _resolve_schedule_id(self, *, task_id: str, schedule_id: int | None) -> int:
        if schedule_id is not None:
            return schedule_id
        kind = self._find_task_kind(task_id)
        if kind == TASK_KIND_ONE_TIME:
            return 1
        raise DomainError("Recurring task requires --sid.")

    def set_schedule_status(self, *, task_id: str, schedule_id: int | None, status: str) -> int:
        validate_status(status)
        resolved_schedule_id = self._resolve_schedule_id(task_id=task_id, schedule_id=schedule_id)
        schedule = self._find_schedule(task_id, resolved_schedule_id)
        schedule.status = status
        self._save()
        return resolved_schedule_id

    def mark_overdue_schedules_done(self) -> int:
        yesterday = self.today_provider() - timedelta(days=1)
        updated = 0
        for schedule in self.schedules:
            if schedule.end_date <= yesterday and schedule.status != STATUS_DONE:
                schedule.status = STATUS_DONE
                updated += 1
        if updated:
            self._save()
        return updated

    def delay_overdue_one_time_tasks_to_today(self) -> int:
        today = self.today_provider()
        yesterday = today - timedelta(days=1)
        updated = 0

        for task in list(self.one_time_tasks.values()):
            if task.end_date > yesterday:
                continue

            try:
                schedule = self._find_schedule(task.task_id, 1)
            except DomainError:
                continue

            if schedule.status == STATUS_DONE:
                continue

            task.end_date = today
            self._sync_task_schedules(task.task_id)
            updated += 1

        if updated:
            self._save()
        return updated

    def list_tasks(self) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for task in self.one_time_tasks.values():
            output.append(
                {
                    "kind": TASK_KIND_ONE_TIME,
                    "task_id": task.task_id,
                    "name": task.name,
                    "start_date": task.start_date,
                    "end_date": task.end_date,
                    "is_test": task.is_test,
                }
            )
        for task in self.recurring_tasks.values():
            output.append(
                {
                    "kind": TASK_KIND_RECURRING,
                    "task_id": task.task_id,
                    "name": task.name,
                    "start_date": task.task_start_date,
                    "end_date": task.task_end_date,
                    "is_test": task.is_test,
                    "repeat_unit": task.repeat_unit,
                    "n": task.n,
                }
            )
        return sorted(output, key=lambda item: item["task_id"])

    def list_schedules(self, task_id: str | None = None) -> list[Schedule]:
        items = self.schedules
        if task_id is not None:
            items = [item for item in items if item.task_id == task_id]
        return sorted(items, key=lambda item: (item.start_date, item.task_id, item.schedule_id))

    def view_calendar(
        self,
        *,
        from_date_text: str | None,
        to_date_text: str | None,
        filter_mode: str,
    ) -> dict[str, Any]:
        today = self.today_provider()
        from_date = parse_date(from_date_text, "from_date") if from_date_text else today
        to_date = parse_date(to_date_text, "to_date") if to_date_text else (from_date + timedelta(days=6))
        if to_date < from_date:
            raise DomainError("to_date must be greater than or equal to from_date.")

        allowed_statuses = _status_filter(filter_mode)
        grouped: dict[date, list[Schedule]] = {}
        day = from_date
        while day <= to_date:
            entries = [
                item
                for item in self.schedules
                if item.status in allowed_statuses and item.start_date <= day <= item.end_date
            ]
            grouped[day] = sorted(entries, key=lambda entry: (entry.task_id, entry.schedule_id))
            day += timedelta(days=1)

        overdue = sorted(
            [
                item
                for item in self.schedules
                if item.end_date < today and item.status != STATUS_DONE
            ],
            key=lambda entry: (entry.end_date, entry.task_id, entry.schedule_id),
        )

        return {"from_date": from_date, "to_date": to_date, "grouped": grouped, "overdue": overdue}


def _status_filter(filter_mode: str) -> set[str]:
    if filter_mode == "todo":
        return {"todo"}
    if filter_mode == "active":
        return {"todo", "doing"}
    if filter_mode == "all":
        return {"todo", "doing", "done"}
    raise DomainError(f"Unsupported filter mode: {filter_mode}")
