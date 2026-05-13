from __future__ import annotations

from datetime import date, timedelta

from cal_app.domain.date_utils import add_interval, add_months, add_years
from cal_app.domain.models import OneTimeTask, RecurringTask, Schedule, Task


def generate_schedules_for_task(task: Task, today: date) -> list[Schedule]:
    if isinstance(task, OneTimeTask):
        return [
            Schedule(
                task_id=task.task_id,
                schedule_id=1,
                name=task.name,
                description=task.description,
                start_date=task.start_date,
                end_date=task.end_date,
            )
        ]
    return _generate_recurring_schedules(task, today)


def _generate_recurring_schedules(task: RecurringTask, today: date) -> list[Schedule]:
    generated: list[Schedule] = []
    duration = task.first_end_date - task.first_start_date
    window_end_lower_bound = add_months(today, -1)
    window_start_upper_bound = add_years(today, 1)

    current_start = task.first_start_date
    schedule_id = 1

    while current_start <= task.task_end_date:
        current_end = current_start + timedelta(days=duration.days)
        if current_end > task.task_end_date:
            break

        if (
            current_start >= task.task_start_date
            and current_end <= task.task_end_date
            and current_end >= window_end_lower_bound
            and current_start <= window_start_upper_bound
        ):
            generated.append(
                Schedule(
                    task_id=task.task_id,
                    schedule_id=schedule_id,
                    name=task.name,
                    description=task.description,
                    start_date=current_start,
                    end_date=current_end,
                )
            )

        current_start = add_interval(current_start, task.repeat_unit, task.n)
        schedule_id += 1

    return generated
