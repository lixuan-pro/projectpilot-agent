"""Planner models for the read-only ProjectPilot agent workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from projectpilot.schemas.tool_schema import ToolSpec


@dataclass(frozen=True)
class PlannedStep:
    step_id: str
    tool_name: str
    reason: str
    read_only: bool
    requires_human_confirmation: bool
    depends_on: list[str]
    input_summary: dict[str, Any]
    expected_output: str


@dataclass(frozen=True)
class AgentPlan:
    goal: str
    planner_provider: str
    planned_steps: list[PlannedStep]


class MockAgentPlanner:
    """Deterministic planner used by default and by tests."""

    provider = "mock"

    def plan(self, goal: str, tool_catalog: list[ToolSpec]) -> AgentPlan:
        del tool_catalog
        normalized_goal = goal.strip().lower()
        if _is_dangerous_guard_demo_goal(normalized_goal):
            steps = _dangerous_tool_guard_demo_steps()
        elif "analyze raghub delivery readiness" in normalized_goal:
            steps = _raghub_delivery_steps(focus="delivery readiness")
        elif _is_raghub_resume_goal(normalized_goal):
            steps = _raghub_delivery_steps(focus="resume evidence boundaries")
        elif _is_raghub_interview_goal(normalized_goal):
            steps = _raghub_delivery_steps(focus="interview risk review")
        elif _is_raghub_improvement_goal(normalized_goal):
            steps = _raghub_delivery_steps(focus="project improvement opportunities")
        else:
            steps = _generic_read_only_steps()
        return AgentPlan(
            goal=goal,
            planner_provider=self.provider,
            planned_steps=steps,
        )


def _raghub_delivery_steps(focus: str) -> list[PlannedStep]:
    focus_reason = _focus_reason(focus)
    return [
        PlannedStep(
            step_id="read_context",
            tool_name="context_reader",
            reason=f"Read bounded repository evidence before making {focus_reason}.",
            read_only=True,
            requires_human_confirmation=False,
            depends_on=[],
            input_summary={
                "focus": focus,
                "evidence": "README, docs, tests, eval files",
            },
            expected_output="bounded_context_snapshot",
        ),
        PlannedStep(
            step_id="read_git_log",
            tool_name="git_reader",
            reason=f"Read recent commit subjects as evidence for {focus}.",
            read_only=True,
            requires_human_confirmation=False,
            depends_on=[],
            input_summary={"focus": focus, "max_commits": "configured"},
            expected_output="recent_git_commits",
        ),
        PlannedStep(
            step_id="read_eval_metrics",
            tool_name="raghub_eval_metrics_reader",
            reason=(
                "Parse Eval-100 JSON metrics deterministically before planning "
                f"{focus}."
            ),
            read_only=True,
            requires_human_confirmation=False,
            depends_on=[],
            input_summary={"focus": focus, "case": "raghub_eval100"},
            expected_output="raghub_eval100_metrics",
        ),
        PlannedStep(
            step_id="analyze_delivery_risks",
            tool_name="raghub_delivery_analyzer",
            reason=(
                "Classify RAGHub delivery risks from Eval-100 metrics with focus "
                f"on {focus}."
            ),
            read_only=True,
            requires_human_confirmation=True,
            depends_on=["read_eval_metrics"],
            input_summary={"focus": focus, "source": "raghub_eval100_metrics"},
            expected_output="delivery_risk_report",
        ),
        PlannedStep(
            step_id="generate_next_tasks",
            tool_name="next_tasks_writer",
            reason=(
                "Convert open risks and roadmap items into human-reviewed next "
                f"tasks for {focus}."
            ),
            read_only=True,
            requires_human_confirmation=True,
            depends_on=["analyze_delivery_risks"],
            input_summary={"focus": focus, "source": "delivery_risk_report"},
            expected_output="agent_next_tasks",
        ),
        PlannedStep(
            step_id="check_consistency",
            tool_name="consistency_checker",
            reason=(
                "Check generated ProjectPilot outputs for unsupported overclaims "
                f"before using them for {focus}."
            ),
            read_only=True,
            requires_human_confirmation=True,
            depends_on=["generate_next_tasks"],
            input_summary={"focus": focus, "scope": "ProjectPilot agent outputs"},
            expected_output="consistency_check",
        ),
        PlannedStep(
            step_id="write_agent_summary",
            tool_name="agent_summary_writer",
            reason=(
                "Record planned, executed, and skipped steps for human review "
                f"of {focus}."
            ),
            read_only=True,
            requires_human_confirmation=True,
            depends_on=[
                "read_context",
                "read_git_log",
                "read_eval_metrics",
                "analyze_delivery_risks",
                "generate_next_tasks",
                "check_consistency",
            ],
            input_summary={"focus": focus, "summary": "planned/executed/skipped"},
            expected_output="agent_run_summary",
        ),
    ]


def _generic_read_only_steps() -> list[PlannedStep]:
    return [
        PlannedStep(
            step_id="read_context",
            tool_name="context_reader",
            reason="Read bounded repository evidence for the requested goal.",
            read_only=True,
            requires_human_confirmation=False,
            depends_on=[],
            input_summary={"goal": "generic"},
            expected_output="bounded_context_snapshot",
        ),
        PlannedStep(
            step_id="read_git_log",
            tool_name="git_reader",
            reason="Read recent commit subjects without modifying the repository.",
            read_only=True,
            requires_human_confirmation=False,
            depends_on=[],
            input_summary={"max_commits": "configured"},
            expected_output="recent_git_commits",
        ),
        PlannedStep(
            step_id="write_agent_summary",
            tool_name="agent_summary_writer",
            reason="Record the read-only agent run for human review.",
            read_only=True,
            requires_human_confirmation=True,
            depends_on=["read_context", "read_git_log"],
            input_summary={"summary": "planned/executed/skipped"},
            expected_output="agent_run_summary",
        ),
    ]


def _dangerous_tool_guard_demo_steps() -> list[PlannedStep]:
    return [
        PlannedStep(
            step_id="read_context",
            tool_name="context_reader",
            reason="Read safe context first so the guard demo has a normal executed step.",
            read_only=True,
            requires_human_confirmation=False,
            depends_on=[],
            input_summary={"demo": "dangerous_tool_guard"},
            expected_output="bounded_context_snapshot",
        ),
        PlannedStep(
            step_id="attempt_git_push",
            tool_name="git_push",
            reason="Demonstrate that repository push tools are skipped.",
            read_only=False,
            requires_human_confirmation=True,
            depends_on=["read_context"],
            input_summary={"demo": "dangerous_tool_guard"},
            expected_output="skipped_by_router",
        ),
        PlannedStep(
            step_id="attempt_modify_target_project",
            tool_name="modify_target_project",
            reason="Demonstrate that target-project mutation tools are skipped.",
            read_only=False,
            requires_human_confirmation=True,
            depends_on=["read_context"],
            input_summary={"demo": "dangerous_tool_guard"},
            expected_output="skipped_by_router",
        ),
        PlannedStep(
            step_id="attempt_deploy",
            tool_name="deploy",
            reason="Demonstrate that deployment tools are skipped.",
            read_only=False,
            requires_human_confirmation=True,
            depends_on=["read_context"],
            input_summary={"demo": "dangerous_tool_guard"},
            expected_output="skipped_by_router",
        ),
        PlannedStep(
            step_id="write_agent_summary",
            tool_name="agent_summary_writer",
            reason="Record the dangerous tool guard demo for human review.",
            read_only=True,
            requires_human_confirmation=True,
            depends_on=[
                "read_context",
                "attempt_git_push",
                "attempt_modify_target_project",
                "attempt_deploy",
            ],
            input_summary={"demo": "dangerous_tool_guard"},
            expected_output="agent_run_summary",
        ),
    ]


def _is_dangerous_guard_demo_goal(normalized_goal: str) -> bool:
    return (
        "demo dangerous tool guard" in normalized_goal
        or "演示危险工具拦截" in normalized_goal
    )


def _is_raghub_improvement_goal(normalized_goal: str) -> bool:
    return (
        "raghub" in normalized_goal
        and (
            "增强" in normalized_goal
            or "改进" in normalized_goal
            or "可以增强" in normalized_goal
            or "还有什么" in normalized_goal
        )
    )


def _is_raghub_interview_goal(normalized_goal: str) -> bool:
    return "raghub" in normalized_goal and (
        "面试" in normalized_goal or "问穿" in normalized_goal
    )


def _is_raghub_resume_goal(normalized_goal: str) -> bool:
    return "raghub" in normalized_goal and (
        "简历" in normalized_goal or "resume" in normalized_goal
    )


def _focus_reason(focus: str) -> str:
    if focus == "project improvement opportunities":
        return "RAGHub improvement recommendations"
    if focus == "interview risk review":
        return "interview-facing RAGHub claims"
    if focus == "resume evidence boundaries":
        return "resume-facing RAGHub claims"
    return "delivery claims"
