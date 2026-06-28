"""LLM-assisted resume asset writer for the RAGHub Eval-100 case."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from projectpilot.analyzers.eval_metrics_reader import RAGHubEvalMetrics
from projectpilot.analyzers.raghub_delivery_analyzer import RAGHubDeliveryReport
from projectpilot.feedback.human_feedback import HumanFeedbackStatus
from projectpilot.llm.base import LLMConfigurationError, LLMProviderError
from projectpilot.llm.client_factory import get_llm_client, get_llm_provider
from projectpilot.schemas.tool_schema import ToolCallStatus


MAX_ADVISOR_CONTEXT_CHARS = 3000


@dataclass(frozen=True)
class LLMResumeAssetResult:
    provider: str
    output_path: Path
    status: ToolCallStatus
    message: str
    prompt: str
    asset_text: str
    confirmation_status: HumanFeedbackStatus = HumanFeedbackStatus.PENDING


class LLMResumeAssetWriter:
    """Generate bounded resume bullets from RAGHub and ProjectPilot evidence."""

    def write(
        self,
        metrics: RAGHubEvalMetrics,
        delivery_report: RAGHubDeliveryReport,
        interview_assets_summary: str = "",
        task_plan_summary: str = "",
        output_path: str | Path = "outputs/raghub_eval100/resume_assets.md",
        provider: str | None = None,
    ) -> LLMResumeAssetResult:
        selected_provider = provider or get_llm_provider()
        prompt = build_resume_asset_prompt(
            metrics=metrics,
            delivery_report=delivery_report,
            interview_assets_summary=interview_assets_summary[:MAX_ADVISOR_CONTEXT_CHARS],
            task_plan_summary=task_plan_summary[:MAX_ADVISOR_CONTEXT_CHARS],
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
            error_message = "LLM provider returned an empty resume asset draft."

        message = _message_for_status(status, selected_provider, error_message)
        asset_text = build_resume_asset_markdown(
            metrics=metrics,
            delivery_report=delivery_report,
            provider=selected_provider,
            status=status,
            generated_text=generated_text,
            message=message,
        )

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(asset_text, encoding="utf-8")
        return LLMResumeAssetResult(
            provider=selected_provider,
            output_path=path,
            status=status,
            message=message,
            prompt=prompt,
            asset_text=asset_text,
        )


def build_resume_asset_prompt(
    metrics: RAGHubEvalMetrics,
    delivery_report: RAGHubDeliveryReport,
    interview_assets_summary: str,
    task_plan_summary: str,
) -> str:
    issue_lines = [
        f"- {issue.issue_name}: status={issue.status}; evidence={issue.evidence}"
        for issue in delivery_report.issues
    ]
    return "\n".join(
        [
            "你是简历素材助手，只能基于给定 RAGHub Eval-100 指标和 ProjectPilot 风险登记生成中文简历素材。",
            "不要编造指标；不要写生产级、企业级、准确率 99%、完全解决幻觉、hybrid 全面优于 vector。",
            "不要建议自动修改或自动提交 RAGHub。输出必须保留边界和人工确认。",
            "",
            "必须输出：RAGHub bullets 3 条；ProjectPilot bullets 3 条；RAGHub + ProjectPilot combo description 1 段；不能放进简历的过度表述清单。",
            "",
            "## Metrics",
            f"- total_queries: {metrics.total_queries}",
            f"- out_of_corpus_rejected: {metrics.out_of_corpus_rejected}",
            f"- answerability_accuracy: {metrics.answerability_accuracy:.4f}",
            f"- exact_source_hit_rate: {metrics.exact_source_hit_rate:.4f}",
            f"- acceptable_source_hit_rate: {metrics.acceptable_source_hit_rate:.4f}",
            f"- source_group_hit_rate: {metrics.source_group_hit_rate:.4f}",
            f"- vector_average_score: {_optional(metrics.vector_average_score)}",
            f"- hybrid_average_score: {_optional(metrics.hybrid_average_score)}",
            f"- vector_wins: {_optional(metrics.vector_wins)}",
            f"- hybrid_wins: {_optional(metrics.hybrid_wins)}",
            f"- ties: {_optional(metrics.ties)}",
            "",
            "## Delivery issues",
            *issue_lines,
            "",
            "## Interview assets summary",
            interview_assets_summary or "No interview asset summary was provided.",
            "",
            "## Task plan summary",
            task_plan_summary or "No task plan summary was provided.",
            "",
            "保持 human_confirmation_status=pending，不输出自动执行命令。",
        ]
    )


def build_resume_asset_markdown(
    metrics: RAGHubEvalMetrics,
    delivery_report: RAGHubDeliveryReport,
    provider: str,
    status: ToolCallStatus,
    generated_text: str,
    message: str,
) -> str:
    issue_status = {
        issue.issue_name: issue.status for issue in delivery_report.issues
    }
    lines = [
        "# RAGHub Resume Assets",
        "",
        "本素材用于把 RAGHub 与 ProjectPilot 的项目证据转换成简历候选表达，所有内容仍需人工确认。",
        "",
        "## RAGHub bullets",
        "",
        "- 设计并维护 RAGHub Eval-100 项目级评测集，覆盖 in-corpus 与 out-of-corpus 问题，跟踪 answerability、source hit、keyword hit 等指标。",
        f"- 将 no-answer 风险纳入评测闭环，在当前 Eval-100 中实现 out_of_corpus_rejected={metrics.out_of_corpus_rejected}，并明确该结论只覆盖项目级样本。",
        f"- 对比 vector 与 hybrid 检索实验，记录 vector/hybrid/tie={metrics.vector_wins}/{metrics.hybrid_wins}/{metrics.ties}，据此保留 vector 默认路径并把 hybrid 放入实验模式。",
        "",
        "## ProjectPilot bullets",
        "",
        "- 构建 ProjectPilot workflow，确定性读取 RAGHub Eval-100 JSON 指标并生成 eval_metrics_summary、risk_register 和 issue_to_task_map。",
        f"- 将 source competition 登记为 {issue_status.get('source_competition')}，把 source_type filter、heading-aware chunk、metadata filter、answer-level source selection 拆成后续任务。",
        "- 接入 LLM Advisor 作为风险复盘、任务计划和表达素材助手，同时保留 tool_call_log、run_log 与 human_confirmation_status=pending。",
        "",
        "## RAGHub + ProjectPilot combo description",
        "",
        "围绕本地 RAG 项目 RAGHub，使用 ProjectPilot 将 Eval-100 评测结果、检索对比和风险登记串成可复核的交付分析 workflow：确定性指标读取负责证据可靠性，DeepSeek Advisor 负责语义复盘和表达辅助，最终输出仍保持人工确认，不自动修改或提交 RAGHub。",
        "",
        "## Overclaims not to put in resume",
        "",
        "- 不写“生产级 RAG 平台”或“企业级治理平台”。",
        "- 不写“完全解决幻觉”或“彻底解决 no-answer 安全问题”。",
        "- 不写“hybrid 全面优于 vector”或“已默认替换 vector”。",
        "- 不写“准确率 99%”来概括整体系统能力；只能描述 Eval-100 的 answerability_accuracy=0.99。",
        "- 不写“ProjectPilot 自动修复 RAGHub”或“自动提交代码”。",
        "- 不写未经证据支持的 source_hit_rate 0.95、hybrid 显著领先、out_of_corpus 超过 12/12 等指标。",
        "",
        "## LLM Draft Note",
        "",
        _llm_section_for_status(status, generated_text),
        "",
        "## Human Confirmation",
        "",
        "- status: pending",
        "- human_confirmation_status: pending",
        f"- LLM Provider: {provider}",
        f"- Tool Call Status: {status.value}",
        f"- message: {message}",
        f"- hybrid_default_recommended: {delivery_report.hybrid_default_recommended}",
        "",
    ]
    return "\n".join(lines)


def _llm_section_for_status(status: ToolCallStatus, generated_text: str) -> str:
    if status == ToolCallStatus.SUCCESS:
        return generated_text
    if status == ToolCallStatus.PERMISSION_DENIED:
        return "未满足真实 LLM 调用配置，本次仅保留确定性简历素材结构。"
    if status == ToolCallStatus.EMPTY_RESULT:
        return "LLM provider 返回空结果，本次仅保留确定性简历素材结构。"
    return "LLM provider 调用失败，本次仅保留确定性简历素材结构。"


def _message_for_status(
    status: ToolCallStatus,
    provider: str,
    error_message: str = "",
) -> str:
    if status == ToolCallStatus.SUCCESS:
        if provider == "mock":
            return "使用 mock LLM provider 生成 RAGHub resume assets。"
        return "已完成 RAGHub DeepSeek resume asset draft。"
    if status == ToolCallStatus.PERMISSION_DENIED:
        return error_message or "LLM provider 缺少必要配置，已跳过真实调用。"
    if status == ToolCallStatus.EMPTY_RESULT:
        return "LLM provider 返回空结果。"
    return error_message or "LLM resume asset writer 执行失败。"


def _optional(value: float | int | None) -> str:
    if value is None:
        return "None"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)
