# ProjectPilot 分析 RAGHub Demo Case

## 1. Demo 目标

这个 Demo 用 ProjectPilot Agent 对真实 AI 工程项目 RAGHub 做一次只读分析，展示它如何从 README、docs、tests、eval 和 git log 中整理交付证据，并生成项目状态报告、下一步任务、风险提醒、README 建议、commit 建议草案、可选 LLM Review、Tool Call Log 和 Run Log。

Demo 的重点不是让 ProjectPilot 自动改代码，而是证明它可以作为 workflow-first Agent 原型，帮助项目作者梳理当前项目的展示材料、交付缺口和后续推进顺序。

## 2. 输入项目

- 目标项目：RAGHub
- 本地路径：`E:\Code\Py\raghub`
- 分析配置：`examples/projectpilot.yaml`
- 运行方式：只读读取目标项目，不调用 RAGHub API，不执行 `/retrieve`，不修改 RAGHub 文件，不自动提交代码。

## 3. 运行命令

```powershell
python -m projectpilot.cli analyze --config examples/projectpilot.yaml
```

## 4. 读取到的上下文

本次真实运行读取结果：

- 读取文件数：24
- 最近提交数：10
- 截断文件数：1
- 根目录 `README.md` 已读取，因超过 20 KB 单文件限制被截断读取。
- docs 包含设计文档、周报、项目讲解稿、面试问答和问题复盘。
- tests 包含健康检查、文件加载、文本切分、向量检索、retrieve API、chat API 等测试。
- eval 包含 `queries.jsonl`、`results.json` 和 `bad_cases.md`。
- git log 包含最近 10 条提交，例如 chat citations、no-answer handling、eval workflow、retrieve API、vector search 等迭代记录。

## 5. 生成的输出文件

本次运行生成：

- `outputs/context_summary.md`
- `outputs/project_status_report.md`
- `outputs/next_tasks.md`
- `outputs/readme_suggestions.md`
- `outputs/risk_report.md`
- `outputs/commit_suggestions.md`
- `outputs/llm_review.md`
- `outputs/tool_call_log.md`
- `run_logs/latest_run.json`

这些文件默认不进入 Git 提交，用于本地分析结果查看和复盘。

## 6. 项目状态分析摘要

ProjectPilot 在 RAGHub 中检测到较完整的求职展示型工程证据：

- README 可用于说明项目定位、运行方式和当前边界。
- docs 中存在设计、周报、项目讲解、面试问答、问题复盘等材料。
- tests 覆盖了 RAG 主链路中的加载、切分、检索、API 等部分。
- eval 中存在评测查询、结果和 bad cases。
- git log 能体现从基础检索到 chat API、引用展示、no-answer 处理等迭代过程。

当前规则未检测到影响主链路闭环的 P0 缺口。

## 7. 交付证据完整度评分解释

- 交付证据完整度评分（Evidence Coverage Score）：RAGHub 在当前规则下仍可得到高分。
- 评分类型：规则化证据类型覆盖检查。
- 解释：该分数只表示 RAGHub 在当前求职展示范围内覆盖 README、docs、tests、eval、bad case、问题复盘和 git 记录等证据类型。

这个分数不代表项目质量满分，不代表生产级可用，不代表企业级 readiness，也不代表安全、稳定性、部署或合规层面的完整评估。

## 8. 风险提醒摘要

本次规则化风险提醒中，未检测到必须立即处理的 P0 风险。

已提示的主要风险是：部分文件因读取上限被截断，报告细节可能不完整。如果后续需要更细分析，可以提高读取上限，或者在目标项目中补充更聚焦的摘要文档。

面试表达上需要明确：交付证据完整度评分是规则化 evidence checklist，不是项目质量满分或生产级评分；ProjectPilot 不会自动修改目标项目，也不会自动提交代码。

## 9. 下一步任务摘要

本次生成的 next tasks 以展示材料增强为主：

- P0：当前规则未检测到 P0 任务。
- P1：继续增强 eval 质量和项目展示材料。
- P2：在当前交付叙事清晰后，再扩展 Roadmap。
- 面试准备：准备项目目标、当前范围、非目标、README/docs/tests/eval/git log 证据链，以及 bad cases 和 problems_and_solutions 的复盘表达。

## 10. Tool Call Log 摘要

启用 LLM Review Advisor 后，本 Demo 通常会记录 10 条左右 tool call，具体数量会随 workflow 版本变化。主要步骤包括：

- `context_reader`
- `git_reader`
- `context_summary_writer`
- `project_status_analyzer`
- `project_status_report_writer`
- `next_tasks_writer`
- `readme_advisor`
- `risk_advisor`
- `commit_advisor`
- `llm_review_advisor`

Tool Call Log 记录每一步的 tool name、status、耗时、输入摘要、输出摘要和 message，用于解释 workflow 执行过程。

Day 8 评分校准后，已再次通过 DeepSeek smoke test 验证 LLM Review Advisor 可用；该验证只发送已有报告摘要，不直接读取整个仓库。

## 11. Human Confirmation 状态

本次运行的 Human Confirmation 状态为：

```text
pending
```

含义是：ProjectPilot 可以生成建议，但不自动执行写操作。README 修改、commit 执行、任务调整等动作仍需要人工确认。

## 12. 当前边界

本 Demo 中 ProjectPilot Agent 仍然遵守以下边界：

- 默认使用 mock LLM provider；可选 DeepSeek LLM Review Advisor 只审阅已有报告。
- 不接 LangGraph。
- 不接 MCP。
- 不调用 RAGHub `/retrieve`。
- 不修改 RAGHub。
- 不自动提交 RAGHub。
- 不自动部署。
- 不代表企业级治理或生产级审计。

## 13. 这个 Demo 能证明什么

这个 Demo 可以证明 ProjectPilot Agent 已具备一个最小但闭环的只读项目分析 workflow：

- 能读取真实目标项目的有限上下文。
- 能识别 README、docs、tests、eval、git log 等交付证据。
- 能生成项目状态报告和下一步任务。
- 能生成 README 建议、风险提醒和 commit 建议草案。
- 能生成可选 LLM 语义审阅报告，但 LLM 不直接读取整个仓库，不自动执行动作。
- 能记录 Tool Call Log 和 Workflow Run Log。
- 能通过 Human Confirmation pending 明确区分“生成建议”和“执行动作”。

它目前证明的是 workflow-first Agent 原型的工程链路，不是生产级项目治理平台。
