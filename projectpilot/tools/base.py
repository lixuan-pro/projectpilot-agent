"""Base tool contracts for future ProjectPilot tools."""

from __future__ import annotations

from typing import Protocol

from projectpilot.schemas.tool_schema import ToolSpec


class ProjectPilotTool(Protocol):
    spec: ToolSpec

    def run(self, **kwargs: object) -> object:
        """Run the tool with validated keyword arguments."""
