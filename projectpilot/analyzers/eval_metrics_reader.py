"""Deterministic reader for RAGHub Eval-100 result files."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_RESULTS_PATH = "eval/results_100.json"
DEFAULT_RETRIEVAL_COMPARISON_PATH = "eval/retrieval_comparison_100.json"
DEFAULT_LLM_AB_REVIEW_PATH = "eval/llm_ab_review_100_results.json"


class RAGHubEvalMetricsError(RuntimeError):
    """Controlled reader error with path and field context."""

    def __init__(
        self,
        message: str,
        *,
        error_type: str,
        path: str | Path | None = None,
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.path = str(path) if path is not None else None
        self.field = field

    def to_dict(self) -> dict[str, str | None]:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "path": self.path,
            "field": self.field,
        }


@dataclass(frozen=True)
class RetrievalModeMetrics:
    mode: str
    total_queries: int
    top_k: int | None
    exact_source_hit_rate: float
    acceptable_source_hit_rate: float
    source_group_hit_rate: float
    keyword_hit_rate: float
    mrr_at_k: float | None = None
    recall_at_k: float | None = None


@dataclass(frozen=True)
class RAGHubEvalMetrics:
    total_queries: int
    in_corpus_count: int
    out_of_corpus_count: int
    answerability_accuracy: float
    expected_answerable_accept_rate: float
    expected_unanswerable_reject_rate: float
    out_of_corpus_rejected: str
    exact_source_hit_rate: float
    acceptable_source_hit_rate: float
    source_group_hit_rate: float
    keyword_hit_rate: float
    retrieval_modes: dict[str, RetrievalModeMetrics]
    vector_average_score: float | None
    hybrid_average_score: float | None
    vector_wins: int | None
    hybrid_wins: int | None
    ties: int | None
    source_files: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def read_raghub_eval_metrics(project_path: Path, config: dict[str, Any]) -> RAGHubEvalMetrics:
    """Read RAGHub Eval-100 metrics from JSON files without LLM inference."""

    root = Path(project_path)
    results_path = _resolve_config_path(
        root,
        config,
        "results_path",
        DEFAULT_RESULTS_PATH,
    )
    retrieval_path = _resolve_config_path(
        root,
        config,
        "retrieval_comparison_path",
        DEFAULT_RETRIEVAL_COMPARISON_PATH,
    )
    llm_ab_path = _resolve_config_path(
        root,
        config,
        "llm_ab_review_path",
        DEFAULT_LLM_AB_REVIEW_PATH,
    )

    results_data = _load_json_object(results_path)
    retrieval_data = _load_json_object(retrieval_path)
    llm_ab_data = _load_json_object(llm_ab_path)

    all_cases = _required_mapping(
        _required_mapping(results_data, "summary", results_path, "summary"),
        "all_cases",
        results_path,
        "summary.all_cases",
    )
    expected_unanswerable_total = _required_int(
        all_cases,
        "expected_unanswerable_total",
        results_path,
        "summary.all_cases.expected_unanswerable_total",
    )
    out_of_corpus_rejected = _format_rejected_ratio(
        all_cases.get("out_of_corpus_rejected"),
        expected_unanswerable_total,
        results_path,
        "summary.all_cases.out_of_corpus_rejected",
    )

    retrieval_modes = _read_retrieval_modes(retrieval_data, retrieval_path)
    llm_summary = _required_mapping(llm_ab_data, "summary", llm_ab_path, "summary")

    return RAGHubEvalMetrics(
        total_queries=_required_int(
            all_cases,
            "total_queries",
            results_path,
            "summary.all_cases.total_queries",
        ),
        in_corpus_count=_required_int(
            all_cases,
            "in_corpus_count",
            results_path,
            "summary.all_cases.in_corpus_count",
        ),
        out_of_corpus_count=_required_int(
            all_cases,
            "out_of_corpus_count",
            results_path,
            "summary.all_cases.out_of_corpus_count",
        ),
        answerability_accuracy=_required_float(
            all_cases,
            "answerability_accuracy",
            results_path,
            "summary.all_cases.answerability_accuracy",
        ),
        expected_answerable_accept_rate=_required_float(
            all_cases,
            "expected_answerable_accept_rate",
            results_path,
            "summary.all_cases.expected_answerable_accept_rate",
        ),
        expected_unanswerable_reject_rate=_required_float(
            all_cases,
            "expected_unanswerable_reject_rate",
            results_path,
            "summary.all_cases.expected_unanswerable_reject_rate",
        ),
        out_of_corpus_rejected=out_of_corpus_rejected,
        exact_source_hit_rate=_required_float(
            all_cases,
            "exact_source_hit_rate",
            results_path,
            "summary.all_cases.exact_source_hit_rate",
        ),
        acceptable_source_hit_rate=_required_float(
            all_cases,
            "acceptable_source_hit_rate",
            results_path,
            "summary.all_cases.acceptable_source_hit_rate",
        ),
        source_group_hit_rate=_required_float(
            all_cases,
            "source_group_hit_rate",
            results_path,
            "summary.all_cases.source_group_hit_rate",
        ),
        keyword_hit_rate=_required_float(
            all_cases,
            "keyword_hit_rate",
            results_path,
            "summary.all_cases.keyword_hit_rate",
        ),
        retrieval_modes=retrieval_modes,
        vector_average_score=_optional_mode_score(llm_summary, "vector"),
        hybrid_average_score=_optional_mode_score(llm_summary, "hybrid"),
        vector_wins=_optional_int(llm_summary, "vector_win_count", llm_ab_path),
        hybrid_wins=_optional_int(llm_summary, "hybrid_win_count", llm_ab_path),
        ties=_optional_int(llm_summary, "tie_count", llm_ab_path),
        source_files={
            "results": str(results_path),
            "retrieval_comparison": str(retrieval_path),
            "llm_ab_review": str(llm_ab_path),
        },
    )


def _resolve_config_path(
    root: Path,
    config: dict[str, Any],
    key: str,
    default: str,
) -> Path:
    raw = str(config.get(key, default))
    path = Path(raw)
    if path.is_absolute():
        return path
    return root / path


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RAGHubEvalMetricsError(
            f"Required Eval-100 JSON file is missing: {path}",
            error_type="missing_file",
            path=path,
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RAGHubEvalMetricsError(
            f"Invalid JSON in Eval-100 file: {path}",
            error_type="invalid_json",
            path=path,
        ) from exc
    if not isinstance(payload, dict):
        raise RAGHubEvalMetricsError(
            f"Eval-100 JSON root must be an object: {path}",
            error_type="invalid_json_root",
            path=path,
        )
    return payload


def _read_retrieval_modes(
    payload: dict[str, Any],
    path: Path,
) -> dict[str, RetrievalModeMetrics]:
    summary = _required_mapping(payload, "summary", path, "summary")
    modes: dict[str, RetrievalModeMetrics] = {}
    for mode, raw_metrics in summary.items():
        if not isinstance(raw_metrics, dict):
            continue
        field_prefix = f"summary.{mode}"
        modes[mode] = RetrievalModeMetrics(
            mode=mode,
            total_queries=_required_int(
                raw_metrics,
                "total_queries",
                path,
                f"{field_prefix}.total_queries",
            ),
            top_k=_optional_int(raw_metrics, "top_k", path),
            exact_source_hit_rate=_required_float(
                raw_metrics,
                "exact_source_hit_rate",
                path,
                f"{field_prefix}.exact_source_hit_rate",
            ),
            acceptable_source_hit_rate=_required_float(
                raw_metrics,
                "acceptable_source_hit_rate",
                path,
                f"{field_prefix}.acceptable_source_hit_rate",
            ),
            source_group_hit_rate=_required_float(
                raw_metrics,
                "source_group_hit_rate",
                path,
                f"{field_prefix}.source_group_hit_rate",
            ),
            keyword_hit_rate=_required_float(
                raw_metrics,
                "keyword_hit_rate",
                path,
                f"{field_prefix}.keyword_hit_rate",
            ),
            mrr_at_k=_optional_float(raw_metrics, "mrr_at_k", path),
            recall_at_k=_optional_float(raw_metrics, "recall_at_k", path),
        )
    if not modes:
        raise RAGHubEvalMetricsError(
            "Retrieval comparison summary contains no mode metrics.",
            error_type="missing_field",
            path=path,
            field="summary",
        )
    return modes


def _required_mapping(
    payload: dict[str, Any],
    key: str,
    path: Path,
    field: str,
) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise RAGHubEvalMetricsError(
            f"Missing object field `{field}` in {path}",
            error_type="missing_field",
            path=path,
            field=field,
        )
    return value


def _required_int(payload: dict[str, Any], key: str, path: Path, field: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise RAGHubEvalMetricsError(
            f"Missing integer field `{field}` in {path}",
            error_type="missing_field",
            path=path,
            field=field,
        )
    return value


def _required_float(payload: dict[str, Any], key: str, path: Path, field: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RAGHubEvalMetricsError(
            f"Missing numeric field `{field}` in {path}",
            error_type="missing_field",
            path=path,
            field=field,
        )
    return float(value)


def _optional_int(payload: dict[str, Any], key: str, path: Path) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise RAGHubEvalMetricsError(
            f"Field `{key}` must be an integer in {path}",
            error_type="invalid_field",
            path=path,
            field=key,
        )
    return value


def _optional_float(payload: dict[str, Any], key: str, path: Path) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RAGHubEvalMetricsError(
            f"Field `{key}` must be numeric in {path}",
            error_type="invalid_field",
            path=path,
            field=key,
        )
    return float(value)


def _optional_mode_score(summary: dict[str, Any], mode: str) -> float | None:
    flat_key = f"{mode}_average_score"
    value = summary.get(flat_key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)

    by_mode = summary.get("by_mode")
    if isinstance(by_mode, dict):
        mode_summary = by_mode.get(mode)
        if isinstance(mode_summary, dict):
            nested_value = mode_summary.get("average_score")
            if isinstance(nested_value, (int, float)) and not isinstance(nested_value, bool):
                return float(nested_value)
    return None


def _format_rejected_ratio(
    rejected_value: Any,
    total: int,
    path: Path,
    field: str,
) -> str:
    if isinstance(rejected_value, str) and "/" in rejected_value:
        return rejected_value
    if isinstance(rejected_value, int) and not isinstance(rejected_value, bool):
        return f"{rejected_value}/{total}"
    raise RAGHubEvalMetricsError(
        f"Missing integer or ratio field `{field}` in {path}",
        error_type="missing_field",
        path=path,
        field=field,
    )
