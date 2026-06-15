from __future__ import annotations

from pathlib import Path

from projectpilot.analyzers.commit_advisor import CommitAdvisor
from projectpilot.analyzers.project_status_analyzer import ProjectStatusAnalyzer
from projectpilot.feedback.human_feedback import HumanFeedbackStatus
from projectpilot.tools.context_reader import ContextFile, ContextReadResult
from projectpilot.tools.git_reader import GitCommit, GitLogResult


def test_commit_advisor_generates_draft_without_git_side_effects() -> None:
    context = ContextReadResult(
        project_path=Path("fake"),
        files=[
            ContextFile(
                path="README.md",
                category="readme",
                size_bytes=12,
                content="# Fake\nRoadmap",
            )
        ],
    )
    git = GitLogResult(
        Path("fake"),
        [GitCommit(hash="abc123", subject="docs: update readme")],
        is_git_repo=True,
    )
    status_report = ProjectStatusAnalyzer().analyze("Fake", context, git)

    advice = CommitAdvisor().advise("Fake", status_report, git)

    assert advice.confirmation_status is HumanFeedbackStatus.PENDING
    assert advice.recommended_message
    assert "git add" in " ".join(advice.not_recommended)
    assert advice.recent_commit_summary == ["abc123 docs: update readme"]
