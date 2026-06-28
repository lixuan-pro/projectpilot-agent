# ProjectPilot v0.3 简历取证包

## 1. Git 状态

- ProjectPilot 路径：`E:\Code\AI\projectpilot-agent`
- 当前分支：`feature/raghub-eval100-workflow`
- latest commit：`feat: add planner driven read only agent workflow`（最终 hash 以 `git log -1 --oneline` 为准）。
- git status：本地分支 ahead 1；本轮只提交 ProjectPilot 自身补强，不 push。
- 最近 5 条 commit：
  - `feat: add planner driven read only agent workflow`
  - `291cced feat: add deepseek raghub delivery advisors`
  - `353488a feat: add raghub eval100 delivery workflow`
  - `36b54ff docs: align projectpilot current scope wording`
  - `ea358d0 docs: calibrate projectpilot evidence scoring and demos`
- RAGHub 路径：`E:\Code\Py\raghub`
- RAGHub git status：`main...origin/main`，clean；本轮未修改 RAGHub。

本轮更新涉及的主要文件：

- `projectpilot/cli.py`
- `projectpilot/agent/planner.py`
- `projectpilot/agent/tool_router.py`
- `projectpilot/agent/agent_run.py`
- `examples/raghub_eval100.yaml`
- `docs/demo/raghub_eval100_workflow_case.md`
- `projectpilot/analyzers/consistency_checker.py`
- `projectpilot/analyzers/llm_interview_asset_writer.py`
- `projectpilot/analyzers/llm_resume_asset_writer.py`
- `tests/test_consistency_checker.py`
- `tests/test_agent_planner.py`
- `tests/test_tool_router.py`
- `tests/test_agent_run.py`
- `tests/test_llm_interview_asset_writer.py`
- `tests/test_llm_resume_asset_writer.py`
- `tests/test_raghub_phase4_workflow.py`

## 2. 本轮更新摘要

- 是否新增 RAGHub 分析案例：是。现有 `docs/demo/raghub_eval100_workflow_case.md` 记录 RAGHub Eval-100 workflow，并新增 Phase 4 的 Interview / Resume Assets and Consistency Check 说明。
- 是否真实运行 ProjectPilot 分析 RAGHub：已有运行证据。当前 `run_logs/latest_run.json` 显示 target project 为 `RAGHub Eval-100 Case`，读取 `E:\Code\Py\raghub`，`files_read=40`，`git_commits_read=15`。
- 是否新增 human feedback / human confirmation 记录：是。`tool_call_log.md` 和 `run_logs/latest_run.json` 记录 `human_confirmation_status=pending`。未发现单独的 `human_feedback.md` 文件。
- 是否新增或增强 overclaiming guard：是。新增 `ConsistencyChecker`，检查 `unsupported_metric`、`overclaimed_production_ready`、`overclaimed_hybrid_gain`、`overclaimed_no_answer_security`、`overclaimed_agent_autonomy`、`missing_boundary_statement`。
- 是否新增 planner-driven read-only Agent Workflow：是。新增 mock planner、静态白名单 Tool Router、agent-run workflow，记录 planned/executed/skipped steps。
- 是否新增危险工具 skipped demo：是。`demo dangerous tool guard` goal 会规划 `git_push`、`modify_target_project`、`deploy`，Tool Router 将其记录为 skipped。
- 是否增强 LLM Review Advisor：是。当前 workflow 已包含 RAGHub 专用 LLM Risk Reviewer、Task Planner，以及 Phase 4 的 Interview Asset Writer、Resume Asset Writer。
- 默认 LLM provider：`mock`。
- DeepSeek 是否可选：是。只有显式设置 `LLM_PROVIDER=deepseek` 且存在 `DEEPSEEK_API_KEY` 时才调用真实 provider。
- LLM 是否只审阅已有报告摘要：是。LLM Review Advisor 基于已生成的报告、tool_call_log、结构化指标和风险登记生成语义审阅/素材，不直接接管仓库。
- 是否仍然不自动修改代码、不自动提交、不自动部署：是。源码、文档和 tool log 都明确 ProjectPilot 只生成建议与报告，所有动作保持人工确认。

边界说明：

- 本轮需要重新运行 `python -m projectpilot.cli analyze` 和 `agent-run` 刷新证据；最终结果以本轮报告和当前 run logs 为准。
- `agent-run` 当前 `planner_provider=mock`；即使环境变量设置 `LLM_PROVIDER=deepseek`，也不能写成 DeepSeek planner 驱动。

## 3. RAGHub 联动验证

- RAGHub 路径：`E:\Code\Py\raghub`
- 使用的配置文件：`examples/raghub_eval100.yaml`
- 运行命令：`python -m projectpilot.cli analyze --config examples/raghub_eval100.yaml`
- 输出目录：`outputs/raghub_eval100`
- 读取文件数：40
- 读取 git commits 数：15
- Evidence Coverage Score：60/100
- Human Confirmation 状态：pending
- Run Log 路径：`run_logs/latest_run.json`

