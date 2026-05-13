from __future__ import annotations

from datetime import date

from cal_app.domain.constants import VALID_REPEAT_UNITS, VALID_STATUSES
from cal_app.domain.errors import DomainError


def validate_required_name(name: str) -> None:
    if not name or not name.strip():
        raise DomainError("Name is required.")


def normalize_one_time_dates(start_date: date, end_date: date) -> tuple[date, date, list[str]]:
    messages: list[str] = []
    if start_date > end_date:
        start_date = end_date
        messages.append("start_date was later than end_date, adjusted to end_date.")
    return start_date, end_date, messages


def normalize_recurring_dates(
    first_start_date: date,
    first_end_date: date,
    task_start_date: date,
    task_end_date: date,
) -> tuple[date, date, date, date, list[str]]:
    messages: list[str] = []

    if first_start_date > first_end_date:
        first_start_date = first_end_date
        messages.append("first_start_date was later than first_end_date, adjusted to first_end_date.")

    if task_end_date < first_end_date:
        task_end_date = first_end_date
        messages.append("task_end_date was earlier than first_end_date, adjusted to first_end_date.")

    if task_start_date > first_start_date:
        task_start_date = first_start_date
        messages.append("task_start_date was later than first_start_date, adjusted to first_start_date.")

    return first_start_date, first_end_date, task_start_date, task_end_date, messages


def validate_repeat(repeat_unit: str, n: int) -> None:
    if repeat_unit not in VALID_REPEAT_UNITS:
        raise DomainError(f"Unsupported repeat_unit: {repeat_unit}.")
    if n < 1:
        raise DomainError("n must be at least 1.")


def validate_status(status: str) -> None:
    if status not in VALID_STATUSES:
        raise DomainError(f"Unsupported status: {status}.")
