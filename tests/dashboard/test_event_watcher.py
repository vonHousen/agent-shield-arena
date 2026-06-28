"""Tests for dashboard event watching."""

import asyncio
from pathlib import Path

from common.src.event_emitter import EventEmitter
from common.src.models import ArenaEvent, ConversationTurn, EventType, Role
from dashboard.src.event_watcher import watch_events

POLL_INTERVAL_SECONDS = 0.01
TIMEOUT_SECONDS = 1


class TestWatchEvents:
    """Tests for watch_events."""

    async def test_when_file_has_existing_events_expect_replay_from_beginning(self, tmp_path: Path) -> None:
        # arrange
        event_path = tmp_path / "events.jsonl"
        expected_event = ArenaEvent(
            event_type=EventType.CONVERSATION_TURN,
            payload=ConversationTurn(role=Role.USER, content="refund please"),
        )
        EventEmitter(event_path).emit(expected_event)

        # act
        watcher = watch_events(event_path, poll_interval_seconds=POLL_INTERVAL_SECONDS)
        actual_event = await asyncio.wait_for(anext(watcher), timeout=TIMEOUT_SECONDS)
        await watcher.aclose()

        # assert
        assert actual_event == expected_event

    async def test_when_file_is_truncated_expect_replay_from_beginning(self, tmp_path: Path) -> None:
        # arrange
        event_path = tmp_path / "events.jsonl"
        old_event = ArenaEvent(
            event_type=EventType.CONVERSATION_TURN,
            payload=ConversationTurn(role=Role.USER, content="old message that is long enough to exceed new file size"),
        )
        new_event = ArenaEvent(
            event_type=EventType.CONVERSATION_TURN,
            payload=ConversationTurn(role=Role.ASSISTANT, content="new reply"),
        )
        emitter = EventEmitter(event_path)
        emitter.emit(old_event)

        watcher = watch_events(event_path, poll_interval_seconds=POLL_INTERVAL_SECONDS)
        await asyncio.wait_for(anext(watcher), timeout=TIMEOUT_SECONDS)

        # act — overwrite file with shorter content
        event_path.write_text("")
        emitter = EventEmitter(event_path)
        emitter.emit(new_event)

        actual_event = await asyncio.wait_for(anext(watcher), timeout=TIMEOUT_SECONDS)
        await watcher.aclose()

        # assert
        assert actual_event == new_event

    async def test_when_file_is_created_later_expect_new_event(self, tmp_path: Path) -> None:
        # arrange
        event_path = tmp_path / "missing" / "events.jsonl"
        expected_event = ArenaEvent(
            event_type=EventType.CONVERSATION_TURN,
            payload=ConversationTurn(role=Role.ASSISTANT, content="policy limits apply"),
        )
        watcher = watch_events(event_path, poll_interval_seconds=POLL_INTERVAL_SECONDS)

        # act
        next_event_task = asyncio.ensure_future(anext(watcher))
        await asyncio.sleep(POLL_INTERVAL_SECONDS * 2)
        EventEmitter(event_path).emit(expected_event)
        actual_event = await asyncio.wait_for(next_event_task, timeout=TIMEOUT_SECONDS)
        await watcher.aclose()

        # assert
        assert actual_event == expected_event
