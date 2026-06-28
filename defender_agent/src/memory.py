"""Defender memory models for storing learned exploit patterns."""

from uuid import uuid4

from pydantic import BaseModel, Field


class DefenderMemoryEntry(BaseModel):
    """A learned exploit pattern extracted by the Triage Agent.

    Symmetric to AttackMemoryEntry but stores defensive patterns — observable
    indicators and recommended actions for the Defender to apply at its
    checkpoints.

    Args:
        entry_id: Unique identifier for this memory entry.
        attack_intent: Abstracted description of what the attacker tried.
        violated_rule: The business rule that was violated, if identified.
        affected_component: The system component targeted (e.g. "process_refund").
        signals: Observable indicators the Defender should watch for.
        defensive_action: What the Defender should do when signals match
            (e.g. "BLOCK tool call with multiple small refunds").
        source_trace_id: Identifier of the conversation trace this pattern was extracted from.
        round_number: Which arena round produced this pattern.
    """

    entry_id: str = Field(default_factory=lambda: uuid4().hex)
    attack_intent: str
    violated_rule: str | None = None
    affected_component: str | None = None
    signals: list[str] = Field(default_factory=list)
    defensive_action: str
    source_trace_id: str
    round_number: int
