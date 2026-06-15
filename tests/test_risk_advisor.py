from __future__ import annotations

from pathlib import Path

from projectpilot.analyzers.project_status_analyzer import ProjectStatusAnalyzer
from projectpilot.analyzers.risk_advisor import RiskAdvisor
from projectpilot.tools.context_reader import ContextFile, ContextReadResult
from projectpilot.tools.git_reader import GitLogResult


def test_risk_advisor_classifies_risks() -> None:
    context = ContextReadResult(
        project_path=Path("fake"),
        files=[
            ContextFile(
                path="README.md",
                category="readme",
                size_bytes=12,
                content="# Fake",
            )
        ],
    )
    git = GitLogResult(Path("fake"), commits=[], is_git_repo=False)
    status_report = ProjectStatusAnalyzer().analyze("Fake", context, git)

    advice = RiskAdvisor().advise(status_report, context, git)

    assert advice.p0
    assert advice.p1
    assert advice.p2
    assert advice.interview_risks
    assert any("tests" in item or "eval" in item for item in advice.p0)
