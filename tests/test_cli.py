from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from unittest.mock import patch

from cal_app.application.service import CalendarService
from cal_app.cli import main
from cal_app.domain.date_utils import format_date
from cal_app.infrastructure.repository import JsonRepository


class CliTodayShortcutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.today = date(2026, 4, 8)
        root = Path(self.temp_dir.name)
        self.service = CalendarService(JsonRepository(root), today_provider=lambda: self.today)
        self.service.meta["last_maintenance"] = format_date(self.today)
        self.service._save()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _run_main(self, *argv: str) -> tuple[str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("cal_app.cli.CalendarService.default", return_value=self.service):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                main(list(argv))
        return stdout.getvalue(), stderr.getvalue()

    def test_once_today_creates_today_task(self) -> None:
        self._run_main("once", "today", "--nm", "Quick task", "--tt")

        task = next(iter(self.service.one_time_tasks.values()))
        self.assertEqual(task.start_date, self.today)
        self.assertEqual(task.end_date, self.today)

    def test_rec_today_creates_recurring_task_with_first_dates_today(self) -> None:
        self._run_main("rec", "today", "--nm", "Daily check", "--rp", "d", "--tt")

        task = next(iter(self.service.recurring_tasks.values()))
        self.assertEqual(task.first_start_date, self.today)
        self.assertEqual(task.first_end_date, self.today)

    def test_onceupd_today_updates_start_and_end_to_today(self) -> None:
        task_id = self.service.create_one_time_task(
            name="Later",
            description="",
            start_date_text="2026-04-10",
            end_date_text="2026-04-11",
            is_test=True,
        )["task_id"]

        self._run_main("onceupd", "today", "--id", task_id)

        task = self.service.one_time_tasks[task_id]
        self.assertEqual(task.start_date, self.today)
        self.assertEqual(task.end_date, self.today)

    def test_recupd_today_updates_first_dates_to_today(self) -> None:
        task_id = self.service.create_recurring_task(
            name="Weekly check",
            description="",
            first_start_text="2026-04-01",
            first_end_text="2026-04-02",
            task_start_text=None,
            task_end_text=None,
            repeat_unit="week",
            n=1,
            is_test=True,
        )["task_id"]

        self._run_main("recupd", "today", "--id", task_id)

        task = self.service.recurring_tasks[task_id]
        self.assertEqual(task.first_start_date, self.today)
        self.assertEqual(task.first_end_date, self.today)

    def test_view_today_shows_only_today(self) -> None:
        output, _ = self._run_main("view", "today")

        self.assertIn("2026-04-08 (Wed):", output)
        self.assertNotIn("2026-04-09 (Thu):", output)

    def test_delay_id_updates_specific_one_time_task(self) -> None:
        task_id = self.service.create_one_time_task(
            name="Delay me",
            description="",
            start_date_text="2026-04-02",
            end_date_text="2026-04-06",
            is_test=True,
        )["task_id"]

        output, _ = self._run_main("delay", "--id", task_id)

        self.assertIn(f"Delayed one-time task to today: {task_id}", output)
        self.assertEqual(self.service.one_time_tasks[task_id].end_date, self.today)

    def test_delay_positional_id_updates_specific_one_time_task(self) -> None:
        task_id = self.service.create_one_time_task(
            name="Delay me too",
            description="",
            start_date_text="2026-04-02",
            end_date_text="2026-04-06",
            is_test=True,
        )["task_id"]

        output, _ = self._run_main("delay", task_id)

        self.assertIn(f"Delayed one-time task to today: {task_id}", output)
        self.assertEqual(self.service.one_time_tasks[task_id].end_date, self.today)


if __name__ == "__main__":
    unittest.main()
