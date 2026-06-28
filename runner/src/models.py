"""Data models for the attack runner."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolExecution:
    """A tool call and its returned result.

    Args:
        tool_name: Name of the invoked tool.
        arguments: Arguments passed to the tool.
        result: Value returned by the tool.
    """

    tool_name: str
    arguments: dict[str, Any]
    result: Any


@dataclass(frozen=True)
class ShieldedSystemResponse:
    """Response returned by a shielded system chat call.

    Args:
        content: Assistant response text.
        tool_executions: Tool calls made while producing the response.
    """

    content: str
    tool_executions: list[ToolExecution] = field(default_factory=list)


@dataclass(frozen=True)
class StrategyResult:
    """Evaluation result for one strategy conversation.

    Args:
        strategy_name: Name of the strategy that was evaluated.
        success: Whether the evaluator judged the attack successful.
        trace_id: Identifier of the trace that was evaluated.
        violation_type: Category of violation, when the attack succeeded.
        defender_blocks: Number of Defender BLOCK decisions during the conversation.
    """

    strategy_name: str
    success: bool
    trace_id: str
    violation_type: str | None = None
    defender_blocks: int = 0


@dataclass(frozen=True)
class RoundResult:
    """Aggregated arena result for one round.

    Args:
        round_number: One-based arena round number.
        strategy_results: Per-strategy evaluation results.
    """

    round_number: int
    strategy_results: list[StrategyResult]

    @property
    def success_count(self) -> int:
        return sum(1 for result in self.strategy_results if result.success)

    @property
    def failure_count(self) -> int:
        return len(self.strategy_results) - self.success_count


@dataclass(frozen=True)
class ArenaResult:
    """Aggregated result for a multi-round arena run.

    Args:
        rounds: Per-round arena results.
    """

    rounds: list[RoundResult]
