"""Attack runner loop for arena conversations."""

import asyncio
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

from attack_agent.src.agent import AttackAgent
from attack_agent.src.memory import AttackMemory, AttackMemoryEntry
from attack_agent.src.strategies import SEED_STRATEGIES, AttackStrategy
from common.src.config import settings
from common.src.event_emitter import EventEmitter
from common.src.logging import get_logger
from common.src.models import (
    ArenaEvent,
    ConversationTurn,
    EvaluationVerdict,
    EventType,
    Role,
    RoundStarted,
    RunCompleted,
    RunStarted,
    ScenarioStarted,
    ToolCall,
    ToolResult,
    Trace,
)
from runner.src.attack_source import AttackSource, LLMAttackSource, MockAttackSource
from runner.src.models import ArenaResult, RoundResult, ShieldedSystemResponse, StrategyResult
from runner.src.scenario import get_all_scenarios, get_split_refund_bypass_scenario
from runner.src.trace_builder import build_trace, save_trace

logger = get_logger(__name__)

SCENARIO_PAUSE_SECONDS = 2.0


class ShieldedSystem(Protocol):
    """Chat interface expected by the attack runner."""

    async def chat(self, message: str, history: list[tuple[str, str]]) -> ShieldedSystemResponse:
        """Return a shielded system response for one user message.

        Args:
            message: User message sent by the runner.
            history: Prior conversation turns as role/content tuples.
        """


class Evaluator(Protocol):
    """Evaluator interface used by the arena loop."""

    async def evaluate(self, trace: Trace, business_rules: str) -> EvaluationVerdict:
        """Judge whether a trace contains a successful attack.

        Args:
            trace: Completed conversation trace.
            business_rules: Shielded system business rules.
        """


async def run_attack_scenario(
    shielded_system: ShieldedSystem,
    event_emitter: EventEmitter,
    messages: Sequence[str],
    scenario_name: str,
    turn_delay_seconds: float = settings.runner_turn_delay_seconds,
    max_turns: int = settings.runner_max_turns,
) -> list[ShieldedSystemResponse]:
    """Run an attack scenario against a shielded system and emit JSONL events.

    Args:
        shielded_system: System under test.
        event_emitter: Sink for arena events.
        messages: Ordered user messages that make up the attack scenario.
        scenario_name: Identifier for this scenario, emitted as a scenario_started event.
        turn_delay_seconds: Delay between turns for real-time demo pacing.
        max_turns: Hard ceiling for conversation turns.
    """
    return await run_attack_conversation(
        shielded_system=shielded_system,
        event_emitter=event_emitter,
        attack_source=MockAttackSource(messages),
        scenario_name=scenario_name,
        turn_delay_seconds=turn_delay_seconds,
        max_turns=max_turns,
    )


async def run_attack_conversation(
    shielded_system: ShieldedSystem,
    event_emitter: EventEmitter,
    attack_source: AttackSource,
    scenario_name: str,
    turn_delay_seconds: float = settings.runner_turn_delay_seconds,
    max_turns: int = settings.runner_max_turns,
    history: list[tuple[str, str]] | None = None,
) -> list[ShieldedSystemResponse]:
    """Run a dynamic attack conversation and emit JSONL events.

    Args:
        shielded_system: System under test.
        event_emitter: Sink for arena events.
        attack_source: Source asked for each next attacker message.
        scenario_name: Identifier for this conversation, emitted as a scenario_started event.
        turn_delay_seconds: Delay between turns for real-time demo pacing.
        max_turns: Hard ceiling for conversation turns.
        history: Optional mutable conversation history populated as the runner advances.
    """
    conversation_history = history if history is not None else []
    responses: list[ShieldedSystemResponse] = []

    _emit_scenario_started(event_emitter, scenario_name)
    logger.info(f"Starting attack conversation '{scenario_name}' with max {max_turns} turns")

    for turn in range(1, max_turns + 1):
        message = await attack_source.next_message(conversation_history)
        if message is None:
            logger.info(f"Attack source stopped conversation '{scenario_name}' after {len(responses)} responses")
            break

        logger.info(f"Turn {turn}/{max_turns} — sending user message: {message.replace('\n', '\\n')}")
        _emit_conversation_turn(event_emitter, Role.USER, message)
        conversation_history.append((Role.USER.value, message))

        response = await shielded_system.chat(message, conversation_history)
        responses.append(response)
        logger.info(f"Turn {turn}/{max_turns} — received response: {response.content.replace('\n', '\\n')}")

        for tool_execution in response.tool_executions:
            logger.debug(f"Tool call: {tool_execution.tool_name}({tool_execution.arguments}) → {tool_execution.result}")
            _emit_tool_call(event_emitter, tool_execution.tool_name, tool_execution.arguments)
            _emit_tool_result(event_emitter, tool_execution.tool_name, tool_execution.result)

        _emit_conversation_turn(event_emitter, Role.ASSISTANT, response.content)
        conversation_history.append((Role.ASSISTANT.value, response.content))

        if turn < max_turns and turn_delay_seconds > 0:
            await asyncio.sleep(turn_delay_seconds)
    else:
        logger.warning(f"Attack conversation '{scenario_name}' reached max turn ceiling of {max_turns}")

    logger.info(f"Attack conversation finished — {len(responses)} responses collected")
    return responses


