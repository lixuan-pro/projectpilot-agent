# ProjectPilot Agent

ProjectPilot Agent 是一个面向 AI 工程项目的交付分析与工作流协作智能体原型。

当前处于 v0.1-v0.2 原型阶段，已支持读取目标项目的 README、docs、tests、eval 和 git log，并基于规则生成项目状态报告、下一步任务建议、README 建议、风险提醒、commit 建议草案和 Run Log。

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
- Delivery Readiness Score

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
11. 写入 `run_logs/latest_run.json`。

运行方式：

```powershell
python -m projectpilot.cli --help
python -m projectpilot.cli analyze --config examples/projectpilot.yaml
```

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

Day 3 引入规则化项目状态分析器，不接真实 LLM。

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

## Delivery Readiness Score

Delivery Readiness Score 当前是 v0.1 规则化证据完整度检查。

它表示目标项目在当前展示范围内，README、docs、tests、eval、bad case、问题复盘和 git 记录等证据是否齐全。

它不代表：

- 生产级可用
- 企业级 readiness
- 安全合规评估
- LLM 语义判断
- 招聘结果保证

## 当前边界

- 不接真实 LLM。
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
- Day 3：rule-based project status report、Delivery Readiness Score、next tasks。
- Day 4：README 建议、风险提醒增强、commit 建议草案、Human Feedback / pending confirmation。
- Day 5：Human Confirmation 流程和更完整的 Tool Call Log / Run Log。
