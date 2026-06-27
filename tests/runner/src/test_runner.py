"""Tests for the Stream C attack runner."""

import json

from common.src.event_emitter import EventEmitter
from runner.src.mock_system import MockShieldedSystem
from runner.src.runner import run_attack_scenario
from runner.src.scenario import get_split_refund_bypass_scenario


class TestRunAttackScenario:
    async def test_when_split_refund_scenario_runs_expect_events_for_each_turn_and_tool_call(self, tmp_path) -> None:
        """Verify the runner emits user, tool, and assistant events."""
        # arrange
        events_path = tmp_path / "events.jsonl"
        event_emitter = EventEmitter(events_path)
        messages = get_split_refund_bypass_scenario()
        expected_events_per_turn = 4
        expected_event_count = len(messages) * expected_events_per_turn

        # act
        responses = await run_attack_scenario(
            shielded_system=MockShieldedSystem(),
            event_emitter=event_emitter,
            messages=messages,
            turn_delay_seconds=0,
        )

        # assert
        event_lines = events_path.read_text().splitlines()
        events = [json.loads(line) for line in event_lines]

        assert len(responses) == len(messages)
        assert len(events) == expected_event_count
        assert events[0]["event_type"] == "conversation_turn"
        assert events[0]["payload"]["role"] == "user"
        assert events[0]["payload"]["content"] == messages[0]
        assert events[1]["event_type"] == "tool_call"
        assert events[1]["payload"]["tool_name"] == "process_refund"
        assert events[2]["event_type"] == "tool_result"
        assert events[2]["payload"]["result"]["status"] == "success"
        assert events[3]["event_type"] == "conversation_turn"
        assert events[3]["payload"]["role"] == "assistant"

    async def test_when_scenario_runs_expect_mock_system_receives_conversation_history(self, tmp_path) -> None:
        """Verify conversation history is built as the runner advances turns."""
        # arrange
        events_path = tmp_path / "events.jsonl"
        event_emitter = EventEmitter(events_path)
        messages = get_split_refund_bypass_scenario()
        expected_refund_ids = ["REF-001", "REF-002", "REF-003"]

        # act
        responses = await run_attack_scenario(
            shielded_system=MockShieldedSystem(),
            event_emitter=event_emitter,
            messages=messages,
            turn_delay_seconds=0,
        )

        # assert
        refund_ids = [response.tool_executions[0].result["refund_id"] for response in responses]
        assert refund_ids == expected_refund_ids
