"""Tests for attack agent memory models."""

from attack_agent.src.memory import AttackMemoryEntry


class TestAttackMemoryEntry:
    def test_when_constructed_expect_default_entry_id_generated(self) -> None:
        # act
        entry = AttackMemoryEntry(
            strategy_name="split-refund",
            success=True,
            round_number=1,
            trace_id="trace-1",
        )

        # assert
        assert entry.entry_id
        assert len(entry.entry_id) == 32

    def test_when_success_expect_violation_fields_populated(self) -> None:
        # arrange / act
        entry = AttackMemoryEntry(
            strategy_name="split-refund",
            success=True,
            violated_rule="Refunds above $100 require manager approval",
            affected_component="process_refund",
            signals=["agent processed $90 refund", "repeated refund accepted"],
            round_number=1,
            trace_id="trace-1",
        )

        # assert
        assert entry.success is True
        assert entry.violated_rule == "Refunds above $100 require manager approval"
        assert entry.affected_component == "process_refund"
        assert len(entry.signals) == 2

    def test_when_failure_expect_optional_fields_none(self) -> None:
        # act
        entry = AttackMemoryEntry(
            strategy_name="identity-spoofing",
            success=False,
            signals=["agent refused identity claim"],
            round_number=1,
            trace_id="trace-2",
        )

        # assert
        assert entry.success is False
        assert entry.violated_rule is None
        assert entry.affected_component is None
        assert len(entry.signals) == 1

    def test_when_no_signals_provided_expect_empty_list(self) -> None:
        # act
        entry = AttackMemoryEntry(
            strategy_name="prompt-extraction",
            success=False,
            round_number=2,
            trace_id="trace-3",
        )

        # assert
        assert entry.signals == []

    def test_when_serialized_expect_valid_json_roundtrip(self) -> None:
        # arrange
        entry = AttackMemoryEntry(
            entry_id="entry-1",
            strategy_name="social-engineering",
            success=True,
            violated_rule="Verify address before changes",
            affected_component="update_shipping_address",
            signals=["agent revealed current address"],
            round_number=1,
            trace_id="trace-4",
        )

        # act
        json_str = entry.model_dump_json()
        restored = AttackMemoryEntry.model_validate_json(json_str)

        # assert
        assert restored.entry_id == "entry-1"
        assert restored.strategy_name == "social-engineering"
        assert restored.success is True
        assert restored.signals == ["agent revealed current address"]
