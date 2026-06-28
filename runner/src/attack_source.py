"""Attack message sources for the dynamic runner loop."""

from collections.abc import Sequence
from typing import Protocol

ConversationHistory = list[tuple[str, str]]


class AttackSource(Protocol):
    """Interface for anything that can produce the next attacker message."""

    async def next_message(self, history: ConversationHistory) -> str | None:
        """Return the next attacker message, or None when the attack is done.

        Args:
            history: Conversation turns collected so far as role/content tuples.
        """


class AttackAgent(Protocol):
    """Minimal attack-agent interface wrapped by LLMAttackSource."""

    async def generate_attack(self, conversation_history: ConversationHistory) -> str | None:
        """Generate the next attack message, or None to stop.

        Args:
            conversation_history: Conversation turns collected so far as role/content tuples.
        """


class LLMAttackSource:
    """AttackSource adapter for the LLM-based Attack Agent."""

    def __init__(self, attack_agent: AttackAgent) -> None:
        """Initialize the source.

        Args:
            attack_agent: Attack agent used to generate attacker messages.
        """
        self._attack_agent = attack_agent

    async def next_message(self, history: ConversationHistory) -> str | None:
        """Return the next LLM-generated attacker message.

        Args:
            history: Conversation turns collected so far as role/content tuples.
        """
        return await self._attack_agent.generate_attack(history)


class MockAttackSource:
    """Deterministic AttackSource backed by canned messages."""

    def __init__(self, messages: Sequence[str]) -> None:
        """Initialize the source.

        Args:
            messages: Canned attacker messages returned in order.
        """
        self._messages = list(messages)
        self._index = 0

    async def next_message(self, history: ConversationHistory) -> str | None:
        """Return the next canned attacker message.

        Args:
            history: Conversation turns collected so far as role/content tuples.
        """
        if self._index >= len(self._messages):
            return None

        message = self._messages[self._index]
        self._index += 1
        return message
