# cal

A CLI calendar/task tool with:

- Bottom task pool: one-time tasks and recurring tasks.
- Middle schedule pool: generated schedules with status (`todo`, `doing`, `done`).
- Daily maintenance on the first command run each day.

## Project structure

- `cal_app/domain`: entities, constants, validation, date rules.
- `cal_app/application`: use cases and schedule generation engine.
- `cal_app/infrastructure`: JSON persistence.
- `cal_app/cli.py`: argument parsing and terminal output.
- `data/state.json`: runtime state storage.

## Quick start

Run from `cal/`:

```bash
python main.py --help
```

Date format for all date arguments: `YYYY-MM-DD`.

## Runtime behavior

- All commands except `maintenance-run` first trigger "daily maintenance if needed".
- `maintenance-run` forces maintenance even if already run today.
- IDs are auto-generated 6-char strings using `1-9A-F`.
- For task updates, schedules are regenerated for that task and previous status is preserved by `(task_id, schedule_id)`.

## Command reference

### `task-add-once`

Create a one-time task.

| Parameter | Required | Type | Default | Description |
|---|---|---|---|---|
| `--name` | Yes | string | - | Task name. |
| `--description` | No | string | `""` | Task description. |
| `--start` | Yes | date | - | Start date. |
| `--end` | Yes | date | - | End date. |
| `--test` | No | flag | `False` | Mark as test task (test tasks can be deleted). |

Rule:
- If `start > end`, start is adjusted to `end` and a note is printed.

Example:

```bash
python main.py task-add-once --name "Lecture check" --description "Find good talks" --start 2026-04-10 --end 2026-04-08 --test
```

### `task-update-once`

Update fields of an existing one-time task.

| Parameter | Required | Type | Default | Description |
|---|---|---|---|---|
| `--id` | Yes | string | - | Task ID. |
| `--name` | No | string | keep current | New task name. |
| `--description` | No | string | keep current | New description. |
| `--start` | No | date | keep current | New start date. |
| `--end` | No | date | keep current | New end date. |

Rule:
- After update, if `start > end`, start is adjusted to `end` and a note is printed.

Example:

```bash
python main.py task-update-once --id 123ABC --end 2026-04-12
```

### `task-add-recurring`

Create a recurring task.

| Parameter | Required | Type | Default | Description |
|---|---|---|---|---|
| `--name` | Yes | string | - | Task name. |
| `--description` | No | string | `""` | Task description. |
| `--first-start` | Yes | date | - | First occurrence start date. |
| `--first-end` | Yes | date | - | First occurrence end date. |
| `--task-start` | No | date | `first-start` | Overall recurring task start boundary. |
| `--task-end` | No | date | `2100-01-01` | Overall recurring task end boundary. |
| `--repeat` | Yes | enum | - | Repeat unit: `day`, `week`, `month`, `year`. |
| `--n` | No | int | `1` | Repeat every `n` units. Must be `>= 1`. |
| `--test` | No | flag | `False` | Mark as test task. |

Normalization rules:
- If `first-start > first-end`, `first-start` is adjusted to `first-end`.
- If `task-end < first-end`, `task-end` is adjusted to `first-end`.
- If `task-start > first-start`, `task-start` is adjusted to `first-start`.
- Each adjustment prints a note.

Example:

```bash
python main.py task-add-recurring --name "Weekly check" --first-start 2026-04-08 --first-end 2026-04-09 --task-end 2026-05-01 --repeat week --n 1 --test
```

### `task-update-recurring`

Update fields of an existing recurring task.

| Parameter | Required | Type | Default | Description |
|---|---|---|---|---|
| `--id` | Yes | string | - | Task ID. |
| `--name` | No | string | keep current | New task name. |
| `--description` | No | string | keep current | New description. |
| `--first-start` | No | date | keep current | New first occurrence start date. |
| `--first-end` | No | date | keep current | New first occurrence end date. |
| `--task-start` | No | date | keep current | New recurring boundary start. |
| `--task-end` | No | date | keep current | New recurring boundary end. |
| `--repeat` | No | enum | keep current | `day`, `week`, `month`, `year`. |
| `--n` | No | int | keep current | Repeat every `n` units (`>=1`). |

Normalization rules are the same as `task-add-recurring`.

Example:

```bash
python main.py task-update-recurring --id 123ABC --task-end 2027-01-01 --repeat month --n 2
```

### `task-delete`

Delete a task by ID.

| Parameter | Required | Type | Default | Description |
|---|---|---|---|---|
| `--id` | Yes | string | - | Task ID. |

Rule:
- Only test tasks can be deleted. Non-test tasks return an error.

Example:

```bash
python main.py task-delete --id 123ABC
```

### `task-list`

List all tasks.

Parameters: none.

Example:

```bash
python main.py task-list
```

### `schedule-set-status`

Set a schedule status.

| Parameter | Required | Type | Default | Description |
|---|---|---|---|---|
| `--task-id` | Yes | string | - | Task ID. |
| `--schedule-id` | Yes | int | - | Schedule sequence ID. |
| `--status` | Yes | enum | - | `todo`, `doing`, `done`. |

Example:

```bash
python main.py schedule-set-status --task-id 123ABC --schedule-id 1 --status done
```

### `schedule-list`

List schedules.

| Parameter | Required | Type | Default | Description |
|---|---|---|---|---|
| `--task-id` | No | string | all tasks | Filter schedules by task ID. |

Example:

```bash
python main.py schedule-list
python main.py schedule-list --task-id 123ABC
```

### `calendar-view`

Show calendar lines by date plus past unfinished schedules.

| Parameter | Required | Type | Default | Description |
|---|---|---|---|---|
| `--from` | No | date | today | View start date. |
| `--to` | No | date | `from + 14 days` | View end date (must be `>= from`). |
| `--filter` | No | enum | `active` | `todo`, `active` (`todo+doing`), `all` (`todo+doing+done`). |

Example:

```bash
python main.py calendar-view --from 2026-04-01 --to 2026-04-10 --filter all
```

### `maintenance-run`

Force daily maintenance immediately.

Parameters: none.

Example:

```bash
python main.py maintenance-run
```
