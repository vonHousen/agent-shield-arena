"""Shared event schema — the contract between event producers and consumers."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(StrEnum):
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    ROUND_STARTED = "round_started"
    SCENARIO_STARTED = "scenario_started"
    CONVERSATION_TURN = "conversation_turn"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    EVALUATION_VERDICT = "evaluation_verdict"


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class TracedToolExecution(BaseModel):
    """A tool call paired with its result, for inclusion in a conversation trace.

    Args:
        tool_name: Name of the invoked tool.
        arguments: Arguments passed to the tool.
        result: Value returned by the tool.
    """

    tool_name: str
    arguments: dict[str, Any]
    result: Any


class ConversationTurn(BaseModel):
    """A single conversation message, optionally carrying tool executions.

    Args:
        role: Who sent this message.
        content: Message text.
        tool_executions: Tool calls made during this turn (assistant turns only).
    """

    role: Role
    content: str
    tool_executions: list[TracedToolExecution] = Field(default_factory=list)


class ToolCall(BaseModel):
    """System invoked a tool."""

    tool_name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    """Tool returned a result."""

    tool_name: str
    result: Any


class RunStarted(BaseModel):
    """Marks the beginning of an arena run."""

    scenario_count: int


class RoundStarted(BaseModel):
    """Marks the beginning of an arena round.

    Args:
        round_number: One-based arena round number.
        strategy_count: Number of strategies scheduled for this round.
    """

    round_number: int
    strategy_count: int


class RunCompleted(BaseModel):
    """Marks the end of an arena run."""


class ScenarioStarted(BaseModel):
    """Marks the beginning of a new attack scenario."""

    scenario_name: str


class Trace(BaseModel):
    """Structured representation of a full conversation for evaluation.

    Args:
        trace_id: Unique identifier for this trace.
        scenario_name: Name of the attack scenario that produced this conversation.
        strategy_name: Name of the attack strategy used.
        conversation: Ordered list of conversation turns.
        timestamp: When the conversation took place.
    """

    trace_id: str = Field(default_factory=lambda: uuid4().hex)
    scenario_name: str
    strategy_name: str
    conversation: list[ConversationTurn]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def tool_executions(self) -> list[TracedToolExecution]:
        """Flattened list of all tool executions across conversation turns."""
        return [exe for turn in self.conversation for exe in turn.tool_executions]


class EvaluationVerdict(BaseModel):
    """Structured output from the evaluator judging an attack conversation.

    Args:
        eval_id: Unique identifier for this evaluation.
        trace_id: Identifier of the trace that was evaluated.
        success: Whether the attacker achieved a business-rule violation.
        violation_type: Category of the violation (e.g. "refund bypass", "data leak").
        violated_rule: The specific business rule that was violated.
        evidence: Excerpt or explanation proving the violation.
        severity: How severe the violation is (e.g. "low", "medium", "high").
    """

    eval_id: str = Field(default_factory=lambda: uuid4().hex)
    trace_id: str
    success: bool
    violation_type: str | None = None
    violated_rule: str | None = None
    evidence: str | None = None
    severity: str | None = None


class ArenaEvent(BaseModel):
    """Single event in the arena event stream.

    This is the shared contract between the event producer (runner/shielded system)
    and the event consumer (dashboard).
    """

    event_id: str = Field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: EventType
    payload: (
        ConversationTurn
        | ToolCall
        | ToolResult
        | ScenarioStarted
        | RunStarted
        | RoundStarted
        | RunCompleted
        | EvaluationVerdict
    )
