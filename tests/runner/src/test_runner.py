"""Tests for the Stream C attack runner."""

import json
from pathlib import Path
from unittest.mock import patch

from attack_agent.src.agent import AttackOutput
from attack_agent.src.memory import AttackMemory, TacticalReflection
from attack_agent.src.strategies import AttackStrategy
from common.src.event_emitter import EventEmitter
from common.src.models import DefenderDecision, EvaluationVerdict, Trace, TriageDecision
from defender_agent.src.memory import DefenderMemoryEntry
from runner.src.attack_source import AttackOutput as SourceAttackOutput
from runner.src.attack_source import ConversationHistory, MockAttackSource
from runner.src.mock_system import MockShieldedSystem
from runner.src.models import ShieldedSystemResponse
from runner.src.runner import (
    run_all_llm_scenarios,
    run_all_scenarios,
    run_arena,
    run_attack_conversation,
    run_attack_scenario,
)
from runner.src.scenario import get_all_scenarios, get_split_refund_bypass_scenario
from shielded_system.src.models import ChatMessage


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


class RecordingEvaluator:
    """Evaluator test double that records traces and returns deterministic verdicts."""

    def __init__(self) -> None:
        """Initialize recorded traces."""
        self.traces: list[Trace] = []

    async def evaluate(self, trace: Trace, business_rules: str) -> EvaluationVerdict:
        """Record the trace and return success for split-refund only.

        Args:
            trace: Trace submitted for evaluation.
            business_rules: Business rules supplied by the runner.
        """
        self.traces.append(trace)
        success = trace.strategy_name == "split-refund"
        return EvaluationVerdict(
            trace_id=trace.trace_id,
            success=success,
            violation_type="refund bypass" if success else None,
            violated_rule="Refunds above $100 require manager approval" if success else None,
            evidence="processed repeated refunds" if success else "assistant refused",
            severity="high" if success else None,
        )


class FakeReflector:
    """Reflector test double that returns a fixed tactical reflection."""

    async def reflect(self, trace: Trace, verdict: EvaluationVerdict) -> TacticalReflection:
        """Return a deterministic reflection based on the verdict.

        Args:
            trace: Trace submitted for reflection.
            verdict: Evaluation verdict.
        """
        if verdict.success:
            return TacticalReflection(
                tactic_used="split refund into smaller amounts",
                why_outcome="each amount was below the approval threshold",
                suggested_mutations=["try three-way split", "use different order IDs"],
            )
        return TacticalReflection(
            tactic_used="direct identity claim",
            why_outcome="agent enforced identity verification",
            defensive_trigger="identity verification check",
            suggested_mutations=["start as verified user then pivot"],
        )


class RecordingDefender:
    """Defender test double that allows inputs and blocks refund tool calls."""

    async def on_user_input(self, message: str, conversation_history: ConversationHistory) -> DefenderDecision:
        """Allow every user message.

        Args:
            message: User message being evaluated.
            conversation_history: Prior conversation history.
        """
        return DefenderDecision(checkpoint="on_user_input", decision="ALLOW", reason="Allowed by test defender.")

    async def on_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, object],
        conversation_history: ConversationHistory,
    ) -> DefenderDecision:
        """Block refund tool calls and allow everything else.

        Args:
            tool_name: Tool name being evaluated.
            arguments: Tool arguments being evaluated.
            conversation_history: Prior conversation history.
        """
        if tool_name == "process_refund":
            return DefenderDecision(
                checkpoint="on_tool_call",
                decision="BLOCK",
                reason="Refund call matched a learned pattern.",
                matched_patterns=["def-pattern-1"],
            )
        return DefenderDecision(checkpoint="on_tool_call", decision="ALLOW", reason="Tool allowed.")


class RecordingDefenderMemory:
    """Defender memory double that records appended patterns."""

    def __init__(self) -> None:
        """Initialize empty memory state."""
        self.entries: list[DefenderMemoryEntry] = []

    def append(self, entry: DefenderMemoryEntry) -> None:
        """Record a defender memory entry.

        Args:
            entry: Entry extracted from triage.
        """
        self.entries.append(entry)


