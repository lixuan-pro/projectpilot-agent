from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from projectpilot.agent.agent_run import run_agent_workflow
from projectpilot.agent.planner import AgentPlan, PlannedStep
from projectpilot.schemas.tool_schema import ToolSpec


def test_agent_run_generates_outputs_and_run_log_without_deepseek_key(
    tmp_path,
    monkeypatch,
) -> None:
    fake_project = _write_fake_raghub_project(tmp_path, initialize_git=True)
    output_dir = tmp_path / "outputs" / "raghub_agent"
    run_logs_dir = tmp_path / "run_logs"
    config_path = _write_config(tmp_path, fake_project, run_logs_dir)
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    before_status = _git_status(fake_project)
    result = run_agent_workflow(
        config_path=config_path,
        goal="analyze RAGHub delivery readiness",
        output_dir=output_dir,
    )
    after_status = _git_status(fake_project)

    assert len(result.plan.planned_steps) == 7
    assert result.executed_steps_count == 7
    assert result.skipped_steps_count == 0
    assert result.human_confirmation_status.value == "pending"
    assert before_status == after_status
    assert (output_dir / "agent_plan.md").exists()
    assert (output_dir / "agent_run_summary.md").exists()
    assert (output_dir / "skipped_steps.md").exists()
    assert (output_dir / "tool_call_log.md").exists()
    assert (run_logs_dir / "raghub_agent_latest_run.json").exists()

    summary = (output_dir / "agent_run_summary.md").read_text(encoding="utf-8")
    assert "planned_steps_count: 7" in summary
    assert "executed_steps_count: 7" in summary
    assert "skipped_steps_count: 0" in summary
    assert "human_confirmation_status: pending" in summary

    tool_call_log = (output_dir / "tool_call_log.md").read_text(encoding="utf-8")
    assert "context_reader" in tool_call_log
    assert "agent_summary_writer" in tool_call_log

    payload = json.loads(
        (run_logs_dir / "raghub_agent_latest_run.json").read_text(encoding="utf-8")
    )
    assert payload["agent_run"] == {
        "goal": "analyze RAGHub delivery readiness",
        "planner_provider": "mock",
        "planned_steps_count": 7,
        "executed_steps_count": 7,
        "skipped_steps_count": 0,
        "human_confirmation_status": "pending",
    }
    assert "tool_calls" in payload
    assert any(call["tool_name"] == "raghub_eval_metrics_reader" for call in payload["tool_calls"])


def test_agent_run_records_dangerous_tools_as_skipped(tmp_path) -> None:
    fake_project = _write_fake_raghub_project(tmp_path)
    output_dir = tmp_path / "outputs" / "raghub_agent"
    run_logs_dir = tmp_path / "run_logs"
    config_path = _write_config(tmp_path, fake_project, run_logs_dir)

    result = run_agent_workflow(
        config_path=config_path,
        goal="test dangerous plan",
        planner=_DangerousPlanner(),
        output_dir=output_dir,
    )

    assert len(result.plan.planned_steps) == 3
    assert result.executed_steps_count == 1
    assert result.skipped_steps_count == 2
    skipped_steps = (output_dir / "skipped_steps.md").read_text(encoding="utf-8")
    assert "dangerous_tool_for_read_only_agent" in skipped_steps
    assert "tool_not_allowed" in skipped_steps

    tool_call_log = (output_dir / "tool_call_log.md").read_text(encoding="utf-8")
    assert "skipped" in tool_call_log

    payload = json.loads(
        (run_logs_dir / "raghub_agent_latest_run.json").read_text(encoding="utf-8")
    )
    assert payload["agent_run"]["skipped_steps_count"] == 2
    assert payload["agent_run"]["human_confirmation_status"] == "pending"


