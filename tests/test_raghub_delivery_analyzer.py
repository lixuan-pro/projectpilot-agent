from __future__ import annotations

from projectpilot.analyzers.eval_metrics_reader import (
    RAGHubEvalMetrics,
    RetrievalModeMetrics,
)
from projectpilot.analyzers.raghub_delivery_analyzer import analyze_raghub_delivery


def test_raghub_delivery_analyzer_identifies_required_statuses() -> None:
    report = analyze_raghub_delivery(_metrics())

    statuses = {issue.issue_name: issue.status for issue in report.issues}

    assert statuses["no_answer_risk"] == "resolved"
    assert statuses["source_competition"] == "open"
    assert statuses["hybrid_default_decision"] == "not_recommended"
    assert statuses["eval_100_scope"] == "project_level_benchmark"
    assert statuses["production_readiness"] == "not_production"
    assert report.hybrid_default_recommended is False


def test_raghub_delivery_analyzer_includes_evidence_and_actions() -> None:
    report = analyze_raghub_delivery(_metrics())

    for issue in report.issues:
        assert issue.evidence
        assert issue.recommended_action

    source_issue = next(
        issue for issue in report.issues if issue.issue_name == "source_competition"
    )
    assert "source_group" in source_issue.reason
    assert "source_type filters" in source_issue.recommended_action


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
