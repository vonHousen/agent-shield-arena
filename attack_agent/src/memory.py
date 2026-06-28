"""Attack agent memory models for storing conversation outcomes."""

from pathlib import Path
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


class AttackMemoryStore:
    """Append-only JSONL storage for attack memory entries.

    Args:
        path: JSONL file path used for persisted attack memory entries.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def append(self, entry: AttackMemoryEntry) -> None:
        """Append one attack memory entry as a JSON line.

        Args:
            entry: Memory entry to persist.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a") as file:
            file.write(entry.model_dump_json() + "\n")

    def read_all(self) -> list[AttackMemoryEntry]:
        """Read all persisted attack memory entries in file order."""
        if not self._path.exists():
            return []

        with self._path.open() as file:
            return [AttackMemoryEntry.model_validate_json(line) for line in file if line.strip()]
