from __future__ import annotations

from projectpilot.analyzers.eval_metrics_reader import (
    RAGHubEvalMetrics,
    RetrievalModeMetrics,
)
from projectpilot.analyzers.llm_resume_asset_writer import (
    LLMResumeAssetWriter,
    build_resume_asset_prompt,
)
from projectpilot.analyzers.raghub_delivery_analyzer import analyze_raghub_delivery
from projectpilot.schemas.tool_schema import ToolCallStatus


def test_llm_resume_asset_writer_generates_mock_assets(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    metrics = _metrics()
    report = analyze_raghub_delivery(metrics)
    output_path = tmp_path / "resume_assets.md"

    result = LLMResumeAssetWriter().write(
        metrics=metrics,
        delivery_report=report,
        interview_assets_summary="interview cards",
        task_plan_summary="task plan",
        output_path=output_path,
    )

    assert result.provider == "mock"
    assert result.status == ToolCallStatus.SUCCESS
    markdown = output_path.read_text(encoding="utf-8")
    assert "## RAGHub bullets" in markdown
    assert "## ProjectPilot bullets" in markdown
    assert "## RAGHub + ProjectPilot combo description" in markdown
    assert "## Overclaims not to put in resume" in markdown
    assert "out_of_corpus_rejected=12/12" in markdown
    assert "vector/hybrid/tie=12/12/76" in markdown
    assert "human_confirmation_status: pending" in markdown
    assert "不写“ProjectPilot 自动修复 RAGHub”" in markdown


def test_resume_asset_prompt_contains_boundaries() -> None:
    metrics = _metrics()
    prompt = build_resume_asset_prompt(
        metrics=metrics,
        delivery_report=analyze_raghub_delivery(metrics),
        interview_assets_summary="interview",
        task_plan_summary="plan",
    )

    assert "不要编造指标" in prompt
    assert "生产级、企业级、准确率 99%" in prompt
    assert "hybrid 全面优于 vector" in prompt
    assert "不要建议自动修改或自动提交 RAGHub" in prompt
    assert "RAGHub bullets 3 条" in prompt
    assert "ProjectPilot bullets 3 条" in prompt


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
