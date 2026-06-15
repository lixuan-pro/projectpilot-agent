from __future__ import annotations

from projectpilot.feedback.human_feedback import HumanFeedbackStatus
from projectpilot.logging.tool_call_log import build_tool_call_record, utc_now
from projectpilot.schemas.tool_schema import ToolCallStatus
from projectpilot.workflow.workflow_run import (
    WorkflowRunRecord,
    build_workflow_step,
    workflow_run_to_dict,
)


def test_workflow_run_records_multiple_steps() -> None:
    started_at = utc_now()
    finished_at = utc_now()
    steps = [
        build_workflow_step(
            "reading_context",
            ToolCallStatus.SUCCESS,
            started_at,
            finished_at,
            "已读取目标项目上下文。",
        ),
        build_workflow_step(
            "generating_context_summary",
            ToolCallStatus.SUCCESS,
            started_at,
            finished_at,
            "已生成上下文摘要。",
        ),
    ]
    tool_call = build_tool_call_record(
        "context_reader",
        ToolCallStatus.SUCCESS,
        started_at,
        finished_at,
        output_summary={"files_read": 2},
    )
    run = WorkflowRunRecord(
        run_id="test-run",
        target_project="Fake Project",
        workflow_status="completed",
        started_at=started_at,
        finished_at=finished_at,
        steps=steps,
        tool_calls=[tool_call],
        human_confirmation_status=HumanFeedbackStatus.PENDING,
    )

    payload = workflow_run_to_dict(run)

    assert payload["workflow_status"] == "completed"
    assert len(payload["steps"]) == 2
    assert payload["tool_calls"][0]["tool_name"] == "context_reader"
    assert payload["human_confirmation_status"] == "pending"
