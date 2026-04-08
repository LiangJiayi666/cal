from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from cal_app.domain.constants import (
    STATUS_TODO,
    TASK_KIND_ONE_TIME,
    TASK_KIND_RECURRING,
)
from cal_app.domain.date_utils import format_date, parse_date
from cal_app.domain.errors import DomainError


@dataclass
class OneTimeTask:
    task_id: str
    name: str
    description: str
    start_date: date
    end_date: date
    is_test: bool
    created_date: date
    kind: str = TASK_KIND_ONE_TIME

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "start_date": format_date(self.start_date),
            "end_date": format_date(self.end_date),
            "is_test": self.is_test,
            "created_date": format_date(self.created_date),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OneTimeTask":
        return cls(
            task_id=data["task_id"],
            name=data["name"],
            description=data.get("description", ""),
            start_date=parse_date(data["start_date"], "start_date"),
            end_date=parse_date(data["end_date"], "end_date"),
            is_test=bool(data.get("is_test", False)),
            created_date=parse_date(data["created_date"], "created_date"),
        )


@dataclass
class RecurringTask:
    task_id: str
    name: str
    description: str
    first_start_date: date
    first_end_date: date
    task_start_date: date
    task_end_date: date
    repeat_unit: str
    n: int
    is_test: bool
    created_date: date
    kind: str = TASK_KIND_RECURRING

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "first_start_date": format_date(self.first_start_date),
            "first_end_date": format_date(self.first_end_date),
            "task_start_date": format_date(self.task_start_date),
            "task_end_date": format_date(self.task_end_date),
            "repeat_unit": self.repeat_unit,
            "n": self.n,
            "is_test": self.is_test,
            "created_date": format_date(self.created_date),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecurringTask":
        return cls(
            task_id=data["task_id"],
            name=data["name"],
            description=data.get("description", ""),
            first_start_date=parse_date(data["first_start_date"], "first_start_date"),
            first_end_date=parse_date(data["first_end_date"], "first_end_date"),
            task_start_date=parse_date(data["task_start_date"], "task_start_date"),
            task_end_date=parse_date(data["task_end_date"], "task_end_date"),
            repeat_unit=data["repeat_unit"],
            n=int(data["n"]),
            is_test=bool(data.get("is_test", False)),
            created_date=parse_date(data["created_date"], "created_date"),
        )


@dataclass
class Schedule:
    task_id: str
    schedule_id: int
    name: str
    description: str
    start_date: date
    end_date: date
    status: str = STATUS_TODO

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "schedule_id": self.schedule_id,
            "name": self.name,
            "description": self.description,
            "start_date": format_date(self.start_date),
            "end_date": format_date(self.end_date),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Schedule":
        return cls(
            task_id=data["task_id"],
            schedule_id=int(data["schedule_id"]),
            name=data["name"],
            description=data.get("description", ""),
            start_date=parse_date(data["start_date"], "start_date"),
            end_date=parse_date(data["end_date"], "end_date"),
            status=data["status"],
        )


Task = OneTimeTask | RecurringTask


def task_from_dict(data: dict[str, Any]) -> Task:
    kind = data.get("kind")
    if kind == TASK_KIND_ONE_TIME:
        return OneTimeTask.from_dict(data)
    if kind == TASK_KIND_RECURRING:
        return RecurringTask.from_dict(data)
    raise DomainError(f"Unknown task kind: {kind}")
