# ProjectPilot Agent

ProjectPilot Agent 是面向 AI 工程项目的交付管理与工作流协作智能体。

当前状态：Day 2 context reader。这个仓库目前提供工程骨架、CLI 入口、schema 草案、workflow 状态枚举、最小 run log、基础测试，以及只读项目上下文读取能力。

## 项目定位

ProjectPilot Agent 读取项目仓库中的 README、docs、tests、eval、git log 等上下文，帮助生成：

- 项目状态分析
- 交付缺口
- 下一步任务
- 风险提醒
- README 建议
- commit 建议
- 简历 / 面试素材
- run log
- human feedback
- Delivery Readiness Score

RAGHub 会是第一个真实分析对象，但 ProjectPilot Agent 不强依赖 RAGHub API。

## 不是什么

ProjectPilot Agent 不是：

- Claude Code 替代品
- Cursor 替代品
- 自动写代码工具
- 自动提交工具
- 自动部署工具
- 企业级治理平台

## 当前运行方式

```powershell
python -m projectpilot.cli --help
python -m projectpilot.cli analyze --config examples/projectpilot.yaml
```

Day 1 的 `analyze` 只加载配置并输出 mock summary，不执行真实项目分析。

Day 2 的 `analyze` 会按配置读取目标项目的有限上下文，包含 README、docs、tests、eval 和最近 git log，并写入：

- `outputs/context_summary.md`
- `run_logs/latest_run.json`

这仍然只是上下文摘要，不做语义分析、不接 LLM、不自动生成任务。

## 当前边界

- 不实现真实 LLM。
- 不接 LangGraph。
- 不接 MCP。
- 不调用 RAGHub `/retrieve`。
- 不自动改代码。
- 不自动提交。
- 不全量读取大仓库。
- 不做复杂前端。
- 不做企业级权限系统。
- 不生成最终项目状态判断。
- 不自动生成下一步任务。

## 未来 Workflow

ProjectPilot Agent 未来会按工作流推进，而不是直接执行自由形式的自动化：

1. 初始化项目配置。
2. 读取有限上下文。
3. 分析项目状态和交付缺口。
4. 生成下一步任务和风险提醒。
5. 对写操作进入人工确认。
6. 输出报告、run log 和建议。

## 当前只读 Context Reader

Day 2 支持读取：

- `README.md`
- `docs/**/*.md`
- `tests/**/*.py`
- `eval/**/*.jsonl`
- `eval/**/*.json`
- `eval/**/*.md`
- 最近若干条 git commit

读取器默认最多读取 30 个文件，单文件最多 20 KB，并跳过 `.git`、`.venv`、`__pycache__`、`.pytest_cache`、`node_modules`、`data/raw`、`data/processed`、`models`、`cache` 等目录。

## Roadmap

- Day 1：工程骨架、文档、CLI、schema 草案、基础测试。
- Day 2：只读项目上下文读取器、受限文件扫描、git log 读取、context summary。
- Day 3：项目状态分析报告模板。
- Day 4：任务建议、风险提醒和 README 建议。
- Day 5：human confirmation 流程和更完整 run log。
