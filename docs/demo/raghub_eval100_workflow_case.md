# ProjectPilot RAGHub Eval-100 Workflow Case

## 1. Demo 目标

这个 Demo 展示 ProjectPilot v0.3 如何基于 RAGHub Eval-100 的确定性输出文件，生成指标摘要、风险登记、DeepSeek Advisor 复盘、任务计划、Tool Call Log 和 Run Log。

重点不是让 ProjectPilot 修改 RAGHub，而是验证它能把已有评测证据整理成一个可复核的交付分析 workflow。

## 2. 运行命令

```powershell
python -m projectpilot.cli analyze --config examples/raghub_eval100.yaml
```

配置文件中启用：

```yaml
raghub_eval100:
  enable_llm_advisors: true
```

## 3. 输入证据文件

ProjectPilot 只读以下 RAGHub 文件：

- `eval/results_100.json`
- `eval/retrieval_comparison_100.json`
- `eval/llm_ab_review_100_results.json`
- `docs/eval_100_report.md`
- `eval/bad_cases.md`

LLM Advisor 不直接读取完整 JSON 自由发挥，而是基于 ProjectPilot 已解析出的结构化指标和风险登记生成语义复盘。

## 4. 解析到的 Eval-100 指标

| metric | value |
| ------ | ----: |
| total_queries | 100 |
| in_corpus / out_of_corpus | 88 / 12 |
| answerability_accuracy | 0.99 |
| out_of_corpus_rejected | 12/12 |
| exact_source_hit_rate | 0.5909 |
| acceptable_source_hit_rate | 0.7955 |
| source_group_hit_rate | 0.9091 |
| keyword_hit_rate | 0.6414 |
| vector_average_score | 8.83 |
| hybrid_average_score | 8.90 |
| vector wins / hybrid wins / ties | 12 / 12 / 76 |

这些指标来自 JSON parser，不由 LLM 推断。

## 5. ProjectPilot 风险识别结果

| issue | status | reason |
| ----- | ------ | ------ |
| no_answer_risk | resolved | out-of-corpus rejected = 12/12 |
| source_competition | open | source_group hit 明显高于 exact source hit |
| hybrid_default_decision | not_recommended | hybrid gain 小且多数 case tie |
| eval_100_scope | project_level_benchmark | 100-query project-level eval |
| production_readiness | not_production | 不是生产级 benchmark 或审计 |

## 6. DeepSeek Advisors 做了什么

Phase 3 新增两个 LLM Advisor：

- `llm_raghub_risk_reviewer`：基于结构化指标和风险登记生成 `llm_risk_review.md`。
- `llm_raghub_task_planner`：基于指标、风险登记和风险复盘摘要生成 `llm_task_plan.md`。

如果 `LLM_PROVIDER=mock`，输出使用 mock provider 生成，用于本地测试和离线验证。

如果 `LLM_PROVIDER=deepseek` 但缺少 `DEEPSEEK_API_KEY`，Advisor 会返回 `permission_denied` 并写出可控的降级报告，不会崩溃。

## 7. 输出文件

运行后会生成：

- `outputs/raghub_eval100/eval_metrics_summary.md`
- `outputs/raghub_eval100/raghub_risk_review.md`
- `outputs/raghub_eval100/risk_register.json`
- `outputs/raghub_eval100/issue_to_task_map.md`
- `outputs/raghub_eval100/llm_risk_review.md`
- `outputs/raghub_eval100/llm_task_plan.md`
- `outputs/raghub_eval100/tool_call_log.md`
- `run_logs/latest_run.json`

`outputs/` 和 `run_logs/` 是本地生成产物，默认不进入 Git 提交。

## 8. tool_call_log / run_log 记录

Tool Call Log 会记录新增步骤：

- `raghub_eval_metrics_reader`
- `raghub_delivery_analyzer`
- `raghub_case_report_writer`
- `llm_raghub_risk_reviewer`
- `llm_raghub_task_planner`

Run Log 会记录：

- `raghub_eval100.llm_advisors_enabled`
- `raghub_eval100.llm_risk_review`
- `raghub_eval100.llm_task_plan`
- `raghub_eval100.human_confirmation_status`

## 9. Human Confirmation

所有建议保持：

```text
human_confirmation_status = pending
```

含义是 ProjectPilot 只生成分析和任务建议，不自动修改 RAGHub，不自动提交，不自动创建 PR。

## Real DeepSeek Advisor Smoke Run

本 demo 已在 `LLM_PROVIDER=deepseek` 下完成一次真实 smoke run，用于验证 ProjectPilot 的 LLM Advisor 链路可以在真实 provider 下运行。

验证内容：

- `llm_raghub_risk_reviewer` 成功生成 `llm_risk_review.md`
- `llm_raghub_task_planner` 成功生成 `llm_task_plan.md`
- `tool_call_log.md` 记录两个 LLM advisor step
- `run_logs/latest_run.json` 记录 `llm_advisors_enabled=true`
- `human_confirmation_status=pending`
- 未输出或提交真实 API key

本次内容复核：

- Risk Reviewer 围绕 Eval-100、no-answer、source competition、hybrid not default 和 project-level benchmark 展开，没有把 RAGHub 说成生产级平台。
- Task Planner 成功生成 P0/P1/P2/P3 任务计划，但 DeepSeek 自由输出中曾把 `source_competition` 放入 P0；这与当前 ProjectPilot 规则中“source competition -> P1/P2”的默认分层不完全一致。
- 因此该输出可作为真实 provider smoke 证据，但任务优先级仍必须经过人工确认，不能作为自动执行计划。

边界：

- DeepSeek 只作为 Advisor，不执行工具、不修改 RAGHub、不提交代码。
- 输出仍需人工确认。
- ProjectPilot 不是生产级治理平台。

## 10. 当前边界

- 不修改 RAGHub。
- 不自动提交 RAGHub。
- 不接 FastAPI。
- 不接 LangGraph。
- 不接 MCP。
- 不做多 Agent。
- 不把 ProjectPilot 包装成企业级治理平台。
- 不把 Eval-100 或 DeepSeek Advisor 输出说成生产级审计报告。
- 不声称 no-answer 已经解决所有幻觉或安全问题。
- 不建议默认启用 hybrid。

这个 Demo 证明的是 ProjectPilot v0.3 的交付分析 workflow 能把真实 Eval-100 证据转成可复核报告和待确认任务，不是生产级项目治理系统。
