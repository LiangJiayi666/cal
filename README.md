# cal — 个人日程 CLI 工具

## 简介

双层结构：

- **任务池（task）**：一次性任务 + 周期任务，定义"做什么"
- **日程池（schedule）**：从任务生成的具体日程，带状态（`todo` / `doing` / `done`）

每天首次运行命令时会自动触发日程维护。

## 安装

```bash
git clone https://github.com/LiangJiayi666/cal.git
cd cal
```

> 所有操作都在项目文件夹 `cal` 内进行。

## 快速开始

```bash
python main.py --help
```

日期格式：`YYYY-MM-DD`，所有日期参数均用此格式。

## 使用方式

### 日常操作：用 cal skill（推荐）

在 Claude Code 中直接说自然语言，调用 `/cal` skill 处理日常任务：创建、查询、改状态等。skill 会自动生成确认后再执行。

### Web 前端（可视化）

如果想用浏览器操作（创建/编辑任务、筛选日程、批量改状态等），可以启动内置前端：

```bash
python -m cal_app.web
```

启动后打开 `http://127.0.0.1:8765` 即可（默认端口是 `8765`，一般不需要自定义）。

### 命令行操作

详细命令参数见 `.claude/skills/cal/SKILL.md`，以下是常用命令速查。

### 创建类

```bash
# 一次性任务
python main.py once --nm <名称> --sd <开始> --ed <结束> [--ds <描述>] [--tt]
python main.py once today --nm <名称>                      # 今天

# 周期任务
python main.py rec --nm <名称> --fs <首次开始> --fe <首次结束> --rp <单位> [--iv <间隔>]
python main.py rec today --nm <名称> --rp d                  # 今天开始的每日任务
```

### 查询类

```bash
python main.py list              # 列出所有任务
python main.py schlist           # 列出所有日程
python main.py schlist --id <任务ID>  # 按任务过滤日程
python main.py view              # 查看日历（默认14天）
python main.py view today        # 只看今天
python main.py view --fd <起始> --td <结束> --m l  # 全量模式
```

### 修改类

```bash
python main.py todo <任务ID> [--sid <日程ID>]
python main.py doing <任务ID> --sid <日程ID>
python main.py done <任务ID> [--sid <日程ID>]
python main.py done all          # 将昨天及之前未完成的日程全部标记为 done
python main.py delay             # 将所有过期的一次性任务延期到今天
```

### 删除类

```bash
python main.py del all           # 删除所有测试任务
python main.py del <任务ID>       # 删除指定测试任务
```

### 维护类

```bash
python main.py maint            # 强制运行每日维护
```

## 项目结构

```
cal_app/
  domain/          实体、常量、校验、日期规则
  application/     业务逻辑、排程生成引擎
  infrastructure/  JSON 持久化
  cli.py           命令行入口
data/
  state.json       运行状态存储
main.py            CLI 入口
```

## 运行时行为

- 除 `maint` 外，所有命令首次运行时会触发每日维护
- `maint` 强制立即执行维护（即使今天已运行）
- ID 为 6 位字符串，字符集 `1-9A-F`
- 任务更新后该任务所有 schedule 重新生成，原有 `(task_id, schedule_id)` 的 status 会被保留
