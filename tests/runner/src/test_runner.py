"""Tests for the Stream C attack runner."""

import json

from common.src.event_emitter import EventEmitter
from runner.src.mock_system import MockShieldedSystem
from runner.src.runner import run_all_scenarios, run_attack_scenario
from runner.src.scenario import get_all_scenarios, get_split_refund_bypass_scenario


class TestRunAttackScenario:
    async def test_when_split_refund_scenario_runs_expect_events_for_each_turn_and_tool_call(self, tmp_path) -> None:
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

    async def test_when_scenario_runs_expect_mock_system_receives_conversation_history(self, tmp_path) -> None:
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


class TestRunAllScenarios:
    async def test_when_all_scenarios_run_expect_run_started_and_run_completed_events(self, tmp_path) -> None:
        """Verify run_all_scenarios wraps everything with run_started and run_completed."""
        # arrange
        events_path = tmp_path / "events.jsonl"
        event_emitter = EventEmitter(events_path)
        expected_scenario_count = len(get_all_scenarios())

        # act
        await run_all_scenarios(
            shielded_system=MockShieldedSystem(),
            event_emitter=event_emitter,
            turn_delay_seconds=0,
        )

        # assert
        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        assert events[0]["event_type"] == "run_started"
        assert events[0]["payload"]["scenario_count"] == expected_scenario_count
        assert events[-1]["event_type"] == "run_completed"
