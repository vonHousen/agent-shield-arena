"""Shared event schema — the contract between event producers and consumers."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
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
    ATTACK_REFLECTION = "attack_reflection"
    ATTACK_BRIEFING = "attack_briefing"
    ATTACKER_REASONING = "attacker_reasoning"
    DEFENDER_DECISION = "defender_decision"
    DEFENDER_TIP = "defender_tip"
    TRIAGE_DECISION = "triage_decision"
    CONTENT_FILTER = "content_filter"


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


class AttackReflection(BaseModel):
    """Post-mortem tactical analysis produced after each conversation.

    Args:
        strategy_name: Name of the attack strategy that was used.
        round_number: Which arena round this reflection is from.
        success: Whether the attack achieved a business-rule violation.
        tactic_used: The specific conversational tactic the attacker employed.
        why_outcome: Why the tactic succeeded or failed.
        defensive_trigger: Which defensive behavior blocked the attack (None if succeeded).
        suggested_mutations: Concrete alternative approaches for the next attempt.
    """

    strategy_name: str
    round_number: int
    success: bool
    tactic_used: str
    why_outcome: str
    defensive_trigger: str | None = None
    suggested_mutations: list[str] = Field(default_factory=list)


class AttackBriefing(BaseModel):
    """Intelligence briefing given to the attacker before a Round 2+ conversation.

    Args:
        strategy_name: Name of the attack strategy being briefed.
        round_number: Which arena round the briefing precedes.
        memory_context: The exact memory text injected into the attacker's system prompt.
    """

    strategy_name: str
    round_number: int
    memory_context: str


class AttackerReasoning(BaseModel):
    """Per-message chain-of-thought from the attacker explaining its approach.

    Args:
        strategy_name: Name of the attack strategy in use.
        round_number: Which arena round this reasoning occurs in.
        turn_number: Which conversation turn this reasoning precedes.
        reasoning: The attacker's explicit thinking before generating its message.
    """

    strategy_name: str
    round_number: int
    turn_number: int
    reasoning: str


class DefenderDecision(BaseModel):
    """Output of a Defender checkpoint evaluation.

    Args:
        decision_id: Unique identifier for this decision.
        checkpoint: Which checkpoint produced this decision.
        decision: Whether the input or tool call was blocked or allowed.
        reason: Human-readable explanation of the decision.
        matched_patterns: Memory pattern IDs that triggered the decision (empty when no memory).
        confidence: Optional LLM confidence score for the decision.
        tool_name: Name of the evaluated tool (only for on_tool_call checkpoint).
        tool_arguments: Arguments of the evaluated tool call (only for on_tool_call checkpoint).
    """

    decision_id: str = Field(default_factory=lambda: uuid4().hex)
    checkpoint: Literal["on_user_input", "on_tool_call"]
    decision: Literal["BLOCK", "ALLOW"]
    reason: str
    matched_patterns: list[str] = Field(default_factory=list)
    confidence: float | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None


class DefenderTip(BaseModel):
    """Security advisory injected into the assistant context when defender tip mode is active.

    Args:
        tip_text: The full advisory text sent to the shielded system.
    """

    tip_text: str


class TriageDecision(BaseModel):
    """Triage agent output classifying a successful attack into a remediation path.

    Args:
        triage_id: Unique identifier for this triage decision.
        trace_id: Identifier of the trace that was triaged.
        remediation_path: Whether to update defender memory or propose a code change.
        pattern_description: What to store in defender memory, or what structural fix is needed.
        affected_component: The system component involved (e.g. "process_refund").
        rationale: Why this remediation path was chosen.
    """

    triage_id: str = Field(default_factory=lambda: uuid4().hex)
    trace_id: str
    remediation_path: Literal["defender_memory", "code_change"]
    pattern_description: str
    affected_component: str | None = None
    rationale: str


class ContentFilterEvent(BaseModel):
    """Emitted when an LLM call is rejected by the provider's content policy.

    Args:
        source: Which component triggered the filter
            (e.g. "attacker", "shielded_system", "evaluator", "reflector", "triage").
        scenario_name: Active scenario when the filter was triggered.
        turn_number: Conversation turn number (None if post-conversation).
        message: Human-readable description of what happened.
    """

    source: str
    scenario_name: str | None = None
    turn_number: int | None = None
    message: str


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
        | AttackReflection
        | AttackBriefing
        | AttackerReasoning
        | DefenderDecision
        | DefenderTip
        | TriageDecision
        | ContentFilterEvent
    )