async def run_arena(
    shielded_system: ShieldedSystem,
    event_emitter: EventEmitter,
    evaluator: Evaluator,
    memory: AttackMemory,
    business_rules: str,
    memory_run_dir: Path,
    rounds: int = settings.arena_rounds,
    strategies: Sequence[AttackStrategy] | None = None,
    attack_source_factory: Callable[[AttackStrategy, int], AttackSource] | None = None,
    turn_delay_seconds: float = settings.runner_turn_delay_seconds,
) -> ArenaResult:
    """Run a multi-round arena loop with evaluation and attack memory updates.

    Args:
        shielded_system: System under test.
        event_emitter: Sink for arena events.
        evaluator: Evaluator used to judge completed traces.
        memory: Attack memory receiving one entry per evaluated conversation.
        business_rules: Business rules supplied to the evaluator.
        memory_run_dir: Run-scoped directory for traces and memory artifacts.
        rounds: Number of arena rounds to execute.
        strategies: Strategies to execute in each round.
        attack_source_factory: Optional factory used by tests to provide attack sources.
        turn_delay_seconds: Delay between turns for real-time demo pacing.
    """
    arena_strategies = strategies or SEED_STRATEGIES
    round_results: list[RoundResult] = []

    _emit_run_started(event_emitter, len(arena_strategies))
    try:
        for round_number in range(1, rounds + 1):
            _emit_round_started(event_emitter, round_number=round_number, strategy_count=len(arena_strategies))
            strategy_results: list[StrategyResult] = []
            memory_round_dir = memory_run_dir / f"round_{round_number}"

            for strategy in arena_strategies:
                history: list[tuple[str, str]] = []
                attack_source = _attack_source_for_strategy(strategy, round_number, attack_source_factory, memory)
                responses = await run_attack_conversation(
                    shielded_system=shielded_system,
                    event_emitter=event_emitter,
                    attack_source=attack_source,
                    scenario_name=strategy.name,
                    turn_delay_seconds=turn_delay_seconds,
                    history=history,
                )
                trace = build_trace(
                    scenario_name=strategy.name,
                    strategy_name=strategy.name,
                    history=history,
                    responses=responses,
                )
                save_trace(trace=trace, memory_round_dir=memory_round_dir)
                verdict = await evaluator.evaluate(trace=trace, business_rules=business_rules)
                memory.append(_memory_entry_from_verdict(strategy.name, round_number, verdict))
                _emit_evaluation_verdict(event_emitter, verdict)
                strategy_results.append(
                    StrategyResult(
                        strategy_name=strategy.name,
                        success=verdict.success,
                        trace_id=trace.trace_id,
                        violation_type=verdict.violation_type,
                    )
                )

            round_result = RoundResult(round_number=round_number, strategy_results=strategy_results)
            logger.info(
                f"Round {round_number} complete — {round_result.success_count} succeeded, "
                f"{round_result.failure_count} failed"
            )
            round_results.append(round_result)
    finally:
        _emit_run_completed(event_emitter)

    return ArenaResult(rounds=round_results)


async def run_default_attack_scenario(
    shielded_system: ShieldedSystem,
    event_emitter: EventEmitter,
    turn_delay_seconds: float = settings.runner_turn_delay_seconds,
) -> list[ShieldedSystemResponse]:
    """Run the default split-refund bypass scenario.

    Args:
        shielded_system: System under test.
        event_emitter: Sink for arena events.
        turn_delay_seconds: Delay between turns for real-time demo pacing.
    """
    return await run_attack_scenario(
        shielded_system=shielded_system,
        event_emitter=event_emitter,
        messages=get_split_refund_bypass_scenario(),
        scenario_name="split_refund_bypass",
        turn_delay_seconds=turn_delay_seconds,
    )


async def run_all_scenarios(
    shielded_system: ShieldedSystem,
    event_emitter: EventEmitter,
    turn_delay_seconds: float = settings.runner_turn_delay_seconds,
    scenario_pause_seconds: float = SCENARIO_PAUSE_SECONDS,
) -> dict[str, list[ShieldedSystemResponse]]:
    """Run every registered attack scenario sequentially.

    Each scenario starts with a fresh conversation history. A short pause
    separates scenarios so the dashboard can visually distinguish them.

    Args:
        shielded_system: System under test.
        event_emitter: Sink for arena events.
        turn_delay_seconds: Delay between turns for real-time demo pacing.
        scenario_pause_seconds: Pause between scenarios for demo pacing.
    """
    all_scenarios = get_all_scenarios()
    all_responses: dict[str, list[ShieldedSystemResponse]] = {}

    _emit_run_started(event_emitter, len(all_scenarios))
    try:
        for name, messages in all_scenarios.items():
            logger.info(f"=== Starting scenario: {name} ===")
            responses = await run_attack_scenario(
                shielded_system=shielded_system,
                event_emitter=event_emitter,
                messages=messages,
                scenario_name=name,
                turn_delay_seconds=turn_delay_seconds,
            )
            all_responses[name] = responses
            if scenario_pause_seconds > 0:
                await asyncio.sleep(scenario_pause_seconds)
    finally:
        _emit_run_completed(event_emitter)

    logger.info(f"All {len(all_responses)} scenarios complete")
    return all_responses


