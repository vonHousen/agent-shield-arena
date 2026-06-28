"""Attack agent memory models for storing conversation outcomes."""

from uuid import uuid4

from pydantic import BaseModel, Field


class AttackMemoryEntry(BaseModel):
    """What gets stored per conversation outcome.

    Args:
        entry_id: Unique identifier for this memory entry.
        strategy_name: Name of the attack strategy that was used.
        success: Whether the attack achieved a business-rule violation.
        violated_rule: The specific business rule that was violated, if any.
        affected_component: The system component that was exploited (e.g. "refund tool").
        signals: Observable cues that indicated success or failure (e.g. "agent revealed address").
        round_number: Which arena round this entry was produced in.
        trace_id: Identifier of the conversation trace this entry corresponds to.
    """

    entry_id: str = Field(default_factory=lambda: uuid4().hex)
    strategy_name: str
    success: bool
    violated_rule: str | None = None
    affected_component: str | None = None
    signals: list[str] = Field(default_factory=list)
    round_number: int
    trace_id: str
