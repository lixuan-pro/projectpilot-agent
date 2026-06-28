"""Static tool router for the planner-driven read-only agent workflow."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from projectpilot.agent.planner import PlannedStep
from projectpilot.schemas.tool_schema import ToolInputSchema, ToolOutputSchema, ToolSpec


READ_ONLY_TOOL_ALLOWLIST = {
    "context_reader",
    "git_reader",
    "raghub_eval_metrics_reader",
    "raghub_delivery_analyzer",
    "risk_advisor",
    "next_tasks_writer",
    "consistency_checker",
    "llm_review_advisor",
    "agent_summary_writer",
}

DANGEROUS_TOOLS = {
    "write_code",
    "modify_target_project",
    "delete_file",
    "git_add",
    "git_commit",
    "git_push",
    "deploy",
    "run_shell_command",
}

ToolHandler = Callable[[PlannedStep], dict[str, Any]]


@dataclass(frozen=True)
class RoutedToolResult:
    step_id: str
    tool_name: str
    status: Literal["executed", "skipped", "failed"]
    reason: str
    output_summary: dict[str, Any]


class AgentToolRouter:
    """Validate planned tool names against a fixed allowlist before execution."""

    def __init__(
        self,
        handlers: Mapping[str, ToolHandler] | None = None,
        allowlist: set[str] | None = None,
        dangerous_tools: set[str] | None = None,
    ) -> None:
        self._handlers = dict(handlers or {})
        self._allowlist = set(allowlist or READ_ONLY_TOOL_ALLOWLIST)
        self._dangerous_tools = set(dangerous_tools or DANGEROUS_TOOLS)

    def execute(self, step: PlannedStep) -> RoutedToolResult:
        skip_reason = self._skip_reason(step)
        if skip_reason is not None:
            return RoutedToolResult(
                step_id=step.step_id,
                tool_name=step.tool_name,
                status="skipped",
                reason=skip_reason,
                output_summary={},
            )

        handler = self._handlers.get(step.tool_name)
        if handler is None:
            return RoutedToolResult(
                step_id=step.step_id,
                tool_name=step.tool_name,
                status="executed",
                reason="tool_allowed",
                output_summary={},
            )

        try:
            output_summary = handler(step)
        except Exception as exc:
            return RoutedToolResult(
                step_id=step.step_id,
                tool_name=step.tool_name,
                status="failed",
                reason="internal_error",
                output_summary={
                    "error_type": exc.__class__.__name__,
                    "message": str(exc),
                },
            )

        return RoutedToolResult(
            step_id=step.step_id,
            tool_name=step.tool_name,
            status="executed",
            reason="tool_allowed",
            output_summary=output_summary,
        )

    def _skip_reason(self, step: PlannedStep) -> str | None:
        if step.tool_name in self._dangerous_tools:
            return "dangerous_tool_for_read_only_agent"
        if not step.read_only:
            return "non_read_only_step"
        if step.tool_name not in self._allowlist:
            return "tool_not_allowed"
        return None


def build_read_only_tool_catalog() -> list[ToolSpec]:
    descriptions = {
        "context_reader": "Read bounded target-project context without modification.",
        "git_reader": "Read recent git commit subjects without mutation.",
        "raghub_eval_metrics_reader": "Parse RAGHub Eval-100 JSON metrics.",
        "raghub_delivery_analyzer": "Classify RAGHub delivery risks from metrics.",
        "risk_advisor": "Generate read-only risk advice.",
        "next_tasks_writer": "Write ProjectPilot next-task suggestions.",
        "consistency_checker": "Check generated outputs for unsafe claims.",
        "llm_review_advisor": "Optionally review generated reports.",
        "agent_summary_writer": "Write the agent run summary.",
    }
    return [
        ToolSpec(
            name=name,
            description=descriptions[name],
            input_schema=ToolInputSchema(properties={"step_id": {"type": "string"}}),
            output_schema=ToolOutputSchema(properties={"summary": {"type": "object"}}),
            is_readonly=True,
        )
        for name in sorted(READ_ONLY_TOOL_ALLOWLIST)
    ]

