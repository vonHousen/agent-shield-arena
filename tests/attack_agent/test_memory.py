"""Tests for attack agent memory models."""

from pathlib import Path

import pytest

from attack_agent.src.memory import AttackMemory, AttackMemoryEntry, TacticalReflection

FIRST_ROUND = 1
SECOND_ROUND = 2


def _sample_reflection(
    tactic: str = "asked about refund limit",
    why: str = "agent treated it as FAQ",
    trigger: str | None = None,
    mutations: list[str] | None = None,
) -> TacticalReflection:
    return TacticalReflection(
        tactic_used=tactic,
        why_outcome=why,
        defensive_trigger=trigger,
        suggested_mutations=mutations or ["try a different angle"],
    )


class TestTacticalReflection:
    def test_when_constructed_expect_all_fields_populated(self) -> None:
        # act
        reflection = TacticalReflection(
            tactic_used="claimed to be family member",
            why_outcome="agent refused third-party access",
            defensive_trigger="identity verification check",
            suggested_mutations=["start as verified customer then switch IDs"],
        )

        # assert
        assert reflection.tactic_used == "claimed to be family member"
        assert reflection.why_outcome == "agent refused third-party access"
        assert reflection.defensive_trigger == "identity verification check"
        assert reflection.suggested_mutations == ["start as verified customer then switch IDs"]

    def test_when_optional_fields_omitted_expect_defaults(self) -> None:
        # act
        reflection = TacticalReflection(
            tactic_used="asked a question",
            why_outcome="it worked",
        )

        # assert
        assert reflection.defensive_trigger is None
        assert reflection.suggested_mutations == []


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

    def test_when_success_with_reflection_expect_fields_populated(self) -> None:
        # arrange
        reflection = _sample_reflection(
            tactic="split $180 into two $90 requests",
            why="each request was below $100 threshold",
        )

        # act
        entry = AttackMemoryEntry(
            strategy_name="split-refund",
            success=True,
            violated_rule="Refunds above $100 require manager approval",
            affected_component="process_refund",
            reflection=reflection,
            round_number=1,
            trace_id="trace-1",
        )

        # assert
        assert entry.success is True
        assert entry.violated_rule == "Refunds above $100 require manager approval"
        assert entry.affected_component == "process_refund"
        assert entry.reflection is not None
        assert entry.reflection.tactic_used == "split $180 into two $90 requests"

    def test_when_failure_expect_optional_fields_none(self) -> None:
        # act
        entry = AttackMemoryEntry(
            strategy_name="identity-spoofing",
            success=False,
            reflection=_sample_reflection(trigger="identity check"),
            round_number=1,
            trace_id="trace-2",
        )

        # assert
        assert entry.success is False
        assert entry.violated_rule is None
        assert entry.affected_component is None
        assert entry.reflection is not None

    def test_when_no_reflection_provided_expect_none(self) -> None:
        # act
        entry = AttackMemoryEntry(
            strategy_name="prompt-extraction",
            success=False,
            round_number=2,
            trace_id="trace-3",
        )

        # assert
        assert entry.reflection is None

    def test_when_serialized_expect_valid_json_roundtrip(self) -> None:
        # arrange
        reflection = _sample_reflection(
            tactic="asked about address verification",
            why="agent revealed current address during verification",
        )
        entry = AttackMemoryEntry(
            entry_id="entry-1",
            strategy_name="social-engineering",
            success=True,
            violated_rule="Verify address before changes",
            affected_component="update_shipping_address",
            reflection=reflection,
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
        assert restored.reflection is not None
        assert restored.reflection.tactic_used == "asked about address verification"


class TestAttackMemoryAppend:
    def test_when_appending_entry_expect_jsonl_file_created(self, tmp_path: Path) -> None:
        # arrange
        memory_path = tmp_path / "attack_memory.jsonl"
        memory = AttackMemory(memory_path=memory_path)
        entry = AttackMemoryEntry(
            strategy_name="split-refund",
            success=True,
            violated_rule="Refunds above $100 require manager approval",
            affected_component="process_refund",
            reflection=_sample_reflection(),
            round_number=FIRST_ROUND,
            trace_id="trace-1",
        )

        # act
        memory.append(entry)

        # assert
        loaded_entries = memory.load_all()
        assert loaded_entries == [entry]
        assert memory_path.exists()


class TestAttackMemoryLoadAll:
    def test_when_memory_file_missing_expect_empty_list(self, tmp_path: Path) -> None:
        # arrange
        memory = AttackMemory(memory_path=tmp_path / "missing.jsonl")

        # act
        entries = memory.load_all()

        # assert
        assert entries == []

    def test_when_jsonl_contains_blank_lines_expect_only_entries_loaded(self, tmp_path: Path) -> None:
        # arrange
        memory_path = tmp_path / "attack_memory.jsonl"
        entry = AttackMemoryEntry(
            entry_id="entry-1",
            strategy_name="prompt-extraction",
            success=False,
            reflection=_sample_reflection(trigger="policy disclosure check"),
            round_number=FIRST_ROUND,
            trace_id="trace-1",
        )
        memory_path.write_text(f"\n{entry.model_dump_json()}\n\n", encoding="utf-8")
        memory = AttackMemory(memory_path=memory_path)

        # act
        entries = memory.load_all()

        # assert
        assert entries == [entry]


class TestAttackMemoryGetByStrategy:
    def test_when_entries_exist_expect_only_matching_strategy_returned(self, tmp_path: Path) -> None:
        # arrange
        memory = AttackMemory(memory_path=tmp_path / "attack_memory.jsonl")
        split_refund = AttackMemoryEntry(
            strategy_name="split-refund",
            success=True,
            round_number=FIRST_ROUND,
            trace_id="trace-1",
        )
        prompt_extraction = AttackMemoryEntry(
            strategy_name="prompt-extraction",
            success=False,
            round_number=FIRST_ROUND,
            trace_id="trace-2",
        )
        memory.append(split_refund)
        memory.append(prompt_extraction)

        # act
        entries = memory.get_by_strategy("split-refund")

        # assert
        assert entries == [split_refund]


class TestAttackMemorySummary:
    def test_when_entries_exist_expect_per_strategy_counts_and_recent_reflection(self, tmp_path: Path) -> None:
        # arrange
        memory = AttackMemory(memory_path=tmp_path / "attack_memory.jsonl")
        round1_reflection = _sample_reflection(
            tactic="split large refund into two",
            why="each was below threshold",
        )
        round2_reflection = _sample_reflection(
            tactic="asked for another refund on same order",
            why="manager approval was required",
            trigger="refund limit enforcement",
        )
        memory.append(
            AttackMemoryEntry(
                strategy_name="split-refund",
                success=True,
                violated_rule="Refunds above $100 require manager approval",
                reflection=round1_reflection,
                round_number=FIRST_ROUND,
                trace_id="trace-1",
            )
        )
        memory.append(
            AttackMemoryEntry(
                strategy_name="split-refund",
                success=False,
                reflection=round2_reflection,
                round_number=SECOND_ROUND,
                trace_id="trace-2",
            )
        )

        # act
        summary = memory.summary()

        # assert
        split_refund = summary["split-refund"]
        assert split_refund.success_count == 1
        assert split_refund.failure_count == 1
        assert split_refund.success_rate == pytest.approx(0.5)
        assert split_refund.last_violated_rules == ["Refunds above $100 require manager approval"]
        assert split_refund.last_reflection == round2_reflection