class RecordingTriageAgent:
    """Triage test double that records successful traces."""

    def __init__(self) -> None:
        """Initialize recorded triage inputs."""
        self.calls: list[tuple[Trace, EvaluationVerdict, TacticalReflection | None]] = []

    async def triage(
        self,
        trace: Trace,
        verdict: EvaluationVerdict,
        business_rules: str,
        reflection: TacticalReflection | None = None,
    ) -> TriageDecision:
        """Return a defender-memory remediation decision.

        Args:
            trace: Successful attack trace.
            verdict: Evaluation verdict for the trace.
            business_rules: Business rules supplied by the runner.
            reflection: Tactical reflection produced by the runner.
        """
        self.calls.append((trace, verdict, reflection))
        return TriageDecision(
            trace_id=trace.trace_id,
            remediation_path="defender_memory",
            pattern_description="Multiple small refunds below approval threshold on the same order.",
            affected_component="process_refund",
            rationale="A tool-call pattern could block the repeated refund sequence.",
        )


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
            scenario_pause_seconds=0,
        )

        # assert
        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        assert events[0]["event_type"] == "run_started"
        assert events[0]["payload"]["scenario_count"] == expected_scenario_count
        assert events[-1]["event_type"] == "run_completed"


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

    async def test_when_attack_source_returns_empty_message_expect_runner_stops(self, tmp_path: Path) -> None:
        """Verify the runner treats an empty-string message the same as None (defense-in-depth)."""
        # arrange
        events_path = tmp_path / "events.jsonl"
        event_emitter = EventEmitter(events_path)
        shielded_system = RecordingShieldedSystem()
        attack_source = _EmptyMessageAttackSource()

        # act
        responses = await run_attack_conversation(
            shielded_system=shielded_system,
            event_emitter=event_emitter,
            attack_source=attack_source,
            scenario_name="empty_msg_test",
            turn_delay_seconds=0,
            max_turns=5,
        )

        # assert
        assert len(responses) == 0
        assert shielded_system.messages == []


class _EmptyMessageAttackSource:
    """Attack source that returns an empty-string message on first call."""

    async def next_message(self, history: ConversationHistory) -> SourceAttackOutput | None:
        """Return an empty message.

        Args:
            history: Unused.
        """
        return SourceAttackOutput(message="   ", reasoning=None)


class FakeAttackAgent:
    """Attack agent double that returns one canned message then stops."""

    def __init__(self, strategy: AttackStrategy | None = None) -> None:
        """Initialize.

        Args:
            strategy: Strategy (captured for test assertions).
        """
        self.strategy = strategy
        self._sent = False

    async def generate_attack(self, conversation_history: list[ChatMessage]) -> AttackOutput | None:
        """Return one message then stop.

        Args:
            conversation_history: Unused.
        """
        if self._sent:
            return None
        self._sent = True
        message = f"attack from {self.strategy.name}" if self.strategy else "attack"
        return AttackOutput(message=message, reasoning=None)


class TestRunAllLlmScenarios:
    async def test_when_all_strategies_run_expect_run_lifecycle_and_per_strategy_scenarios(
        self, tmp_path: Path
    ) -> None:
        # arrange
        events_path = tmp_path / "events.jsonl"
        event_emitter = EventEmitter(events_path)
        test_strategies = [
            AttackStrategy(name="alpha", goal="Alpha goal.", opening="Alpha opening."),
            AttackStrategy(name="beta", goal="Beta goal.", opening="Beta opening."),
        ]

        # act
        with (
            patch("runner.src.runner.SEED_STRATEGIES", test_strategies),
            patch("runner.src.runner.AttackAgent", FakeAttackAgent),
        ):
            results = await run_all_llm_scenarios(
                shielded_system=RecordingShieldedSystem(),
                event_emitter=event_emitter,
                turn_delay_seconds=0,
                scenario_pause_seconds=0,
            )

        # assert
        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        assert events[0]["event_type"] == "run_started"
        assert events[0]["payload"]["scenario_count"] == len(test_strategies)
        assert events[-1]["event_type"] == "run_completed"

        scenario_names = [e["payload"]["scenario_name"] for e in events if e["event_type"] == "scenario_started"]
        assert scenario_names == ["alpha", "beta"]
        assert set(results.keys()) == {"alpha", "beta"}


