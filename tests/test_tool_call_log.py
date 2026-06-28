from __future__ import annotations

from projectpilot.feedback.human_feedback import HumanFeedbackStatus
from projectpilot.logging.tool_call_log import (
    build_tool_call_record,
    build_tool_call_log_markdown,
    utc_now,
)
from projectpilot.schemas.tool_schema import ToolCallStatus


def test_tool_call_log_markdown_includes_success_record() -> None:
    started_at = utc_now()
    finished_at = utc_now()
    record = build_tool_call_record(
        tool_name="context_reader",
        status=ToolCallStatus.SUCCESS,
        started_at=started_at,
        finished_at=finished_at,
        input_summary={"project": "fake"},
        output_summary={"files_read": 3},
        message="已读取目标项目上下文。",
    )

    markdown = build_tool_call_log_markdown(
        [record],
        human_confirmation_status=HumanFeedbackStatus.PENDING,
    )

    assert "# Tool Call Log" in markdown
    assert "context_reader" in markdown
    assert "success" in markdown
    assert "pending" in markdown


def test_tool_call_log_records_empty_and_internal_error() -> None:
    started_at = utc_now()
    finished_at = utc_now()
    records = [
        build_tool_call_record(
            tool_name="git_reader",
            status=ToolCallStatus.EMPTY_RESULT,
            started_at=started_at,
            finished_at=finished_at,
            message="未读取到 git commit 记录。",
        ),
        build_tool_call_record(
            tool_name="risk_advisor",
            status=ToolCallStatus.INTERNAL_ERROR,
            started_at=started_at,
            finished_at=finished_at,
            error_type="internal_error",
            message="步骤执行失败。",
        ),
    ]

    markdown = build_tool_call_log_markdown(
        records,
        human_confirmation_status=HumanFeedbackStatus.PENDING,
    )

    assert "empty_result" in markdown
    assert "internal_error" in markdown
    assert "失败或空结果" in markdown


def test_tool_call_log_records_skipped_step() -> None:
    started_at = utc_now()
    finished_at = utc_now()
    record = build_tool_call_record(
        tool_name="git_push",
        status=ToolCallStatus.SKIPPED,
        started_at=started_at,
        finished_at=finished_at,
        error_type="dangerous_tool_for_read_only_agent",
        message="dangerous_tool_for_read_only_agent",
    )

    markdown = build_tool_call_log_markdown(
        [record],
        human_confirmation_status=HumanFeedbackStatus.PENDING,
    )

    assert "git_push" in markdown
    assert "skipped" in markdown
    assert "dangerous_tool_for_read_only_agent" in markdown
