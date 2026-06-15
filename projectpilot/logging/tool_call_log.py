"""Tool call log helpers for ProjectPilot Agent."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from projectpilot.feedback.human_feedback import HumanFeedbackStatus
from projectpilot.schemas.tool_schema import ToolCallRecord, ToolCallStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def duration_ms(started_at: datetime, finished_at: datetime) -> int:
    return int((finished_at - started_at).total_seconds() * 1000)


def build_tool_call_record(
    tool_name: str,
    status: ToolCallStatus,
    started_at: datetime,
    finished_at: datetime,
    input_summary: dict[str, Any] | None = None,
    output_summary: dict[str, Any] | None = None,
    error_type: str | None = None,
    message: str = "",
) -> ToolCallRecord:
    return ToolCallRecord(
        tool_name=tool_name,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms(started_at, finished_at),
        error_type=error_type,
        message=message,
        input_summary=input_summary or {},
        output_summary=output_summary or {},
    )


def tool_call_to_dict(record: ToolCallRecord) -> dict[str, Any]:
    payload = asdict(record)
    payload["status"] = record.status.value
    payload["started_at"] = record.started_at.isoformat()
    payload["finished_at"] = record.finished_at.isoformat() if record.finished_at else None
    return payload


def write_tool_call_log(
    records: list[ToolCallRecord],
    output_path: str | Path = "outputs/tool_call_log.md",
    human_confirmation_status: HumanFeedbackStatus = HumanFeedbackStatus.PENDING,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        build_tool_call_log_markdown(records, human_confirmation_status),
        encoding="utf-8",
    )
    return path


def build_tool_call_log_markdown(
    records: list[ToolCallRecord],
    human_confirmation_status: HumanFeedbackStatus,
) -> str:
    lines = [
        "# Tool Call Log",
        "",
        "## 1. 本次运行概览",
        "",
        "- 日志类型：v0.1 workflow run log",
        f"- Tool Call 数量：{len(records)}",
        f"- 人工确认状态：{human_confirmation_status.value}",
        "- 说明：该日志用于本地流程追踪，不代表企业级审计系统。",
        "",
        "## 2. Tool Calls",
        "",
        "| Step | Tool | Status | Duration(ms) | Input Summary | Output Summary |",
        "|---|---|---|---:|---|---|",
    ]
    for index, record in enumerate(records, start=1):
        lines.append(
            "| "
            f"{index} | "
            f"{record.tool_name} | "
            f"{record.status.value} | "
            f"{record.duration_ms or 0} | "
            f"{_summary(record.input_summary)} | "
            f"{_summary(record.output_summary)} |"
        )

    lines.extend(
        [
            "",
            "## 3. 失败或空结果",
            "",
            *_failure_lines(records),
            "",
            "## 4. 人工确认状态",
            "",
            f"- 状态：{human_confirmation_status.value}",
            "- 说明：以上建议和记录仅供人工审查，ProjectPilot 不会自动修改代码或提交。",
            "",
        ]
    )
    return "\n".join(lines)


def _summary(payload: dict[str, Any]) -> str:
    if not payload:
        return "-"
    parts = [f"{key}={value}" for key, value in payload.items()]
    return "<br>".join(str(part).replace("|", "/") for part in parts)


def _failure_lines(records: list[ToolCallRecord]) -> list[str]:
    problem_records = [
        record
        for record in records
        if record.status
        in {
            ToolCallStatus.EMPTY_RESULT,
            ToolCallStatus.INVALID_ARGS,
            ToolCallStatus.TIMEOUT,
            ToolCallStatus.PERMISSION_DENIED,
            ToolCallStatus.INTERNAL_ERROR,
        }
    ]
    if not problem_records:
        return ["- 本次运行未记录失败或空结果。"]
    return [
        f"- `{record.tool_name}`：{record.status.value}，{record.message or '无补充说明'}"
        for record in problem_records
    ]
