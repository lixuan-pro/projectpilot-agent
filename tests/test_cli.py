from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from projectpilot.logging.run_log import write_run_log


def test_cli_help_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "projectpilot.cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "ProjectPilot Agent CLI" in result.stdout


def test_cli_analyze_generates_context_summary(tmp_path) -> None:
    fake_project = tmp_path / "fake_project"
    (fake_project / "docs").mkdir(parents=True)
    (fake_project / "tests").mkdir()
    (fake_project / "eval").mkdir()
    (fake_project / "README.md").write_text("# Fake Project\n", encoding="utf-8")
    (fake_project / "docs" / "usage.md").write_text("## Usage\n", encoding="utf-8")
    (fake_project / "tests" / "test_fake.py").write_text("def test_fake():\n    assert True\n", encoding="utf-8")
    (fake_project / "eval" / "cases.jsonl").write_text('{"case": 1}\n', encoding="utf-8")

    config_path = tmp_path / "projectpilot.yaml"
    output_dir = tmp_path / "outputs"
    run_logs_dir = tmp_path / "run_logs"
    config_path.write_text(
        "\n".join(
            [
                "project:",
                "  name: Fake Project",
                f"  path: {fake_project}",
                "context:",
                "  max_files: 30",
                "  max_file_size_kb: 20",
                "  include:",
                "    - README.md",
                "    - docs/**/*.md",
                "    - tests/**/*.py",
                "    - eval/**/*.jsonl",
                "git:",
                "  max_commits: 10",
                "outputs:",
                f"  directory: {output_dir}",
                f"  run_logs_directory: {run_logs_dir}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "projectpilot.cli",
            "analyze",
            "--config",
            str(config_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "ProjectPilot analysis completed." in result.stdout
    assert "Target project: Fake Project" in result.stdout
    assert "Files read: 4" in result.stdout
    assert "交付就绪评分：" in result.stdout
    assert "评分类型：规则化证据完整度检查" in result.stdout

    summary_path = output_dir / "context_summary.md"
    status_report_path = output_dir / "project_status_report.md"
    next_tasks_path = output_dir / "next_tasks.md"
    assert summary_path.exists()
    assert status_report_path.exists()
    assert next_tasks_path.exists()
    summary = summary_path.read_text(encoding="utf-8")
    assert "# Project Context Summary" in summary
    assert "## 7. Recent Git Commits" in summary
    assert "# Project Status Report" in status_report_path.read_text(encoding="utf-8")
    assert "# Next Tasks" in next_tasks_path.read_text(encoding="utf-8")


def test_run_log_can_write(tmp_path) -> None:
    log_path = write_run_log(
        run_id="test-run",
        status="success",
        message="test message",
        output_dir=tmp_path,
    )

    payload = json.loads(log_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "test-run"
    assert payload["status"] == "success"
    assert payload["message"] == "test message"


def test_cli_analyze_writes_run_log(tmp_path) -> None:
    fake_project = tmp_path / "fake_project"
    fake_project.mkdir()
    (fake_project / "README.md").write_text("# Fake Project\n", encoding="utf-8")
    output_dir = tmp_path / "outputs"
    run_logs_dir = tmp_path / "run_logs"
    config_path = tmp_path / "projectpilot.yaml"
    config_path.write_text(
        "\n".join(
            [
                "project:",
                "  name: Fake Project",
                f"  path: {fake_project}",
                "outputs:",
                f"  directory: {output_dir}",
                f"  run_logs_directory: {run_logs_dir}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "projectpilot.cli", "analyze", "--config", str(config_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    run_log_path = Path(run_logs_dir / "latest_run.json")
    assert run_log_path.exists()
    payload = json.loads(run_log_path.read_text(encoding="utf-8"))
    assert payload["status"] == "success"
    assert payload["target_project"] == "Fake Project"
    assert "delivery_readiness_score" in payload
    assert "project_status_report" in payload["outputs"]