生成的报告文件列表：

- `outputs/raghub_eval100/context_summary.md`
- `outputs/raghub_eval100/project_status_report.md`
- `outputs/raghub_eval100/next_tasks.md`
- `outputs/raghub_eval100/readme_suggestions.md`
- `outputs/raghub_eval100/risk_report.md`
- `outputs/raghub_eval100/commit_suggestions.md`
- `outputs/raghub_eval100/llm_review.md`
- `outputs/raghub_eval100/tool_call_log.md`
- `outputs/raghub_eval100/eval_metrics_summary.md`
- `outputs/raghub_eval100/raghub_risk_review.md`
- `outputs/raghub_eval100/risk_register.json`
- `outputs/raghub_eval100/issue_to_task_map.md`
- `outputs/raghub_eval100/llm_risk_review.md`
- `outputs/raghub_eval100/llm_task_plan.md`
- `outputs/raghub_eval100/interview_case_cards.md`
- `outputs/raghub_eval100/resume_assets.md`
- `outputs/raghub_eval100/consistency_check.md`
- `outputs/raghub_eval100/consistency_check.json`

Tool Call Log 中的主要 step：

- `context_reader`
- `git_reader`
- `context_summary_writer`
- `project_status_analyzer`
- `project_status_report_writer`
- `next_tasks_writer`
- `readme_advisor`
- `risk_advisor`
- `commit_advisor`
- `raghub_eval_metrics_reader`
- `raghub_delivery_analyzer`
- `raghub_case_report_writer`
- `llm_raghub_risk_reviewer`
- `llm_raghub_task_planner`
- `llm_interview_asset_writer`
- `llm_resume_asset_writer`
- `consistency_checker`
- `llm_review_advisor`

ProjectPilot 对 RAGHub 识别出的主要风险和 next tasks：

- `no_answer_risk=resolved`：Eval-100 中 out-of-corpus 样本 `12/12` 拒答，但只能作为项目级证据，不能写成彻底解决幻觉。
- `source_competition=open`：`exact_source_hit_rate=0.5909`，`source_group_hit_rate=0.9091`，说明相关证据组命中较好，但精确 source 竞争仍存在。
- `hybrid_default_decision=not_recommended`：`vector_average_score=8.83`，`hybrid_average_score=8.90`，`vector/hybrid/tie=12/12/76`，hybrid 不建议作为默认。
- `eval_100_scope=project_level_benchmark`：Eval-100 是项目级 benchmark，不是生产级 benchmark。
- `production_readiness=not_production`：不能把 RAGHub 或 ProjectPilot 包装成生产级平台。
- 后续任务包括 source_type filter、heading-aware chunk、metadata filter、answer-level source selection，以及 no-answer guard 的后续 LLM judge 补充。

## 4. 关键报告摘要

- `context_summary.md`：读取 RAGHub Eval-100 Case，目标路径 `E:\Code\Py\raghub`，读取 40 个文件，包括 README、docs、Eval-100 报告和知识库文档。
- `project_status_report.md`：记录读取文件数 40、git commit 15、Evidence Coverage Score 60/100；当前上下文主要是 docs/README，未读取 tests/eval 文件类别证据。
- `next_tasks.md`：P0 包括为 workflow 补 tests、补最小 eval cases 和结果记录；P1 包括补 bad case 记录；面试准备包括项目目标、范围、README/docs/tests/eval/recent commits walkthrough。
- `risk_report.md`：提醒 tests/eval 证据不足会影响交付链路可信度；面试时必须说明 Evidence Coverage Score 是 evidence checklist，不是生产 readiness。
- `commit_suggestions.md`：仅生成 commit 建议草案，明确不要提交 `outputs/`、`run_logs/`，不要在未人工确认前执行 `git add` 或 `git commit`。
- `tool_call_log.md`：记录 18 个 tool call，状态主要为 success，人工确认状态为 pending；包含 RAGHub Eval-100 reader、delivery analyzer、LLM advisors、asset writers 和 consistency checker。
- `llm_review.md`：当前由 DeepSeek 生成审阅报告，强调不要包装为工业级/SOTA/生产级，LLM 结果只能作为辅助检查，不能作为权威质量背书。
- `human_feedback.md`：未发现该文件；human confirmation 通过 tool_call_log/run_log 字段记录。
- `docs/demo/raghub_analysis_case.md`：记录较早 RAGHub demo，强调只读读取、不调用 RAGHub API、不修改 RAGHub、不自动提交；展示 ProjectPilot 能生成报告、Tool Call Log、Run Log 和 Human Confirmation pending。
- `run_logs/latest_run.json`：记录 `target_project=RAGHub Eval-100 Case`、`workflow_status=completed`、`files_read=40`、`git_commits_read=15`、`delivery_readiness_score=60`、`human_confirmation_status=pending` 和当前 LLM provider。
- DeepSeek 真实复跑中，LLM advisor 产物可以成功生成；若 LLM 输出包含生产级指标等边界敏感表述，`consistency_checker` 会记录 finding，不能把该输出直接写成最终可展示结论。
- `run_logs/raghub_agent_latest_run.json`：记录 `agent_run.goal`、`planner_provider=mock`、planned/executed/skipped steps 计数和 `human_confirmation_status=pending`。

