"""Draft tool schema models for ProjectPilot Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ToolCallStatus(str, Enum):
    SUCCESS = "success"
    INVALID_ARGS = "invalid_args"
    TIMEOUT = "timeout"
    EMPTY_RESULT = "empty_result"
    PERMISSION_DENIED = "permission_denied"
    INTERNAL_ERROR = "internal_error"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class ToolInputSchema:
    type: str = "object"
    properties: dict[str, Any] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ToolOutputSchema:
    type: str = "object"
    properties: dict[str, Any] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: ToolInputSchema
    output_schema: ToolOutputSchema
    is_readonly: bool = True


@dataclass(frozen=True)
class ToolCallRecord:
    tool_name: str
    status: ToolCallStatus
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = None
    error_type: str | None = None
    message: str = ""
    input_summary: dict[str, Any] = field(default_factory=dict)
    output_summary: dict[str, Any] = field(default_factory=dict)
