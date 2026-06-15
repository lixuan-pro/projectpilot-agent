from __future__ import annotations

from pathlib import Path

from projectpilot.analyzers.readme_advisor import ReadmeAdvisor
from projectpilot.feedback.human_feedback import HumanFeedbackStatus
from projectpilot.tools.context_reader import ContextFile, ContextReadResult


def test_readme_advisor_generates_suggestions() -> None:
    context = ContextReadResult(
        project_path=Path("fake"),
        files=[
            ContextFile(
                path="README.md",
                category="readme",
                size_bytes=20,
                content="# Fake\n项目定位\n运行方式\n/retrieve\n",
            )
        ],
    )

    advice = ReadmeAdvisor().advise(context)

    assert advice.confirmation_status is HumanFeedbackStatus.PENDING
    assert advice.strengths
    assert advice.suggested_changes
    assert any("生产级" in item for item in advice.avoid_overpackaging)


def test_readme_advisor_handles_missing_readme() -> None:
    advice = ReadmeAdvisor().advise(ContextReadResult(Path("fake"), files=[]))

    assert advice.missing_content
    assert "根目录 README" in advice.suggested_changes[0]
