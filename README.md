# ProjectPilot Agent

ProjectPilot Agent 是一个面向 AI 工程项目的交付分析与工作流协作智能体原型。

当前处于 v0.3 原型阶段，已支持读取目标项目的 README、docs、tests、eval 和 git log，并基于规则生成项目状态报告、下一步任务建议、README 建议、风险提醒、commit 建议草案、可选 LLM 语义审阅、Planner-driven Read-only Agent Workflow、Tool Call Log 和 Run Log。

## 项目定位

ProjectPilot Agent 面向“如何判断一个 AI 工程项目当前做到什么程度、还缺什么、下一步应该做什么”这个问题。

它的目标不是替代代码编辑器或自动写代码，而是围绕项目交付证据进行分析：

- 项目状态分析
- 交付缺口
- 下一步任务
- 风险提醒
- README / commit 建议草案
- 面试表达素材
- Run Log
- 交付证据完整度评分（Evidence Coverage Score）

RAGHub 是第一个真实分析对象，但 ProjectPilot Agent 不依赖 RAGHub API。

## 不是什么

ProjectPilot Agent 不是：

- Claude Code / Cursor / Codex 替代品
- 自动写代码工具
- 自动提交工具
- 自动部署工具
- 企业级项目治理平台

## 当前能力

当前 `analyze` 命令会执行只读分析流程：

1. 加载 `projectpilot.yaml` 配置。
2. 读取目标项目的有限上下文。
3. 读取最近 git log。
4. 生成 `outputs/context_summary.md`。
5. 运行 rule-based analyzer。
6. 生成 `outputs/project_status_report.md`。
7. 生成 `outputs/next_tasks.md`。
8. 生成 `outputs/readme_suggestions.md`。
9. 生成 `outputs/risk_report.md`。
10. 生成 `outputs/commit_suggestions.md`。
11. 生成 `outputs/llm_review.md`。
12. 生成 `outputs/tool_call_log.md`。
13. 写入 `run_logs/latest_run.json`。

运行方式：

```powershell
python -m projectpilot.cli --help
python -m projectpilot.cli analyze --config examples/projectpilot.yaml
python -m projectpilot.cli agent-run --config examples/raghub_eval100.yaml --goal "analyze RAGHub delivery readiness"
```

## Planner-driven Read-only Agent Workflow

ProjectPilot 支持一个 planner-driven read-only Agent Workflow。用户提供 goal 后，默认 mock Planner 会生成 planned steps；Tool Router 只允许白名单只读工具执行，危险工具和未知工具会被 skipped；整个过程会记录 planned_steps、executed_steps、skipped_steps、Tool Call Log、Run Log，并保持 human_confirmation_status=pending。

示例：

```powershell
python -m projectpilot.cli agent-run --config examples/raghub_eval100.yaml --goal "analyze RAGHub delivery readiness"
```

默认输出：

- `outputs/raghub_agent/agent_plan.md`
- `outputs/raghub_agent/agent_run_summary.md`
- `outputs/raghub_agent/skipped_steps.md`
- `outputs/raghub_agent/tool_call_log.md`
- `run_logs/raghub_agent_latest_run.json`

边界：

- 不自动修改目标项目。
- 不自动提交。
- 不自动部署。
- 不执行任意 shell 命令。
- DeepSeek planner 是可选方向，不是默认依赖。
- 当前仍是 read-only Agent prototype，不是企业级治理平台。

## Demo Case：分析 RAGHub

RAGHub 是 ProjectPilot Agent 当前第一个真实分析对象。可以通过下面命令运行只读分析：

```powershell
python -m projectpilot.cli analyze --config examples/projectpilot.yaml
```

本地运行会生成：

- `outputs/context_summary.md`
- `outputs/project_status_report.md`
- `outputs/next_tasks.md`
- `outputs/readme_suggestions.md`
- `outputs/risk_report.md`
- `outputs/commit_suggestions.md`
- `outputs/llm_review.md`
- `outputs/tool_call_log.md`
- `run_logs/latest_run.json`

Demo 文档入口：`docs/demo/raghub_analysis_case.md`。

当前 Demo 只做只读分析，不调用 RAGHub API，不自动修改 RAGHub，不自动提交代码。

## Demo Case：不完整项目验证

Day 8 新增一个只有 README 的最小示例项目：

- 示例项目：`examples/incomplete_project`
- 示例配置：`examples/incomplete_project.yaml`
- Demo 文档：`docs/demo/incomplete_project_analysis_case.md`

这个 Demo 用来验证 ProjectPilot 不只会分析 RAGHub。它应识别缺少 docs、tests、eval、bad cases、problems_and_solutions 和 git log 等交付证据，并给出较低的交付证据完整度评分。

## 只读 Context Reader

Context Reader 默认读取：

