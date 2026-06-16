# ProjectPilot Agent Scope

## 项目定位

ProjectPilot Agent 是一个面向 AI 工程项目的交付分析与工作流协作智能体原型。

它关注的不是“自动生成代码”，而是帮助判断一个项目当前是否有清晰的交付证据、还缺哪些材料、下一步任务应该如何排序，以及如何把项目过程转化为可复盘、可展示、可面试表达的工程材料。

## 为什么是 Workflow-first Agent

AI 工程项目常见的问题不是单次代码生成能力不足，而是：

- 项目状态不清楚。
- 交付边界不清楚。
- README、docs、tests、eval 等证据分散。
- 下一步任务优先级不清楚。
- 面试时难以把工程过程讲清楚。

因此 ProjectPilot Agent 采用 Workflow-first Agent 思路：

1. 先读取有限上下文。
2. 再基于明确证据做规则化分析。
3. 再生成项目报告和下一步任务。
4. 再生成 README 建议、风险提醒和 commit 建议草案。
5. 涉及写操作时必须进入 Human Confirmation。
6. 每次运行都写入 Run Log，方便复盘。

## 当前能力范围

截至 Day 5，ProjectPilot Agent 支持：

- 读取 README/docs/tests/eval/git log。
- 生成 `outputs/context_summary.md`。
- 运行 rule-based analyzer。
- 生成 `outputs/project_status_report.md`。
- 生成 `outputs/next_tasks.md`。
- 生成 `outputs/readme_suggestions.md`。
- 生成 `outputs/risk_report.md`。
- 生成 `outputs/commit_suggestions.md`。
- 生成 `outputs/tool_call_log.md`。
- 写入 `run_logs/latest_run.json`。
- 计算 v0.1 Delivery Readiness Score。
- 记录 Human Confirmation 的 `pending` 状态。
- 记录 workflow steps 和 tool calls。

## Delivery Readiness Score 边界

Delivery Readiness Score 是规则化证据完整度检查，不是生产级 readiness 评估。

当前分数只回答一个问题：

> 在当前求职展示范围内，目标项目是否具备较完整的 README、docs、tests、eval、bad case、问题复盘和 git 记录等证据？

它不代表生产环境可用，也不代表企业级治理、稳定性、安全性或合规性评估。

## Day 4 边界

Day 4 只生成建议：

- README 建议不等于自动改 README。
- Commit 建议不等于自动执行 commit。
- 风险提醒不等于生产级审计。
- Human Confirmation 当前只记录 `pending`，不做交互式审批界面。

## Day 5 边界

Day 5 增强 Tool Call Log 和 Workflow Run Log，用于追踪本地分析流程。

这些日志用于说明每个分析步骤是否执行、耗时多久、输入输出摘要是什么。它们不代表企业级审计、权限治理、合规系统或生产监控。

## Day 6 展示材料边界

Day 6 不新增核心分析能力，重点是把当前 ProjectPilot 对 RAGHub 的真实分析结果整理成可展示、可复盘、可面试表达的材料：

- `docs/demo/raghub_analysis_case.md`：说明 ProjectPilot 如何只读分析 RAGHub。
- `docs/projectpilot_project_pitch.md`：整理 30 秒、2 分钟、5 分钟和简历版本讲解稿。
- `docs/interview/projectpilot_interview_questions.md`：整理 ProjectPilot 面试高频问答。

这些材料用于国内实习 / 秋招展示，不代表 ProjectPilot 已经成为企业级项目治理平台，也不改变当前只读分析、Human Confirmation pending 和不自动执行写操作的边界。

## 当前不做什么

ProjectPilot Agent 当前不是：

- Claude Code / Cursor / Codex 替代品
- 自动写代码工具
- 自动提交工具
- 自动部署工具
- 企业级项目治理平台

Day 4 不接真实 LLM，不接 LangGraph，不接 MCP，不调用 RAGHub API，不自动修改目标项目，不自动提交，也不生成最终简历版本。
