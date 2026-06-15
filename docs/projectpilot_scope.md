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
4. 涉及写操作时必须进入 Human Confirmation。
5. 每次运行都写入 Run Log，方便复盘。

## 当前能力范围

截至 Day 3，ProjectPilot Agent 支持：

- 读取 README/docs/tests/eval/git log。
- 生成 `outputs/context_summary.md`。
- 运行 rule-based analyzer。
- 生成 `outputs/project_status_report.md`。
- 生成 `outputs/next_tasks.md`。
- 写入 `run_logs/latest_run.json`。
- 计算 v0.1 Delivery Readiness Score。

## Delivery Readiness Score 边界

Delivery Readiness Score 是规则化证据完整度检查，不是生产级 readiness 评估。

当前分数只回答一个问题：

> 在当前求职展示范围内，目标项目是否具备较完整的 README、docs、tests、eval、bad case、问题复盘和 git 记录等证据？

它不代表生产环境可用，也不代表企业级治理、稳定性、安全性或合规性评估。

## 当前不做什么

ProjectPilot Agent 当前不是：

- Claude Code / Cursor / Codex 替代品
- 自动写代码工具
- 自动提交工具
- 自动部署工具
- 企业级项目治理平台

Day 3 不接真实 LLM，不接 LangGraph，不接 MCP，不调用 RAGHub API，不自动修改目标项目，不自动提交，也不生成最终简历版本。
