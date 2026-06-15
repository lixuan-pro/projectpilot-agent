"""Human feedback state for suggestion outputs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HumanFeedbackStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMMENT_REQUIRED = "comment_required"


@dataclass(frozen=True)
class HumanFeedbackRecord:
    status: HumanFeedbackStatus = HumanFeedbackStatus.PENDING
    message: str = (
        "以上建议仅供人工审查，ProjectPilot 不会自动修改代码、自动提交或自动部署。"
    )


def default_human_feedback() -> HumanFeedbackRecord:
    return HumanFeedbackRecord()
