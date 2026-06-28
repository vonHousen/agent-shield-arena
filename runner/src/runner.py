"""Attack runner loop for arena conversations."""

import asyncio
from collections.abc import Sequence
from typing import Protocol

from attack_agent.src.agent import AttackAgent
from attack_agent.src.strategies import SEED_STRATEGIES
from common.src.config import settings
from common.src.event_emitter import EventEmitter
from common.src.logging import get_logger
from common.src.models import (
    ArenaEvent,
    ConversationTurn,
    EventType,
    Role,
    RunCompleted,
    RunStarted,
    ScenarioStarted,
    ToolCall,
    ToolResult,
)
from runner.src.attack_source import AttackSource, LLMAttackSource, MockAttackSource
from runner.src.models import ShieldedSystemResponse
from runner.src.scenario import get_all_scenarios, get_split_refund_bypass_scenario

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
) -> list[ShieldedSystemResponse]:
    """Run a dynamic attack conversation and emit JSONL events.

    Args:
        shielded_system: System under test.
        event_emitter: Sink for arena events.
        attack_source: Source asked for each next attacker message.
        scenario_name: Identifier for this conversation, emitted as a scenario_started event.
        turn_delay_seconds: Delay between turns for real-time demo pacing.
        max_turns: Hard ceiling for conversation turns.
    """
    history: list[tuple[str, str]] = []
    responses: list[ShieldedSystemResponse] = []

    _emit_scenario_started(event_emitter, scenario_name)
    logger.info(f"Starting attack conversation '{scenario_name}' with max {max_turns} turns")

    for turn in range(1, max_turns + 1):
        message = await attack_source.next_message(history)
        if message is None:
            logger.info(f"Attack source stopped conversation '{scenario_name}' after {len(responses)} responses")
            break

        logger.info(f"Turn {turn}/{max_turns} — sending user message: {message.replace('\n', '\\n')}")
        _emit_conversation_turn(event_emitter, Role.USER, message)
        history.append((Role.USER.value, message))

        response = await shielded_system.chat(message, history)
        responses.append(response)
        logger.info(f"Turn {turn}/{max_turns} — received response: {response.content.replace('\n', '\\n')}")

        for tool_execution in response.tool_executions:
            logger.debug(f"Tool call: {tool_execution.tool_name}({tool_execution.arguments}) → {tool_execution.result}")
            _emit_tool_call(event_emitter, tool_execution.tool_name, tool_execution.arguments)
            _emit_tool_result(event_emitter, tool_execution.tool_name, tool_execution.result)

        _emit_conversation_turn(event_emitter, Role.ASSISTANT, response.content)
        history.append((Role.ASSISTANT.value, response.content))

        if turn < max_turns and turn_delay_seconds > 0:
            await asyncio.sleep(turn_delay_seconds)
    else:
        logger.warning(f"Attack conversation '{scenario_name}' reached max turn ceiling of {max_turns}")

    logger.info(f"Attack conversation finished — {len(responses)} responses collected")
    return responses


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
) -> dict[str, list[ShieldedSystemResponse]]:
    """Run every registered attack scenario sequentially.

    Each scenario starts with a fresh conversation history. A short pause
    separates scenarios so the dashboard can visually distinguish them.

    Args:
        shielded_system: System under test.
        event_emitter: Sink for arena events.
        turn_delay_seconds: Delay between turns for real-time demo pacing.
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
            await asyncio.sleep(SCENARIO_PAUSE_SECONDS)
    finally:
        _emit_run_completed(event_emitter)

    logger.info(f"All {len(all_responses)} scenarios complete")
    return all_responses


async def run_all_llm_scenarios(
    shielded_system: ShieldedSystem,
    event_emitter: EventEmitter,
    turn_delay_seconds: float = settings.runner_turn_delay_seconds,
) -> dict[str, list[ShieldedSystemResponse]]:
    """Run one LLM-driven conversation per seed strategy.

    Each strategy gets a fresh AttackAgent pinned to that single strategy.
    A short pause separates scenarios so the dashboard can distinguish them.

    Args:
        shielded_system: System under test.
        event_emitter: Sink for arena events.
        turn_delay_seconds: Delay between turns for real-time demo pacing.
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
            await asyncio.sleep(SCENARIO_PAUSE_SECONDS)
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


def _emit_scenario_started(event_emitter: EventEmitter, scenario_name: str) -> None:
    event_emitter.emit(
        ArenaEvent(
            event_type=EventType.SCENARIO_STARTED,
            payload=ScenarioStarted(scenario_name=scenario_name),
        )
    )


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
