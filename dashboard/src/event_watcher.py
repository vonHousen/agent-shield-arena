"""Async JSONL event watcher for the dashboard."""

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path

from pydantic import ValidationError

from common.src.event_emitter import DEFAULT_EVENTS_PATH
from common.src.models import ArenaEvent

POLL_INTERVAL_SECONDS = 0.1


async def watch_events(
    path: Path = DEFAULT_EVENTS_PATH,
    poll_interval_seconds: float = POLL_INTERVAL_SECONDS,
) -> AsyncIterator[ArenaEvent]:
    """Replay existing events and yield newly appended events.

    Args:
        path: JSONL event file to read and tail.
        poll_interval_seconds: Delay between file polling attempts.
    """
    position = 0

    if path.exists():
        async for event in _read_events_from_position(path, position):
            position = event.file_position
            yield event.arena_event

    while True:
        if not path.exists():
            await asyncio.sleep(poll_interval_seconds)
            continue

        async for event in _read_events_from_position(path, position):
            position = event.file_position
            yield event.arena_event

        await asyncio.sleep(poll_interval_seconds)


class WatchedEvent:
    """Arena event with the source file position after its JSONL line."""

    def __init__(self, arena_event: ArenaEvent, file_position: int) -> None:
        self.arena_event = arena_event
        self.file_position = file_position


async def _read_events_from_position(path: Path, position: int) -> AsyncIterator[WatchedEvent]:
    with path.open() as file:
        file.seek(position)

        while line := file.readline():
            position = file.tell()
            stripped_line = line.strip()
            if not stripped_line:
                continue

            yield WatchedEvent(arena_event=_parse_event(stripped_line), file_position=position)


def _parse_event(line: str) -> ArenaEvent:
    try:
        return ArenaEvent.model_validate_json(line)
    except (json.JSONDecodeError, ValidationError) as error:
        msg = f"Invalid arena event line: {line}"
        raise ValueError(msg) from error
