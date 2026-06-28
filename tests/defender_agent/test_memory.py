"""Tests for defender memory models."""

from defender_agent.src.memory import DefenderMemoryEntry

FIRST_ROUND = 1
SECOND_ROUND = 2


class TestDefenderMemoryEntry:
    def test_when_constructed_expect_default_entry_id_generated(self) -> None:
        # act
        entry = DefenderMemoryEntry(
            attack_intent="Split-refund bypass",
            defensive_action="BLOCK tool call with multiple small refunds",
            source_trace_id="trace-1",
            round_number=FIRST_ROUND,
        )

        # assert
        assert entry.entry_id
        assert len(entry.entry_id) == 32

    def test_when_fully_populated_expect_all_fields_stored(self) -> None:
        # act
        entry = DefenderMemoryEntry(
            attack_intent="Multiple small refunds below approval threshold on same order",
            violated_rule="Refunds above $100 require manager approval",
            affected_component="process_refund",
            signals=[
                "multiple refund requests in same conversation",
                "refund amounts just below $100 threshold",
                "same order referenced repeatedly",
            ],
            defensive_action="BLOCK second+ refund tool call on the same order",
            source_trace_id="trace-1",
            round_number=FIRST_ROUND,
        )

        # assert
        assert entry.attack_intent == "Multiple small refunds below approval threshold on same order"
        assert entry.violated_rule == "Refunds above $100 require manager approval"
        assert entry.affected_component == "process_refund"
        assert len(entry.signals) == 3
        assert entry.defensive_action == "BLOCK second+ refund tool call on the same order"
        assert entry.source_trace_id == "trace-1"
        assert entry.round_number == FIRST_ROUND

    def test_when_optional_fields_omitted_expect_defaults(self) -> None:
        # act
        entry = DefenderMemoryEntry(
            attack_intent="Prompt extraction attempt",
            defensive_action="BLOCK user input requesting system internals",
            source_trace_id="trace-2",
            round_number=FIRST_ROUND,
        )

        # assert
        assert entry.violated_rule is None
        assert entry.affected_component is None
        assert entry.signals == []

    def test_when_serialized_expect_valid_json_roundtrip(self) -> None:
        # arrange
        entry = DefenderMemoryEntry(
            entry_id="def-entry-001",
            attack_intent="Cross-customer data access via ID switching",
            violated_rule="Never reveal another customer's data",
            affected_component="lookup_customer",
            signals=["mid-conversation customer ID switch", "request for another customer's details"],
            defensive_action="BLOCK lookup_customer when customer ID differs from conversation context",
            source_trace_id="trace-3",
            round_number=SECOND_ROUND,
        )

        # act
        json_str = entry.model_dump_json()
        restored = DefenderMemoryEntry.model_validate_json(json_str)

        # assert
        assert restored.entry_id == "def-entry-001"
        assert restored.attack_intent == "Cross-customer data access via ID switching"
        assert restored.violated_rule == "Never reveal another customer's data"
        assert restored.affected_component == "lookup_customer"
        assert len(restored.signals) == 2
        assert restored.source_trace_id == "trace-3"
        assert restored.round_number == SECOND_ROUND
