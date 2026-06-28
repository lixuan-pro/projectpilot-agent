"""LLM task planner for the RAGHub Eval-100 delivery case."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from projectpilot.analyzers.eval_metrics_reader import RAGHubEvalMetrics
from projectpilot.analyzers.raghub_delivery_analyzer import RAGHubDeliveryReport
from projectpilot.feedback.human_feedback import HumanFeedbackStatus
from projectpilot.llm.base import LLMConfigurationError, LLMProviderError
from projectpilot.llm.client_factory import get_llm_client, get_llm_provider
from projectpilot.schemas.tool_schema import ToolCallStatus


MAX_RISK_REVIEW_CHARS = 2500


@dataclass(frozen=True)
class LLMRAGHubTaskPlanResult:
    provider: str
    output_path: Path
    status: ToolCallStatus
    message: str
    prompt: str
    plan_text: str
    confirmation_status: HumanFeedbackStatus = HumanFeedbackStatus.PENDING


class LLMRAGHubTaskPlanner:
    """Turn structured RAGHub risks into pending P0/P1/P2/P3 tasks."""

    def plan(
        self,
        metrics: RAGHubEvalMetrics,
        delivery_report: RAGHubDeliveryReport,
        risk_review_summary: str,
        output_path: str | Path = "outputs/raghub_eval100/llm_task_plan.md",
        provider: str | None = None,
    ) -> LLMRAGHubTaskPlanResult:
        selected_provider = provider or get_llm_provider()
        prompt = build_raghub_task_plan_prompt(
            metrics=metrics,
            delivery_report=delivery_report,
            risk_review_summary=risk_review_summary[:MAX_RISK_REVIEW_CHARS],
        )
        status = ToolCallStatus.SUCCESS
        error_message = ""

        try:
            client = get_llm_client(selected_provider)
            generated_text = client.generate(prompt).strip()
        except LLMConfigurationError as exc:
            status = ToolCallStatus.PERMISSION_DENIED
            generated_text = ""
            error_message = str(exc)
        except LLMProviderError as exc:
            status = ToolCallStatus.INTERNAL_ERROR
            generated_text = ""
            error_message = str(exc)

        if status == ToolCallStatus.SUCCESS and not generated_text:
            status = ToolCallStatus.EMPTY_RESULT
            error_message = "LLM provider 返回空结果。"

        message = _message_for_status(status, selected_provider, error_message)
        plan_text = build_raghub_task_plan_markdown(
            metrics=metrics,
            delivery_report=delivery_report,
            provider=selected_provider,
            status=status,
            generated_text=generated_text,
            message=message,
        )

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(plan_text, encoding="utf-8")
        return LLMRAGHubTaskPlanResult(
            provider=selected_provider,
            output_path=path,
            status=status,
            message=message,
            prompt=prompt,
            plan_text=plan_text,
        )


def build_raghub_task_plan_prompt(
    metrics: RAGHubEvalMetrics,
    delivery_report: RAGHubDeliveryReport,
    risk_review_summary: str,
) -> str:
    issue_lines = [
        f"- {issue.issue_name}: status={issue.status}; evidence={issue.evidence}; "
        f"recommended_action={issue.recommended_action}"
        for issue in delivery_report.issues
    ]
    return "\n".join(
        [
            "请将风险转化为 P0/P1/P2/P3 任务。",
            "P0 只包含影响当前项目可信度或展示边界的任务。",
            "不要建议继续扩 RAGHub 功能。",
            "不要建议默认启用 hybrid。",
            "不要建议接入 Qdrant、LangGraph、MCP 作为当前 P0。",
            "",
            "任务分层要求：",
            "- P0：当前必须处理，否则影响项目可信度",
            "- P1：近期可以增强，但不阻塞展示",
            "- P2：Roadmap",
            "- P3：面试储备，不进入当前开发",
            "",
            "## RAGHub Eval-100 指标",
            f"- total_queries: {metrics.total_queries}",
            f"- out_of_corpus_rejected: {metrics.out_of_corpus_rejected}",
            f"- answerability_accuracy: {metrics.answerability_accuracy:.4f}",
            f"- exact_source_hit_rate: {metrics.exact_source_hit_rate:.4f}",
            f"- source_group_hit_rate: {metrics.source_group_hit_rate:.4f}",
            f"- vector_average_score: {_optional(metrics.vector_average_score)}",
            f"- hybrid_average_score: {_optional(metrics.hybrid_average_score)}",
            f"- ties: {_optional(metrics.ties)}",
            "",
            "## ProjectPilot 风险登记",
            *issue_lines,
            "",
            "## llm_risk_review 摘要",
            risk_review_summary or "未提供风险复盘摘要。",
            "",
            "请保持所有任务为 Human Confirmation pending，不输出自动执行命令。",
        ]
    )


def build_raghub_task_plan_markdown(
    metrics: RAGHubEvalMetrics,
    delivery_report: RAGHubDeliveryReport,
    provider: str,
    status: ToolCallStatus,
    generated_text: str,
    message: str,
) -> str:
    llm_section = _llm_section_for_status(status, generated_text)
    lines = [
        "# DeepSeek RAGHub Task Plan",
        "",
        "本任务计划基于 RAGHub Eval-100 指标、ProjectPilot 风险登记和 LLM 风险复盘摘要生成，所有任务均需人工确认。",
        "",
        "## P0：当前必须处理，否则影响项目可信度",
        "",
        "- Eval-100 boundary wording：README / 展示材料 / 面试表达必须明确 Eval-100 是项目级 benchmark，不是生产级 benchmark。",
        "- Overclaim guard：避免将 ProjectPilot 描述为自动修复 RAGHub 或生产级治理平台。",
        "",
        "## P1：近期可以增强，但不阻塞展示",
        "",
        "- source competition -> source_type filter：减少 eval/review 文档与直接 source 的竞争。",
        "- source competition -> heading-aware chunk：降低相邻接口字段混淆。",
        "- no-answer guard -> LLM-based answerability judge：作为后续审阅补充，不替代现有规则。",
        "",
        "## P2：Roadmap",
        "",
        "- source competition -> metadata filter：按 source、file_type 或 section 约束候选证据。",
        "- answer-level source selection：在生成答案前选择更直接的证据来源。",
        "- retrieval comparison dashboard：继续保留 exact / acceptable / source_group 分层指标。",
        "",
        "## P3：面试储备，不进入当前开发",
        "",
        "- 准备 source competition 的案例说明。",
        "- 准备 no-answer guard 从 4/12 到 12/12 的复盘表达。",
        "- 准备 hybrid 为什么保持实验模式的取舍说明。",
        "",
        "## Accepted decisions",
        "",
        f"- hybrid_default_recommended = {delivery_report.hybrid_default_recommended}",
        f"- vector_average_score = {_optional(metrics.vector_average_score)}",
        f"- hybrid_average_score = {_optional(metrics.hybrid_average_score)}",
        "- 不默认启用 hybrid，不把 Qdrant、LangGraph、MCP 放入当前 P0。",
        "",
        "## DeepSeek planner output",
        "",
        llm_section,
        "",
        "## Human confirmation",
        "",
        "- 状态：pending",
        f"- LLM Provider：{provider}",
        f"- Tool Call 状态：{status.value}",
        f"- 说明：{message}",
        "",
    ]
    return "\n".join(lines)


def _llm_section_for_status(status: ToolCallStatus, generated_text: str) -> str:
    if status == ToolCallStatus.SUCCESS:
        return generated_text
    if status == ToolCallStatus.PERMISSION_DENIED:
        return "未满足真实 LLM 调用配置，本次仅保留结构化任务计划框架。"
    if status == ToolCallStatus.EMPTY_RESULT:
        return "LLM provider 返回空结果，本次仅保留结构化任务计划框架。"
    return "LLM provider 调用失败，本次仅保留结构化任务计划框架。"


def _message_for_status(
    status: ToolCallStatus,
    provider: str,
    error_message: str = "",
) -> str:
    if status == ToolCallStatus.SUCCESS:
        if provider == "mock":
            return "使用 mock LLM provider 生成 RAGHub 任务计划。"
        return "已完成 RAGHub DeepSeek 任务计划。"
    if status == ToolCallStatus.PERMISSION_DENIED:
        return error_message or "LLM provider 缺少必要配置，已跳过真实调用。"
    if status == ToolCallStatus.EMPTY_RESULT:
        return "LLM provider 返回空结果。"
    return error_message or "LLM 任务计划执行失败。"


def _optional(value: float | int | None) -> str:
    if value is None:
        return "None"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)
