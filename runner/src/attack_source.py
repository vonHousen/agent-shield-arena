"""Attack message sources for the dynamic runner loop."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from attack_agent.src.agent import AttackOutput as AgentAttackOutput
from shielded_system.src.models import ChatMessage, ChatRole

ConversationHistory = list[tuple[str, str]]


@dataclass
class AttackOutput:
    """Structured output from an attack source containing the message and optional reasoning.

    Args:
        message: The customer message to send to the shielded system.
        reasoning: The attacker's tactical reasoning explaining its approach.
    """

    message: str
    reasoning: str | None = None


class AttackSource(Protocol):
    """Interface for anything that can produce the next attacker message."""

    async def next_message(self, history: ConversationHistory) -> AttackOutput | None:
        """Return the next attacker output, or None when the attack is done.

        Args:
            history: Conversation turns collected so far as role/content tuples.
        """


class AttackAgent(Protocol):
    """Minimal attack-agent interface wrapped by LLMAttackSource."""

    async def generate_attack(self, conversation_history: list[ChatMessage]) -> AgentAttackOutput | str | None:
        """Generate the next attack output, or None to stop.

        Args:
            conversation_history: Conversation turns converted to shielded-system chat messages.
        """


class LLMAttackSource:
    """AttackSource adapter for the LLM-based Attack Agent."""

    def __init__(self, attack_agent: AttackAgent) -> None:
        """Initialize the source.

        Args:
            attack_agent: Attack agent used to generate attacker messages.
        """
        self._attack_agent = attack_agent

    async def next_message(self, history: ConversationHistory) -> AttackOutput | None:
        """Return the next LLM-generated attacker output with reasoning.

        Args:
            history: Conversation turns collected so far as role/content tuples.
        """
        result = await self._attack_agent.generate_attack(_to_chat_messages(history))
        if result is None:
            return None
        if isinstance(result, str):
            return AttackOutput(message=result, reasoning=None)
        if isinstance(result, AgentAttackOutput):
            return AttackOutput(message=result.message, reasoning=result.reasoning)
        return AttackOutput(message=str(result), reasoning=None)


class MockAttackSource:
    """Deterministic AttackSource backed by canned messages."""

    def __init__(self, messages: Sequence[str]) -> None:
        """Initialize the source.

        Args:
            messages: Canned attacker messages returned in order.
        """
        self._messages = list(messages)
        self._index = 0

    async def next_message(self, history: ConversationHistory) -> AttackOutput | None:
        """Return the next canned attacker message (no reasoning).

        Args:
            history: Conversation turns collected so far as role/content tuples.
        """
        if self._index >= len(self._messages):
            return None

        message = self._messages[self._index]
        self._index += 1
        return AttackOutput(message=message, reasoning=None)


def _to_chat_messages(history: ConversationHistory) -> list[ChatMessage]:
    return [ChatMessage(role=ChatRole(role), content=content) for role, content in history]
