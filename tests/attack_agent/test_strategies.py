"""Tests for attack strategy selection."""

from attack_agent.src.strategies import AttackStrategy, RoundRobinStrategySelector


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
