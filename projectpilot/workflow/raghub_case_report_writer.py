"""Writers for the RAGHub Eval-100 ProjectPilot case outputs."""

from __future__ import annotations

import json
from pathlib import Path

from projectpilot.analyzers.eval_metrics_reader import RAGHubEvalMetrics
from projectpilot.analyzers.raghub_delivery_analyzer import RAGHubDeliveryReport


def write_raghub_case_reports(
    metrics: RAGHubEvalMetrics,
    report: RAGHubDeliveryReport,
    output_dir: str | Path,
) -> dict[str, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    outputs = {
        "eval_metrics_summary": root / "eval_metrics_summary.md",
        "raghub_risk_review": root / "raghub_risk_review.md",
        "risk_register": root / "risk_register.json",
        "issue_to_task_map": root / "issue_to_task_map.md",
    }
    outputs["eval_metrics_summary"].write_text(
        build_eval_metrics_summary(metrics),
        encoding="utf-8",
    )
    outputs["raghub_risk_review"].write_text(
        build_raghub_risk_review(metrics, report),
        encoding="utf-8",
    )
    outputs["risk_register"].write_text(
        json.dumps(build_risk_register(metrics, report), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    outputs["issue_to_task_map"].write_text(
        build_issue_to_task_map(report),
        encoding="utf-8",
    )
    return outputs


def build_eval_metrics_summary(metrics: RAGHubEvalMetrics) -> str:
    lines = [
        "# RAGHub Eval-100 指标摘要",
        "",
        "## 1. Query 分布",
        "",
        "| metric | value |",
        "| ------ | ----: |",
        f"| Eval-100 query 数 | {metrics.total_queries} |",
        f"| in_corpus / out_of_corpus | {metrics.in_corpus_count} / {metrics.out_of_corpus_count} |",
        f"| answerability_accuracy | {_rate(metrics.answerability_accuracy)} |",
        f"| expected_answerable_accept_rate | {_rate(metrics.expected_answerable_accept_rate)} |",
        f"| expected_unanswerable_reject_rate | {_rate(metrics.expected_unanswerable_reject_rate)} |",
        f"| out_of_corpus_rejected | {metrics.out_of_corpus_rejected} |",
        f"| exact_source_hit_rate | {_rate(metrics.exact_source_hit_rate)} |",
        f"| acceptable_source_hit_rate | {_rate(metrics.acceptable_source_hit_rate)} |",
        f"| source_group_hit_rate | {_rate(metrics.source_group_hit_rate)} |",
        f"| keyword_hit_rate | {_rate(metrics.keyword_hit_rate)} |",
        "",
        "## 2. Retrieval comparison",
        "",
        "| mode | exact | acceptable | source_group | keyword | MRR@k | Recall@k |",
        "| ---- | ----: | ---------: | -----------: | ------: | ----: | -------: |",
        *_retrieval_mode_lines(metrics),
        "",
        "## 3. DeepSeek A/B 摘要",
        "",
        "| metric | value |",
        "| ------ | ----: |",
        f"| vector_average_score | {_number(metrics.vector_average_score)} |",
        f"| hybrid_average_score | {_number(metrics.hybrid_average_score)} |",
        f"| vector_wins | {_number(metrics.vector_wins)} |",
        f"| hybrid_wins | {_number(metrics.hybrid_wins)} |",
        f"| ties | {_number(metrics.ties)} |",
        "",
        "## 4. 边界说明",
        "",
        "- Eval-100 是项目级 benchmark，不是生产级 benchmark。",
        "- 指标来自 RAGHub JSON 文件的确定性解析，不由 LLM 总结或推断。",
        "- ProjectPilot 本轮只读取 RAGHub 文件，不修改 RAGHub 项目。",
        "- human_confirmation_status = pending",
        "",
    ]
    return "\n".join(lines)


def build_raghub_risk_review(
    metrics: RAGHubEvalMetrics,
    report: RAGHubDeliveryReport,
) -> str:
    issue_lines = [
        f"| {issue.issue_name} | {issue.status} | {issue.evidence} | {issue.recommended_action} |"
        for issue in report.issues
    ]
    lines = [
        "# RAGHub 交付风险识别",
        "",
        "## resolved",
        "",
        "- no-answer 漏拒已修复：out_of_corpus_rejected = "
        f"{metrics.out_of_corpus_rejected}，expected_unanswerable_reject_rate = "
        f"{_rate(metrics.expected_unanswerable_reject_rate)}。",
        "",
        "## open",
        "",
        "- source competition 仍存在：exact_source_hit_rate = "
        f"{_rate(metrics.exact_source_hit_rate)}，source_group_hit_rate = "
        f"{_rate(metrics.source_group_hit_rate)}。",
        "",
        "## accepted decision",
        "",
        "- hybrid 不默认启用：DeepSeek A/B 为 vector wins = "
        f"{metrics.vector_wins}，hybrid wins = {metrics.hybrid_wins}，ties = {metrics.ties}。",
        "",
        "## roadmap",
        "",
        "- source_type filter",
        "- heading-aware chunk",
        "- metadata filter",
        "- answer-level source selection",
        "",
        "## issue table",
        "",
        "| issue | status | evidence | recommended_action |",
        "| ----- | ------ | -------- | ------------------ |",
        *issue_lines,
        "",
        "## boundary",
        "",
        "- 本报告不是生产级审计报告。",
        "- ProjectPilot 不声称自动发现并修复了 RAGHub 问题；这里只登记基于 Eval-100 证据的风险状态。",
        "- human_confirmation_status = pending",
        "",
    ]
    return "\n".join(lines)


def build_risk_register(
    metrics: RAGHubEvalMetrics,
    report: RAGHubDeliveryReport,
) -> dict[str, object]:
    return {
        "case": "raghub_eval100",
        "report_type": "project_level_delivery_review",
        "human_confirmation_status": report.human_confirmation_status,
        "production_readiness": report.issue_status("production_readiness"),
        "hybrid_default_recommended": report.hybrid_default_recommended,
        "metrics": {
            "total_queries": metrics.total_queries,
            "in_corpus_count": metrics.in_corpus_count,
            "out_of_corpus_count": metrics.out_of_corpus_count,
            "answerability_accuracy": metrics.answerability_accuracy,
            "out_of_corpus_rejected": metrics.out_of_corpus_rejected,
            "exact_source_hit_rate": metrics.exact_source_hit_rate,
            "acceptable_source_hit_rate": metrics.acceptable_source_hit_rate,
            "source_group_hit_rate": metrics.source_group_hit_rate,
            "keyword_hit_rate": metrics.keyword_hit_rate,
            "vector_average_score": metrics.vector_average_score,
            "hybrid_average_score": metrics.hybrid_average_score,
            "vector_wins": metrics.vector_wins,
            "hybrid_wins": metrics.hybrid_wins,
            "ties": metrics.ties,
        },
        "issues": [issue.__dict__ for issue in report.issues],
        "source_files": metrics.source_files,
    }


def build_issue_to_task_map(report: RAGHubDeliveryReport) -> str:
    issue_table = [
        f"| {issue.issue_name} | {issue.status} | {issue.recommended_action} |"
        for issue in report.issues
    ]
    lines = [
        "# RAGHub Issue to Task Map",
        "",
        "## Required mappings",
        "",
        "- source competition -> P1/P2 任务：source_type filter、heading-aware chunk、metadata filter、answer-level source selection。",
        "- no-answer guard -> 已完成 + 后续 LLM judge：保持当前 guard，并在后续评审中补充 judge。",
        "- hybrid default decision -> 保留实验模式：不默认替换 vector。",
        "- Eval-100 boundary -> README / 面试中说明：项目级 benchmark，不是生产级 benchmark。",
        "",
        "## Task table",
        "",
        "| issue | status | task |",
        "| ----- | ------ | ---- |",
        *issue_table,
        "",
        "## Human confirmation",
        "",
        f"- 状态：{report.human_confirmation_status}",
        "- ProjectPilot 只输出建议和登记，不自动修改 RAGHub。",
        "",
    ]
    return "\n".join(lines)


def _retrieval_mode_lines(metrics: RAGHubEvalMetrics) -> list[str]:
    preferred_order = ["vector", "bm25", "hybrid", "hybrid_rerank"]
    ordered_names = [
        *[name for name in preferred_order if name in metrics.retrieval_modes],
        *[
            name
            for name in sorted(metrics.retrieval_modes)
            if name not in preferred_order
        ],
    ]
    lines = []
    for name in ordered_names:
        item = metrics.retrieval_modes[name]
        lines.append(
            "| "
            f"{item.mode} | "
            f"{_rate(item.exact_source_hit_rate)} | "
            f"{_rate(item.acceptable_source_hit_rate)} | "
            f"{_rate(item.source_group_hit_rate)} | "
            f"{_rate(item.keyword_hit_rate)} | "
            f"{_rate(item.mrr_at_k)} | "
            f"{_rate(item.recall_at_k)} |"
        )
    return lines


def _rate(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.4f}"


def _number(value: int | float | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)
