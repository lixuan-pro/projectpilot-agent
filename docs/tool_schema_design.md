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

## Day 5 Tool Call Record 字段

Day 5 增强 Tool Call Log，用于记录每个分析步骤的最小可追踪信息：

- `tool_name`
- `status`
- `started_at`
- `finished_at`
- `duration_ms`
- `input_summary`
- `output_summary`
- `error_type`
- `message`

状态继续使用：

- `success`
- `invalid_args`
- `timeout`
- `empty_result`
- `permission_denied`
- `internal_error`

当前 Tool Call Log 是 v0.1 本地 workflow run log，不代表企业级审计系统。

## Day 7 LLM Tool Call 记录

Day 7 新增 `llm_review_advisor` tool call，用于记录可选 LLM 语义审阅。

该 tool call 的输入摘要只记录 provider 和已有报告来源，不记录 API key，不直接记录整个目标仓库内容。输出摘要记录：

- `llm_provider`
- `llm_review`

可能状态包括：

- `success`：mock provider 或真实 DeepSeek 调用成功。
- `empty_result`：LLM provider 返回空结果。
- `permission_denied`：选择 DeepSeek provider 但缺少 `DEEPSEEK_API_KEY` 等必要配置。
- `internal_error`：provider 调用失败或返回格式不可解析。

LLM Review Advisor 只基于已有分析结果生成 `outputs/llm_review.md`，不替代 rule-based analyzer，不自动修改代码，不自动提交。

## 写操作为什么要 human confirmation

ProjectPilot Agent 未来可能提出 README 修改、commit 建议或任务文件更新，但这些都影响项目交付记录。写操作必须先进入人工确认，避免自动化越界。

## Day 1 边界

Day 1 只定义 schema，不实现真实工具、不连接外部系统、不做自动写入。
