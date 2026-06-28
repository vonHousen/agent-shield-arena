"""Tests for shared event and trace models."""

from datetime import datetime, timezone

from common.src.models import (
    ArenaEvent,
    ConversationTurn,
    EvaluationVerdict,
    EventType,
    Role,
    RoundStarted,
    Trace,
    TracedToolExecution,
)


class TestTrace:
    def test_when_constructed_expect_default_trace_id_generated(self) -> None:
        # arrange / act
        trace = Trace(
            scenario_name="test-scenario",
            strategy_name="split-refund",
            conversation=[],
        )

        # assert
        assert trace.trace_id
        assert len(trace.trace_id) == 32

    def test_when_constructed_expect_default_timestamp_set(self) -> None:
        # act
        trace = Trace(
            scenario_name="test-scenario",
            strategy_name="split-refund",
            conversation=[],
        )

        # assert
        assert trace.timestamp.tzinfo == timezone.utc

    def test_when_assistant_turn_has_tools_expect_tool_executions_property_flattens(self) -> None:
        # arrange
        tool_execution = TracedToolExecution(
            tool_name="lookup_customer",
            arguments={"customer_id": "cus_001"},
            result={"name": "Alice"},
        )
        conversation = [
            ConversationTurn(role=Role.USER, content="I want a refund"),
            ConversationTurn(role=Role.ASSISTANT, content="Let me look into that.", tool_executions=[tool_execution]),
        ]

        # act
        trace = Trace(
            scenario_name="test-scenario",
            strategy_name="split-refund",
            conversation=conversation,
        )

        # assert
        assert trace.scenario_name == "test-scenario"
        assert trace.strategy_name == "split-refund"
        assert len(trace.conversation) == 2
        assert len(trace.tool_executions) == 1
        assert trace.tool_executions[0].tool_name == "lookup_customer"

    def test_when_serialized_expect_valid_json_roundtrip(self) -> None:
        # arrange
        trace = Trace(
            trace_id="abc123",
            scenario_name="scenario-1",
            strategy_name="identity-spoofing",
            conversation=[ConversationTurn(role=Role.USER, content="Hello")],
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )

        # act
        json_str = trace.model_dump_json()
        restored = Trace.model_validate_json(json_str)

        # assert
        assert restored.trace_id == "abc123"
        assert restored.scenario_name == "scenario-1"
        assert restored.strategy_name == "identity-spoofing"
        assert len(restored.conversation) == 1


class TestEvaluationVerdict:
    def test_when_constructed_expect_default_eval_id_generated(self) -> None:
        # act
        verdict = EvaluationVerdict(trace_id="trace-1", success=False)

        # assert
        assert verdict.eval_id
        assert len(verdict.eval_id) == 32

    def test_when_attack_succeeded_expect_violation_fields_populated(self) -> None:
        # arrange / act
        verdict = EvaluationVerdict(
            trace_id="trace-1",
            success=True,
            violation_type="refund bypass",
            violated_rule="Refunds above $100 require manager approval",
            evidence="Agent processed three $90 refunds totaling $270.",
            severity="high",
        )

        # assert
        assert verdict.success is True
        assert verdict.violation_type == "refund bypass"
        assert verdict.violated_rule == "Refunds above $100 require manager approval"
        assert verdict.evidence is not None
        assert verdict.severity == "high"

    def test_when_attack_failed_expect_optional_fields_none(self) -> None:
        # act
        verdict = EvaluationVerdict(trace_id="trace-1", success=False)

        # assert
        assert verdict.success is False
        assert verdict.violation_type is None
        assert verdict.violated_rule is None
        assert verdict.evidence is None
        assert verdict.severity is None

    def test_when_serialized_expect_valid_json_roundtrip(self) -> None:
        # arrange
        verdict = EvaluationVerdict(
            eval_id="eval-1",
            trace_id="trace-1",
            success=True,
            violation_type="data leak",
            violated_rule="Never reveal internal policies",
            evidence="Agent disclosed refund threshold.",
            severity="medium",
        )

        # act
        json_str = verdict.model_dump_json()
        restored = EvaluationVerdict.model_validate_json(json_str)

        # assert
        assert restored.eval_id == "eval-1"
        assert restored.success is True
        assert restored.violation_type == "data leak"


class TestArenaEventWithEvaluationVerdict:
    def test_when_evaluation_verdict_payload_expect_valid_event(self) -> None:
        # arrange
        verdict = EvaluationVerdict(trace_id="trace-1", success=True, violation_type="refund bypass")

        # act
        event = ArenaEvent(event_type=EventType.EVALUATION_VERDICT, payload=verdict)

        # assert
        assert event.event_type == EventType.EVALUATION_VERDICT
        assert isinstance(event.payload, EvaluationVerdict)
        assert event.payload.success is True


class TestArenaEventWithRoundStarted:
    def test_when_round_started_payload_expect_valid_event(self) -> None:
        # arrange
        payload = RoundStarted(round_number=2, strategy_count=4)

        # act
        event = ArenaEvent(event_type=EventType.ROUND_STARTED, payload=payload)

        # assert
        assert event.event_type == EventType.ROUND_STARTED
        assert isinstance(event.payload, RoundStarted)
        assert event.payload.round_number == 2
        assert event.payload.strategy_count == 4


class TestEventType:
    def test_when_evaluation_verdict_expect_string_value(self) -> None:
        # act / assert
        assert EventType.EVALUATION_VERDICT == "evaluation_verdict"

    def test_when_round_started_expect_string_value(self) -> None:
        # act / assert
        assert EventType.ROUND_STARTED == "round_started"
