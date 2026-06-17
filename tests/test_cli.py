from __future__ import annotations

import json
import os
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

    env = os.environ.copy()
    env["LLM_PROVIDER"] = "mock"
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
        env=env,
    )

    assert result.returncode == 0
    assert "ProjectPilot 分析完成" in result.stdout
    assert "目标项目：Fake Project" in result.stdout
    assert "读取文件数：4" in result.stdout
    assert "交付证据完整度评分（Evidence Coverage Score）：" in result.stdout
    assert "评分类型：规则化证据类型覆盖检查" in result.stdout
    assert "README 建议：" in result.stdout
    assert "风险提醒：" in result.stdout
    assert "Commit 建议：" in result.stdout
    assert "LLM Review：" in result.stdout
    assert "LLM Provider：mock" in result.stdout
    assert "Tool Call Log：" in result.stdout
    assert "Workflow 状态：completed" in result.stdout
    assert "人工确认状态：pending" in result.stdout

    summary_path = output_dir / "context_summary.md"
    status_report_path = output_dir / "project_status_report.md"
    next_tasks_path = output_dir / "next_tasks.md"
    readme_suggestions_path = output_dir / "readme_suggestions.md"
    risk_report_path = output_dir / "risk_report.md"
    commit_suggestions_path = output_dir / "commit_suggestions.md"
    llm_review_path = output_dir / "llm_review.md"
    tool_call_log_path = output_dir / "tool_call_log.md"
    assert summary_path.exists()
    assert status_report_path.exists()
    assert next_tasks_path.exists()
    assert readme_suggestions_path.exists()
    assert risk_report_path.exists()
    assert commit_suggestions_path.exists()
    assert llm_review_path.exists()
    assert tool_call_log_path.exists()
    summary = summary_path.read_text(encoding="utf-8")
    assert "# Project Context Summary" in summary
    assert "## 7. Recent Git Commits" in summary
    assert "# 项目状态报告" in status_report_path.read_text(encoding="utf-8")
    assert "# 下一步任务" in next_tasks_path.read_text(encoding="utf-8")
    assert "# README 建议" in readme_suggestions_path.read_text(encoding="utf-8")
    assert "# 风险提醒" in risk_report_path.read_text(encoding="utf-8")
    assert "# Commit 建议草案" in commit_suggestions_path.read_text(encoding="utf-8")
    assert "# LLM 语义审阅报告" in llm_review_path.read_text(encoding="utf-8")
    tool_call_log = tool_call_log_path.read_text(encoding="utf-8")
    assert "# Tool Call Log" in tool_call_log
    assert "llm_review_advisor" in tool_call_log


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

    env = os.environ.copy()
    env["LLM_PROVIDER"] = "mock"
    result = subprocess.run(
        [sys.executable, "-m", "projectpilot.cli", "analyze", "--config", str(config_path)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0
    run_log_path = Path(run_logs_dir / "latest_run.json")
    assert run_log_path.exists()
    payload = json.loads(run_log_path.read_text(encoding="utf-8"))
    assert payload["status"] == "success"
    assert payload["workflow_status"] == "completed"
    assert payload["target_project"] == "Fake Project"
    assert "delivery_readiness_score" in payload
    assert payload["human_confirmation_status"] == "pending"
    assert payload["llm_provider"] == "mock"
    assert "llm_review_output" in payload
    assert "project_status_report" in payload["outputs"]
    assert "readme_suggestions" in payload["outputs"]
    assert "risk_report" in payload["outputs"]
    assert "commit_suggestions" in payload["outputs"]
    assert "llm_review" in payload["outputs"]
    assert "tool_call_log" in payload["outputs"]
    assert "tool_calls" in payload
    assert payload["tool_calls"]
    assert any(call["tool_name"] == "llm_review_advisor" for call in payload["tool_calls"])
    assert "steps" in payload
