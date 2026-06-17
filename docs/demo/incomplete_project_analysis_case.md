# ProjectPilot 分析 Incomplete Demo Project Demo Case

## 1. Demo 目标

这个 Demo 用一个只有 README 的最小示例项目验证 ProjectPilot 不是只为 RAGHub 写死。目标是确认 ProjectPilot 能识别缺少 docs、tests、eval、bad cases、problems_and_solutions 和 git log 等交付证据的项目，并给出较低的交付证据完整度评分。

## 2. 输入项目

- 项目名称：Incomplete Demo Project
- 示例路径：`examples/incomplete_project`
- 配置文件：`examples/incomplete_project.yaml`

该示例项目只包含：

- `README.md`

## 3. 运行命令

```powershell
python -m projectpilot.cli analyze --config examples/incomplete_project.yaml
```

## 4. 预期分析结果

该项目不应该得到高分，因为它缺少以下证据：

- docs 设计或范围说明
- tests 测试文件
- eval 评测材料
- bad cases 记录
- problems_and_solutions 问题复盘
- 独立 git log 迭代证据

## 5. ProjectPilot 应识别的 gap

ProjectPilot 应提示：

- 补充 docs，说明架构、范围或 workflow 决策。
- 补充 tests，覆盖核心项目行为。
- 补充 eval 材料，让质量检查可以复现。
- 补充 bad cases，让当前限制和失败样例更明确。
- 补充 problems_and_solutions，支持交付复盘和面试表达。
- 补充 recent git commits 或提交记录证据。

## 6. 这个 Demo 能证明什么

这个 Demo 证明 ProjectPilot 的 analyzer 至少能区分“证据较完整的真实项目”和“只有 README 的不完整项目”。

它不能证明 ProjectPilot 已具备深度代码质量分析能力。当前评分仍然是 rule-based evidence checklist，只表示交付证据类型覆盖程度，不代表项目质量满分、生产级 readiness 或企业级审计结果。

## 7. 当前边界

- 不调用外部项目 API。
- 不修改示例项目。
- 不自动提交代码。
- LLM Review Advisor 默认使用 mock；如果启用 DeepSeek，也只审阅已有报告，不直接读取整个仓库。
