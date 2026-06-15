"""Workflow run records for ProjectPilot Agent."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from projectpilot.feedback.human_feedback import HumanFeedbackStatus
from projectpilot.logging.tool_call_log import tool_call_to_dict
from projectpilot.schemas.tool_schema import ToolCallRecord, ToolCallStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def duration_ms(started_at: datetime, finished_at: datetime) -> int:
    return int((finished_at - started_at).total_seconds() * 1000)


@dataclass(frozen=True)
class WorkflowStepRecord:
    step_name: str
    status: ToolCallStatus
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    message: str = ""


@dataclass(frozen=True)
class WorkflowRunRecord:
    run_id: str
    target_project: str
    workflow_status: str
    started_at: datetime
    finished_at: datetime
    steps: list[WorkflowStepRecord] = field(default_factory=list)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    human_confirmation_status: HumanFeedbackStatus = HumanFeedbackStatus.PENDING

    @property
    def duration_ms(self) -> int:
        return duration_ms(self.started_at, self.finished_at)


def build_workflow_step(
    step_name: str,
    status: ToolCallStatus,
    started_at: datetime,
    finished_at: datetime,
    message: str = "",
) -> WorkflowStepRecord:
    return WorkflowStepRecord(
        step_name=step_name,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms(started_at, finished_at),
        message=message,
    )


def workflow_step_to_dict(record: WorkflowStepRecord) -> dict[str, Any]:
    payload = asdict(record)
    payload["status"] = record.status.value
    payload["started_at"] = record.started_at.isoformat()
    payload["finished_at"] = record.finished_at.isoformat()
    return payload


def workflow_run_to_dict(record: WorkflowRunRecord) -> dict[str, Any]:
    return {
        "run_id": record.run_id,
        "target_project": record.target_project,
        "workflow_status": record.workflow_status,
        "started_at": record.started_at.isoformat(),
        "finished_at": record.finished_at.isoformat(),
        "duration_ms": record.duration_ms,
        "steps": [workflow_step_to_dict(step) for step in record.steps],
        "tool_calls": [tool_call_to_dict(tool_call) for tool_call in record.tool_calls],
        "human_confirmation_status": record.human_confirmation_status.value,
    }