## 5. 测试结果

- pytest 命令：`python -m pytest`
- 测试结果：`python -m pytest` 全量通过（当前为 68 个测试，最终耗时以本轮命令输出为准）。
- 是否访问网络：否。测试使用 mock provider 或 mocked OpenAI-compatible client。
- 是否调用真实 DeepSeek：测试不调用；真实 DeepSeek 仅在 `LLM_PROVIDER=deepseek` 且存在 `DEEPSEEK_API_KEY` 的验收命令中调用。
- 是否需要 API key：测试不需要。真实 DeepSeek 复跑需要本机环境已设置 `DEEPSEEK_API_KEY`，报告只记录是否存在，不输出值。
- 是否修改目标项目：否。测试运行在 ProjectPilot 仓库和 pytest 临时目录中，未修改 RAGHub。

## 6. 简历可写内容

- 构建 ProjectPilot workflow-first 分析原型，读取 README/docs/eval/git log 等项目证据，生成 context summary、project status、next tasks、risk report、tool call log 和 run log。
- 面向 RAGHub Eval-100 增加结构化指标读取与风险登记，识别 no-answer、source competition、hybrid default decision、Eval-100 scope 和 production readiness 等项目级风险。
- 新增 planner-driven read-only Agent Workflow，支持用户 goal 生成 planned steps，并通过静态白名单 Tool Router 执行只读工具、记录危险工具 skipped。
- 接入可选 LLM Advisor，在 `mock` 默认 provider 下可离线运行，在显式配置 DeepSeek 时可生成风险复盘、任务计划和语义审阅；所有输出保持 `human_confirmation_status=pending`。
- 新增面试素材、简历素材和 consistency checker，将 RAGHub Eval-100 证据转换为候选表达，并用规则检查生产级、自动提交、hybrid 过度收益、unsupported metric 等 overclaim 风险。
- 通过 pytest 覆盖 CLI、LLM provider、RAGHub Eval-100 workflow、asset writers 和 consistency checker，当前测试结果为 `54 passed`。

## 7. 简历不能写内容

- 不能写生产级平台。
- 不能写企业级治理系统。
- 不能写自动项目经理。
- 不能写自动代码审查或自动代码修复。
- 不能写自动修改代码。
- 不能写自动提交 git。
- 不能写自动部署。
- 不能写完整审批系统。
- 不能写完整 Agent 平台。
- 不能写 DeepSeek planner 已驱动 agent-run，除非后续真的实现并运行 DeepSeek planner。
- 不能写多 Agent 协作。
- 不能写 LLM 全流程自主决策。
- 不能写 RAGHub 历史问题全由 ProjectPilot 自动发现和修复。
- 不能写完全解决幻觉、完全解决 no-answer 安全问题。
- 不能写 hybrid 全面优于 vector。
- 不能写 Eval-100 等同生产级 benchmark。

## 8. 推荐简历项目标题

- ProjectPilot Agent | 面向 RAGHub 的 AI 工程项目 Workflow 分析原型
- ProjectPilot Agent | AI 工程项目交付分析 Workflow Agent
- ProjectPilot Agent | Planner-driven Read-only 项目分析 Agent 原型
- ProjectPilot Agent | RAGHub 项目交付复盘与风险分析 Agent 原型

## 9. 推荐最终简历表述

项目标题：ProjectPilot Agent | 面向 RAGHub 的 AI 工程项目 Workflow 分析原型

技术栈：Python、pytest、Markdown workflow、JSON run log、可选 DeepSeek/OpenAI-compatible LLM provider、RAGHub Eval-100 artifacts

- 实现 workflow-first 项目分析链路，读取 README/docs/eval/git log 等证据并生成状态报告、下一步任务、风险提醒、Tool Call Log 和 Run Log。
- 面向 RAGHub Eval-100 增加确定性指标读取与风险登记，识别 no-answer、source competition、hybrid 默认策略和项目级 benchmark 边界。
- 新增 planner-driven read-only agent-run，支持自然语言 goal 生成 planned steps，通过静态 Tool Router 执行白名单只读工具并记录危险工具 skipped。
- 接入可选 LLM Advisor，默认使用 mock provider，显式配置 DeepSeek 时生成风险复盘和任务计划；所有建议保持人工确认，不自动修改或提交代码。
- 新增 interview/resume asset writer 与 consistency checker，将项目证据转换为候选表达，并检查生产级、自动提交、unsupported metric 等过度表述风险。

结论：当前更新足以支撑简历中写 ProjectPilot 与 RAGHub 联动验证，但只能写成“项目级只读 workflow 分析、planner-driven 原型和证据整理工具”，不能写成生产级平台、自动修复系统或由 DeepSeek 控制的自主 Agent。
