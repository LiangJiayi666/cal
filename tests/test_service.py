from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from cal_app.application.service import CalendarService
from cal_app.infrastructure.repository import JsonRepository


class CalendarServiceDelayTests(unittest.TestCase):
    def _build_service(self, today: date) -> CalendarService:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        return CalendarService(JsonRepository(root), today_provider=lambda: today)

    def tearDown(self) -> None:
        temp_dir = getattr(self, "temp_dir", None)
        if temp_dir is not None:
            temp_dir.cleanup()

    def test_delay_moves_only_overdue_unfinished_one_time_tasks(self) -> None:
        service = self._build_service(date(2026, 4, 8))

        overdue = service.create_one_time_task(
            name="Overdue",
            description="",
            start_date_text="2026-04-01",
            end_date_text="2026-04-07",
            is_test=True,
        )["task_id"]
        due_today = service.create_one_time_task(
            name="Today",
            description="",
            start_date_text="2026-04-08",
            end_date_text="2026-04-08",
            is_test=True,
        )["task_id"]
        already_done = service.create_one_time_task(
            name="Done",
            description="",
            start_date_text="2026-04-05",
            end_date_text="2026-04-06",
            is_test=True,
        )["task_id"]

        service.set_schedule_status(task_id=already_done, schedule_id=None, status="done")

        updated = service.delay_overdue_one_time_tasks_to_today()

        self.assertEqual(updated, 1)
        self.assertEqual(service.one_time_tasks[overdue].end_date, date(2026, 4, 8))
        self.assertEqual(service.one_time_tasks[due_today].end_date, date(2026, 4, 8))
        self.assertEqual(service.one_time_tasks[already_done].end_date, date(2026, 4, 6))
        self.assertEqual(service._find_schedule(overdue, 1).end_date, date(2026, 4, 8))
        self.assertEqual(service._find_schedule(overdue, 1).status, "todo")

    def test_delay_preserves_non_done_status(self) -> None:
        service = self._build_service(date(2026, 4, 8))

        task_id = service.create_one_time_task(
            name="Doing",
            description="",
            start_date_text="2026-04-03",
            end_date_text="2026-04-06",
            is_test=True,
        )["task_id"]
        service.set_schedule_status(task_id=task_id, schedule_id=None, status="doing")

        updated = service.delay_overdue_one_time_tasks_to_today()

        self.assertEqual(updated, 1)
        self.assertEqual(service.one_time_tasks[task_id].end_date, date(2026, 4, 8))
        self.assertEqual(service._find_schedule(task_id, 1).status, "doing")

    def test_view_defaults_to_one_week(self) -> None:
        service = self._build_service(date(2026, 4, 8))

        view = service.view_calendar(
            from_date_text=None,
            to_date_text=None,
            filter_mode="active",
        )

        self.assertEqual(view["from_date"], date(2026, 4, 8))
        self.assertEqual(view["to_date"], date(2026, 4, 14))
        self.assertEqual(len(view["grouped"]), 7)
        self.assertEqual(sorted(view["grouped"].keys())[-1], date(2026, 4, 8) + timedelta(days=6))


if __name__ == "__main__":
    unittest.main()
