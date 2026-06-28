"""Tests for attack strategy selection."""

from pathlib import Path

from attack_agent.src.memory import AttackMemory, AttackMemoryEntry
from attack_agent.src.strategies import AttackStrategy, MemoryDrivenStrategySelector, RoundRobinStrategySelector

FIRST_ROUND = 1


class HighestWeightRandom:
    """Fake random source that records weights and returns the highest-weight population item."""

    def __init__(self) -> None:
        self.weights: list[float] = []

    def choices(
        self,
        population: list[AttackStrategy],
        weights: list[float],
        k: int,
    ) -> list[AttackStrategy]:
        """Return the highest-weight strategy.

        Args:
            population: Candidate strategies.
            weights: Selection weights matching the population.
            k: Number of choices requested.
        """
        self.weights = weights
        highest_weight_index = weights.index(max(weights))
        return [population[highest_weight_index] for _ in range(k)]


class TestRoundRobinStrategySelectorSelect:
    def test_when_called_repeatedly_expect_strategies_cycle_in_order(self) -> None:
        # arrange
        strategies = [
            AttackStrategy(name="first", goal="First goal.", opening="First opening."),
            AttackStrategy(name="second", goal="Second goal.", opening="Second opening."),
        ]
        selector = RoundRobinStrategySelector(strategies=strategies)

        # act
        selected = [selector.select().name, selector.select().name, selector.select().name]

        # assert
        assert selected == ["first", "second", "first"]


class TestMemoryDrivenStrategySelectorSelect:
    def test_when_strategy_has_highest_success_rate_expect_it_selected(self, tmp_path: Path) -> None:
        # arrange
        strategies = [
            AttackStrategy(name="split-refund", goal="Split refund goal.", opening="Split refund opening."),
            AttackStrategy(name="prompt-extraction", goal="Prompt extraction goal.", opening="Prompt opening."),
        ]
        memory = AttackMemory(memory_path=tmp_path / "attack_memory.jsonl")
        memory.append(
            AttackMemoryEntry(
                strategy_name="split-refund",
                success=True,
                round_number=FIRST_ROUND,
                trace_id="trace-1",
            )
        )
        memory.append(
            AttackMemoryEntry(
                strategy_name="prompt-extraction",
                success=False,
                round_number=FIRST_ROUND,
                trace_id="trace-2",
            )
        )
        random = HighestWeightRandom()
        selector = MemoryDrivenStrategySelector(strategies=strategies, memory=memory, random=random)

        # act
        selected = selector.select()

        # assert
        assert selected.name == "split-refund"
        assert random.weights[0] > random.weights[1]

    def test_when_strategy_has_zero_attempts_expect_unexplored_strategy_selected(self, tmp_path: Path) -> None:
        # arrange
        strategies = [
            AttackStrategy(name="split-refund", goal="Split refund goal.", opening="Split refund opening."),
            AttackStrategy(name="identity-spoofing", goal="Identity spoofing goal.", opening="Identity opening."),
        ]
        memory = AttackMemory(memory_path=tmp_path / "attack_memory.jsonl")
        memory.append(
            AttackMemoryEntry(
                strategy_name="split-refund",
                success=True,
                round_number=FIRST_ROUND,
                trace_id="trace-1",
            )
        )
        selector = MemoryDrivenStrategySelector(strategies=strategies, memory=memory)

        # act
        selected = selector.select()

        # assert
        assert selected.name == "identity-spoofing"
