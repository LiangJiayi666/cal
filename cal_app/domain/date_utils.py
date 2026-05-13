from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from cal_app.domain.constants import (
    DATE_FORMAT,
    REPEAT_DAY,
    REPEAT_MONTH,
    REPEAT_WEEK,
    REPEAT_YEAR,
)
from cal_app.domain.errors import DomainError


def parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise DomainError(f"Invalid date for {field_name}: {value}. Use YYYY-MM-DD.") from error


def format_date(value: date) -> str:
    return value.strftime(DATE_FORMAT)


def add_months(value: date, months: int) -> date:
    month_index = (value.month - 1) + months
    year = value.year + (month_index // 12)
    month = (month_index % 12) + 1
    max_day = monthrange(year, month)[1]
    day = min(value.day, max_day)
    return date(year, month, day)


def add_years(value: date, years: int) -> date:
    target_year = value.year + years
    max_day = monthrange(target_year, value.month)[1]
    day = min(value.day, max_day)
    return date(target_year, value.month, day)


def add_interval(value: date, repeat_unit: str, n: int) -> date:
    if repeat_unit == REPEAT_DAY:
        return value + timedelta(days=n)
    if repeat_unit == REPEAT_WEEK:
        return value + timedelta(weeks=n)
    if repeat_unit == REPEAT_MONTH:
        return add_months(value, n)
    if repeat_unit == REPEAT_YEAR:
        return add_years(value, n)
    raise DomainError(f"Unsupported repeat unit: {repeat_unit}")
