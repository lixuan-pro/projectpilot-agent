"""LLM-assisted interview case writer for the RAGHub Eval-100 case."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from projectpilot.analyzers.eval_metrics_reader import RAGHubEvalMetrics
from projectpilot.analyzers.raghub_delivery_analyzer import RAGHubDeliveryReport
from projectpilot.feedback.human_feedback import HumanFeedbackStatus
from projectpilot.llm.base import LLMConfigurationError, LLMProviderError
from projectpilot.llm.client_factory import get_llm_client, get_llm_provider
from projectpilot.schemas.tool_schema import ToolCallStatus


MAX_ADVISOR_CONTEXT_CHARS = 3500


@dataclass(frozen=True)
class LLMInterviewAssetResult:
    provider: str
    output_path: Path
    status: ToolCallStatus
    message: str
    prompt: str
    asset_text: str
    confirmation_status: HumanFeedbackStatus = HumanFeedbackStatus.PENDING


class LLMInterviewAssetWriter:
    """Generate interview-ready case cards from structured RAGHub evidence."""

    def write(
        self,
        metrics: RAGHubEvalMetrics,
        delivery_report: RAGHubDeliveryReport,
        risk_review_summary: str = "",
        task_plan_summary: str = "",
        output_path: str | Path = "outputs/raghub_eval100/interview_case_cards.md",
        provider: str | None = None,
    ) -> LLMInterviewAssetResult:
        selected_provider = provider or get_llm_provider()
        prompt = build_interview_asset_prompt(
            metrics=metrics,
            delivery_report=delivery_report,
            risk_review_summary=risk_review_summary[:MAX_ADVISOR_CONTEXT_CHARS],
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
            error_message = "LLM provider returned an empty interview asset draft."

        message = _message_for_status(status, selected_provider, error_message)
        asset_text = build_interview_asset_markdown(
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
        return LLMInterviewAssetResult(
            provider=selected_provider,
            output_path=path,
            status=status,
            message=message,
            prompt=prompt,
            asset_text=asset_text,
        )


def build_interview_asset_prompt(
    metrics: RAGHubEvalMetrics,
    delivery_report: RAGHubDeliveryReport,
    risk_review_summary: str,
    task_plan_summary: str,
) -> str:
    issue_lines = [
        f"- {issue.issue_name}: status={issue.status}; evidence={issue.evidence}; "
        f"recommended_action={issue.recommended_action}"
        for issue in delivery_report.issues
    ]
    return "\n".join(
        [
            "你是面试案例素材助手，只能基于给定 RAGHub Eval-100 指标和 ProjectPilot 风险登记生成中文素材。",
            "不要编造不存在指标；不要声称 RAGHub 是生产级平台；不要声称彻底解决幻觉。",
            "不要声称 hybrid 已经全面胜过 vector；不要建议自动修改或自动提交 RAGHub。",
            "输出应围绕 Eval-100、source competition、no-answer、hybrid not default、project-level benchmark。",
            "",
            "必须生成四个 case：",
            "1. source competition and hybrid retrieval experiment",
            "2. Eval-100 exposed no-answer misses and fix",
            "3. why hybrid is not default",
            "4. how ProjectPilot analyzes RAGHub delivery evidence",
            "",
            "每个 case 必须包含：问题背景、现象指标、定位过程、解决或决策、当前边界、30 秒回答、60 秒回答、不能夸大的点。",
            "",
            "## Metrics",
            f"- total_queries: {metrics.total_queries}",
            f"- in_corpus_count: {metrics.in_corpus_count}",
            f"- out_of_corpus_count: {metrics.out_of_corpus_count}",
            f"- answerability_accuracy: {metrics.answerability_accuracy:.4f}",
            f"- out_of_corpus_rejected: {metrics.out_of_corpus_rejected}",
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
            "## Risk review summary",
            risk_review_summary or "No risk review summary was provided.",
            "",
            "## Task plan summary",
            task_plan_summary or "No task plan summary was provided.",
            "",
            "保持 human_confirmation_status=pending，不输出自动执行命令。",
        ]
    )


def build_interview_asset_markdown(
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
        "# RAGHub Interview Case Cards",
        "",
        "本素材由 ProjectPilot 基于 Eval-100 指标、风险登记和 LLM Advisor 草稿生成，只用于面试表达准备。",
        "所有表述保持 human_confirmation_status=pending，不自动修改 RAGHub，不自动提交代码。",
        "",
        _case_source_competition(metrics, issue_status),
        _case_no_answer(metrics, issue_status),
        _case_hybrid_default(metrics, delivery_report),
        _case_projectpilot_evidence(metrics, issue_status),
        "## LLM Draft Note",
        "",
        _llm_section_for_status(status, generated_text),
        "",
        "## Human Confirmation",
        "",
        "- status: pending",
        f"- LLM Provider: {provider}",
        f"- Tool Call Status: {status.value}",
        f"- message: {message}",
        "",
    ]
    return "\n".join(lines)


def _case_source_competition(
    metrics: RAGHubEvalMetrics,
    issue_status: dict[str, str],
) -> str:
    return "\n".join(
        [
            "## Case 1: source competition and hybrid retrieval experiment",
            "",
            "### 问题背景",
            "",
            "RAGHub 在 Eval-100 中需要回答项目内问题，但检索结果可能命中同一 source group 下的相邻或相关文档，而不是最直接的 source。",
            "",
            "### 现象指标",
            "",
            f"- exact_source_hit_rate = {metrics.exact_source_hit_rate:.4f}",
            f"- acceptable_source_hit_rate = {metrics.acceptable_source_hit_rate:.4f}",
            f"- source_group_hit_rate = {metrics.source_group_hit_rate:.4f}",
            f"- source_competition status = {issue_status.get('source_competition')}",
            "",
            "### 定位过程",
            "",
            "ProjectPilot 将 exact source、acceptable source 和 source group 分开看，发现系统常能找到相关证据组，但精确 source 竞争仍然存在。",
            "",
            "### 解决或决策",
            "",
            "把 source_type filter、heading-aware chunk、metadata filter、answer-level source selection 放入后续任务；hybrid 只保留为实验模式。",
            "",
            "### 当前边界",
            "",
            "Eval-100 证明了 source competition 的证据链，不代表检索质量已经达到生产级稳定性。",
            "",
            "### 30 秒回答",
            "",
            "我没有只看一个命中率，而是把 exact、acceptable、source group 分层。结果显示 RAGHub 能找到相关证据组，但最直接 source 仍会竞争，所以后续任务聚焦 source filter 和 chunk 结构优化。",
            "",
            "### 60 秒回答",
            "",
            "这个问题不是简单说检索失败。Eval-100 里 exact_source_hit_rate 是 "
            f"{metrics.exact_source_hit_rate:.4f}，source_group_hit_rate 是 {metrics.source_group_hit_rate:.4f}。"
            "这说明系统常命中同一证据组，但可能不是最直接文件。我的处理是把问题拆成 source_type filter、heading-aware chunk、metadata filter 和 answer-level source selection，而不是把 hybrid 直接设成默认。",
            "",
            "### 不能夸大的点",
            "",
            "- 不能说 hybrid 已经全面优于 vector。",
            "- 不能说 source competition 已经彻底解决。",
            "- 不能说 Eval-100 等同生产级 benchmark。",
            "",
        ]
    )


def _case_no_answer(
    metrics: RAGHubEvalMetrics,
    issue_status: dict[str, str],
) -> str:
    return "\n".join(
        [
            "## Case 2: Eval-100 exposed no-answer misses and fix",
            "",
            "### 问题背景",
            "",
            "RAG 问答需要识别项目语料外的问题，否则系统容易用相近材料生成看似合理但无依据的回答。",
            "",
            "### 现象指标",
            "",
            f"- out_of_corpus_count = {metrics.out_of_corpus_count}",
            f"- out_of_corpus_rejected = {metrics.out_of_corpus_rejected}",
            f"- expected_unanswerable_reject_rate = {metrics.expected_unanswerable_reject_rate:.4f}",
            f"- no_answer_risk status = {issue_status.get('no_answer_risk')}",
            "",
            "### 定位过程",
            "",
            "ProjectPilot 从 Eval-100 的 answerability 指标读取 no-answer 表现，并把 out-of-corpus 样本单独登记为风险证据。",
            "",
            "### 解决或决策",
            "",
            "当前 guard 对 Eval-100 的 out-of-corpus 样本达到 12/12 拒答，作为项目级证据记录；后续可以补 LLM-based answerability judge。",
            "",
            "### 当前边界",
            "",
            "这个结果只覆盖 Eval-100 的 12 条 out-of-corpus 样本，不代表彻底解决幻觉或安全问题。",
            "",
            "### 30 秒回答",
            "",
            "我把 no-answer 单独做成 Eval-100 指标。当前 12 条语料外问题全部拒答，所以这个项目级风险可以标记为 resolved，但我不会把它包装成彻底解决幻觉。",
            "",
            "### 60 秒回答",
            "",
            "最初 RAG 系统容易对语料外问题给出不可靠回答，所以我在 Eval-100 里保留了 out-of-corpus 类别。当前结果是 "
            f"{metrics.out_of_corpus_rejected}，expected_unanswerable_reject_rate={metrics.expected_unanswerable_reject_rate:.4f}。"
            "ProjectPilot 会把这个证据登记成 no_answer_risk resolved，同时保留边界：它是项目级样本集上的表现，不是生产安全结论。",
            "",
            "### 不能夸大的点",
            "",
            "- 不能说完全解决幻觉。",
            "- 不能说所有语料外问题都能安全处理。",
            "- 不能把 12/12 扩大成生产级安全审计结论。",
            "",
        ]
    )


def _case_hybrid_default(
    metrics: RAGHubEvalMetrics,
    delivery_report: RAGHubDeliveryReport,
) -> str:
    return "\n".join(
        [
            "## Case 3: why hybrid is not default",
            "",
            "### 问题背景",
            "",
            "RAGHub 做了 vector 与 hybrid 的对比，但是否切换默认检索模式需要看收益和稳定性，而不是只看单点样例。",
            "",
            "### 现象指标",
            "",
            f"- vector_average_score = {_optional(metrics.vector_average_score)}",
            f"- hybrid_average_score = {_optional(metrics.hybrid_average_score)}",
            f"- vector_wins / hybrid_wins / ties = {metrics.vector_wins} / {metrics.hybrid_wins} / {metrics.ties}",
            f"- hybrid_default_recommended = {delivery_report.hybrid_default_recommended}",
            "",
            "### 定位过程",
            "",
            "ProjectPilot 把 A/B 分数和 win/tie 分布一起看，避免用少量 hybrid 优势样例替代整体决策。",
            "",
            "### 解决或决策",
            "",
            "当前保留 vector 默认路径，hybrid 作为实验模式和后续对比项，不把它作为默认替换方案。",
            "",
            "### 当前边界",
            "",
            "hybrid 有实验价值，但目前证据不足以说明它全面优于 vector。",
            "",
            "### 30 秒回答",
            "",
            "我没有因为 hybrid 分数略高就切默认。A/B 结果里 tie 很多，hybrid 的优势不够稳定，所以我保留 vector 默认，把 hybrid 放在实验和 roadmap 里。",
            "",
            "### 60 秒回答",
            "",
            "切默认模式需要看收益、稳定性和回归风险。当前 vector_average_score="
            f"{_optional(metrics.vector_average_score)}，hybrid_average_score={_optional(metrics.hybrid_average_score)}，"
            f"vector/hybrid/tie 是 {metrics.vector_wins}/{metrics.hybrid_wins}/{metrics.ties}。"
            "这个结果更适合说明 hybrid 值得继续实验，而不是已经可以全面替换 vector。",
            "",
            "### 不能夸大的点",
            "",
            "- 不能说 hybrid 全面胜过 vector。",
            "- 不能说已经完成默认检索策略切换。",
            "- 不能把实验模式描述成生产默认模式。",
            "",
        ]
    )


def _case_projectpilot_evidence(
    metrics: RAGHubEvalMetrics,
    issue_status: dict[str, str],
) -> str:
    return "\n".join(
        [
            "## Case 4: how ProjectPilot analyzes RAGHub delivery evidence",
            "",
            "### 问题背景",
            "",
            "RAGHub 有评测结果、bad cases 和实验对比，但面试或交付时需要把它们变成可复核的风险登记和任务计划。",
            "",
            "### 现象指标",
            "",
            f"- total_queries = {metrics.total_queries}",
            f"- eval_100_scope status = {issue_status.get('eval_100_scope')}",
            f"- production_readiness status = {issue_status.get('production_readiness')}",
            "",
            "### 定位过程",
            "",
            "ProjectPilot 先确定性读取 JSON 指标，再用规则分析风险，最后把 LLM 只作为 Advisor 生成复盘和表达素材。",
            "",
            "### 解决或决策",
            "",
            "输出 eval_metrics_summary、risk_register、issue_to_task_map、DeepSeek advisor 文档和本面试素材，但全部保持人工确认。",
            "",
            "### 当前边界",
            "",
            "ProjectPilot 不是生产级治理平台，不执行工具链修改，不自动提交 RAGHub。",
            "",
            "### 30 秒回答",
            "",
            "ProjectPilot 的价值不是替我改 RAGHub，而是把 Eval-100 的证据整理成风险登记、任务计划和面试素材，并保留 pending 人工确认。",
            "",
            "### 60 秒回答",
            "",
            "我把 ProjectPilot 设计成 workflow-first 的交付分析助手。它读取 RAGHub 的 Eval-100 JSON 和报告，确定性生成指标摘要和风险登记；LLM 只用于 advisor 和表达素材，不直接执行工具、不修改 RAGHub、不自动提交。这样面试时可以讲清楚证据、决策和边界。",
            "",
            "### 不能夸大的点",
            "",
            "- 不能说 ProjectPilot 自动修复 RAGHub。",
            "- 不能说 ProjectPilot 是企业级治理平台。",
            "- 不能说 LLM 输出无需人工确认。",
            "",
        ]
    )


def _llm_section_for_status(status: ToolCallStatus, generated_text: str) -> str:
    if status == ToolCallStatus.SUCCESS:
        return generated_text
    if status == ToolCallStatus.PERMISSION_DENIED:
        return "未满足真实 LLM 调用配置，本次仅保留确定性面试案例结构。"
    if status == ToolCallStatus.EMPTY_RESULT:
        return "LLM provider 返回空结果，本次仅保留确定性面试案例结构。"
    return "LLM provider 调用失败，本次仅保留确定性面试案例结构。"


def _message_for_status(
    status: ToolCallStatus,
    provider: str,
    error_message: str = "",
) -> str:
    if status == ToolCallStatus.SUCCESS:
        if provider == "mock":
            return "使用 mock LLM provider 生成 RAGHub interview assets。"
        return "已完成 RAGHub DeepSeek interview asset draft。"
    if status == ToolCallStatus.PERMISSION_DENIED:
        return error_message or "LLM provider 缺少必要配置，已跳过真实调用。"
    if status == ToolCallStatus.EMPTY_RESULT:
        return "LLM provider 返回空结果。"
    return error_message or "LLM interview asset writer 执行失败。"


def _optional(value: float | int | None) -> str:
    if value is None:
        return "None"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)
