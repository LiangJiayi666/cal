---
name: cal
description: 操作 cal CLI 日历/任务工具，支持创建、查询、更新、删除任务和日程。
---

# cal CLI Skill

## 执行流程（供 agent 遵循）

当人用自然语言提出需求时：

1. **揣测意图**：判断是创建任务、更新任务、查看状态、删除还是修改 schedule 状态。
2. **生成命令**：根据意图和命令参考，拼接完整的 `python main.py ...` 命令。
3. **解释并请求确认**：向人解释这条命令会做什么，给出确认选项（用 Claude Code 的 AskUserQuestion 工具渲染选项）。
4. **等待确认**：只有人明确选择确认后，才用 Bash 工具执行该命令。
5. **返回结果**：命令执行后，将输出结果告知人。

---

## 工具信息

- 入口：`python main.py <command> [args]`
- 日期格式：`YYYY-MM-DD`
- 所有命令（除 `maint`）首次运行时会自动触发每日维护。
- IDs 为自动生成的 6 位字符串（字符集 `1-9A-F`）。
- 任务更新后，该任务的所有 schedule 会重新生成，原有 `(task_id, schedule_id)` 的 status 会被保留。

---

## 任务类型

### 一次性任务（one-time）

创建后生成单个 schedule，状态为 `todo`。

### recurring 任务（recurring）

创建后按规则生成多个 schedule，覆盖一段时间。

---

## 命令参考

### `once` — 创建一次性任务

```bash
python main.py once --nm <name> --sd <start_date> --ed <end_date> [--ds <description>] [--tt]
python main.py once today --nm <name> [--ds <description>] [--tt]
```

| 参数    | 必填 | 类型   | 默认 | 说明                    |
|---------|------|--------|------|------------------------|
| `today` | 否   | token  | -    | 快捷方式：`sd=ed=today`。不可与 `--sd`/`--ed` 共用。 |
| `--nm`  | 是   | string | -    | 任务名称。              |
| `--ds`  | 否   | string | `""` | 任务描述。              |
| `--sd`  | 条件 | date   | -    | 开始日期，`today` 时不填。 |
| `--ed`  | 条件 | date   | -    | 结束日期，`today` 时不填。 |
| `--tt`  | 否   | flag   | `False` | 标记为测试任务。    |

规则：`sd > ed` 时，start 会被调整到 end 并打印提示。

### `onceupd` — 更新一次性任务

```bash
python main.py onceupd --id <task_id> [--nm <name>] [--ds <description>] [--sd <start_date>] [--ed <end_date>]
python main.py onceupd today --id <task_id>
```

| 参数    | 必填 | 类型   | 默认          | 说明                    |
|---------|------|--------|---------------|------------------------|
| `today` | 否   | token  | -            | 快捷方式：`sd=ed=today`。不可与 `--sd`/`--ed` 共用。 |
| `--id`  | 是   | string | -            | 任务 ID。              |
| `--nm`  | 否   | string | 保持不变      | 新名称。               |
| `--ds`  | 否   | string | 保持不变      | 新描述。               |
| `--sd`  | 否   | date   | 保持不变      | 新开始日期。           |
| `--ed`  | 否   | date   | 保持不变      | 新结束日期。           |

规则：更新后若 `sd > ed`，start 会被调整到 end 并打印提示。

### `rec` — 创建 recurring 任务

```bash
python main.py rec --nm <name> --fs <first_start> --fe <first_end> --rp <repeat_unit> [--iv <interval>] [--ds <description>] [--ts <task_start>] [--te <task_end>] [--tt]
python main.py rec today --nm <name> --rp <repeat_unit> [--iv <interval>] [--ds <description>]
```

| 参数    | 必填 | 类型   | 默认          | 说明                                        |
|---------|------|--------|---------------|-------------------------------------------|
| `today` | 否   | token  | -            | 快捷方式：`fs=fe=today`。不可与 `--fs`/`--fe` 共用。 |
| `--nm`  | 是   | string | -            | 任务名称。                                 |
| `--ds`  | 否   | string | `""`         | 任务描述。                                 |
| `--fs`  | 条件 | date   | -            | 首次发生开始日期，`today` 时不填。         |
| `--fe`  | 条件 | date   | -            | 首次发生结束日期，`today` 时不填。         |
| `--ts`  | 否   | date   | `fs`         | 任务开始边界。                             |
| `--te`  | 否   | date   | `2100-01-01` | 任务结束边界。                             |
| `--rp`  | 是   | enum   | -            | 重复单位：`d/w/m/y` 或 `day/week/month/year`。 |
| `--iv`  | 否   | int    | `1`          | 重复间隔（`>=1`）。                        |
| `--tt`  | 否   | flag   | `False`      | 标记为测试任务。                           |

规范化规则：
- `fs > fe` → fs 调整到 fe
- `te < fe` → te 调整到 fe
- `ts > fs` → ts 调整到 fs

