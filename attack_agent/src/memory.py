"""Attack agent memory models for storing conversation outcomes."""

from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field


class TacticalReflection(BaseModel):
    """Structured tactical feedback produced by the reflector after each conversation.

    Args:
        tactic_used: The specific conversational tactic the attacker employed.
        why_outcome: Why the tactic succeeded or failed — what behavior was triggered or bypassed.
        defensive_trigger: Which defensive behavior blocked the attack (None if attack succeeded).
        suggested_mutations: Concrete alternative approaches for the next attempt.
        tactic_achieved_goal: Whether the tactic operationally achieved its intended effect,
            regardless of whether a formal business-rule violation was detected.
    """

    tactic_used: str
    why_outcome: str
    defensive_trigger: str | None = None
    suggested_mutations: list[str] = Field(default_factory=list)
    tactic_achieved_goal: bool = False


class AttackMemoryEntry(BaseModel):
    """What gets stored per conversation outcome.

    Args:
        entry_id: Unique identifier for this memory entry.
        strategy_name: Name of the attack strategy that was used.
        success: Whether the attack achieved a business-rule violation.
        violated_rule: The specific business rule that was violated, if any.
        affected_component: The system component that was exploited (e.g. "refund tool").
        reflection: Tactical feedback from the reflector explaining how/why the attack played out.
        round_number: Which arena round this entry was produced in.
        trace_id: Identifier of the conversation trace this entry corresponds to.
    """

    entry_id: str = Field(default_factory=lambda: uuid4().hex)
    strategy_name: str
    success: bool
    violated_rule: str | None = None
    affected_component: str | None = None
    reflection: TacticalReflection | None = None
    round_number: int
    trace_id: str


class StrategySummary(BaseModel):
    """Aggregated memory outcomes for one strategy.

    Args:
        strategy_name: Name of the summarized strategy.
        success_count: Number of successful attempts.
        failure_count: Number of failed attempts.
        success_rate: Successful attempts divided by total attempts.
        last_violated_rules: Recent violated rules recorded for successful attempts.
        last_reflection: Tactical reflection from the most recent attempt.
    """

    strategy_name: str
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    last_violated_rules: list[str] = Field(default_factory=list)
    last_reflection: TacticalReflection | None = None


class AttackMemory:
    """JSONL-backed store for attack outcomes.

    Args:
        memory_path: Path to the attack memory JSONL file.
    """

    def __init__(self, memory_path: Path) -> None:
        self.memory_path = memory_path

    def append(self, entry: AttackMemoryEntry) -> None:
        """Append one attack memory entry as a JSON line.

        Args:
            entry: Memory entry to persist.
        """
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        with self.memory_path.open("a", encoding="utf-8") as memory_file:
            memory_file.write(f"{entry.model_dump_json()}\n")

    def load_all(self) -> list[AttackMemoryEntry]:
        """Load all memory entries from disk."""
        if not self.memory_path.exists():
            return []

        entries = []
        with self.memory_path.open(encoding="utf-8") as memory_file:
            for line in memory_file:
                stripped_line = line.strip()
                if stripped_line:
                    entries.append(AttackMemoryEntry.model_validate_json(stripped_line))
        return entries

    def get_by_strategy(self, strategy_name: str) -> list[AttackMemoryEntry]:
        """Load memory entries for one strategy.

        Args:
            strategy_name: Strategy name to filter by.
        """
        return [entry for entry in self.load_all() if entry.strategy_name == strategy_name]

    def summary(self) -> dict[str, StrategySummary]:
        """Return per-strategy outcome summaries."""
        summaries: dict[str, StrategySummary] = {}

        for entry in self.load_all():
            summary = summaries.setdefault(entry.strategy_name, StrategySummary(strategy_name=entry.strategy_name))
            if entry.success:
                summary.success_count += 1
            else:
                summary.failure_count += 1

            if entry.violated_rule is not None:
                summary.last_violated_rules = [entry.violated_rule]
            summary.last_reflection = entry.reflection

        for summary in summaries.values():
            total_count = summary.success_count + summary.failure_count
            summary.success_rate = summary.success_count / total_count

        return summaries
