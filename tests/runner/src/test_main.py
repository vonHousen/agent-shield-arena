"""Tests for the runner CLI entry point."""

import json
from pathlib import Path
from unittest.mock import patch

from attack_agent.src.strategies import AttackStrategy
from common.src.event_emitter import EVENTS_FILENAME
from runner.src import __main__ as runner_main
from shielded_system.src.models import ChatMessage

TWO_TEST_STRATEGIES = [
    AttackStrategy(name="test-alpha", goal="Alpha goal.", opening="Alpha opening."),
    AttackStrategy(name="test-beta", goal="Beta goal.", opening="Beta opening."),
]


class FakeAttackAgent:
    """Attack agent double that emits one message per strategy then stops."""

    def __init__(self, strategy: AttackStrategy | None = None, **_kwargs: object) -> None:
        """Initialize.

        Args:
            strategy: The pinned strategy (used to generate a unique message).
        """
        self._strategy = strategy
        self._sent = False

    async def generate_attack(self, conversation_history: list[ChatMessage]) -> str | None:
        """Return one message then stop.

        Args:
            conversation_history: Unused.
        """
        if self._sent:
            return None
        self._sent = True
        name = self._strategy.name if self._strategy else "default"
        return f"attack from {name}"


def _read_events(events_dir: Path) -> list[dict]:
    """Read all events from the latest run directory."""
    events_path = events_dir / "latest" / EVENTS_FILENAME
    return [json.loads(line) for line in events_path.read_text().splitlines()]


class TestMain:
    def test_when_mode_omitted_expect_llm_mode_runs_all_strategies(self, tmp_path: Path) -> None:
        """Verify LLM mode is the default and runs one scenario per strategy."""
        # arrange
        events_dir = tmp_path / "events"

        # act
        with (
            patch("runner.src.runner.SEED_STRATEGIES", TWO_TEST_STRATEGIES),
            patch("runner.src.runner.AttackAgent", FakeAttackAgent),
        ):
            runner_main.main(
                events_dir=events_dir,
                memory_dir=tmp_path / "memory",
                delay=0,
                mock=True,
                rounds=1,
                verbose=False,
                log_file=tmp_path / "arena.log",
                scenario="all",
            )

        # assert
        events = _read_events(events_dir)
        assert events[0]["event_type"] == "run_started"
        assert events[0]["payload"]["scenario_count"] == len(TWO_TEST_STRATEGIES)
        scenario_names = [e["payload"]["scenario_name"] for e in events if e["event_type"] == "scenario_started"]
        assert scenario_names == ["test-alpha", "test-beta"]
        assert events[-1]["event_type"] == "run_completed"

    def test_when_mode_llm_expect_per_strategy_scenarios_with_generated_messages(self, tmp_path: Path) -> None:
        """Verify LLM mode wires one AttackAgent per strategy into separate conversations."""
        # arrange
        events_dir = tmp_path / "events"

        # act
        with (
            patch("runner.src.runner.SEED_STRATEGIES", TWO_TEST_STRATEGIES),
            patch("runner.src.runner.AttackAgent", FakeAttackAgent),
        ):
            runner_main.main(
                events_dir=events_dir,
                memory_dir=tmp_path / "memory",
                delay=0,
                mock=True,
                mode="llm",
                rounds=1,
                verbose=False,
                log_file=tmp_path / "arena.log",
                scenario="all",
            )

        # assert
        events = _read_events(events_dir)
        attacker_messages = [
            e["payload"]["content"]
            for e in events
            if e["event_type"] == "conversation_turn" and e["payload"]["role"] == "user"
        ]
        assert attacker_messages == ["attack from test-alpha", "attack from test-beta"]

    def test_when_mode_llm_with_rounds_expect_memory_artifacts_created(self, tmp_path: Path) -> None:
        """Verify LLM mode runs the v3 arena loop and writes matching memory artifacts."""
        # arrange
        events_dir = tmp_path / "events"
        memory_dir = tmp_path / "memory"
        rounds = 2

        # act
        with (
            patch("runner.src.runner.SEED_STRATEGIES", TWO_TEST_STRATEGIES),
            patch("runner.src.runner.AttackAgent", FakeAttackAgent),
        ):
            runner_main.main(
                events_dir=events_dir,
                memory_dir=memory_dir,
                delay=0,
                mock=True,
                mode="llm",
                rounds=rounds,
                verbose=False,
                log_file=tmp_path / "arena.log",
                scenario="all",
            )

        # assert
        events = _read_events(events_dir)
        memory_latest = memory_dir / "latest"
        memory_entries = (memory_latest / "attack_memory.jsonl").read_text().splitlines()
        trace_files = sorted(memory_latest.glob("round_*/traces/*.json"))
        round_events = [event for event in events if event["event_type"] == "round_started"]
        verdict_events = [event for event in events if event["event_type"] == "evaluation_verdict"]

        assert memory_latest.resolve().name == (events_dir / "latest").resolve().name
        assert len(round_events) == rounds
        assert len(verdict_events) == rounds * len(TWO_TEST_STRATEGIES)
        assert len(memory_entries) == rounds * len(TWO_TEST_STRATEGIES)
        assert len(trace_files) == rounds * len(TWO_TEST_STRATEGIES)

    def test_when_invalid_mode_expect_bad_parameter(self, tmp_path: Path) -> None:
        """Verify CLI mode validation rejects unknown modes."""
        # arrange
        invalid_mode = "unknown"

        # act/assert
        try:
            runner_main.main(
                events_dir=tmp_path / "events",
                memory_dir=tmp_path / "memory",
                delay=0,
                mock=True,
                mode=invalid_mode,
                rounds=1,
                verbose=False,
                log_file=tmp_path / "arena.log",
                scenario="all",
            )
        except Exception as error:
            assert str(error) == f"Unknown mode '{invalid_mode}'. Available: scenario, llm"
        else:
            raise AssertionError("Expected invalid mode to raise an exception.")
