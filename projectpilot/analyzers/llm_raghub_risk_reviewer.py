"""LLM risk reviewer for the RAGHub Eval-100 delivery case."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from projectpilot.analyzers.eval_metrics_reader import RAGHubEvalMetrics
from projectpilot.analyzers.raghub_delivery_analyzer import RAGHubDeliveryReport
from projectpilot.feedback.human_feedback import HumanFeedbackStatus
from projectpilot.llm.base import LLMConfigurationError, LLMProviderError
from projectpilot.llm.client_factory import get_llm_client, get_llm_provider
from projectpilot.schemas.tool_schema import ToolCallStatus


@dataclass(frozen=True)
class LLMRAGHubRiskReviewResult:
    provider: str
    output_path: Path
    status: ToolCallStatus
    message: str
    prompt: str
    review_text: str
    confirmation_status: HumanFeedbackStatus = HumanFeedbackStatus.PENDING


class LLMRAGHubRiskReviewer:
    """Review RAGHub risks from structured ProjectPilot evidence only."""

    def review(
        self,
        metrics: RAGHubEvalMetrics,
        delivery_report: RAGHubDeliveryReport,
        output_path: str | Path = "outputs/raghub_eval100/llm_risk_review.md",
        provider: str | None = None,
    ) -> LLMRAGHubRiskReviewResult:
        selected_provider = provider or get_llm_provider()
        prompt = build_raghub_risk_review_prompt(metrics, delivery_report)
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
        review_text = build_raghub_risk_review_markdown(
            metrics=metrics,
            delivery_report=delivery_report,
            provider=selected_provider,
            status=status,
            generated_text=generated_text,
            message=message,
        )

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(review_text, encoding="utf-8")
        return LLMRAGHubRiskReviewResult(
            provider=selected_provider,
            output_path=path,
            status=status,
            message=message,
            prompt=prompt,
            review_text=review_text,
        )


def build_raghub_risk_review_prompt(
    metrics: RAGHubEvalMetrics,
    delivery_report: RAGHubDeliveryReport,
) -> str:
    issue_lines = [
        f"- {issue.issue_name}: status={issue.status}; evidence={issue.evidence}; "
        f"reason={issue.reason}; recommended_action={issue.recommended_action}"
        for issue in delivery_report.issues
    ]
    return "\n".join(
        [
            "你只能基于给定的 RAGHub Eval-100 指标和 ProjectPilot 风险登记进行分析。",
            "不要编造不存在的指标。",
            "不要声称项目是生产级系统。",
            "不要声称 no-answer 已经解决所有幻觉或安全问题。",
            "不要建议自动修改或自动提交代码。",
            "",
            "请输出中文 Markdown，至少包含以下小节：",
            "1. 风险总览",
            "2. no-answer 风险为什么可以标记为 resolved",
            "3. source competition 为什么仍然 open",
            "4. hybrid 为什么不建议默认启用",
            "5. Eval-100 为什么不是生产 benchmark",
            "6. 后续建议",
            "7. 不能夸大的边界",
            "",
            "## RAGHub Eval-100 指标",
            f"- total_queries: {metrics.total_queries}",
            f"- in_corpus_count: {metrics.in_corpus_count}",
            f"- out_of_corpus_count: {metrics.out_of_corpus_count}",
            f"- answerability_accuracy: {metrics.answerability_accuracy:.4f}",
            f"- expected_answerable_accept_rate: {metrics.expected_answerable_accept_rate:.4f}",
            f"- expected_unanswerable_reject_rate: {metrics.expected_unanswerable_reject_rate:.4f}",
            f"- out_of_corpus_rejected: {metrics.out_of_corpus_rejected}",
            f"- exact_source_hit_rate: {metrics.exact_source_hit_rate:.4f}",
            f"- acceptable_source_hit_rate: {metrics.acceptable_source_hit_rate:.4f}",
            f"- source_group_hit_rate: {metrics.source_group_hit_rate:.4f}",
            f"- keyword_hit_rate: {metrics.keyword_hit_rate:.4f}",
            f"- vector_average_score: {_optional(metrics.vector_average_score)}",
            f"- hybrid_average_score: {_optional(metrics.hybrid_average_score)}",
            f"- vector_wins: {_optional(metrics.vector_wins)}",
            f"- hybrid_wins: {_optional(metrics.hybrid_wins)}",
            f"- ties: {_optional(metrics.ties)}",
            "",
            "## ProjectPilot 风险登记",
            *issue_lines,
            "",
            "请保持结论为人工确认 pending，不输出自动执行命令。",
        ]
    )


def build_raghub_risk_review_markdown(
    metrics: RAGHubEvalMetrics,
    delivery_report: RAGHubDeliveryReport,
    provider: str,
    status: ToolCallStatus,
    generated_text: str,
    message: str,
) -> str:
    llm_section = _llm_section_for_status(status, generated_text)
    issue_statuses = {
        issue.issue_name: issue.status for issue in delivery_report.issues
    }
    lines = [
        "# DeepSeek RAGHub Risk Review",
        "",
        "本报告基于 ProjectPilot 已解析出的 RAGHub Eval-100 指标和风险登记生成，仅供人工审查。",
        "",
        "## 1. 风险总览",
        "",
        f"- no_answer_risk: {issue_statuses.get('no_answer_risk')}",
        f"- source_competition: {issue_statuses.get('source_competition')}",
        f"- hybrid_default_decision: {issue_statuses.get('hybrid_default_decision')}",
        f"- eval_100_scope: {issue_statuses.get('eval_100_scope')}",
        f"- production_readiness: {issue_statuses.get('production_readiness')}",
        "",
        "## 2. no-answer 风险为什么可以标记为 resolved",
        "",
        f"- out_of_corpus_rejected = {metrics.out_of_corpus_rejected}",
        f"- expected_unanswerable_reject_rate = {metrics.expected_unanswerable_reject_rate:.4f}",
        "- 该结论只覆盖 Eval-100 中的 out-of-corpus 样本，不代表所有幻觉或安全问题都已解决。",
        "",
        "## 3. source competition 为什么仍然 open",
        "",
        f"- exact_source_hit_rate = {metrics.exact_source_hit_rate:.4f}",
        f"- source_group_hit_rate = {metrics.source_group_hit_rate:.4f}",
        "- source_group 明显高于 exact source，说明系统常能命中相关证据组，但不一定命中最直接文件。",
        "",
        "## 4. hybrid 为什么不建议默认启用",
        "",
        f"- vector_average_score = {_optional(metrics.vector_average_score)}",
        f"- hybrid_average_score = {_optional(metrics.hybrid_average_score)}",
        f"- vector_wins / hybrid_wins / ties = {metrics.vector_wins} / {metrics.hybrid_wins} / {metrics.ties}",
        "- hybrid 收益较小且多数 case 持平，因此保留实验模式，不默认替换 vector。",
        "",
        "## 5. Eval-100 为什么不是生产 benchmark",
        "",
        f"- Eval-100 覆盖 {metrics.total_queries} 条项目级 query，其中 in_corpus={metrics.in_corpus_count}，out_of_corpus={metrics.out_of_corpus_count}。",
        "- 它证明当前项目评测链路和边界表达更完整，不等同于生产级安全、可用性或治理审计。",
        "",
        "## 6. DeepSeek 语义复盘",
        "",
        llm_section,
        "",
        "## 7. 后续建议",
        "",
        "- 将 source competition 拆成 source_type filter、heading-aware chunk、metadata filter 和 answer-level source selection 任务。",
        "- 为 no-answer guard 追加 LLM-based answerability judge，但不把它表述为生产级安全系统。",
        "- 继续把 hybrid 保持为实验 provider。",
        "",
        "## 8. 不能夸大的边界",
        "",
        "- 不声称 ProjectPilot 自动修复 RAGHub。",
        "- 不声称 RAGHub 是生产级系统。",
        "- 不声称 no-answer 已经解决所有幻觉或安全问题。",
        "- 不输出自动修改、自动提交或自动部署建议。",
        "",
        "## 9. 人工确认状态",
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
        return "未满足真实 LLM 调用配置，本次仅保留结构化风险复盘框架。"
    if status == ToolCallStatus.EMPTY_RESULT:
        return "LLM provider 返回空结果，本次仅保留结构化风险复盘框架。"
    return "LLM provider 调用失败，本次仅保留结构化风险复盘框架。"


def _message_for_status(
    status: ToolCallStatus,
    provider: str,
    error_message: str = "",
) -> str:
    if status == ToolCallStatus.SUCCESS:
        if provider == "mock":
            return "使用 mock LLM provider 生成 RAGHub 风险复盘。"
        return "已完成 RAGHub DeepSeek 风险复盘。"
    if status == ToolCallStatus.PERMISSION_DENIED:
        return error_message or "LLM provider 缺少必要配置，已跳过真实调用。"
    if status == ToolCallStatus.EMPTY_RESULT:
        return "LLM provider 返回空结果。"
    return error_message or "LLM 风险复盘执行失败。"


def _optional(value: float | int | None) -> str:
    if value is None:
        return "None"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)
