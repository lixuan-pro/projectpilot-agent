# ProjectPilot Agent 面试高频问答

本文档用于准备 ProjectPilot Agent 在国内实习 / 秋招面试中的讲解与追问回答。回答以当前 v0.1-v0.2 原型为准，重点强调 workflow-first Agent、只读分析、Tool Call Log、Run Log 和 Human Confirmation。

# 一、项目定位

## Q：ProjectPilot Agent 是什么？

### 回答要点

ProjectPilot Agent 是一个面向 AI 工程项目的交付分析与 workflow 协作智能体原型。它通过只读读取项目材料，生成项目状态报告、下一步任务、风险提醒和展示材料。

### 项目中的具体实现

当前会读取 README、docs、tests、eval 和 git log，并生成 context summary、project status report、next tasks、risk report、commit suggestions、llm review、Tool Call Log 和 Run Log。

### 后续可增强

可以接入 LLM 提升摘要质量，也可以支持更多项目类型和报告模板。

## Q：ProjectPilot 是 Agent 还是 Workflow？

### 回答要点

当前更准确地说是 workflow-first Agent 原型。它有 Agent 的目标拆解和工具调用思想，但优先保证 workflow 的步骤、边界和日志可解释。

### 项目中的具体实现

当前流程固定为读取上下文、读取 git log、生成 summary、规则分析、生成报告、生成建议、记录日志、等待 human confirmation。

### 后续可增强

后续可以把部分分析节点替换为 LLM 节点，或用 LangGraph 管理状态转移。

## Q：为什么不做成全自动项目经理？

### 回答要点

全自动项目经理容易越权，也很难保证建议和执行都可靠。当前项目更关注可控、可解释、可复盘的交付分析。

### 项目中的具体实现

ProjectPilot 只生成建议，不自动改 README、不自动 commit、不自动部署，所有建议保持 `pending`。

### 后续可增强

可以增加审批界面或 diff preview，但仍需要 Human Confirmation。

## Q：它和 Claude Code / Cursor / Codex 有什么区别？

### 回答要点

Claude Code / Cursor / Codex 更偏代码生成和工程执行辅助，ProjectPilot 更偏项目交付状态分析、证据整理和 workflow 协作。

### 项目中的具体实现

ProjectPilot 不编辑目标项目代码，只读取项目证据并生成报告、建议和日志。

### 后续可增强

可以把 Codex 等工具生成的 commit 或 run log 纳入分析材料，但不替代这些工具。

## Q：这个项目解决的真实痛点是什么？

### 回答要点

AI 工程项目在求职展示时经常不是没有功能，而是缺少清晰证据链和表达结构。ProjectPilot 帮助整理“做了什么、证据在哪里、还缺什么、下一步做什么”。

### 项目中的具体实现

通过读取 README、docs、tests、eval 和 git log，生成 context summary、项目状态报告、next tasks 和面试素材。

### 后续可增强

可以增加简历 bullet 生成、STAR 复盘生成和多版本展示材料对比。

# 二、Workflow / Agent 设计

## Q：为什么采用 Workflow-first Agent 设计？

### 回答要点

项目交付分析需要稳定步骤和明确边界。先做 workflow 能保证读取、分析、输出、日志和确认机制可控。

### 项目中的具体实现

workflow 从 initialized 到 reading_context，再到 analyzing、generating_tasks、pending_confirmation 和 completed。

### 后续可增强

可以在每个 workflow 节点加入更强的模型能力，但保留状态管理。

## Q：为什么先用 rule-based analyzer，而不是直接接 LLM？

### 回答要点

规则分析更稳定、可测试、可解释，适合作为早期 baseline。LLM 适合后续增强摘要和表达，但不应该一开始替代所有边界。

### 项目中的具体实现

ProjectStatusAnalyzer 根据 README、docs、tests、eval、bad cases、problems_and_solutions 和 git commits 判断证据完整度。

### 后续可增强

可以在规则输出之后增加 LLM rewriter 或 insight generator。

## Q：如果后续接 LLM，应该接在哪里？

### 回答要点

LLM 更适合接在 summary 和建议生成阶段，而不是直接控制文件读取或执行写操作。

### 项目中的具体实现

可以在 context summary 之后，用 LLM 生成更自然的项目分析、风险解释、README 建议和面试回答。

### 后续可增强

需要加入 prompt template、输出 schema 校验、人工确认和失败兜底。

## Q：如何避免 Agent 越权？

### 回答要点

通过只读工具、Tool Schema、Human Confirmation、Run Log 和明确非目标来限制行为。

### 项目中的具体实现

当前不修改目标项目、不执行 commit、不调用 RAGHub API，建议输出只作为草案。

### 后续可增强

可以加入权限级别、操作 allowlist、diff review 和审批记录。

## Q：为什么要限制读取文件数量和大小？

### 回答要点

限制读取可以避免全量扫描大仓库、减少无关信息、提升运行稳定性，也更符合只读分析工具的边界。

### 项目中的具体实现

Context Reader 默认最多读取 30 个文件，单文件最多读取 20 KB，并跳过 `.git`、`.venv`、`node_modules`、data、models、cache 等目录。

