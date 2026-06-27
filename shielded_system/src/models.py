"""Models used by the customer support shielded system."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class ChatRole(StrEnum):
    """Supported roles in a chat transcript."""

    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """A single message in the chat transcript.

    Args:
        role: Speaker role for the message.
        content: Message text.
    """

    role: ChatRole
    content: str


class ToolInvocation(BaseModel):
    """A tool call made by the support agent.

    Args:
        tool_name: Name of the tool that was called.
        arguments: Arguments passed to the tool.
        result: Tool execution result.
    """

    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any]


class Response(BaseModel):
    """Final support-agent response and tool activity.

    Args:
        message: Assistant response shown to the user.
        tool_calls: Tool calls made while preparing the response.
    """

    message: str
    tool_calls: list[ToolInvocation]
