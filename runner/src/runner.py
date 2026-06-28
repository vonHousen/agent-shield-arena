"""Attack runner loop for the v1 live conversation demo."""

import asyncio
from collections.abc import Sequence
from typing import Protocol

from common.src.event_emitter import EventEmitter
from common.src.logging import get_logger
from common.src.models import ArenaEvent, ConversationTurn, EventType, Role, ScenarioStarted, ToolCall, ToolResult
from runner.src.models import ShieldedSystemResponse
from runner.src.scenario import get_all_scenarios, get_split_refund_bypass_scenario

logger = get_logger(__name__)

DEFAULT_TURN_DELAY_SECONDS = 1.0
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
    turn_delay_seconds: float = DEFAULT_TURN_DELAY_SECONDS,
) -> list[ShieldedSystemResponse]:
    """Run an attack scenario against a shielded system and emit JSONL events.

    Args:
        shielded_system: System under test.
        event_emitter: Sink for arena events.
        messages: Ordered user messages that make up the attack scenario.
        scenario_name: Identifier for this scenario, emitted as a scenario_started event.
        turn_delay_seconds: Delay between turns for real-time demo pacing.
    """
    history: list[tuple[str, str]] = []
    responses: list[ShieldedSystemResponse] = []

    _emit_scenario_started(event_emitter, scenario_name)
    logger.info(f"Starting attack scenario '{scenario_name}' with {len(messages)} messages")

    for index, message in enumerate(messages):
        turn = index + 1
        logger.info("Turn %d/%d — sending user message: %s", turn, len(messages), message.replace("\n", "\\n"))
        _emit_conversation_turn(event_emitter, Role.USER, message)
        history.append((Role.USER.value, message))

        response = await shielded_system.chat(message, history)
        responses.append(response)
        logger.info("Turn %d/%d — received response: %s", turn, len(messages), response.content.replace("\n", "\\n"))

        for tool_execution in response.tool_executions:
            logger.debug(f"Tool call: {tool_execution.tool_name}({tool_execution.arguments}) → {tool_execution.result}")
            _emit_tool_call(event_emitter, tool_execution.tool_name, tool_execution.arguments)
            _emit_tool_result(event_emitter, tool_execution.tool_name, tool_execution.result)

        _emit_conversation_turn(event_emitter, Role.ASSISTANT, response.content)
        history.append((Role.ASSISTANT.value, response.content))

        if index < len(messages) - 1 and turn_delay_seconds > 0:
            await asyncio.sleep(turn_delay_seconds)

    logger.info(f"Attack scenario finished — {len(responses)} responses collected")
    return responses


async def run_default_attack_scenario(
    shielded_system: ShieldedSystem,
    event_emitter: EventEmitter,
    turn_delay_seconds: float = DEFAULT_TURN_DELAY_SECONDS,
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
    turn_delay_seconds: float = DEFAULT_TURN_DELAY_SECONDS,
) -> dict[str, list[ShieldedSystemResponse]]:
    """Run every registered attack scenario sequentially.

    Each scenario starts with a fresh conversation history. A short pause
    separates scenarios so the dashboard can visually distinguish them.

    Args:
        shielded_system: System under test.
        event_emitter: Sink for arena events.
        turn_delay_seconds: Delay between turns for real-time demo pacing.
    """
    all_responses: dict[str, list[ShieldedSystemResponse]] = {}

    for name, messages in get_all_scenarios().items():
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

    logger.info(f"All {len(all_responses)} scenarios complete")
    return all_responses


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
