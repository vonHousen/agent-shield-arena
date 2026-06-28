"""Shielded system wrapper that applies Defender checkpoints."""

from typing import Protocol

from common.src.event_emitter import EventEmitter
from common.src.models import ArenaEvent, DefenderDecision, EventType
from runner.src.models import ShieldedSystemResponse

BLOCKED_RESPONSE = "[BLOCKED BY DEFENDER] This request was flagged as potentially malicious."
BLOCK_DECISION = "BLOCK"


class ShieldedSystem(Protocol):
    """Chat interface wrapped by the Defender."""

    async def chat(self, message: str, history: list[tuple[str, str]]) -> ShieldedSystemResponse:
        """Return a shielded system response for one user message.

        Args:
            message: User message sent by the runner.
            history: Prior conversation turns as role/content tuples.
        """


class Defender(Protocol):
    """Defender checkpoint interface used by the wrapper."""

    async def on_user_input(
        self,
        message: str,
        conversation_history: list[tuple[str, str]],
    ) -> DefenderDecision:
        """Decide whether to allow or block a user message.

        Args:
            message: User message being evaluated.
            conversation_history: Prior conversation turns as role/content tuples.
        """

    async def on_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, object],
        conversation_history: list[tuple[str, str]],
    ) -> DefenderDecision:
        """Decide whether to allow or block a tool call.

        Args:
            tool_name: Name of the invoked tool.
            arguments: Arguments passed to the tool.
            conversation_history: Prior conversation turns as role/content tuples.
        """


class DefendedSystem:
    """Apply Defender checkpoints around a shielded system chat call.

    Args:
        inner_system: Shielded system being protected.
        defender: Defender used for input and tool-call decisions.
        event_emitter: Sink for defender decision events.
    """

    def __init__(self, inner_system: ShieldedSystem, defender: Defender, event_emitter: EventEmitter) -> None:
        self._inner_system = inner_system
        self._defender = defender
        self._event_emitter = event_emitter
        self._block_count = 0

    async def chat(self, message: str, history: list[tuple[str, str]]) -> ShieldedSystemResponse:
        """Evaluate a user message, forward allowed input, and evaluate resulting tool calls.

        Args:
            message: User message sent by the runner.
            history: Prior conversation turns as role/content tuples.
        """
        input_decision = await self._defender.on_user_input(message, history)
        self._emit_decision(input_decision)
        if input_decision.decision == BLOCK_DECISION:
            self._block_count += 1
            return ShieldedSystemResponse(content=BLOCKED_RESPONSE)

        response = await self._inner_system.chat(message, history)
        for tool_execution in response.tool_executions:
            tool_decision = await self._defender.on_tool_call(
                tool_name=tool_execution.tool_name,
                arguments=tool_execution.arguments,
                conversation_history=history,
            )
            self._emit_decision(tool_decision)
            if tool_decision.decision == BLOCK_DECISION:
                self._block_count += 1

        return response

    def consume_block_count(self) -> int:
        """Return and reset the number of BLOCK decisions since the last call."""
        block_count = self._block_count
        self._block_count = 0
        return block_count

    def _emit_decision(self, decision: DefenderDecision) -> None:
        self._event_emitter.emit(ArenaEvent(event_type=EventType.DEFENDER_DECISION, payload=decision))
