from __future__ import annotations

from pathlib import Path

from projectpilot.analyzers.project_status_analyzer import ProjectStatusAnalyzer
from projectpilot.tools.context_reader import ContextFile, ContextReadResult
from projectpilot.tools.git_reader import GitCommit, GitLogResult


def test_analyzer_detects_core_evidence() -> None:
    report = ProjectStatusAnalyzer().analyze(
        project_name="Fake Project",
        context_result=_context(
            [
                _file("README.md", "readme", "# Fake\nRoadmap and boundary notes."),
                _file("docs/guide.md", "docs", "# Guide"),
                _file("tests/test_app.py", "tests", "def test_app(): assert True"),
                _file("eval/cases.jsonl", "eval", '{"case": 1}'),
            ]
        ),
        git_result=_git(commits=1),
    )

    assert report.delivery_readiness_score == 80
    assert "README 项目定位证据" in report.implemented_capabilities
    assert "docs 文档证据" in report.implemented_capabilities
    assert "tests 测试证据" in report.implemented_capabilities
    assert "eval 评测证据" in report.implemented_capabilities


def test_analyzer_detects_bad_cases_and_problem_notes() -> None:
    report = ProjectStatusAnalyzer().analyze(
        project_name="Fake Project",
        context_result=_context(
            [
                _file("README.md", "readme", "# Fake\nScope."),
                _file("docs/problems_and_solutions.md", "docs", "# Problems"),
                _file("eval/bad_cases.md", "eval", "# Bad Cases"),
            ]
        ),
        git_result=_git(commits=0),
    )

    assert "bad cases 记录" in report.implemented_capabilities
    assert "problems_and_solutions 问题复盘" in report.implemented_capabilities
    assert report.score_breakdown["bad_cases present"] == 10
    assert report.score_breakdown["problems_and_solutions present"] == 10


def test_score_changes_with_evidence_files() -> None:
    analyzer = ProjectStatusAnalyzer()
    minimal = analyzer.analyze(
        project_name="Fake Project",
        context_result=_context([_file("README.md", "readme", "# Fake")]),
        git_result=_git(commits=0),
    )
    fuller = analyzer.analyze(
        project_name="Fake Project",
        context_result=_context(
            [
                _file("README.md", "readme", "# Fake\nRoadmap."),
                _file("docs/guide.md", "docs", "# Guide"),
                _file("tests/test_app.py", "tests", "def test_app(): assert True"),
                _file("eval/bad_cases.md", "eval", "# Bad Cases"),
                _file("docs/problems_and_solutions.md", "docs", "# Problems"),
            ]
        ),
        git_result=_git(commits=2),
    )

    assert minimal.delivery_readiness_score < fuller.delivery_readiness_score


def test_analyzer_handles_non_git_directory() -> None:
    report = ProjectStatusAnalyzer().analyze(
        project_name="Fake Project",
        context_result=_context([_file("README.md", "readme", "# Fake")]),
        git_result=GitLogResult(Path("fake"), [], is_git_repo=False, error="not_git"),
    )

    assert any("git commit 证据" in risk for risk in report.risks)


def _file(path: str, category: str, content: str) -> ContextFile:
    return ContextFile(
        path=path,
        category=category,
        size_bytes=len(content.encode("utf-8")),
        content=content,
    )


def _context(files: list[ContextFile]) -> ContextReadResult:
    return ContextReadResult(project_path=Path("fake"), files=files)


def _git(commits: int) -> GitLogResult:
    return GitLogResult(
        project_path=Path("fake"),
        commits=[
            GitCommit(hash=f"abc123{index}", subject=f"commit {index}")
            for index in range(commits)
        ],
        is_git_repo=commits > 0,
    )
