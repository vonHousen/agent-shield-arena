"""Shared event schema — the contract between event producers and consumers."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(StrEnum):
    CONVERSATION_TURN = "conversation_turn"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationTurn(BaseModel):
    """Who said what."""

    role: Role
    content: str


class ToolCall(BaseModel):
    """System invoked a tool."""

    tool_name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    """Tool returned a result."""

    tool_name: str
    result: Any


class ArenaEvent(BaseModel):
    """Single event in the arena event stream.

    This is the shared contract between the event producer (runner/shielded system)
    and the event consumer (dashboard).
    """

    event_id: str = Field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: EventType
    payload: ConversationTurn | ToolCall | ToolResult
