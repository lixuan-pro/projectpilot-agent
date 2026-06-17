"""Optional LLM semantic review advisor based on existing reports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from projectpilot.feedback.human_feedback import HumanFeedbackStatus
from projectpilot.llm.base import LLMConfigurationError, LLMProviderError
from projectpilot.llm.client_factory import get_llm_client, get_llm_provider
from projectpilot.schemas.tool_schema import ToolCallStatus


MAX_REPORT_CHARS = 3000


@dataclass(frozen=True)
class LLMReviewResult:
    provider: str
    output_path: Path
    status: ToolCallStatus
    message: str
    review_text: str
    confirmation_status: HumanFeedbackStatus = HumanFeedbackStatus.PENDING


class LLMReviewAdvisor:
    """Generate optional semantic review without reading the target repository."""

    def review(
        self,
        report_paths: dict[str, str | Path],
        output_path: str | Path = "outputs/llm_review.md",
        provider: str | None = None,
    ) -> LLMReviewResult:
        selected_provider = provider or get_llm_provider()
        summaries = _read_report_summaries(report_paths)
        prompt = build_llm_review_prompt(summaries)
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
        review_text = build_llm_review_markdown(
            provider=selected_provider,
            status=status,
            generated_text=generated_text,
            message=message,
            summaries=summaries,
            confirmation_status=HumanFeedbackStatus.PENDING,
        )

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(review_text, encoding="utf-8")
        return LLMReviewResult(
            provider=selected_provider,
            output_path=path,
            status=status,
            message=message,
            review_text=review_text,
        )


def build_llm_review_prompt(summaries: dict[str, str]) -> str:
    sections = [
        "请基于以下 ProjectPilot 已有分析报告摘要，做中文语义审阅。",
        "不要要求自动修改代码，不要要求自动提交，不要把项目包装成生产级平台。",
        "请关注项目状态复核、风险补充、README/展示材料、面试表达和不应过度包装的地方。",
        "",
    ]
    for name, content in summaries.items():
        sections.extend([f"## {name}", content or "未读取到摘要。", ""])
    return "\n".join(sections)


def build_llm_review_markdown(
    provider: str,
    status: ToolCallStatus,
    generated_text: str,
    message: str,
    summaries: dict[str, str],
    confirmation_status: HumanFeedbackStatus = HumanFeedbackStatus.PENDING,
) -> str:
    status_note = {
        ToolCallStatus.SUCCESS: generated_text,
        ToolCallStatus.EMPTY_RESULT: "LLM provider 返回空结果，本次仅保留固定审阅框架。",
        ToolCallStatus.PERMISSION_DENIED: "未满足真实 LLM 调用配置，本次已友好跳过真实调用。",
        ToolCallStatus.INTERNAL_ERROR: "LLM provider 调用失败，本次已保留固定审阅框架。",
    }.get(status, generated_text)

    source_lines = [f"- {name}" for name in summaries]
    lines = [
        "# LLM 语义审阅报告",
        "",
        "本报告由可选 LLM Review Advisor 基于已有分析结果生成，仅供人工审查，不会自动修改代码或提交。",
        "",
        "## 1. 审阅目标",
        "",
        "- 基于 ProjectPilot 已经生成的结构化报告做语义审阅。",
        "- 不直接读取整个目标仓库，不替代 rule-based analyzer。",
        "- 输出建议保持 Human Confirmation pending。",
        "",
        "## 2. 项目状态复核",
        "",
        status_note,
        "",
        "## 3. 风险补充建议",
        "",
        "- 继续区分展示材料完整度和生产级 readiness。",
        "- 对被截断文件或未读取证据保持谨慎表述。",
        "- 如使用真实 LLM provider，需要确认 API key 不进入日志或报告。",
        "",
        "## 4. README / 展示材料建议",
        "",
        "- 优先补充能解释项目定位、当前范围、非目标和运行方式的内容。",
        "- 保留中文为主、关键技术词英文的求职展示风格。",
        "- 不要把建议输出包装成自动执行能力。",
        "",
        "## 5. 面试表达建议",
        "",
        "- 说明 ProjectPilot 是 workflow-first Agent 原型，不是自动项目经理。",
        "- 强调 Tool Call Log、Run Log 和 Human Confirmation 如何限制 Agent 越权。",
        "- 说明交付证据完整度评分是规则化 evidence checklist，不代表项目质量满分或生产级可用。",
        "",
        "## 6. 不应过度包装的地方",
        "",
        "- 不应宣称已经具备企业级治理、权限、审计或部署能力。",
        "- 不应宣称 LLM 可以直接接管项目分析或执行写操作。",
        "- 不应把 mock provider 的输出当作真实 LLM 结论。",
        "",
        "## 7. 人工确认状态",
        "",
        f"- 状态：{confirmation_status.value}",
        f"- LLM Provider：{provider}",
        f"- Tool Call 状态：{status.value}",
        f"- 说明：{message}",
        "",
        "## 8. 审阅输入来源",
        "",
        *source_lines,
        "",
    ]
    return "\n".join(lines)


def _read_report_summaries(report_paths: dict[str, str | Path]) -> dict[str, str]:
    summaries: dict[str, str] = {}
    for name, raw_path in report_paths.items():
        path = Path(raw_path)
        if not path.exists():
            summaries[name] = "报告文件不存在。"
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        summaries[name] = text[:MAX_REPORT_CHARS]
    return summaries


def _message_for_status(
    status: ToolCallStatus,
    provider: str,
    error_message: str = "",
) -> str:
    if status == ToolCallStatus.SUCCESS:
        if provider == "mock":
            return "使用 mock LLM provider 生成审阅报告。"
        return "已完成基于已有报告的 LLM 语义审阅。"
    if status == ToolCallStatus.PERMISSION_DENIED:
        return error_message or "LLM provider 缺少必要配置，已跳过真实调用。"
    if status == ToolCallStatus.EMPTY_RESULT:
        return "LLM provider 返回空结果。"
    return error_message or "LLM 语义审阅执行失败。"
