from __future__ import annotations

from projectpilot.analyzers.eval_metrics_reader import (
    RAGHubEvalMetrics,
    RetrievalModeMetrics,
)
from projectpilot.analyzers.llm_interview_asset_writer import (
    LLMInterviewAssetWriter,
    build_interview_asset_prompt,
)
from projectpilot.analyzers.raghub_delivery_analyzer import analyze_raghub_delivery
from projectpilot.schemas.tool_schema import ToolCallStatus


def test_llm_interview_asset_writer_generates_mock_case_cards(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    metrics = _metrics()
    report = analyze_raghub_delivery(metrics)
    output_path = tmp_path / "interview_case_cards.md"

    result = LLMInterviewAssetWriter().write(
        metrics=metrics,
        delivery_report=report,
        risk_review_summary="source competition open",
        task_plan_summary="hybrid remains experimental",
        output_path=output_path,
    )

    assert result.provider == "mock"
    assert result.status == ToolCallStatus.SUCCESS
    markdown = output_path.read_text(encoding="utf-8")
    assert "## Case 1: source competition and hybrid retrieval experiment" in markdown
    assert "## Case 2: Eval-100 exposed no-answer misses and fix" in markdown
    assert "## Case 3: why hybrid is not default" in markdown
    assert "## Case 4: how ProjectPilot analyzes RAGHub delivery evidence" in markdown
    assert "### 问题背景" in markdown
    assert "### 30 秒回答" in markdown
    assert "### 60 秒回答" in markdown
    assert "### 不能夸大的点" in markdown
    assert "human_confirmation_status=pending" in markdown
    assert "不自动修改 RAGHub" in markdown


def test_interview_asset_prompt_contains_boundaries() -> None:
    metrics = _metrics()
    prompt = build_interview_asset_prompt(
        metrics=metrics,
        delivery_report=analyze_raghub_delivery(metrics),
        risk_review_summary="risk",
        task_plan_summary="plan",
    )

    assert "不要编造不存在指标" in prompt
    assert "不要声称 RAGHub 是生产级平台" in prompt
    assert "不要声称 hybrid 已经全面胜过 vector" in prompt
    assert "不要建议自动修改或自动提交 RAGHub" in prompt
    assert "source competition and hybrid retrieval experiment" in prompt
    assert "how ProjectPilot analyzes RAGHub delivery evidence" in prompt


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
