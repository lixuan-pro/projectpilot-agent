from __future__ import annotations

import json
from pathlib import Path

import pytest

from projectpilot.analyzers.eval_metrics_reader import (
    RAGHubEvalMetricsError,
    read_raghub_eval_metrics,
)


def test_eval_metrics_reader_parses_eval100_json(tmp_path: Path) -> None:
    fake_project = _write_fake_raghub_eval_files(tmp_path)

    metrics = read_raghub_eval_metrics(fake_project, _config())

    assert metrics.total_queries == 100
    assert metrics.in_corpus_count == 88
    assert metrics.out_of_corpus_count == 12
    assert metrics.out_of_corpus_rejected == "12/12"
    assert metrics.answerability_accuracy == 0.99
    assert set(metrics.retrieval_modes) == {
        "vector",
        "bm25",
        "hybrid",
        "hybrid_rerank",
    }
    assert metrics.retrieval_modes["hybrid_rerank"].exact_source_hit_rate == 0.6023
    assert metrics.vector_average_score == 8.83
    assert metrics.hybrid_average_score == 8.9
    assert metrics.vector_wins == 12
    assert metrics.hybrid_wins == 12
    assert metrics.ties == 76


def test_eval_metrics_reader_returns_controlled_error_for_missing_json(
    tmp_path: Path,
) -> None:
    fake_project = tmp_path / "fake_raghub"
    (fake_project / "eval").mkdir(parents=True)

    with pytest.raises(RAGHubEvalMetricsError) as exc_info:
        read_raghub_eval_metrics(fake_project, _config())

    payload = exc_info.value.to_dict()
    assert payload["error_type"] == "missing_file"
    assert payload["path"]
    assert "results_100.json" in payload["path"]


def _write_fake_raghub_eval_files(tmp_path: Path) -> Path:
    fake_project = tmp_path / "fake_raghub"
    eval_dir = fake_project / "eval"
    eval_dir.mkdir(parents=True)

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


def _config() -> dict[str, str]:
    return {
        "results_path": "eval/results_100.json",
        "retrieval_comparison_path": "eval/retrieval_comparison_100.json",
        "llm_ab_review_path": "eval/llm_ab_review_100_results.json",
    }
