from __future__ import annotations

from pathlib import Path

from projectpilot.analyzers.project_status_analyzer import (
    ProjectStatusAnalyzer,
    ProjectStatusReport,
)
from projectpilot.tools.context_reader import ContextFile, ContextReadResult
from projectpilot.tools.git_reader import GitCommit, GitLogResult
from projectpilot.workflow.report_writer import (
    write_next_tasks,
    write_project_status_report,
)


def test_report_writer_generates_markdown_files(tmp_path) -> None:
    report = _report()
    status_path = write_project_status_report(
        report,
        tmp_path / "project_status_report.md",
    )
    tasks_path = write_next_tasks(report, tmp_path / "next_tasks.md")

    assert status_path.exists()
    assert tasks_path.exists()

    status = status_path.read_text(encoding="utf-8")
    tasks = tasks_path.read_text(encoding="utf-8")
    assert "# 项目状态报告" in status
    assert "## 7. 交付就绪评分" in status
    assert "规则化证据完整度检查" in status
    assert "不代表生产级可用" in status
    assert "# 下一步任务" in tasks
    assert "## 面试准备" in tasks


def _report() -> ProjectStatusReport:
    context = ContextReadResult(
        project_path=Path("fake"),
        files=[
            ContextFile(
                path="README.md",
                category="readme",
                size_bytes=16,
                content="# Fake\nRoadmap",
            ),
            ContextFile(
                path="tests/test_app.py",
                category="tests",
                size_bytes=24,
                content="def test_app(): assert True",
            ),
        ],
    )
    git = GitLogResult(
        Path("fake"),
        [GitCommit(hash="abc123", subject="initial")],
        is_git_repo=True,
    )
    return ProjectStatusAnalyzer().analyze("Fake Project", context, git)
