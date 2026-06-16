# Workflow Design

## 设计目标

ProjectPilot Agent 采用 Workflow-first 设计，用固定流程约束项目分析行为，避免把它做成不可控的自动化 Agent。

当前目标是让每次分析都能回答：

- 读取了哪些项目证据？
- 当前项目有哪些已实现能力？
- 交付证据是否完整？
- 还存在哪些风险和缺口？
- 下一步任务应该如何排序？
- 哪些建议需要人工确认？
- 每个 workflow step 和 tool call 是否有可追踪记录？

## Workflow State

当前基础状态包括：

- `initialized`
- `reading_context`
- `analyzing`
- `generating_tasks`
- `generating_suggestions`
- `llm_reviewing`
- `pending_confirmation`
- `completed`
- `failed`

## Day 2 流程

Day 2 实现最小只读上下文读取：

```text
initialized -> reading_context -> completed
```

该阶段只读取目标项目的 README、docs、tests、eval 和 git log，生成：

- `outputs/context_summary.md`
- `run_logs/latest_run.json`

## Day 3 流程

Day 3 在只读上下文基础上加入规则化分析：

```text
initialized -> reading_context -> analyzing -> generating_tasks -> completed
```

各阶段含义：

- `initialized`：加载配置。
- `reading_context`：读取有限项目上下文和 git log。
- `analyzing`：基于规则检查 README、docs、tests、eval、bad_cases、problems_and_solutions、recent commits 等证据。
- `generating_tasks`：生成 `project_status_report.md` 和 `next_tasks.md`。
- `completed`：写入 Run Log 并结束。

## Day 4 流程

Day 4 在任务生成之后补充建议输出和人工确认状态：

```text
initialized -> reading_context -> analyzing -> generating_tasks -> generating_suggestions -> pending_confirmation -> completed
```

新增阶段含义：

- `generating_suggestions`：生成 README 建议、风险提醒和 commit 建议草案。
- `pending_confirmation`：记录人工确认状态为 `pending`。ProjectPilot 只输出建议，不自动修改目标项目，不自动提交。

Day 4 新增输出：

- `outputs/readme_suggestions.md`
- `outputs/risk_report.md`
- `outputs/commit_suggestions.md`

## Day 5 流程

Day 5 增强 workflow run 记录：

```text
initialized -> reading_context -> reading_git_log -> generating_context_summary -> analyzing_project_status -> generating_suggestions -> pending_confirmation -> completed
```

实际 CLI 会记录更细的步骤，包括：

- `reading_context`
- `reading_git_log`
- `generating_context_summary`
- `analyzing_project_status`
- `generating_project_status_report`
- `generating_next_tasks`
- `generating_readme_suggestions`
- `generating_risk_report`
- `generating_commit_suggestions`
- `pending_human_confirmation`
- `generating_tool_call_log`

这些步骤会写入 `run_logs/latest_run.json` 的 `steps` 字段；对应工具调用会写入 `tool_calls` 字段，并生成 `outputs/tool_call_log.md`。

## Day 7 流程

Day 7 在建议生成之后加入可选 LLM Review Advisor：

```text
reading_context
-> analyzing_project_status
-> generating_suggestions
-> llm_reviewing
-> pending_confirmation
-> completed
```

新增阶段含义：

- `llm_reviewing`：基于已有报告摘要生成 `outputs/llm_review.md`。
- 默认 `LLM_PROVIDER=mock`，不访问网络。
- `LLM_PROVIDER=deepseek` 且存在 `DEEPSEEK_API_KEY` 时才尝试真实 LLM 调用。
- 缺少 API key 时记录 `permission_denied`，友好跳过，不影响整体分析流程。
- LLM review 结果仍需人工确认，不自动修改目标项目，不自动提交代码。

## Human Confirmation

ProjectPilot Agent 默认只读。未来如果涉及以下动作，必须进入 Human Confirmation：

- 修改目标项目文件。
- 生成或执行 commit。
- 执行部署。
- 调用外部系统产生副作用。

Day 4 只记录 `pending` 状态，不做交互式审批界面。

## Score 表述边界

Delivery Readiness Score 当前是 v0.1 规则化证据完整度检查。

它用于辅助判断项目展示材料是否齐全，不代表生产级可用，不代表企业级 readiness，也不是 LLM 对项目质量的语义评价。

## 当前边界

Day 7 默认使用 mock LLM provider；真实 LLM review 需要显式配置。当前不接 LangGraph，不接 MCP，不调用 RAGHub `/retrieve`，不修改目标项目，不自动提交，不部署。当前日志用于本地流程追踪，不代表企业级审计系统。
