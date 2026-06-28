from __future__ import annotations

from datetime import datetime, timezone

from projectpilot.schemas.tool_schema import (
    ToolCallRecord,
    ToolCallStatus,
    ToolInputSchema,
    ToolOutputSchema,
    ToolSpec,
)
from projectpilot.workflow.state import WorkflowState


def test_tool_spec_can_be_instantiated() -> None:
    spec = ToolSpec(
        name="read_project_file",
        description="Read a project file without modifying it.",
        input_schema=ToolInputSchema(
            properties={"path": {"type": "string"}},
            required=["path"],
        ),
        output_schema=ToolOutputSchema(
            properties={"content": {"type": "string"}},
            required=["content"],
        ),
        is_readonly=True,
    )

    assert spec.name == "read_project_file"
    assert spec.is_readonly is True
    assert spec.input_schema.required == ["path"]


def test_tool_call_status_values_exist() -> None:
    assert ToolCallStatus.SUCCESS.value == "success"
    assert ToolCallStatus.INVALID_ARGS.value == "invalid_args"
    assert ToolCallStatus.TIMEOUT.value == "timeout"
    assert ToolCallStatus.EMPTY_RESULT.value == "empty_result"
    assert ToolCallStatus.PERMISSION_DENIED.value == "permission_denied"
    assert ToolCallStatus.INTERNAL_ERROR.value == "internal_error"
    assert ToolCallStatus.SKIPPED.value == "skipped"


def test_tool_call_record_can_be_instantiated() -> None:
    started_at = datetime.now(timezone.utc)
    record = ToolCallRecord(
        tool_name="read_project_file",
        status=ToolCallStatus.SUCCESS,
        started_at=started_at,
        duration_ms=12,
        message="读取成功。",
    )

    assert record.tool_name == "read_project_file"
    assert record.status is ToolCallStatus.SUCCESS
    assert record.finished_at is None
    assert record.duration_ms == 12
    assert record.message == "读取成功。"


def test_tool_call_record_can_capture_empty_and_internal_error() -> None:
    started_at = datetime.now(timezone.utc)
    empty = ToolCallRecord(
        tool_name="git_reader",
        status=ToolCallStatus.EMPTY_RESULT,
        started_at=started_at,
        message="未读取到 git commit。",
    )
    failed = ToolCallRecord(
        tool_name="context_reader",
        status=ToolCallStatus.INTERNAL_ERROR,
        started_at=started_at,
        error_type="internal_error",
        message="步骤执行失败。",
    )

    assert empty.status is ToolCallStatus.EMPTY_RESULT
    assert failed.status is ToolCallStatus.INTERNAL_ERROR
    assert failed.error_type == "internal_error"


def test_workflow_state_values_exist() -> None:
    assert WorkflowState.INITIALIZED.value == "initialized"
    assert WorkflowState.READING_CONTEXT.value == "reading_context"
    assert WorkflowState.ANALYZING.value == "analyzing"
    assert WorkflowState.GENERATING_TASKS.value == "generating_tasks"
    assert WorkflowState.GENERATING_SUGGESTIONS.value == "generating_suggestions"
    assert WorkflowState.PENDING_CONFIRMATION.value == "pending_confirmation"
    assert WorkflowState.COMPLETED.value == "completed"
    assert WorkflowState.FAILED.value == "failed"
