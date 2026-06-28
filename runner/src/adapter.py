"""Adapter bridging the real ShieldedSystem to the runner's expected interface."""

from runner.src.models import ShieldedSystemResponse, ToolExecution
from shielded_system.src.models import ChatMessage, ChatRole
from shielded_system.src.system import ShieldedSystem


class RealShieldedSystemAdapter:
    """Wraps the LLM-backed ShieldedSystem to match the runner Protocol.

    Args:
        shielded_system: The real LLM-backed shielded system instance.
    """

    def __init__(self, shielded_system: ShieldedSystem | None = None) -> None:
        self._system = shielded_system or ShieldedSystem()

    async def chat(
        self, message: str, history: list[tuple[str, str]], security_tip: str | None = None
    ) -> ShieldedSystemResponse:
        """Send a message to the real shielded system and adapt the response.

        Args:
            message: User message to process.
            history: Prior conversation turns as (role, content) tuples.
            security_tip: Optional security advisory to inject before the user message.
        """
        chat_history = [ChatMessage(role=ChatRole(role), content=content) for role, content in history]
        response = await self._system.chat(message=message, history=chat_history, security_tip=security_tip)

        tool_executions = [
            ToolExecution(
                tool_name=invocation.tool_name,
                arguments=invocation.arguments,
                result=invocation.result,
            )
            for invocation in response.tool_calls
        ]

        return ShieldedSystemResponse(content=response.message, tool_executions=tool_executions)
