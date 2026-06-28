from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_cli_runs_raghub_phase4_when_enabled(tmp_path) -> None:
    fake_project = _write_fake_raghub_project(tmp_path)
    output_dir = tmp_path / "outputs"
    run_logs_dir = tmp_path / "run_logs"
    config_path = _write_config(
        tmp_path=tmp_path,
        fake_project=fake_project,
        output_dir=output_dir,
        run_logs_dir=run_logs_dir,
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
    assert (output_dir / "interview_case_cards.md").exists()
    assert (output_dir / "resume_assets.md").exists()
    assert (output_dir / "consistency_check.md").exists()
    assert (output_dir / "consistency_check.json").exists()
    tool_call_log = (output_dir / "tool_call_log.md").read_text(encoding="utf-8")
    assert "llm_interview_asset_writer" in tool_call_log
    assert "llm_resume_asset_writer" in tool_call_log
    assert "consistency_checker" in tool_call_log

    run_log = json.loads((run_logs_dir / "latest_run.json").read_text(encoding="utf-8"))
    phase4 = run_log["raghub_eval100"]
    assert phase4["asset_writers_enabled"] is True
    assert phase4["consistency_check_enabled"] is True
    assert phase4["interview_assets"] == "generated"
    assert phase4["resume_assets"] == "generated"
    assert phase4["consistency_status"] == "passed"
    assert phase4["human_confirmation_status"] == "pending"
    assert "interview_case_cards" in run_log["outputs"]
    assert "resume_assets" in run_log["outputs"]
    assert "consistency_check" in run_log["outputs"]


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
) -> Path:
    config_path = tmp_path / "phase4.yaml"
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
                "  enable_llm_advisors: true",
                "  enable_asset_writers: true",
                "  enable_consistency_check: true",
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