async def run_all_llm_scenarios(
    shielded_system: ShieldedSystem,
    event_emitter: EventEmitter,
    turn_delay_seconds: float = settings.runner_turn_delay_seconds,
    scenario_pause_seconds: float = SCENARIO_PAUSE_SECONDS,
) -> dict[str, list[ShieldedSystemResponse]]:
    """Run one LLM-driven conversation per seed strategy.

    Each strategy gets a fresh AttackAgent pinned to that single strategy.
    A short pause separates scenarios so the dashboard can distinguish them.

    Args:
        shielded_system: System under test.
        event_emitter: Sink for arena events.
        turn_delay_seconds: Delay between turns for real-time demo pacing.
        scenario_pause_seconds: Pause between scenarios for demo pacing.
    """
    all_responses: dict[str, list[ShieldedSystemResponse]] = {}

    _emit_run_started(event_emitter, len(SEED_STRATEGIES))
    try:
        for strategy in SEED_STRATEGIES:
            logger.info(f"=== Starting LLM scenario: {strategy.name} ===")
            agent = AttackAgent(strategy=strategy)
            responses = await run_attack_conversation(
                shielded_system=shielded_system,
                event_emitter=event_emitter,
                attack_source=LLMAttackSource(agent),
                scenario_name=strategy.name,
                turn_delay_seconds=turn_delay_seconds,
            )
            all_responses[strategy.name] = responses
            if scenario_pause_seconds > 0:
                await asyncio.sleep(scenario_pause_seconds)
    finally:
        _emit_run_completed(event_emitter)

    logger.info(f"All {len(all_responses)} LLM scenarios complete")
    return all_responses


def _emit_run_started(event_emitter: EventEmitter, scenario_count: int) -> None:
    event_emitter.emit(
        ArenaEvent(
            event_type=EventType.RUN_STARTED,
            payload=RunStarted(scenario_count=scenario_count),
        )
    )


def _emit_run_completed(event_emitter: EventEmitter) -> None:
    event_emitter.emit(
        ArenaEvent(
            event_type=EventType.RUN_COMPLETED,
            payload=RunCompleted(),
        )
    )


def _emit_round_started(event_emitter: EventEmitter, round_number: int, strategy_count: int) -> None:
    event_emitter.emit(
        ArenaEvent(
            event_type=EventType.ROUND_STARTED,
            payload=RoundStarted(round_number=round_number, strategy_count=strategy_count),
        )
    )


def _emit_scenario_started(event_emitter: EventEmitter, scenario_name: str) -> None:
    event_emitter.emit(
        ArenaEvent(
            event_type=EventType.SCENARIO_STARTED,
            payload=ScenarioStarted(scenario_name=scenario_name),
        )
    )


def _emit_evaluation_verdict(event_emitter: EventEmitter, verdict: EvaluationVerdict) -> None:
    event_emitter.emit(ArenaEvent(event_type=EventType.EVALUATION_VERDICT, payload=verdict))


def _emit_conversation_turn(event_emitter: EventEmitter, role: Role, content: str) -> None:
    event_emitter.emit(
        ArenaEvent(
            event_type=EventType.CONVERSATION_TURN,
            payload=ConversationTurn(role=role, content=content),
        )
    )


def _emit_tool_call(event_emitter: EventEmitter, tool_name: str, arguments: dict[str, object]) -> None:
    event_emitter.emit(
        ArenaEvent(
            event_type=EventType.TOOL_CALL,
            payload=ToolCall(tool_name=tool_name, arguments=arguments),
        )
    )


def _emit_tool_result(event_emitter: EventEmitter, tool_name: str, result: object) -> None:
    event_emitter.emit(
        ArenaEvent(
            event_type=EventType.TOOL_RESULT,
            payload=ToolResult(tool_name=tool_name, result=result),
        )
    )


def _attack_source_for_strategy(
    strategy: AttackStrategy,
    round_number: int,
    attack_source_factory: Callable[[AttackStrategy, int], AttackSource] | None,
    memory: AttackMemory | None = None,
) -> AttackSource:
    if attack_source_factory is not None:
        return attack_source_factory(strategy, round_number)
    return LLMAttackSource(AttackAgent(strategy=strategy, memory=memory))


def _memory_entry_from_verdict(
    strategy_name: str,
    round_number: int,
    verdict: EvaluationVerdict,
) -> AttackMemoryEntry:
    signals = [verdict.evidence] if verdict.evidence is not None else []
    return AttackMemoryEntry(
        strategy_name=strategy_name,
        success=verdict.success,
        violated_rule=verdict.violated_rule,
        affected_component=verdict.violation_type,
        signals=signals,
        round_number=round_number,
        trace_id=verdict.trace_id,
    )
