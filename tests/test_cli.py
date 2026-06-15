from __future__ import annotations

import json
import subprocess
import sys

from projectpilot.logging.run_log import write_run_log


def test_cli_help_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "projectpilot.cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "ProjectPilot Agent Day 1 skeleton CLI" in result.stdout


def test_cli_analyze_runs() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "projectpilot.cli",
            "analyze",
            "--config",
            "examples/projectpilot.yaml",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "ProjectPilot Agent skeleton is ready." in result.stdout
    assert "No real analysis executed yet." in result.stdout


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
