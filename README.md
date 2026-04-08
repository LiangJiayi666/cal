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

- All commands except `maint` first trigger "daily maintenance if needed".
- `maint` forces maintenance even if already run today.
- IDs are auto-generated 6-char strings using `1-9A-F`.
- For task updates, schedules are regenerated for that task and previous status is preserved by `(task_id, schedule_id)`.

### Common parameter abbreviations

| Parameter | Meaning           |
| --------- | ----------------- |
| `--id`    | task id           |
| `--sid`   | schedule id       |
| `--nm`    | name              |
| `--ds`    | description       |
| `--sd`    | start date        |
| `--ed`    | end date          |
| `--fs`    | first start date  |
| `--fe`    | first end date    |
| `--ts`    | task start date   |
| `--te`    | task end date     |
| `--rp`    | repeat unit       |
| `--iv`    | interval number   |
| `--tt`    | mark as test task |
| `--fd`    | from date         |
| `--td`    | to date           |
| `--m`     | view mode         |

## Command reference

### `once`

Create a one-time task.

| Parameter | Required | Type   | Default | Description        |
| --------- | -------- | ------ | ------- | ------------------ |
| `today`   | No       | token  | -       | Shortcut: set `sd=ed=today`. |
| `--nm`    | Yes      | string | -       | Task name.         |
| `--ds`    | No       | string | `""`    | Task description.  |
| `--sd`    | Cond.    | date   | -       | Start date. Required unless using `today`. |
| `--ed`    | Cond.    | date   | -       | End date. Required unless using `today`. |
| `--tt`    | No       | flag   | `False` | Mark as test task. |

Rule:
- If `sd > ed`, start is adjusted to end and a note is printed.
- `once today` sets both `sd` and `ed` to today.
- `once today` cannot be combined with `--sd` or `--ed`.

Example:

```bash
python main.py once --nm "Lecture check" --ds "Find good talks" --sd 2026-04-10 --ed 2026-04-08 --tt
python main.py once today --nm "Quick note"
```

### `onceupd`

Update fields of an existing one-time task.

| Parameter | Required | Type   | Default      | Description      |
| --------- | -------- | ------ | ------------ | ---------------- |
| `today`   | No       | token  | -            | Shortcut: set `sd=ed=today`. |
| `--id`    | Yes      | string | -            | Task ID.         |
| `--nm`    | No       | string | keep current | New name.        |
| `--ds`    | No       | string | keep current | New description. |
| `--sd`    | No       | date   | keep current | New start date.  |
| `--ed`    | No       | date   | keep current | New end date.    |

Rule:
- After update, if `sd > ed`, start is adjusted to end and a note is printed.
- `onceupd today` sets both `sd` and `ed` to today.
- `onceupd today` cannot be combined with `--sd` or `--ed`.

Example:

```bash
python main.py onceupd --id 123ABC --ed 2026-04-12
python main.py onceupd today --id 123ABC
```

### `rec`

Create a recurring task.

| Parameter | Required | Type   | Default      | Description                                      |
| --------- | -------- | ------ | ------------ | ------------------------------------------------ |
| `today`   | No       | token  | -            | Shortcut: set `fs=fe=today`.                     |
| `--nm`    | Yes      | string | -            | Task name.                                       |
| `--ds`    | No       | string | `""`         | Task description.                                |
| `--fs`    | Cond.    | date   | -            | First occurrence start date. Required unless using `today`. |
| `--fe`    | Cond.    | date   | -            | First occurrence end date. Required unless using `today`. |
| `--ts`    | No       | date   | `fs`         | Recurring task start boundary.                   |
| `--te`    | No       | date   | `2100-01-01` | Recurring task end boundary.                     |
| `--rp`    | Yes      | enum   | -            | Repeat unit: `d/w/m/y` or `day/week/month/year`. |
| `--iv`    | No       | int    | `1`          | Repeat every `iv` units (`>=1`).                 |
| `--tt`    | No       | flag   | `False`      | Mark as test task.                               |

Normalization rules:
- If `fs > fe`, `fs` is adjusted to `fe`.
- If `te < fe`, `te` is adjusted to `fe`.
- If `ts > fs`, `ts` is adjusted to `fs`.
- `rec today` sets both `fs` and `fe` to today.
- `rec today` cannot be combined with `--fs` or `--fe`.

Example:

```bash
python main.py rec --nm "Weekly check" --fs 2026-04-08 --fe 2026-04-09 --te 2026-05-01 --rp w --iv 1 --tt
python main.py rec today --nm "Daily check" --rp d
```

### `recupd`

Update fields of an existing recurring task.

