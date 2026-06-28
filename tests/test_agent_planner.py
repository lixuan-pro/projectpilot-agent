from __future__ import annotations

from projectpilot.agent.planner import MockAgentPlanner
from projectpilot.agent.tool_router import build_read_only_tool_catalog


def test_mock_planner_generates_raghub_delivery_plan() -> None:
    planner = MockAgentPlanner()

    plan = planner.plan(
        goal="analyze RAGHub delivery readiness",
        tool_catalog=build_read_only_tool_catalog(),
    )

    assert plan.planner_provider == "mock"
    assert plan.goal == "analyze RAGHub delivery readiness"
    step_ids = [step.step_id for step in plan.planned_steps]
    assert step_ids == [
        "read_context",
        "read_git_log",
        "read_eval_metrics",
        "analyze_delivery_risks",
        "generate_next_tasks",
        "check_consistency",
        "write_agent_summary",
    ]
    assert all(step.reason for step in plan.planned_steps)
    assert all(step.read_only for step in plan.planned_steps)


def test_mock_planner_uses_whitelisted_tools_for_raghub_goal() -> None:
    plan = MockAgentPlanner().plan(
        goal="analyze RAGHub delivery readiness",
        tool_catalog=build_read_only_tool_catalog(),
    )

    tool_names = {step.tool_name for step in plan.planned_steps}

    assert "context_reader" in tool_names
    assert "git_reader" in tool_names
    assert "raghub_eval_metrics_reader" in tool_names
    assert "raghub_delivery_analyzer" in tool_names
    assert "next_tasks_writer" in tool_names
    assert "consistency_checker" in tool_names
    assert "agent_summary_writer" in tool_names


def test_mock_planner_supports_chinese_raghub_improvement_goal() -> None:
    plan = MockAgentPlanner().plan(
        goal="看看我的 RAGHub 项目目前还有什么可以增强的",
        tool_catalog=build_read_only_tool_catalog(),
    )

    assert plan.planner_provider == "mock"
    assert [step.step_id for step in plan.planned_steps] == [
        "read_context",
        "read_git_log",
        "read_eval_metrics",
        "analyze_delivery_risks",
        "generate_next_tasks",
        "check_consistency",
        "write_agent_summary",
    ]
    assert any(
        step.input_summary.get("focus") == "project improvement opportunities"
        for step in plan.planned_steps
    )


def test_mock_planner_varies_focus_for_interview_and_resume_goals() -> None:
    planner = MockAgentPlanner()

    interview_plan = planner.plan(
        goal="检查 RAGHub 面试会不会被问穿",
        tool_catalog=build_read_only_tool_catalog(),
    )
    resume_plan = planner.plan(
        goal="看看 RAGHub 是否适合写进简历",
        tool_catalog=build_read_only_tool_catalog(),
    )

    assert interview_plan.planned_steps[0].input_summary["focus"] == (
        "interview risk review"
    )
    assert resume_plan.planned_steps[0].input_summary["focus"] == (
        "resume evidence boundaries"
    )
    assert interview_plan.planned_steps[0].reason != resume_plan.planned_steps[0].reason


def test_mock_planner_generates_dangerous_tool_guard_demo_plan() -> None:
    plan = MockAgentPlanner().plan(
        goal="demo dangerous tool guard",
        tool_catalog=build_read_only_tool_catalog(),
    )

    assert [step.tool_name for step in plan.planned_steps] == [
        "context_reader",
        "git_push",
        "modify_target_project",
        "deploy",
        "agent_summary_writer",
    ]
    assert [step.read_only for step in plan.planned_steps] == [
        True,
        False,
        False,
        False,
        True,
    ]
