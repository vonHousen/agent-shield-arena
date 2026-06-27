"""EventEmitter — appends ArenaEvent objects as JSON lines to a JSONL file."""

from pathlib import Path

from common.src.models import ArenaEvent

DEFAULT_EVENTS_PATH = Path("data/events/arena_events.jsonl")


class EventEmitter:
    """Appends ArenaEvent instances as JSON lines to a file.

    Args:
        path: Path to the JSONL output file. Created if it doesn't exist.
    """

    def __init__(self, path: Path = DEFAULT_EVENTS_PATH) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def emit(self, event: ArenaEvent) -> None:
        """Serialize and append a single event as a JSON line."""
        with self._path.open("a") as f:
            f.write(event.model_dump_json() + "\n")
