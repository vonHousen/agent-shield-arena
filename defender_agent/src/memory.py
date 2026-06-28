"""Defender memory models for storing learned exploit patterns."""

from pathlib import Path
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


class DefenderMemory:
    """JSONL-backed store for learned defender exploit patterns.

    Args:
        memory_path: Path to the defender memory JSONL file.
    """

    def __init__(self, memory_path: Path) -> None:
        self.memory_path = memory_path

    def append(self, entry: DefenderMemoryEntry) -> None:
        """Append one defender memory entry as a JSON line.

        Args:
            entry: Memory entry to persist.
        """
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        with self.memory_path.open("a", encoding="utf-8") as memory_file:
            memory_file.write(f"{entry.model_dump_json()}\n")

    def load_all(self) -> list[DefenderMemoryEntry]:
        """Load all defender memory entries from disk."""
        if not self.memory_path.exists():
            return []

        entries = []
        with self.memory_path.open(encoding="utf-8") as memory_file:
            for line in memory_file:
                stripped_line = line.strip()
                if stripped_line:
                    entries.append(DefenderMemoryEntry.model_validate_json(stripped_line))
        return entries

    def get_by_component(self, component: str) -> list[DefenderMemoryEntry]:
        """Load defender memory entries for one affected component.

        Args:
            component: Affected component to filter by.
        """
        return [entry for entry in self.load_all() if entry.affected_component == component]

    def format_for_prompt(self) -> str:
        """Format all defender memory entries as human-readable prompt context."""
        entries = self.load_all()
        if not entries:
            return "No known attack patterns."

        formatted_entries = []
        for index, entry in enumerate(entries, start=1):
            formatted_entries.append(_format_entry_for_prompt(index, entry))
        return "\n\n".join(formatted_entries)


def _format_entry_for_prompt(index: int, entry: DefenderMemoryEntry) -> str:
    component = entry.affected_component or "unknown component"
    violated_rule = entry.violated_rule or "unknown rule"
    signals = ", ".join(entry.signals) if entry.signals else "no specific signals recorded"

    return (
        f"Known attack pattern #{index}: {entry.attack_intent}\n"
        f"- Affected component: {component}\n"
        f"- Violated rule: {violated_rule}\n"
        f"- Signals: {signals}\n"
        f"- Defensive action: {entry.defensive_action}"
    )