class TestRunArena:
    async def test_when_multiple_rounds_run_expect_traces_evaluations_memory_and_metrics(self, tmp_path: Path) -> None:
        """Verify the v3 arena loop evaluates and stores every strategy outcome."""
        # arrange
        events_path = tmp_path / "events" / "arena_events.jsonl"
        memory_run_dir = tmp_path / "memory" / "20260101_000000"
        event_emitter = EventEmitter(events_path)
        evaluator = RecordingEvaluator()
        memory = AttackMemory(memory_run_dir / "attack_memory.jsonl")
        strategies = [
            AttackStrategy(name="split-refund", goal="Refund bypass.", opening="Ask for refunds."),
            AttackStrategy(name="identity-spoofing", goal="Identity bypass.", opening="Ask for another account."),
        ]
        rounds = 2

        # act
        result = await run_arena(
            shielded_system=RecordingShieldedSystem(),
            event_emitter=event_emitter,
            evaluator=evaluator,
            memory=memory,
            business_rules="1. Refunds above $100 require manager approval.",
            memory_run_dir=memory_run_dir,
            rounds=rounds,
            strategies=strategies,
            attack_source_factory=lambda strategy, round_number: MockAttackSource(
                [f"round {round_number} attack from {strategy.name}"]
            ),
            turn_delay_seconds=0,
            reflector=FakeReflector(),
        )

        # assert
        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        expected_conversation_count = rounds * len(strategies)
        entries = memory.load_all()

        assert len(evaluator.traces) == expected_conversation_count
        assert len(entries) == expected_conversation_count
        assert len(result.rounds) == rounds
        assert result.rounds[0].success_count == 1
        assert result.rounds[0].failure_count == 1
        assert [entry.round_number for entry in entries] == [1, 1, 2, 2]
        assert {entry.strategy_name for entry in entries} == {"split-refund", "identity-spoofing"}
        assert all(entry.trace_id for entry in entries)

        round_events = [event for event in events if event["event_type"] == "round_started"]
        verdict_events = [event for event in events if event["event_type"] == "evaluation_verdict"]
        trace_files = sorted(memory_run_dir.glob("round_*/traces/*.json"))

        assert [event["payload"] for event in round_events] == [
            {"round_number": 1, "strategy_count": len(strategies)},
            {"round_number": 2, "strategy_count": len(strategies)},
        ]
        assert len(verdict_events) == expected_conversation_count
        assert len(trace_files) == expected_conversation_count

    async def test_when_defender_and_triage_configured_expect_decisions_and_memory_updates(
        self, tmp_path: Path
    ) -> None:
        """Verify v4 runner wiring emits defender decisions and stores triage patterns."""
        # arrange
        events_path = tmp_path / "events" / "arena_events.jsonl"
        memory_run_dir = tmp_path / "memory" / "20260101_000000"
        event_emitter = EventEmitter(events_path)
        memory = AttackMemory(memory_run_dir / "attack_memory.jsonl")
        defender_memory = RecordingDefenderMemory()
        triage_agent = RecordingTriageAgent()
        strategies = [AttackStrategy(name="split-refund", goal="Refund bypass.", opening="Ask for refunds.")]

        # act
        result = await run_arena(
            shielded_system=MockShieldedSystem(),
            event_emitter=event_emitter,
            evaluator=RecordingEvaluator(),
            memory=memory,
            business_rules="1. Refunds above $100 require manager approval.",
            memory_run_dir=memory_run_dir,
            rounds=1,
            strategies=strategies,
            attack_source_factory=lambda strategy, round_number: MockAttackSource(["refund attack"]),
            turn_delay_seconds=0,
            reflector=FakeReflector(),
            defender=RecordingDefender(),
            defender_memory=defender_memory,
            triage_agent=triage_agent,
        )

        # assert
        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        defender_events = [event for event in events if event["event_type"] == "defender_decision"]
        triage_events = [event for event in events if event["event_type"] == "triage_decision"]

        assert len(defender_events) == 2
        assert [event["payload"]["checkpoint"] for event in defender_events] == ["on_user_input", "on_tool_call"]
        assert [event["payload"]["decision"] for event in defender_events] == ["ALLOW", "BLOCK"]
        assert len(triage_events) == 1
        assert len(triage_agent.calls) == 1
        assert len(defender_memory.entries) == 1
        assert defender_memory.entries[0].attack_intent == (
            "Multiple small refunds below approval threshold on the same order."
        )
        assert defender_memory.entries[0].affected_component == "process_refund"
        assert result.rounds[0].strategy_results[0].defender_blocks == 1
