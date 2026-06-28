"""Tests for the runner CLI entry point."""

import json
from pathlib import Path
from unittest.mock import patch

from attack_agent.src.memory import TacticalReflection
from attack_agent.src.strategies import AttackStrategy
from common.src.event_emitter import EVENTS_FILENAME
from common.src.models import EvaluationVerdict, Trace
from runner.src import __main__ as runner_main
from runner.src.models import ArenaResult
from runner.src.simple_evaluator import HeuristicEvaluator
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


class FakeReflector:
    """Reflector double that returns a fixed reflection without LLM calls."""

    async def reflect(self, trace: Trace, verdict: EvaluationVerdict) -> TacticalReflection:
        """Return a deterministic reflection.

        Args:
            trace: Trace submitted for reflection.
            verdict: Evaluation verdict.
        """
        return TacticalReflection(
            tactic_used="test tactic",
            why_outcome="test outcome",
            suggested_mutations=["try something else"],
        )


class FakeDefender:
    """Defender double used to verify CLI wiring."""

    def __init__(self, business_rules: str, memory: object) -> None:
        """Initialize.

        Args:
            business_rules: Business rules supplied by the CLI.
            memory: Defender memory supplied by the CLI.
        """
        self.business_rules = business_rules
        self.memory = memory


class FakeDefenderMemory:
    """Defender memory double used to verify CLI wiring."""

    def __init__(self, memory_path: Path) -> None:
        """Initialize.

        Args:
            memory_path: Path supplied by the CLI.
        """
        self.memory_path = memory_path


class FakeTriageAgent:
    """Triage agent double used to verify CLI wiring."""


class CapturingRunArena:
    """Callable test double that records run_arena keyword arguments."""

    def __init__(self) -> None:
        """Initialize captured call storage."""
        self.kwargs: dict[str, object] | None = None

    async def __call__(self, **kwargs: object) -> ArenaResult:
        """Record keyword arguments and return an empty arena result.

        Args:
            kwargs: Keyword arguments passed by the CLI.
        """
        self.kwargs = kwargs
        return ArenaResult(rounds=[])


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
            patch("runner.src.__main__.Evaluator", HeuristicEvaluator),
            patch("runner.src.runner.TacticalReflector", lambda: FakeReflector()),
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
            patch("runner.src.__main__.Evaluator", HeuristicEvaluator),
            patch("runner.src.runner.TacticalReflector", lambda: FakeReflector()),
        ):
            runner_main.main(
                events_dir=events_dir,
                memory_dir=tmp_path / "memory",
                delay=0,
                mock=True,
                mode="llm",
                rounds=1,
                no_defender=True,
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
            patch("runner.src.__main__.Evaluator", HeuristicEvaluator),
            patch("runner.src.runner.TacticalReflector", lambda: FakeReflector()),
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

    def test_when_defender_enabled_expect_cli_passes_defender_stack_to_arena(self, tmp_path: Path) -> None:
        """Verify the default LLM CLI path wires Defender, DefenderMemory, and TriageAgent."""
        # arrange
        captured_run_arena = CapturingRunArena()

        # act
        with (
            patch("runner.src.__main__.run_arena", captured_run_arena),
            patch("runner.src.__main__.Defender", FakeDefender, create=True),
            patch("runner.src.__main__.DefenderMemory", FakeDefenderMemory, create=True),
            patch("runner.src.__main__.TriageAgent", FakeTriageAgent, create=True),
        ):
            runner_main.main(
                events_dir=tmp_path / "events",
                memory_dir=tmp_path / "memory",
                delay=0,
                mock=True,
                mode="llm",
                rounds=1,
                no_defender=False,
                verbose=False,
                log_file=tmp_path / "arena.log",
                scenario="all",
            )

        # assert
        assert captured_run_arena.kwargs is not None
        assert isinstance(captured_run_arena.kwargs["defender"], FakeDefender)
        assert isinstance(captured_run_arena.kwargs["defender_memory"], FakeDefenderMemory)
        assert isinstance(captured_run_arena.kwargs["triage_agent"], FakeTriageAgent)

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

    def test_when_no_defender_flag_set_expect_llm_mode_still_runs(self, tmp_path: Path) -> None:
        """Verify the undefended comparison flag is accepted by the CLI."""
        # arrange
        events_dir = tmp_path / "events"

        # act
        with (
            patch("runner.src.runner.SEED_STRATEGIES", TWO_TEST_STRATEGIES),
            patch("runner.src.runner.AttackAgent", FakeAttackAgent),
            patch("runner.src.__main__.Evaluator", HeuristicEvaluator),
            patch("runner.src.runner.TacticalReflector", lambda: FakeReflector()),
        ):
            runner_main.main(
                events_dir=events_dir,
                memory_dir=tmp_path / "memory",
                delay=0,
                mock=True,
                mode="llm",
                rounds=1,
                no_defender=True,
                verbose=False,
                log_file=tmp_path / "arena.log",
                scenario="all",
            )

        # assert
        events = _read_events(events_dir)
        assert events[0]["event_type"] == "run_started"
        assert events[-1]["event_type"] == "run_completed"