def test_agent_run_builtin_dangerous_demo_records_skipped_steps(tmp_path) -> None:
    fake_project = _write_fake_raghub_project(tmp_path, initialize_git=True)
    output_dir = tmp_path / "outputs" / "raghub_agent"
    run_logs_dir = tmp_path / "run_logs"
    config_path = _write_config(tmp_path, fake_project, run_logs_dir)

    before_status = _git_status(fake_project)
    result = run_agent_workflow(
        config_path=config_path,
        goal="demo dangerous tool guard",
        output_dir=output_dir,
    )
    after_status = _git_status(fake_project)

    assert result.executed_steps_count == 2
    assert result.skipped_steps_count == 3
    assert before_status == after_status
    skipped_steps = (output_dir / "skipped_steps.md").read_text(encoding="utf-8")
    assert "git_push" in skipped_steps
    assert "modify_target_project" in skipped_steps
    assert "deploy" in skipped_steps
    assert "dangerous_tool_for_read_only_agent" in skipped_steps

    payload = json.loads(
        (run_logs_dir / "raghub_agent_latest_run.json").read_text(encoding="utf-8")
    )
    assert payload["agent_run"]["skipped_steps_count"] == 3
    skipped_calls = [
        call for call in payload["tool_calls"] if call["status"] == "skipped"
    ]
    assert [call["tool_name"] for call in skipped_calls] == [
        "git_push",
        "modify_target_project",
        "deploy",
    ]


def test_agent_run_chinese_goal_uses_mock_planner_and_executes(tmp_path) -> None:
    fake_project = _write_fake_raghub_project(tmp_path)
    output_dir = tmp_path / "outputs" / "raghub_agent"
    run_logs_dir = tmp_path / "run_logs"
    config_path = _write_config(tmp_path, fake_project, run_logs_dir)

    result = run_agent_workflow(
        config_path=config_path,
        goal="看看我的 RAGHub 项目目前还有什么可以增强的",
        output_dir=output_dir,
    )

    assert result.planner_provider == "mock"
    assert len(result.plan.planned_steps) == 7
    assert result.executed_steps_count == 7
    assert result.skipped_steps_count == 0
    plan_markdown = (output_dir / "agent_plan.md").read_text(encoding="utf-8")
    assert "project improvement opportunities" in plan_markdown


def test_cli_agent_run_command_generates_agent_outputs(tmp_path) -> None:
    fake_project = _write_fake_raghub_project(tmp_path)
    output_dir = Path("outputs/raghub_agent")
    run_logs_dir = tmp_path / "run_logs"
    config_path = _write_config(tmp_path, fake_project, run_logs_dir)

    env = os.environ.copy()
    env["LLM_PROVIDER"] = "mock"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "projectpilot.cli",
            "agent-run",
            "--config",
            str(config_path),
            "--goal",
            "analyze RAGHub delivery readiness",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0
    assert "ProjectPilot agent-run 完成" in result.stdout
    assert "Planner Provider：mock" in result.stdout
    assert "Skipped Steps：0" in result.stdout
    assert output_dir.joinpath("agent_plan.md").exists()
    assert output_dir.joinpath("agent_run_summary.md").exists()
    assert (run_logs_dir / "raghub_agent_latest_run.json").exists()


class _DangerousPlanner:
    def plan(self, goal: str, tool_catalog: list[ToolSpec]) -> AgentPlan:
        del tool_catalog
        return AgentPlan(
            goal=goal,
            planner_provider="test-dangerous",
            planned_steps=[
                _planned_step("safe_context", "context_reader"),
                _planned_step("attempt_push", "git_push", read_only=False),
                _planned_step("unknown_step", "unknown_tool"),
            ],
        )


def _planned_step(
    step_id: str,
    tool_name: str,
    read_only: bool = True,
) -> PlannedStep:
    return PlannedStep(
        step_id=step_id,
        tool_name=tool_name,
        reason="test planned step",
        read_only=read_only,
        requires_human_confirmation=True,
        depends_on=[],
        input_summary={},
        expected_output="test",
    )


