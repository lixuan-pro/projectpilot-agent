from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from projectpilot.analyzers.eval_metrics_reader import (
    RAGHubEvalMetrics,
    RetrievalModeMetrics,
)
from projectpilot.analyzers.llm_raghub_task_planner import (
    LLMRAGHubTaskPlanner,
    build_raghub_task_plan_prompt,
)
from projectpilot.analyzers.raghub_delivery_analyzer import analyze_raghub_delivery
from projectpilot.schemas.tool_schema import ToolCallStatus


def test_llm_raghub_task_planner_generates_mock_plan(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    metrics = _metrics()
    report = analyze_raghub_delivery(metrics)
    output_path = tmp_path / "llm_task_plan.md"

    result = LLMRAGHubTaskPlanner().plan(
        metrics=metrics,
        delivery_report=report,
        risk_review_summary="# DeepSeek RAGHub Risk Review\nsource competition open",
        output_path=output_path,
    )

    assert result.provider == "mock"
    assert result.status == ToolCallStatus.SUCCESS
    markdown = output_path.read_text(encoding="utf-8")
    assert "## P0：当前必须处理，否则影响项目可信度" in markdown
    assert "## P1：近期可以增强，但不阻塞展示" in markdown
    assert "## P2：Roadmap" in markdown
    assert "## P3：面试储备，不进入当前开发" in markdown
    assert "状态：pending" in markdown
    assert "不默认启用 hybrid" in markdown


def test_llm_raghub_task_planner_deepseek_without_key_is_controlled(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    metrics = _metrics()
    report = analyze_raghub_delivery(metrics)
    output_path = tmp_path / "llm_task_plan.md"

    result = LLMRAGHubTaskPlanner().plan(
        metrics=metrics,
        delivery_report=report,
        risk_review_summary="summary",
        output_path=output_path,
    )

    assert result.provider == "deepseek"
    assert result.status == ToolCallStatus.PERMISSION_DENIED
    markdown = output_path.read_text(encoding="utf-8")
    assert "Tool Call 状态：permission_denied" in markdown
    assert "DEEPSEEK_API_KEY" in markdown


def test_raghub_task_plan_prompt_contains_boundaries() -> None:
    prompt = build_raghub_task_plan_prompt(
        metrics=_metrics(),
        delivery_report=analyze_raghub_delivery(_metrics()),
        risk_review_summary="risk summary",
    )

    assert "请将风险转化为 P0/P1/P2/P3 任务" in prompt
    assert "P0 只包含影响当前项目可信度或展示边界的任务" in prompt
    assert "不要建议继续扩 RAGHub 功能" in prompt
    assert "不要建议默认启用 hybrid" in prompt
    assert "不要建议接入 Qdrant、LangGraph、MCP 作为当前 P0" in prompt


def test_cli_runs_raghub_llm_advisors_when_enabled(tmp_path) -> None:
    fake_project = _write_fake_raghub_project(tmp_path)
    output_dir = tmp_path / "outputs"
    run_logs_dir = tmp_path / "run_logs"
    config_path = _write_config(
        tmp_path,
        fake_project,
        output_dir,
        run_logs_dir,
        enable_llm_advisors=True,
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
    assert (output_dir / "llm_risk_review.md").exists()
    assert (output_dir / "llm_task_plan.md").exists()
    tool_call_log = (output_dir / "tool_call_log.md").read_text(encoding="utf-8")
    assert "llm_raghub_risk_reviewer" in tool_call_log
    assert "llm_raghub_task_planner" in tool_call_log
    run_log = json.loads((run_logs_dir / "latest_run.json").read_text(encoding="utf-8"))
    assert run_log["raghub_eval100"]["llm_advisors_enabled"] is True
    assert run_log["raghub_eval100"]["llm_risk_review"] == "generated"
    assert run_log["raghub_eval100"]["llm_task_plan"] == "generated"
    assert run_log["raghub_eval100"]["human_confirmation_status"] == "pending"


def test_cli_skips_raghub_llm_advisors_when_disabled(tmp_path) -> None:
    fake_project = _write_fake_raghub_project(tmp_path)
    output_dir = tmp_path / "outputs"
    run_logs_dir = tmp_path / "run_logs"
    config_path = _write_config(
        tmp_path,
        fake_project,
        output_dir,
        run_logs_dir,
        enable_llm_advisors=False,
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
    assert not (output_dir / "llm_risk_review.md").exists()
    assert not (output_dir / "llm_task_plan.md").exists()
    tool_call_log = (output_dir / "tool_call_log.md").read_text(encoding="utf-8")
    assert "llm_raghub_risk_reviewer" not in tool_call_log
    assert "llm_raghub_task_planner" not in tool_call_log
    run_log = json.loads((run_logs_dir / "latest_run.json").read_text(encoding="utf-8"))
    assert run_log["raghub_eval100"]["llm_advisors_enabled"] is False
    assert run_log["raghub_eval100"]["llm_risk_review"] == "disabled"
    assert run_log["raghub_eval100"]["llm_task_plan"] == "disabled"


def _write_fake_raghub_project(tmp_path: Path) -> Path:
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
    return fake_project


def _write_config(
    tmp_path: Path,
    fake_project: Path,
    output_dir: Path,
    run_logs_dir: Path,
    enable_llm_advisors: bool,
) -> Path:
    config_path = tmp_path / ("enabled.yaml" if enable_llm_advisors else "disabled.yaml")
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
                f"  directory: {output_dir}",
                f"  run_logs_directory: {run_logs_dir}",
                "raghub_eval100:",
                f"  enable_llm_advisors: {str(enable_llm_advisors).lower()}",
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


def _metrics() -> RAGHubEvalMetrics:
    return RAGHubEvalMetrics(
        total_queries=100,
        in_corpus_count=88,
        out_of_corpus_count=12,
        answerability_accuracy=0.99,
        expected_answerable_accept_rate=0.9886,
        expected_unanswerable_reject_rate=1.0,
        out_of_corpus_rejected="12/12",
        exact_source_hit_rate=0.5909,
        acceptable_source_hit_rate=0.7955,
        source_group_hit_rate=0.9091,
        keyword_hit_rate=0.6414,
        retrieval_modes={
            "vector": RetrievalModeMetrics(
                mode="vector",
                total_queries=100,
                top_k=3,
                exact_source_hit_rate=0.5909,
                acceptable_source_hit_rate=0.7955,
                source_group_hit_rate=0.9091,
                keyword_hit_rate=0.6391,
            )
        },
        vector_average_score=8.83,
        hybrid_average_score=8.9,
        vector_wins=12,
        hybrid_wins=12,
        ties=76,
        source_files={},
    )
