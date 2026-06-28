"""EventEmitter — appends ArenaEvent objects as JSON lines to a JSONL file."""

import os
from datetime import UTC, datetime
from pathlib import Path

from common.src.models import ArenaEvent

DEFAULT_EVENTS_DIR = Path("data/events")
EVENTS_FILENAME = "arena_events.jsonl"

TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"


def create_run_dir(events_dir: Path = DEFAULT_EVENTS_DIR) -> Path:
    """Create a timestamped run directory and return the path to its JSONL file.

    Creates ``{events_dir}/{YYYYMMDD_HHMMSS}/arena_events.jsonl`` and updates
    the ``latest`` symlink in *events_dir* to point to the new directory.

    Args:
        events_dir: Parent directory for all run directories.

    Returns:
        Path to the JSONL events file inside the newly created run directory.
    """
    timestamp = datetime.now(UTC).strftime(TIMESTAMP_FORMAT)
    run_dir = events_dir / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    latest_link = events_dir / "latest"
    if latest_link.is_symlink() or latest_link.exists():
        latest_link.unlink()
    os.symlink(run_dir.name, latest_link)

    return run_dir / EVENTS_FILENAME


class EventEmitter:
    """Appends ArenaEvent instances as JSON lines to a file.

    Args:
        path: Path to the JSONL output file. Created if it doesn't exist.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def emit(self, event: ArenaEvent) -> None:
        """Serialize and append a single event as a JSON line."""
        with self._path.open("a") as f:
            f.write(event.model_dump_json() + "\n")