- `README.md`
- `docs/**/*.md`
- `tests/**/*.py`
- `eval/**/*.jsonl`
- `eval/**/*.json`
- `eval/**/*.md`
- 最近若干条 git commit

读取边界：

- 默认最多读取 30 个文件。
- 单文件最多读取 20 KB。
- 根目录 `README.md` 优先读取。
- 根目录 `README.md` 超过限制时截断读取，而不是直接跳过。
- 只允许 `.md`、`.py`、`.json`、`.jsonl`、`.yaml`、`.yml`。
- 跳过 `.git`、`.venv`、`__pycache__`、`.pytest_cache`、`node_modules`、`data/raw`、`data/processed`、`models`、`cache`。

## Rule-Based Analyzer

Day 3 引入规则化项目状态分析器。Day 7 起新增可选 LLM Review Advisor，但 LLM 只审阅已有报告，不替代 rule-based analyzer。

当前会检查：

- README 是否存在
- docs 是否存在
- tests 是否存在
- eval 是否存在
- bad_cases 是否存在
- problems_and_solutions 是否存在
- recent git commits 是否存在
- README/docs 中是否存在边界或 Roadmap 信号

## Day 4 建议输出

Day 4 在规则化项目状态分析基础上新增建议输出：

- README 建议：只给出可执行修改建议，不自动修改 README。
- 风险提醒：按 P0/P1/P2 和面试风险分类。
- Commit 建议草案：只生成 commit message 草案，不执行 `git add` 或 `git commit`。
- Human Confirmation：所有建议默认状态为 `pending`，需要人工确认后才能执行。

## Day 5 日志能力

Day 5 增强 Tool Call Log 和 Workflow Run Log：

- 记录每个分析步骤的 tool name、status、duration、input summary、output summary 和 message。
- 生成 `outputs/tool_call_log.md`，用于本地 workflow 追踪。
- 在 `run_logs/latest_run.json` 中写入 `steps` 和 `tool_calls`。
- 当前日志是 v0.1 本地 workflow run log，不代表企业级审计系统。

## 可选 LLM Review Advisor

Day 7 新增可选 LLM Review Advisor，用于基于已有分析报告做语义审阅和建议增强。

默认配置：

```env
LLM_PROVIDER=mock
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

说明：

- 默认使用 `mock` provider，不访问网络。
- 配置 `LLM_PROVIDER=deepseek` 且存在 `DEEPSEEK_API_KEY` 时，才会尝试调用真实 DeepSeek。
- LLM 只审阅已生成的 `context_summary.md`、`project_status_report.md`、`next_tasks.md`、`risk_report.md`、`commit_suggestions.md` 等报告摘要。
- LLM 不直接读取整个目标仓库，不替代 rule-based analyzer。
- LLM 不自动修改目标项目，不自动提交代码。
- `outputs/llm_review.md` 仅供人工审查，Human Confirmation 仍为 `pending`。
- Day 8 评分校准后，已再次通过 DeepSeek smoke test 验证 LLM Review Advisor 可用。

## 交付证据完整度评分（Evidence Coverage Score）

交付证据完整度评分当前是 v0.2 规则化证据类型覆盖检查。

它表示目标项目在当前展示范围内，README、docs、tests、eval、bad case、问题复盘和 git 记录等证据类型是否覆盖。

它不代表：

- 项目质量满分
- 生产级可用
- 企业级 readiness
- 安全合规评估
- LLM 语义判断的最终结论
- 招聘结果保证

## 当前边界

- 默认使用 mock LLM provider；只有显式配置 DeepSeek provider 和 API key 时才做可选 LLM review。
- `agent-run` 默认使用 mock planner；planner 输出必须经过静态 Tool Router 白名单校验。
- 不接 LangGraph。
- 不接 MCP。
- 不调用 RAGHub `/retrieve`。
- 不自动修改目标项目。
- 不自动提交代码。
- 不自动执行 commit。
- 不自动部署。
- 不全量读取大仓库。
- 不做复杂前端。
- 不做企业级权限或治理系统。

## Roadmap

- Day 1：工程骨架、README、docs、CLI、Tool Schema 草案、基础测试。
- Day 2：只读 Context Reader、git log reader、context summary。
- Day 3：rule-based project status report、交付证据完整度评分、next tasks。
- Day 4：README 建议、风险提醒增强、commit 建议草案、Human Feedback / pending confirmation。
- Day 5：Tool Call Log、Workflow Run Log、workflow step 状态追踪。
- Day 6：RAGHub Demo Case、项目讲解稿、面试高频问答。
- Day 7：可选 LLM Review Advisor、DeepSeek provider 接入边界、`llm_review.md` 输出。
- Day 8：交付证据完整度评分校准、incomplete demo project、GitHub 上传前可信度修复。
- v0.3 Phase 4.5：planner-driven read-only Agent Workflow、静态白名单 Tool Router、planned/executed/skipped 记录。
