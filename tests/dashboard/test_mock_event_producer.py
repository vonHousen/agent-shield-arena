"""Tests for dashboard mock event production."""

from common.src.models import ArenaEvent, DefenderDecision, EvaluationVerdict, EventType, RoundStarted
from dashboard.src.mock_event_producer import _build_mock_events


class TestBuildMockEvents:
    def test_when_built_expect_rounds_and_evaluation_verdicts(self) -> None:
        # arrange
        expected_round_count = 2
        expected_verdict_count = 4

        # act
        events = _build_mock_events()

        # assert
        round_events = _filter_events(events, EventType.ROUND_STARTED)
        verdict_events = _filter_events(events, EventType.EVALUATION_VERDICT)
        round_payloads = [event.payload for event in round_events if isinstance(event.payload, RoundStarted)]
        verdict_payloads = [event.payload for event in verdict_events if isinstance(event.payload, EvaluationVerdict)]

        assert len(round_payloads) == expected_round_count
        assert len(verdict_payloads) == expected_verdict_count
        assert round_payloads[0].round_number == 1
        assert round_payloads[0].strategy_count == 2
        assert round_payloads[1].round_number == 2
        assert round_payloads[1].strategy_count == 2
        assert {payload.success for payload in verdict_payloads} == {True, False}

    def test_when_built_expect_defender_decisions_for_dashboard(self) -> None:
        # arrange
        expected_decisions = {"BLOCK", "ALLOW"}

        # act
        events = _build_mock_events()

        # assert
        defender_events = _filter_events(events, EventType.DEFENDER_DECISION)
        defender_payloads = [event.payload for event in defender_events if isinstance(event.payload, DefenderDecision)]

        assert defender_payloads
        assert {payload.decision for payload in defender_payloads} == expected_decisions


def _filter_events(events: list[ArenaEvent], event_type: EventType) -> list[ArenaEvent]:
    """Return events matching the requested event type.

    Args:
        events: Events to filter.
        event_type: Event type to match.
    """
    return [event for event in events if event.event_type == event_type]