### 后续可增强

可以支持按模块权重、最近变更、配置 priority 或摘要缓存来优化读取策略。

# 三、Tool Schema / Tool Call Log

## Q：Tool Schema 有什么作用？

### 回答要点

Tool Schema 用于描述工具名称、输入、输出、只读属性和调用结果，使工具调用边界清晰、可记录、可测试。

### 项目中的具体实现

项目中定义了 ToolSpec、ToolInputSchema、ToolOutputSchema 和 ToolCallRecord，并包含 success、invalid_args、timeout、empty_result、permission_denied、internal_error 等状态。

### 后续可增强

可以把 Tool Schema 用于 LLM tool calling 或 MCP 适配，但当前不接 MCP。

## Q：Tool Call Log 记录了什么？

### 回答要点

Tool Call Log 记录每个分析步骤的工具名、状态、开始时间、结束时间、耗时、输入摘要、输出摘要、错误类型和 message。

### 项目中的具体实现

启用 LLM Review Advisor 后，真实 RAGHub 运行通常记录 10 条左右 tool call，具体数量会随 workflow 版本变化，包括 context_reader、git_reader、project_status_analyzer、readme_advisor、risk_advisor、commit_advisor 和 llm_review_advisor 等。

### 后续可增强

可以增加 trace id、重试记录、失败原因分类和可视化 timeline。

## Q：Tool Call Log 和普通日志有什么区别？

### 回答要点

普通日志偏运行信息，Tool Call Log 更关注 workflow 中每个工具调用的结构化输入输出和结果状态。

### 项目中的具体实现

`outputs/tool_call_log.md` 面向人查看，`run_logs/latest_run.json` 面向后续程序读取和复盘。

### 后续可增强

可以提供 JSONL 事件日志和 Markdown 报告两种格式。

## Q：为什么要记录 input summary 和 output summary？

### 回答要点

这样可以在不保存完整大文件内容的情况下说明工具做了什么，便于审查和复盘。

### 项目中的具体实现

每条 tool call 会记录输入摘要和输出摘要，例如读取文件数量、生成输出路径、分析结果概要。

### 后续可增强

可以加入更严格的隐私过滤和敏感信息脱敏。

## Q：工具状态为什么要区分多种失败类型？

### 回答要点

不同失败类型需要不同处理策略。参数错误、超时、空结果、权限拒绝和内部错误不能混在一起。

### 项目中的具体实现

Tool schema 中定义了 success、invalid_args、timeout、empty_result、permission_denied、internal_error 等状态。

### 后续可增强

可以为不同错误类型增加 retry policy 和用户提示。

# 四、Run Log / Human Confirmation

## Q：Run Log 有什么作用？

### 回答要点

Run Log 用于记录一次 workflow 运行的整体状态、步骤、工具调用、输出结果和人工确认状态，方便复盘。

### 项目中的具体实现

`run_logs/latest_run.json` 包含 workflow_status、steps、tool_calls、human_confirmation_status、files_read、git_commits_read、delivery_readiness_score、llm_provider 和 llm_review_output。

### 后续可增强

可以支持多次 run 的历史归档、run_id 查询和对比报告。

## Q：Human Confirmation 为什么重要？

### 回答要点

Human Confirmation 是避免 Agent 越权的关键。分析和建议可以自动生成，但真正修改项目、提交代码或改变任务计划必须由人确认。

### 项目中的具体实现

当前所有建议默认 `pending`，CLI 输出会展示“人工确认状态：pending”。

### 后续可增强

可以加入 approve / reject / revise 三种状态，以及确认记录和审批人信息。

## Q：为什么不自动改代码？

### 回答要点

自动改代码属于高风险写操作，需要更强的权限控制、diff 审查、测试验证和回滚机制。当前项目定位是只读分析，不是代码执行工具。

### 项目中的具体实现

ProjectPilot 不修改 RAGHub，也不修改任何目标项目，只在自身 `outputs/` 和 `run_logs/` 下生成分析结果。

### 后续可增强

可以支持生成 patch proposal，但仍需要人工确认后由开发者执行。

## Q：为什么不自动提交代码？

### 回答要点

commit 会改变目标项目历史，风险比生成建议更高。ProjectPilot 只能生成 commit 建议草案，不能自动执行。

### 项目中的具体实现

CommitAdvisor 只输出 `outputs/commit_suggestions.md`，不会运行 `git add` 或 `git commit`。

### 后续可增强

可以增加 commit message review、变更摘要和提交前 checklist。

## Q：pending 状态在当前版本意味着什么？

### 回答要点

pending 表示建议已经生成，但还没有被人确认执行。它是一种边界提示，不是完整审批系统。

### 项目中的具体实现

HumanFeedbackRecord 默认状态为 pending，并写入 run log。

### 后续可增强

可以增加交互式确认命令，例如 `projectpilot confirm --run-id ...`。

# 五、和 RAGHub 的联动

## Q：ProjectPilot 和 RAGHub 是什么关系？

### 回答要点

RAGHub 是 ProjectPilot 的第一个真实分析对象。ProjectPilot 用 RAGHub 验证自己的项目分析 workflow，但不依赖 RAGHub 的运行时 API。

