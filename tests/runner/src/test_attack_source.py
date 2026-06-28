"""Tests for attack source adapters."""

from runner.src.attack_source import LLMAttackSource
from shielded_system.src.models import ChatMessage, ChatRole


class RecordingAttackAgent:
    """Attack agent test double that records converted history."""

    def __init__(self) -> None:
        """Initialize recorded request state."""
        self.histories: list[list[ChatMessage]] = []

    async def generate_attack(self, conversation_history: list[ChatMessage]) -> str | None:
        """Record history and return a deterministic attack message.

        Args:
            conversation_history: Conversation history converted for the attack agent.
        """
        self.histories.append(conversation_history)
        return "next attack"


class TestLLMAttackSourceNextMessage:
    async def test_when_history_contains_runner_tuples_expect_chat_messages_sent_to_agent(self) -> None:
        """Verify LLMAttackSource bridges runner history to AttackAgent history."""
        # arrange
        attack_agent = RecordingAttackAgent()
        attack_source = LLMAttackSource(attack_agent)
        history = [("user", "hello"), ("assistant", "hi")]
        expected_history = [
            ChatMessage(role=ChatRole.USER, content="hello"),
            ChatMessage(role=ChatRole.ASSISTANT, content="hi"),
        ]

        # act
        message = await attack_source.next_message(history)

        # assert
        assert message == "next attack"
        assert attack_agent.histories == [expected_history]
