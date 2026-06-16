# ProjectPilot Agent 项目讲解稿

## 1. 30 秒版本

ProjectPilot Agent 是一个面向 AI 工程项目的交付分析与 workflow 协作智能体原型。它不自动写代码，也不替代 Claude Code / Cursor / Codex，而是只读读取项目中的 README、docs、tests、eval 和 git log，基于规则生成项目状态报告、下一步任务、风险提醒、README 建议、commit 建议草案，并通过 Tool Call Log、Run Log 和 Human Confirmation 记录整个分析过程。

RAGHub 是它的第一个真实分析对象，用来验证这个 workflow 是否能从真实项目中整理出可展示、可复盘、可面试表达的工程材料。

## 2. 2 分钟版本

我做 ProjectPilot Agent 的原因是，AI 工程项目在求职展示时经常不是缺少某一个功能，而是缺少一套清晰的交付证据链。比如 README 写了什么、docs 有没有设计过程、tests 有没有覆盖主链路、eval 有没有结果和 bad cases、git log 能不能体现迭代，这些信息分散在仓库里，面试时很难快速组织成清晰表达。

ProjectPilot Agent 采用 workflow-first Agent 思路，先做只读上下文读取，再做规则化分析，再生成报告和建议。当前它能读取目标项目的 README、docs、tests、eval 和 git log，生成 context summary、project status report、next tasks、readme suggestions、risk report、commit suggestions 和 tool call log，同时写入 run log。

它的一个核心边界是只读和 human confirmation。ProjectPilot 可以给建议，但不会自动修改目标项目、不会自动执行 commit、不会调用目标项目 API。这样可以避免 Agent 越权，也更符合求职展示阶段对可控性和可解释性的要求。

## 3. 5 分钟版本

ProjectPilot Agent 的定位是面向 AI 工程项目的交付分析与工作流协作智能体原型。它要解决的问题不是“帮我写代码”，而是“帮我判断这个项目现在有哪些可展示证据、还有哪些交付缺口、下一步应该补什么，以及面试时应该怎么讲”。

在设计上，我没有直接把它做成一个复杂 LLM Agent，而是先做 workflow-first 的工程骨架。原因是这类项目管理型任务更需要稳定的步骤边界：读取哪些文件、每次最多读取多少、哪些目录要跳过、如何记录工具调用、如何生成报告、哪些建议必须等待人工确认。这些边界如果不先设计清楚，后续接 LLM 很容易变成不可控的自由生成。

当前 workflow 主要包括：

1. 加载 `projectpilot.yaml`。
2. 使用 Context Reader 只读读取 README、docs、tests、eval。
3. 读取最近 git log。
4. 生成 `context_summary.md`。
5. 使用 rule-based analyzer 生成项目状态分析和 Delivery Readiness Score。
6. 生成 `project_status_report.md` 和 `next_tasks.md`。
7. 生成 README 建议、风险提醒和 commit 建议草案。
8. 生成 Tool Call Log。
9. 写入 Workflow Run Log，并把 Human Confirmation 状态保持为 `pending`。

RAGHub 是第一个真实分析对象。本地真实运行时，ProjectPilot 读取了 24 个文件、10 条最近提交，识别出 README、docs、tests、eval、bad cases、problems_and_solutions 和 git 迭代证据，生成了完整的报告链路。Delivery Readiness Score 得到 100/100，但我在文档和输出里明确说明它是规则化证据完整度检查，不代表生产级可用。

这个项目的亮点不在于模型能力，而在于工程边界和 workflow 可解释性：有 Tool Schema，有 Tool Call Log，有 Run Log，有 Human Confirmation，也明确限制不自动改代码、不自动提交、不调用目标项目 API。这让它后续可以比较自然地接入 LLM 或 LangGraph，但当前阶段先保证主链路可运行、可测试、可展示。

## 4. 面试开场版

