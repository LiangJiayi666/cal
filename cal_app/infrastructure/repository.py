from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def default_state() -> dict[str, Any]:
    return {
        "meta": {"last_maintenance": ""},
        "tasks": {"one_time": [], "recurring": []},
        "schedules": [],
    }


class JsonRepository:
    def __init__(self, root_dir: Path) -> None:
        self.data_dir = root_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.data_dir / "state.json"
        if not self.state_file.exists():
            self.save(default_state())

    def load(self) -> dict[str, Any]:
        with self.state_file.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
        return data

    def save(self, state: dict[str, Any]) -> None:
        with self.state_file.open("w", encoding="utf-8") as file:
            json.dump(state, file, ensure_ascii=False, indent=2)