### 项目中的具体实现

配置中指向 `E:\Code\Py\raghub`，ProjectPilot 读取 RAGHub 的 README、docs、tests、eval 和 git log。

### 后续可增强

可以把 ProjectPilot 应用到更多 AI 工程项目，验证泛化能力。

## Q：为什么不调用 RAGHub `/retrieve`？

### 回答要点

当前目标是分析项目交付证据，不是测试 RAGHub 的线上服务能力。调用 API 会引入运行环境和服务状态依赖。

### 项目中的具体实现

ProjectPilot 只读取仓库文件和 git log，不启动 RAGHub 服务，也不调用 `/retrieve` 或 `/chat`。

### 后续可增强

可以在单独的评测阶段增加 API health check，但需要明确权限和配置。

## Q：RAGHub Demo Case 能证明什么？

### 回答要点

它证明 ProjectPilot 可以处理真实项目，而不是只处理 mock 数据，并能把分散材料整理成展示型工程证据链。

### 项目中的具体实现

真实运行读取 24 个文件、10 条 git commit，启用 LLM Review 后会生成 8 个主要 outputs 和 1 个 run log。

### 后续可增强

可以加入多个项目 Demo Case，形成对比分析。

## Q：如果 RAGHub README 很大怎么办？

### 回答要点

读取器需要有边界。对于大 README，可以截断读取，保证根目录 README 仍被纳入分析。

### 项目中的具体实现

根目录 `README.md` 优先读取；超过 20 KB 时截断读取，而不是跳过。

### 后续可增强

可以对大文件先做章节级索引或摘要缓存。

## Q：ProjectPilot 是否只能分析 RAGHub？

### 回答要点

不是。RAGHub 只是第一个真实分析对象。ProjectPilot 通过 `projectpilot.yaml` 配置目标项目路径和读取规则。

### 项目中的具体实现

配置文件中有 project path、context include、exclude_dirs、max_files 和 git max_commits。

### 后续可增强

可以支持多项目配置和批量分析。

# 六、工程边界与风险

## Q：交付证据完整度评分为什么不是生产级评分？

### 回答要点

当前分数是规则化证据类型覆盖检查，只说明求职展示范围内的 README、docs、tests、eval、bad cases、问题复盘和 git 记录等证据类型是否覆盖。

### 项目中的具体实现

CLI 和报告中都会说明“该分数只表示证据类型覆盖程度，不代表项目质量满分、生产级可用或企业级审计结果”。

### 后续可增强

可以增加部署、性能、安全、监控、稳定性等维度，但那会进入更高阶段。

## Q：当前项目最大的边界是什么？

### 回答要点

最大边界是当前仍以 rule-based analyzer 为主。可选 LLM Review Advisor 只审阅已有报告，不直接读取整个仓库，不替代规则分析，也不执行写操作。

### 项目中的具体实现

ProjectStatusAnalyzer 使用规则判断文件、路径、关键词和 git log 证据。

### 后续可增强

可以加入 LLM summary、embedding 检索或人工反馈闭环。

## Q：当前项目最大的风险是什么？

### 回答要点

主要风险是规则过于简单，可能漏掉隐含问题；同时读取上限会导致部分细节不完整。

### 项目中的具体实现

当文件被截断时，risk report 会提示报告细节可能不完整。

### 后续可增强

可以增加更细的 evidence scoring、缺口分类和读取策略。

## Q：如何保证输出可信？

### 回答要点

输出必须基于明确读取到的文件和 git log，并通过 tool call log 和 run log 记录来源和过程。

### 项目中的具体实现

context_summary 列出 files read 和 recent git commits；tool_call_log 记录每个工具调用状态。

### 后续可增强

可以增加引用到具体文件行号、commit hash 和证据片段。

## Q：为什么 outputs 和 run_logs 不提交到 Git？

### 回答要点

这些是本地运行产物，可能随目标项目和运行时间变化，不适合作为源码提交。仓库只提交生成逻辑和文档。

### 项目中的具体实现

`.gitignore` 忽略 outputs 中的生成文件和 `run_logs/latest_run.json`，保留 `.gitkeep`。

### 后续可增强

可以提供示例输出快照，但需要脱敏并明确是 sample。

## Q：如何向面试官解释当前不是企业级平台？

### 回答要点

可以直接说明当前是求职展示型工程原型，目标是验证 workflow 和分析链路，不包含企业级权限、审计、部署和协作平台能力。

### 项目中的具体实现

README、scope 和报告都明确写了不做企业级治理平台、不代表生产级 readiness。

### 后续可增强

如果要走企业级方向，需要补权限模型、审计、项目空间、用户系统和合规能力。

## Q：这个项目后续最合理的 Day 7 是什么？

### 回答要点

比较合理的是做可配置报告模板、LLM 接入设计草案或多项目分析，而不是直接做自动执行。

### 项目中的具体实现

当前已经具备 Context Reader、Analyzer、Advisors、Tool Call Log 和 Run Log，可以在这些节点上扩展。

### 后续可增强

优先增强报告质量和 evidence trace，再考虑更复杂 Agent orchestration。
