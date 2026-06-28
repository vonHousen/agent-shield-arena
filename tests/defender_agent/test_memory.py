"""Tests for defender memory models."""

from pathlib import Path

from defender_agent.src.memory import DefenderMemory, DefenderMemoryEntry

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


class TestDefenderMemory:
    def test_load_all_when_file_missing_expect_empty_list(self, tmp_path: Path) -> None:
        # arrange
        memory = DefenderMemory(tmp_path / "missing" / "defender_memory.jsonl")

        # act
        entries = memory.load_all()

        # assert
        assert entries == []

    def test_append_and_load_all_when_entries_written_expect_roundtrip(self, tmp_path: Path) -> None:
        # arrange
        memory = DefenderMemory(tmp_path / "memory" / "defender_memory.jsonl")
        split_refund_entry = DefenderMemoryEntry(
            entry_id="def-entry-001",
            attack_intent="Split-refund bypass",
            violated_rule="Refunds above $100 require manager approval",
            affected_component="process_refund",
            signals=["multiple refunds on same order", "refund amounts below approval threshold"],
            defensive_action="BLOCK second+ refund tool call on the same order",
            source_trace_id="trace-1",
            round_number=FIRST_ROUND,
        )
        prompt_extraction_entry = DefenderMemoryEntry(
            entry_id="def-entry-002",
            attack_intent="Prompt extraction attempt",
            affected_component="on_user_input",
            signals=["asks for system prompt", "requests hidden instructions"],
            defensive_action="BLOCK user input requesting system internals",
            source_trace_id="trace-2",
            round_number=FIRST_ROUND,
        )

        # act
        memory.append(split_refund_entry)
        memory.append(prompt_extraction_entry)
        entries = memory.load_all()

        # assert
        assert entries == [split_refund_entry, prompt_extraction_entry]

    def test_get_by_component_when_component_matches_expect_filtered_entries(self, tmp_path: Path) -> None:
        # arrange
        memory = DefenderMemory(tmp_path / "defender_memory.jsonl")
        refund_entry = DefenderMemoryEntry(
            attack_intent="Split-refund bypass",
            affected_component="process_refund",
            signals=["multiple refunds on same order"],
            defensive_action="BLOCK second+ refund tool call on the same order",
            source_trace_id="trace-1",
            round_number=FIRST_ROUND,
        )
        lookup_entry = DefenderMemoryEntry(
            attack_intent="Cross-customer lookup",
            affected_component="lookup_customer",
            signals=["customer ID changes mid-conversation"],
            defensive_action="BLOCK lookup_customer for another customer ID",
            source_trace_id="trace-2",
            round_number=FIRST_ROUND,
        )
        memory.append(refund_entry)
        memory.append(lookup_entry)

        # act
        entries = memory.get_by_component("process_refund")

        # assert
        assert entries == [refund_entry]

    def test_format_for_prompt_when_entries_exist_expect_human_readable_patterns(self, tmp_path: Path) -> None:
        # arrange
        memory = DefenderMemory(tmp_path / "defender_memory.jsonl")
        memory.append(
            DefenderMemoryEntry(
                attack_intent="Split-refund bypass",
                violated_rule="Refunds above $100 require manager approval",
                affected_component="process_refund",
                signals=["multiple refunds on same order", "refund amounts below approval threshold"],
                defensive_action="BLOCK second+ refund tool call on the same order",
                source_trace_id="trace-1",
                round_number=FIRST_ROUND,
            )
        )
        memory.append(
            DefenderMemoryEntry(
                attack_intent="Prompt extraction attempt",
                affected_component="on_user_input",
                signals=["asks for system prompt"],
                defensive_action="BLOCK user input requesting system internals",
                source_trace_id="trace-2",
                round_number=SECOND_ROUND,
            )
        )

        # act
        prompt_context = memory.format_for_prompt()

        # assert
        assert "Known attack pattern #1: Split-refund bypass" in prompt_context
        assert "process_refund" in prompt_context
        assert "BLOCK second+ refund tool call on the same order" in prompt_context
        assert "Known attack pattern #2: Prompt extraction attempt" in prompt_context
        assert "BLOCK user input requesting system internals" in prompt_context
