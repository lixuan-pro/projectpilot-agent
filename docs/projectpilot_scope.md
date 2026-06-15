# ProjectPilot Agent Scope

## 定位

ProjectPilot Agent 是面向 AI 工程项目的交付管理与工作流协作智能体。它关注项目是否可交付、下一步应该做什么、风险在哪里，以及如何把工程过程沉淀成可复用材料。

## Workflow-first 的原因

AI 工程项目常见问题不是“缺少一次代码生成”，而是状态不清、交付缺口不清、任务优先级不清。ProjectPilot Agent 因此优先采用 workflow-first 设计：

- 先限定阶段，再执行动作。
- 先读取上下文，再生成判断。
- 先给出建议，再等待人工确认。
- 先记录 run log，再支持复盘。

这种方式降低误操作风险，也让输出更适合作为学习、面试、复盘和交付材料。

## 当前不是

ProjectPilot Agent 当前不是自动编码工具、自动提交工具、自动部署工具，也不是企业级治理平台。

## Day 1 边界

Day 1 只创建工程骨架，不做复杂 Agent，不接 LLM，不接 LangGraph，不接 MCP，不调用 RAGHub API，也不执行真实仓库分析。
