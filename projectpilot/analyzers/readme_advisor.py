"""README suggestion advisor for ProjectPilot Agent."""

from __future__ import annotations

from dataclasses import dataclass, field

from projectpilot.feedback.human_feedback import HumanFeedbackStatus
from projectpilot.tools.context_reader import ContextFile, ContextReadResult


@dataclass(frozen=True)
class ReadmeAdvice:
    strengths: list[str]
    missing_content: list[str]
    avoid_overpackaging: list[str]
    suggested_changes: list[str]
    confirmation_status: HumanFeedbackStatus = HumanFeedbackStatus.PENDING


class ReadmeAdvisor:
    """Generate README suggestions without editing the target project."""

    def advise(self, context_result: ContextReadResult) -> ReadmeAdvice:
        readme = _root_readme(context_result)
        if readme is None:
            return ReadmeAdvice(
                strengths=[],
                missing_content=[
                    "未检测到根目录 README，建议先补充项目定位、运行方式、当前能力和边界。"
                ],
                avoid_overpackaging=[
                    "不要把项目包装成生产级平台，先说明当前原型阶段和展示范围。"
                ],
                suggested_changes=[
                    "新增根目录 README，覆盖项目定位、运行命令、核心接口、eval 和当前边界。"
                ],
            )

        content = readme.content.lower()
        checks = {
            "项目定位": _contains_any(content, ["项目定位", "定位", "scope", "目标"]),
            "运行方式": _contains_any(content, ["运行", "quickstart", "pytest", "uvicorn", "python"]),
            "API 说明": _contains_any(content, ["/retrieve", "/chat", "api"]),
            "eval 说明": _contains_any(content, ["eval", "评测", "evaluation"]),
            "当前边界": _contains_any(content, ["边界", "不代表", "not", "roadmap", "scope"]),
        }

        strengths = [
            f"README 已包含{label}相关信息。"
            for label, present in checks.items()
            if present
        ]
        missing = [
            f"README 可补充{label}，让项目展示材料更完整。"
            for label, present in checks.items()
            if not present
        ]
        if not missing:
            suggested = [
                "当前 README 证据较完整，建议只做小幅校准，不需要强行重写。",
                "可以继续保持项目定位、运行方式、API、eval 和当前边界的清晰表达。",
            ]
        else:
            suggested = [
                "按缺失项补充 README 小节，优先补齐影响面试可信度的信息。",
                "保持当前项目阶段说明，避免夸大为生产级系统。",
            ]

        return ReadmeAdvice(
            strengths=strengths,
            missing_content=missing,
            avoid_overpackaging=[
                "避免承诺企业级治理、自动部署或生产级稳定性。",
                "避免把 rule-based analyzer 包装成真实 LLM 智能体。",
                "避免把交付证据完整度评分解释成项目质量满分或生产级 readiness。",
            ],
            suggested_changes=suggested,
        )


def _root_readme(context_result: ContextReadResult) -> ContextFile | None:
    for item in context_result.files:
        if item.category == "readme":
            return item
    return None


def _contains_any(content: str, needles: list[str]) -> bool:
    return any(needle.lower() in content for needle in needles)