我想介绍的第二个项目是 ProjectPilot Agent。它是一个面向 AI 工程项目的交付分析与 workflow 协作智能体原型，主要用于把一个项目仓库里的 README、docs、tests、eval 和 git log 转化成项目状态报告、下一步任务、风险提醒和面试表达材料。

它和 RAGHub 的关系是：RAGHub 是我的第一个真实 AI 工程项目，ProjectPilot 则是用来分析 RAGHub 的第二个项目。它不依赖 RAGHub API，只读取仓库材料，所以可以扩展到其他 AI 工程项目。

## 5. 简历项目描述版本

ProjectPilot Agent：面向 AI 工程项目的交付分析与 workflow 协作智能体原型。实现 bounded Context Reader、git log reader、rule-based project status analyzer、Delivery Readiness Score、README / risk / commit advisors、Tool Call Log、Workflow Run Log 和 Human Confirmation pending 状态。以 RAGHub 为真实分析对象，生成 context summary、project status report、next tasks、risk report 和展示材料，全流程只读，不自动修改目标项目，不自动提交代码。

## 6. 项目亮点

- Workflow-first Agent：先把分析步骤、输入输出、日志和边界设计清楚，再考虑 LLM 接入。
- 只读上下文读取：限制文件数量、单文件大小、后缀白名单和排除目录，避免全量扫描大仓库。
- Rule-based analyzer：先用可解释规则形成稳定 baseline，避免早期依赖不可控生成。
- Tool Call Log：记录每个 tool call 的状态、耗时、输入输出摘要和 message。
- Workflow Run Log：记录 workflow 状态、steps、tool calls 和 human confirmation 状态。
- Human Confirmation：所有建议默认 pending，不自动执行写操作。
- 真实 Demo Case：使用 RAGHub 做真实分析对象，而不是只在 mock 项目上演示。

## 7. 当前边界怎么说

可以这样说：

ProjectPilot Agent 当前是 v0.1-v0.2 原型，不是生产级项目治理系统。它不接真实 LLM，不接 LangGraph，不接 MCP，不调用目标项目 API，不自动修改代码，也不自动执行 commit。当前重点是验证 workflow-first 的只读分析链路是否成立，以及输出是否能服务于求职展示和面试表达。

## 8. 和 RAGHub 的关系

RAGHub 是第一个真实分析对象，用于验证 ProjectPilot 能否处理真实 AI 工程项目中的 README、docs、tests、eval 和 git log。

ProjectPilot 不强依赖 RAGHub：

- 不调用 RAGHub `/retrieve`。
- 不调用 RAGHub `/chat`。
- 不修改 RAGHub 文件。
- 不要求 RAGHub 提供专用 API。

这种关系更像“分析工具”和“被分析项目”，而不是两个项目之间的运行时依赖。

## 9. 被追问时的回答策略

如果被问为什么不直接接 LLM，可以回答：当前先做 rule-based analyzer，是为了把 workflow、读取边界、日志和人工确认跑通。LLM 更适合放在后续的摘要增强、风险解释、面试素材生成等节点，而不是一开始就替代所有规则。

如果被问为什么不自动改代码，可以回答：ProjectPilot 的定位是交付分析和建议生成，不是代码执行工具。自动改代码和自动 commit 风险更高，需要更完整的权限控制、diff 审查、回滚策略和 human confirmation。

如果被问 Delivery Readiness Score 为什么是 100/100，可以回答：这个分数不是生产级 readiness，而是规则化证据完整度评分。它说明目标项目在当前求职展示范围内具备较完整的 README、docs、tests、eval、bad cases、问题复盘和 git 记录，不代表线上可用或企业级成熟。

如果被问项目后续怎么增强，可以回答：下一步可以接入 LLM 做更高质量的摘要和建议，但仍然保留 Tool Schema、Tool Call Log、Run Log 和 Human Confirmation；也可以扩展多项目对比、报告模板、简历素材生成和更细粒度的风险规则。
