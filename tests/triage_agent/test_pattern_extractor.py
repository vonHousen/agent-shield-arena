"""Tests for converting triage decisions into defender memory entries."""

from common.src.models import EvaluationVerdict, TriageDecision
from defender_agent.src.memory import DefenderMemoryEntry
from triage_agent.src.pattern_extractor import extract_defender_pattern

FIRST_ROUND = 1


class TestExtractDefenderPattern:
    def test_when_triage_selects_defender_memory_expect_memory_entry(self) -> None:
        # arrange
        triage_decision = TriageDecision(
            trace_id="trace-1",
            remediation_path="defender_memory",
            pattern_description="Multiple small refunds on the same order below approval threshold.",
            affected_component="process_refund",
            rationale="The defender can recognize repeated refund tool calls in one conversation.",
        )
        verdict = EvaluationVerdict(
            trace_id="trace-1",
            success=True,
            violated_rule="Refunds above $100 require manager approval.",
        )

        # act
        entry = extract_defender_pattern(
            triage_decision=triage_decision,
            verdict=verdict,
            trace_id="trace-1",
            round_number=FIRST_ROUND,
        )

        # assert
        assert isinstance(entry, DefenderMemoryEntry)
        assert entry.attack_intent == "Multiple small refunds on the same order below approval threshold."
        assert entry.violated_rule == "Refunds above $100 require manager approval."
        assert entry.affected_component == "process_refund"
        assert entry.signals == ["Multiple small refunds on the same order below approval threshold."]
        assert entry.defensive_action == (
            "BLOCK activity matching this pattern: Multiple small refunds on the same order below approval threshold."
        )
        assert entry.source_trace_id == "trace-1"
        assert entry.round_number == FIRST_ROUND

    def test_when_triage_selects_code_change_expect_value_error(self) -> None:
        # arrange
        triage_decision = TriageDecision(
            trace_id="trace-2",
            remediation_path="code_change",
            pattern_description="Add identity verification before customer lookup.",
            affected_component="lookup_customer",
            rationale="The system lacks authentication.",
        )
        verdict = EvaluationVerdict(trace_id="trace-2", success=True)

        # act / assert
        try:
            extract_defender_pattern(
                triage_decision=triage_decision,
                verdict=verdict,
                trace_id="trace-2",
                round_number=FIRST_ROUND,
            )
        except ValueError as error:
            assert str(error) == "Only defender_memory triage decisions can be converted to defender memory."
        else:
            raise AssertionError("Expected ValueError for code_change triage decision.")
