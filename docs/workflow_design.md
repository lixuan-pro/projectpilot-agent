# Workflow Design

## 设计目标

ProjectPilot Agent 的 workflow 用来约束分析过程，让智能体从“自由聊天”变成“可追踪的交付管理流程”。

## 基础状态

Day 1 定义的 workflow state 包括：

- `initialized`
- `reading_context`
- `analyzing`
- `generating_tasks`
- `pending_confirmation`
- `completed`
- `failed`

## 状态含义

- `initialized`：已加载配置，但尚未读取项目上下文。
- `reading_context`：正在读取 README、docs、tests、eval 或 git log 等有限上下文。
- `analyzing`：正在分析项目状态、交付缺口和风险。
- `generating_tasks`：正在生成下一步任务、README 建议或 commit 建议。
- `pending_confirmation`：存在潜在写操作或高影响建议，等待人工确认。
- `completed`：本次 workflow 正常结束。
- `failed`：本次 workflow 因配置、权限、解析或内部错误失败。

## Human confirmation

ProjectPilot Agent 默认应优先只读。任何写入项目文件、生成提交、执行部署或修改外部系统的动作，都必须进入 `pending_confirmation` 并等待人工确认。

## Day 1 边界

Day 1 只定义状态，不实现完整 workflow engine，不调 LLM，不调外部 API。
