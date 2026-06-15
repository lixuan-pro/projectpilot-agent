"""Workflow state definitions for ProjectPilot Agent."""

from __future__ import annotations

from enum import Enum


class WorkflowState(str, Enum):
    INITIALIZED = "initialized"
    READING_CONTEXT = "reading_context"
    ANALYZING = "analyzing"
    GENERATING_TASKS = "generating_tasks"
    GENERATING_SUGGESTIONS = "generating_suggestions"
    PENDING_CONFIRMATION = "pending_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
