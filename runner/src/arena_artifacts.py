"""Run-scoped memory artifacts for the v3 arena loop."""

import os
from pathlib import Path

from attack_agent.src.memory import AttackMemoryEntry

ATTACK_MEMORY_FILENAME = "attack_memory.jsonl"
DEFAULT_MEMORY_DIR = Path("data/memory")


def create_memory_run_dir(memory_dir: Path, run_id: str) -> Path:
    """Create a memory artifact directory matching an event run id.

    Args:
        memory_dir: Parent directory for all memory run directories.
        run_id: Timestamped run id shared with the event directory.
    """
    run_dir = memory_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    latest_link = memory_dir / "latest"
    if latest_link.is_symlink() or latest_link.exists():
        latest_link.unlink()
    os.symlink(run_dir.name, latest_link)

    return run_dir


class JsonlAttackMemory:
    """Append-only JSONL attack memory used by the runner before Stream B integration.

    Args:
        memory_path: Path to the run-scoped attack memory JSONL file.
    """

    def __init__(self, memory_path: Path) -> None:
        self._memory_path = memory_path
        self._memory_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: AttackMemoryEntry) -> None:
        """Append one attack outcome entry as JSON.

        Args:
            entry: Attack memory entry to persist.
        """
        with self._memory_path.open("a") as file:
            file.write(entry.model_dump_json() + "\n")
