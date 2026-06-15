# Tool Schema Design

## 为什么工具需要 schema

ProjectPilot Agent 未来会读取文件、读取 git log、生成报告、写 run log，并可能提出 README 或 commit 建议。每个工具都需要明确输入、输出、只读属性和错误状态，原因是：

- 限定工具能力边界。
- 让调用记录可复盘。
- 让测试可以验证工具契约。
- 区分只读工具和可能写入的工具。
- 为 human confirmation 留出结构化依据。

## Day 1 Schema

`projectpilot/schemas/tool_schema.py` 当前包含：

- `ToolSpec`
- `ToolInputSchema`
- `ToolOutputSchema`
- `ToolCallRecord`
- `ToolCallStatus`

工具状态包括：

- `success`
- `invalid_args`
- `timeout`
- `empty_result`
- `permission_denied`
- `internal_error`

## 为什么需要 tool_call log

ProjectPilot Agent 面向交付管理，必须能说明“读了什么、调用了什么、结果如何、是否失败”。tool call log 是后续 run log、审计、debug 和用户复盘的基础。

## 写操作为什么要 human confirmation

ProjectPilot Agent 未来可能提出 README 修改、commit 建议或任务文件更新，但这些都影响项目交付记录。写操作必须先进入人工确认，避免自动化越界。

## Day 1 边界

Day 1 只定义 schema，不实现真实工具、不连接外部系统、不做自动写入。