| Parameter | Required | Type   | Default      | Description              |
| --------- | -------- | ------ | ------------ | ------------------------ |
| `today`   | No       | token  | -            | Shortcut: set `fs=fe=today`. |
| `--id`    | Yes      | string | -            | Task ID.                 |
| `--nm`    | No       | string | keep current | New name.                |
| `--ds`    | No       | string | keep current | New description.         |
| `--fs`    | No       | date   | keep current | New first start date.    |
| `--fe`    | No       | date   | keep current | New first end date.      |
| `--ts`    | No       | date   | keep current | New task start boundary. |
| `--te`    | No       | date   | keep current | New task end boundary.   |
| `--rp`    | No       | enum   | keep current | `d/w/m/y` or full words. |
| `--iv`    | No       | int    | keep current | New interval (`>=1`).    |

Rule:
- `recupd today` sets both `fs` and `fe` to today.
- `recupd today` cannot be combined with `--fs` or `--fe`.

Example:

```bash
python main.py recupd --id 123ABC --te 2027-01-01 --rp m --iv 2
python main.py recupd today --id 123ABC
```

### `del`

Delete test tasks (single or bulk).

| Parameter | Required | Type   | Default | Description                                |
| --------- | -------- | ------ | ------- | ------------------------------------------ |
| `target`  | No       | string | -       | Positional target: task ID or `all`.       |
| `--id`    | No       | string | -       | Named task ID (same effect as `del <id>`). |

Rule:
- `del all` deletes all test tasks.
- `del <task_id>` or `del --id <task_id>` deletes one test task.
- Non-test tasks return an error.

Example:

```bash
python main.py del all
python main.py del 123ABC
python main.py del --id 123ABC
```

### `list`

List all tasks.

Parameters: none.

```bash
python main.py list
```

### `todo` / `doing` / `done`

Set schedule status directly by command name.

| Parameter | Required | Type   | Default | Description                                  |
| --------- | -------- | ------ | ------- | -------------------------------------------- |
| `target`  | No       | string | -       | Positional task ID, or `all` for `done all`. |
| `--id`    | No       | string | -       | Named task ID (same as positional target).   |
| `--sid`   | No       | int    | auto    | Schedule ID. Omit for one-time tasks.        |

Rules:
- `todo/doing/done <task_id>` and `todo/doing/done --id <task_id>` are both supported.
- If `--sid` is omitted for a one-time task, it auto-uses `sid=1`.
- If `--sid` is omitted for a recurring task, command returns an error.
- `done all` marks all unfinished schedules with `end_date <= yesterday` as `done`.

Examples:

```bash
python main.py todo 123ABC
python main.py todo --id 123ABC --sid 2
python main.py doing --id 123ABC --sid 2
python main.py done --id 123ABC
python main.py done --id 123ABC --sid 2
python main.py done all
```

### `delay`

Delay overdue unfinished one-time tasks to today.

| Parameter | Required | Type   | Default | Description                             |
| --------- | -------- | ------ | ------- | --------------------------------------- |
| `target`  | No       | string | -       | Positional one-time task ID.            |
| `--id`    | No       | string | -       | Named one-time task ID.                 |

Rule:
- `delay` with no task ID updates all one-time tasks whose `end_date <= yesterday` and whose schedule status is not `done`.
- `delay <task_id>` and `delay --id <task_id>` delay one overdue one-time task to today.
- Recurring tasks are not supported.
- Completed one-time tasks are not supported.
- Only the end date is changed; task status is preserved.

Example:

```bash
python main.py delay
python main.py delay 123ABC
python main.py delay --id 123ABC
```

### `schlist`

List schedules.

| Parameter | Required | Type   | Default   | Description                  |
| --------- | -------- | ------ | --------- | ---------------------------- |
| `--id`    | No       | string | all tasks | Filter schedules by task ID. |

Examples:

```bash
python main.py schlist
python main.py schlist --id 123ABC
```

### `view`

Show calendar lines by date and past unfinished schedules.

| Parameter | Required | Type | Default       | Description                          |
| --------- | -------- | ---- | ------------- | ------------------------------------ |
| `today`   | No       | token | -            | Shortcut: view only today.           |
| `--fd`    | No       | date | today         | View start date.                     |
| `--td`    | No       | date | `fd + 6 days` | View end date (`>= fd`).             |
| `--m`     | No       | enum | `a`           | Mode: `t/todo`, `a/active`, `l/all`. |

Rules:
- Default `view` shows one week: `from_date=today`, `to_date=today+6 days`.
- `view today` shows only today.
- `view today` cannot be combined with `--fd` or `--td`.

Examples:

```bash
python main.py view
python main.py view today
python main.py view --fd 2026-04-01 --td 2026-04-10 --m l
python main.py view --m active
```

### `maint`

Force daily maintenance immediately.

Parameters: none.

```bash
python main.py maint
```