def _write_fake_raghub_project(
    tmp_path: Path,
    initialize_git: bool = False,
) -> Path:
    fake_project = tmp_path / "fake_raghub"
    eval_dir = fake_project / "eval"
    docs_dir = fake_project / "docs"
    eval_dir.mkdir(parents=True)
    docs_dir.mkdir()
    (fake_project / "README.md").write_text("# Fake RAGHub\n", encoding="utf-8")
    (eval_dir / "bad_cases.md").write_text("# Bad cases\n", encoding="utf-8")
    (docs_dir / "eval_100_report.md").write_text("# Eval report\n", encoding="utf-8")
    (eval_dir / "results_100.json").write_text(
        json.dumps(
            {
                "summary": {
                    "all_cases": {
                        "total_queries": 100,
                        "in_corpus_count": 88,
                        "out_of_corpus_count": 12,
                        "answerability_accuracy": 0.99,
                        "expected_answerable_accept_rate": 0.9886,
                        "expected_unanswerable_total": 12,
                        "expected_unanswerable_reject_rate": 1.0,
                        "out_of_corpus_rejected": 12,
                        "exact_source_hit_rate": 0.5909,
                        "acceptable_source_hit_rate": 0.7955,
                        "source_group_hit_rate": 0.9091,
                        "keyword_hit_rate": 0.6414,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (eval_dir / "retrieval_comparison_100.json").write_text(
        json.dumps(
            {
                "summary": {
                    "vector": _mode(0.5909, 0.7955, 0.9091, 0.6391),
                    "bm25": _mode(0.4432, 0.6932, 0.8295, 0.6736),
                    "hybrid": _mode(0.5909, 0.8068, 0.9205, 0.6805),
                    "hybrid_rerank": _mode(0.6023, 0.8068, 0.9205, 0.6805),
                }
            }
        ),
        encoding="utf-8",
    )
    (eval_dir / "llm_ab_review_100_results.json").write_text(
        json.dumps(
            {
                "summary": {
                    "vector_average_score": 8.83,
                    "hybrid_average_score": 8.9,
                    "vector_win_count": 12,
                    "hybrid_win_count": 12,
                    "tie_count": 76,
                }
            }
        ),
        encoding="utf-8",
    )
    if initialize_git:
        _initialize_git_repo(fake_project)
    return fake_project


def _write_config(
    tmp_path: Path,
    fake_project: Path,
    run_logs_dir: Path,
) -> Path:
    config_path = tmp_path / "agent_run.yaml"
    config_path.write_text(
        "\n".join(
            [
                "project:",
                "  name: RAGHub Eval-100 Case",
                f"  path: {fake_project}",
                "context:",
                "  max_files: 20",
                "  max_file_size_kb: 80",
                "  include:",
                "    - README.md",
                "    - docs/**/*.md",
                "    - eval/*.md",
                "    - eval/*.json",
                "git:",
                "  max_commits: 5",
                "outputs:",
                f"  run_logs_directory: {run_logs_dir}",
                "raghub_eval100:",
                "  results_path: eval/results_100.json",
                "  retrieval_comparison_path: eval/retrieval_comparison_100.json",
                "  llm_ab_review_path: eval/llm_ab_review_100_results.json",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def _mode(
    exact: float,
    acceptable: float,
    source_group: float,
    keyword: float,
) -> dict[str, float | int]:
    return {
        "total_queries": 100,
        "top_k": 3,
        "exact_source_hit_rate": exact,
        "acceptable_source_hit_rate": acceptable,
        "source_group_hit_rate": source_group,
        "keyword_hit_rate": keyword,
        "mrr_at_k": exact,
        "recall_at_k": acceptable,
    }


def _initialize_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=ProjectPilot Test",
            "commit",
            "-m",
            "init",
        ],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )


def _git_status(path: Path) -> str:
    result = subprocess.run(
        ["git", "status", "-sb"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