### `recupd` — 更新 recurring 任务

```bash
python main.py recoupd --id <task_id> [--nm <name>] [--ds <description>] [--fs <first_start>] [--fe <first_end>] [--ts <task_start>] [--te <task_end>] [--rp <repeat_unit>] [--iv <interval>]
python main.py recoupd today --id <task_id>
```

| 参数    | 必填 | 类型   | 默认          | 说明                        |
|---------|------|--------|---------------|---------------------------|
| `today` | 否   | token  | -            | 快捷方式：`fs=fe=today`。不可与 `--fs`/`--fe` 共用。 |
| `--id`  | 是   | string | -            | 任务 ID。                  |
| `--nm`  | 否   | string | 保持不变      | 新名称。                   |
| `--ds`  | 否   | string | 保持不变      | 新描述。                   |
| `--fs`  | 否   | date   | 保持不变      | 新首次开始日期。           |
| `--fe`  | 否   | date   | 保持不变      | 新首次结束日期。           |
| `--ts`  | 否   | date   | 保持不变      | 新任务开始边界。           |
| `--te`  | 否   | date   | 保持不变      | 新任务结束边界。           |
| `--rp`  | 否   | enum   | 保持不变      | `d/w/m/y` 或完整单词。    |
| `--iv`  | 否   | int    | 保持不变      | 新间隔（`>=1`）。         |

### `del` — 删除测试任务

```bash
python main.py del all              # 删除所有测试任务
python main.py del <task_id>        # 删除指定测试任务
python main.py del --id <task_id>
```

规则：
- `del all` 删除所有测试任务。
- `del <task_id>` 或 `del --id <task_id>` 删除单个测试任务。
- 非测试任务会报错。

### `list` — 列出所有任务

```bash
python main.py list
```

无参数。

### `todo` / `doing` / `done` — 修改 schedule 状态

```bash
python main.py todo <task_id> [--sid <schedule_id>]
python main.py doing <task_id> [--sid <schedule_id>]
python main.py done <task_id> [--sid <schedule_id>]
python main.py done all
```

| 参数     | 必填 | 类型   | 默认   | 说明                                    |
|----------|------|--------|--------|---------------------------------------|
| `target` | 否   | string | -      | 位置参数：task ID 或 `done all`。       |
| `--id`   | 否   | string | -      | 命名 task ID（与位置参数效果相同）。    |
| `--sid`  | 否   | int    | 自动   | Schedule ID。一次任务自动用 `sid=1`。 recurring 任务省略会报错。 |

规则：
- `done all` 将所有 `end_date <= 昨天` 且状态不是 `done` 的 schedule 标记为 `done`。

### `delay` — 延迟过期任务到今天

```bash
python main.py delay
```

规则：
- 将所有 `end_date <= 昨天` 且 schedule 状态不是 `done` 的一次性任务，延期到今天。
- 仅改变结束日期；任务状态保持不变。

### `schlist` — 列出 schedule

```bash
python main.py schlist
python main.py schlist --id <task_id>
```

| 参数  | 必填 | 类型   | 默认     | 说明              |
|-------|------|--------|----------|-----------------|
| `--id` | 否   | string | 所有任务 | 按 task ID 过滤。 |

### `view` — 查看日历

```bash
python main.py view
python main.py view today
python main.py view [--fd <from_date>] [--td <to_date>] [--m <mode>]
```

| 参数    | 必填 | 类型 | 默认         | 说明                                      |
|---------|------|------|--------------|-----------------------------------------|
| `today` | 否   | token | -           | 快捷方式：只显示今天。不可与 `--fd`/`--td` 共用。 |
| `--fd`  | 否   | date | 今天         | 起始日期。                                |
| `--td`  | 否   | date | `fd + 14 天` | 结束日期（`>= fd`）。                     |
| `--m`   | 否   | enum | `a`          | 模式：`t/todo`、`a/active`（默认）、`l/all`。 |

规则：默认 view 显示 14 天（今天起 14 天）。`view today` 只显示今天。

### `maint` — 强制运行每日维护

```bash
python main.py maint
```

无参数。强制立即执行每日维护（即使今天已运行过）。

---

## 参数缩写对照

| 缩写      | 含义             |
|-----------|-----------------|
| `--id`  | task_id          |
| `--sid` | schedule_id      |
| `--nm`  | name             |
| `--ds`  | description      |
| `--sd`  | start_date       |
| `--ed`  | end_date         |
| `--fs`  | first_start_date |
| `--fe`  | first_end_date   |
| `--ts`  | task_start_date  |
| `--te`  | task_end_date    |
| `--rp`  | repeat_unit      |
| `--iv`  | interval         |
| `--tt`  | 标记为测试任务   |
| `--fd`  | from_date        |
| `--td`  | to_date          |
| `--m`   | view mode        |

---
