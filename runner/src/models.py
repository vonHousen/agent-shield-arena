"""Data models for the attack runner."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolExecution:
    """A tool call and its returned result.

    Args:
        tool_name: Name of the invoked tool.
        arguments: Arguments passed to the tool.
        result: Value returned by the tool.
    """

    tool_name: str
    arguments: dict[str, Any]
    result: Any


@dataclass(frozen=True)
class ShieldedSystemResponse:
    """Response returned by a shielded system chat call.

    Args:
        content: Assistant response text.
        tool_executions: Tool calls made while producing the response.
    """

    content: str
    tool_executions: list[ToolExecution] = field(default_factory=list)
