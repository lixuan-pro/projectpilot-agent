from __future__ import annotations

from projectpilot.feedback.human_feedback import (
    HumanFeedbackStatus,
    default_human_feedback,
)


def test_default_human_feedback_is_pending() -> None:
    feedback = default_human_feedback()

    assert feedback.status is HumanFeedbackStatus.PENDING
    assert "不会自动修改" in feedback.message
