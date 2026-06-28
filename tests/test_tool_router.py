from __future__ import annotations

from projectpilot.agent.planner import PlannedStep
from projectpilot.agent.tool_router import AgentToolRouter


def test_tool_router_allows_whitelisted_tool() -> None:
    router = AgentToolRouter(
        handlers={"context_reader": lambda step: {"step_id": step.step_id}},
    )

    result = router.execute(_step("read_context", "context_reader"))

    assert result.status == "executed"
    assert result.reason == "tool_allowed"
    assert result.output_summary == {"step_id": "read_context"}


def test_tool_router_rejects_dangerous_tool() -> None:
    router = AgentToolRouter()

    result = router.execute(
        _step("attempt_push", "git_push", read_only=False),
    )

    assert result.status == "skipped"
    assert result.reason == "dangerous_tool_for_read_only_agent"


def test_tool_router_rejects_unknown_tool() -> None:
    router = AgentToolRouter()

    result = router.execute(_step("mystery", "unknown_tool"))

    assert result.status == "skipped"
    assert result.reason == "tool_not_allowed"


def _step(
    step_id: str,
    tool_name: str,
    read_only: bool = True,
) -> PlannedStep:
    return PlannedStep(
        step_id=step_id,
        tool_name=tool_name,
        reason="test",
        read_only=read_only,
        requires_human_confirmation=True,
        depends_on=[],
        input_summary={},
        expected_output="test",
    )

