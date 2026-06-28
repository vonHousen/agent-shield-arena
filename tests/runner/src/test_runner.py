"""Tests for the Stream C attack runner."""

import json
from pathlib import Path

from common.src.event_emitter import EventEmitter
from runner.src.attack_source import ConversationHistory, MockAttackSource
from runner.src.mock_system import MockShieldedSystem
from runner.src.models import ShieldedSystemResponse
from runner.src.runner import run_attack_conversation, run_attack_scenario
from runner.src.scenario import get_split_refund_bypass_scenario


class RecordingShieldedSystem:
    """Shielded system test double that records received history."""

    def __init__(self) -> None:
        """Initialize recorded request state."""
        self.messages: list[str] = []
        self.histories: list[ConversationHistory] = []

    async def chat(self, message: str, history: ConversationHistory) -> ShieldedSystemResponse:
        """Return a deterministic response and record the request.

        Args:
            message: User message sent by the runner.
            history: Prior conversation turns as role/content tuples.
        """
        self.messages.append(message)
        self.histories.append(list(history))
        return ShieldedSystemResponse(content=f"response to {message}")


class TestRunAttackScenario:
    async def test_when_split_refund_scenario_runs_expect_events_for_each_turn_and_tool_call(
        self, tmp_path: Path
    ) -> None:
        """Verify the runner emits scenario_started, user, tool, and assistant events."""
        # arrange
        events_path = tmp_path / "events.jsonl"
        event_emitter = EventEmitter(events_path)
        messages = get_split_refund_bypass_scenario()
        scenario_name = "test_scenario"
        events_per_turn = 4
        scenario_started_event_count = 1
        expected_event_count = scenario_started_event_count + len(messages) * events_per_turn

        # act
        responses = await run_attack_scenario(
            shielded_system=MockShieldedSystem(),
            event_emitter=event_emitter,
            messages=messages,
            scenario_name=scenario_name,
            turn_delay_seconds=0,
        )

        # assert
        event_lines = events_path.read_text().splitlines()
        events = [json.loads(line) for line in event_lines]

        assert len(responses) == len(messages)
        assert len(events) == expected_event_count
        assert events[0]["event_type"] == "scenario_started"
        assert events[0]["payload"]["scenario_name"] == scenario_name
        assert events[1]["event_type"] == "conversation_turn"
        assert events[1]["payload"]["role"] == "user"
        assert events[1]["payload"]["content"] == messages[0]
        assert events[2]["event_type"] == "tool_call"
        assert events[2]["payload"]["tool_name"] == "process_refund"
        assert events[3]["event_type"] == "tool_result"
        assert events[3]["payload"]["result"]["status"] == "success"
        assert events[4]["event_type"] == "conversation_turn"
        assert events[4]["payload"]["role"] == "assistant"

    async def test_when_scenario_runs_expect_mock_system_receives_conversation_history(self, tmp_path: Path) -> None:
        """Verify conversation history is built as the runner advances turns."""
        # arrange
        events_path = tmp_path / "events.jsonl"
        event_emitter = EventEmitter(events_path)
        messages = get_split_refund_bypass_scenario()
        expected_refund_ids = ["REF-001", "REF-002", "REF-003", "REF-004"]

        # act
        responses = await run_attack_scenario(
            shielded_system=MockShieldedSystem(),
            event_emitter=event_emitter,
            messages=messages,
            scenario_name="test_scenario",
            turn_delay_seconds=0,
        )

        # assert
        refund_ids = [response.tool_executions[0].result["refund_id"] for response in responses]
        assert refund_ids == expected_refund_ids


class TestRunAttackConversation:
    async def test_when_attack_source_stops_expect_runner_returns_collected_responses(self, tmp_path: Path) -> None:
        """Verify the dynamic runner stops when the attack source returns None."""
        # arrange
        events_path = tmp_path / "events.jsonl"
        event_emitter = EventEmitter(events_path)
        messages = ["first attack", "second attack"]
        shielded_system = RecordingShieldedSystem()
        scenario_name = "dynamic_test"
        events_per_turn = 2
        scenario_started_event_count = 1
        expected_event_count = scenario_started_event_count + len(messages) * events_per_turn

        # act
        responses = await run_attack_conversation(
            shielded_system=shielded_system,
            event_emitter=event_emitter,
            attack_source=MockAttackSource(messages),
            scenario_name=scenario_name,
            turn_delay_seconds=0,
            max_turns=10,
        )

        # assert
        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        assert [response.content for response in responses] == ["response to first attack", "response to second attack"]
        assert shielded_system.messages == messages
        assert len(events) == expected_event_count
        assert events[0]["payload"]["scenario_name"] == scenario_name
        assert events[-1]["payload"]["content"] == "response to second attack"

    async def test_when_attack_source_exceeds_max_turns_expect_runner_stops_at_ceiling(self, tmp_path: Path) -> None:
        """Verify settings-style max turns are enforced as a hard ceiling."""
        # arrange
        events_path = tmp_path / "events.jsonl"
        event_emitter = EventEmitter(events_path)
        messages = ["turn one", "turn two", "turn three"]
        max_turns = 2
        shielded_system = RecordingShieldedSystem()

        # act
        responses = await run_attack_conversation(
            shielded_system=shielded_system,
            event_emitter=event_emitter,
            attack_source=MockAttackSource(messages),
            scenario_name="max_turn_test",
            turn_delay_seconds=0,
            max_turns=max_turns,
        )

        # assert
        assert len(responses) == max_turns
        assert shielded_system.messages == ["turn one", "turn two"]
