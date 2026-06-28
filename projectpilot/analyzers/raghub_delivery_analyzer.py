"""Rule-based delivery analysis for the RAGHub Eval-100 case."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from projectpilot.analyzers.eval_metrics_reader import RAGHubEvalMetrics


@dataclass(frozen=True)
class RAGHubRiskIssue:
    issue_name: str
    status: str
    evidence: str
    reason: str
    recommended_action: str


@dataclass(frozen=True)
class RAGHubDeliveryReport:
    issues: list[RAGHubRiskIssue]
    hybrid_default_recommended: bool
    human_confirmation_status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def issue_status(self, issue_name: str) -> str | None:
        for issue in self.issues:
            if issue.issue_name == issue_name:
                return issue.status
        return None


def analyze_raghub_delivery(metrics: RAGHubEvalMetrics) -> RAGHubDeliveryReport:
    """Classify RAGHub delivery risks from deterministic Eval-100 metrics."""

    issues = [
        _no_answer_issue(metrics),
        _source_competition_issue(metrics),
        _hybrid_default_issue(metrics),
        _eval_scope_issue(metrics),
        _production_readiness_issue(metrics),
        _roadmap_issue(metrics),
    ]
    hybrid_default_recommended = (
        next(
            issue.status
            for issue in issues
            if issue.issue_name == "hybrid_default_decision"
        )
        != "not_recommended"
    )
    return RAGHubDeliveryReport(
        issues=issues,
        hybrid_default_recommended=hybrid_default_recommended,
    )


def _no_answer_issue(metrics: RAGHubEvalMetrics) -> RAGHubRiskIssue:
    rejected_count, rejected_total = _parse_ratio(metrics.out_of_corpus_rejected)
    is_resolved = (
        metrics.expected_unanswerable_reject_rate >= 1.0
        and rejected_count == rejected_total
        and rejected_total == metrics.out_of_corpus_count
    )
    return RAGHubRiskIssue(
        issue_name="no_answer_risk",
        status="resolved" if is_resolved else "open",
        evidence=(
            "expected_unanswerable_reject_rate="
            f"{metrics.expected_unanswerable_reject_rate:.4f}, "
            f"out_of_corpus_rejected={metrics.out_of_corpus_rejected}"
        ),
        reason="out-of-corpus samples are all rejected by the current guard."
        if is_resolved
        else "some out-of-corpus samples are still accepted or unverified.",
        recommended_action=(
            "Keep the guard as completed evidence and add a later LLM judge pass."
        ),
    )


def _source_competition_issue(metrics: RAGHubEvalMetrics) -> RAGHubRiskIssue:
    gap = metrics.source_group_hit_rate - metrics.exact_source_hit_rate
    is_open = metrics.exact_source_hit_rate < 0.7 and gap > 0.2
    return RAGHubRiskIssue(
        issue_name="source_competition",
        status="open" if is_open else "accepted_risk",
        evidence=(
            f"exact_source_hit_rate={metrics.exact_source_hit_rate:.4f}, "
            f"source_group_hit_rate={metrics.source_group_hit_rate:.4f}, "
            f"gap={gap:.4f}"
        ),
        reason="source_group is much higher than exact source hit."
        if is_open
        else "exact and source-group metrics do not indicate an active competition gap.",
        recommended_action=(
            "Create P1/P2 tasks for source_type filters, heading-aware chunks, "
            "metadata filters, and answer-level source selection."
        ),
    )


def _hybrid_default_issue(metrics: RAGHubEvalMetrics) -> RAGHubRiskIssue:
    vector_score = metrics.vector_average_score
    hybrid_score = metrics.hybrid_average_score
    ties = metrics.ties
    small_gain = (
        vector_score is not None
        and hybrid_score is not None
        and hybrid_score - vector_score < 0.2
    )
    many_ties = ties is not None and ties >= 50
    not_recommended = small_gain and many_ties
    return RAGHubRiskIssue(
        issue_name="hybrid_default_decision",
        status="not_recommended" if not_recommended else "roadmap",
        evidence=(
            f"vector_average_score={_fmt_optional(vector_score)}, "
            f"hybrid_average_score={_fmt_optional(hybrid_score)}, ties={ties}"
        ),
        reason="hybrid gain is small and most cases tie."
        if not_recommended
        else "hybrid evidence is incomplete or does not meet the no-default rule.",
        recommended_action="Keep hybrid as an experiment mode; do not make it the default.",
    )


def _eval_scope_issue(metrics: RAGHubEvalMetrics) -> RAGHubRiskIssue:
    return RAGHubRiskIssue(
        issue_name="eval_100_scope",
        status="project_level_benchmark",
        evidence=(
            f"total_queries={metrics.total_queries}, "
            f"in_corpus={metrics.in_corpus_count}, "
            f"out_of_corpus={metrics.out_of_corpus_count}"
        ),
        reason="100-query project-level eval, not a production benchmark.",
        recommended_action=(
            "Use README and interview wording that states Eval-100 is project-level evidence."
        ),
    )


def _production_readiness_issue(metrics: RAGHubEvalMetrics) -> RAGHubRiskIssue:
    return RAGHubRiskIssue(
        issue_name="production_readiness",
        status="not_production",
        evidence=(
            f"answerability_accuracy={metrics.answerability_accuracy:.4f}, "
            "scope=local RAG project benchmark"
        ),
        reason="Eval-100 validates a project workflow, not production readiness.",
        recommended_action=(
            "Do not present this as a production audit; keep production claims out of the case."
        ),
    )


def _roadmap_issue(metrics: RAGHubEvalMetrics) -> RAGHubRiskIssue:
    return RAGHubRiskIssue(
        issue_name="retrieval_quality_roadmap",
        status="roadmap",
        evidence=(
            f"acceptable_source_hit_rate={metrics.acceptable_source_hit_rate:.4f}, "
            f"source_group_hit_rate={metrics.source_group_hit_rate:.4f}"
        ),
        reason="acceptable/source-group metrics show recoverable evidence despite exact-source competition.",
        recommended_action=(
            "Plan source_type filter, heading-aware chunk, metadata filter, "
            "and answer-level source selection improvements."
        ),
    )


def _parse_ratio(value: str) -> tuple[int, int]:
    left, _, right = value.partition("/")
    try:
        return int(left), int(right)
    except ValueError:
        return 0, 0


def _fmt_optional(value: float | None) -> str:
    if value is None:
        return "None"
    return f"{value:.2f}"
