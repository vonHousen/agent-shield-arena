"""LLM-backed customer-support shielded system."""

import json
import os
from typing import Any, Protocol

import litellm
from dotenv import load_dotenv

from common.src.llm_client import raise_on_content_filter
from shielded_system.src.models import ChatMessage, ChatRole, Response, ToolInvocation
from shielded_system.src.prompts import build_system_prompt, load_business_rules
from shielded_system.src.tools import TOOL_SCHEMAS, execute_tool

litellm.suppress_debug_info = True

BIFROST_API_BASE_ENV = "BIFROST_API_BASE"
BIFROST_API_KEY_ENV = "BIFROST_API_KEY"
BIFROST_MODEL_ENV = "BIFROST_MODEL"
DEFAULT_BIFROST_MODEL = "azure/gpt-5.4"
MAX_TOOL_ROUNDS = 4

load_dotenv()


class LLMClient(Protocol):
    """Async chat-completion client used by the shielded system."""

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        """Return a chat completion response.

        Args:
            messages: OpenAI-compatible chat messages.
            tools: OpenAI-compatible tool schemas.
        """


class LiteLLMClient:
    """LiteLLM adapter configured for the Bifrost gateway."""

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        """Return a chat completion response from LiteLLM.

        Args:
            messages: OpenAI-compatible chat messages.
            tools: OpenAI-compatible tool schemas.

        Raises:
            ContentFilterError: When the provider rejects the request due to content policy.
        """
        try:
            response = await litellm.acompletion(
                model=os.environ.get(BIFROST_MODEL_ENV, DEFAULT_BIFROST_MODEL),
                api_base=f"{os.environ[BIFROST_API_BASE_ENV]}/litellm",
                api_key=os.environ[BIFROST_API_KEY_ENV],
                messages=messages,
                tools=tools,
            )
        except litellm.BadRequestError as e:
            raise_on_content_filter(e)
            raise

        return response.model_dump()


class ShieldedSystem:
    """Customer-support assistant with mocked support tools.

    Args:
        llm_client: Async LLM client used to generate assistant messages.
        system_prompt: Full system prompt sent before every conversation.
    """

    def __init__(self, llm_client: LLMClient | None = None, system_prompt: str | None = None) -> None:
        self._llm_client = llm_client or LiteLLMClient()
        self._system_prompt = system_prompt or build_system_prompt(load_business_rules())

    async def chat(self, message: str, history: list[ChatMessage] | None = None) -> Response:
        """Respond to a user message and execute any requested support tools.

        Args:
            message: Latest user message.
            history: Previous conversation turns.
        """
        messages = _build_messages(self._system_prompt, message, history or [])
        tool_calls: list[ToolInvocation] = []

        for _round_number in range(MAX_TOOL_ROUNDS):
            completion = await self._llm_client.complete(messages=messages, tools=TOOL_SCHEMAS)
            assistant_message = _completion_message(completion)
            messages.append(assistant_message)

            requested_tools = assistant_message.get("tool_calls") or []
            if not requested_tools:
                return Response(message=assistant_message["content"] or "", tool_calls=tool_calls)

            for requested_tool in requested_tools:
                invocation = _execute_requested_tool(requested_tool)
                tool_calls.append(invocation)
                messages.append(_tool_result_message(requested_tool, invocation))

        return Response(
            message="I could not complete the request because too many tool steps were required.",
            tool_calls=tool_calls,
        )


async def chat(message: str, history: list[ChatMessage] | None = None) -> Response:
    """Respond to a user message using the default shielded system.

    Args:
        message: Latest user message.
        history: Previous conversation turns.
    """
    shielded_system = ShieldedSystem()
    return await shielded_system.chat(message=message, history=history)


def _build_messages(system_prompt: str, message: str, history: list[ChatMessage]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    messages.extend(_history_messages(history))
    messages.append({"role": "user", "content": message})
    return messages


def _history_messages(history: list[ChatMessage]) -> list[dict[str, Any]]:
    return [{"role": chat_message.role.value, "content": chat_message.content} for chat_message in history]


def _completion_message(completion: dict[str, Any]) -> dict[str, Any]:
    return completion["choices"][0]["message"]


def _execute_requested_tool(requested_tool: dict[str, Any]) -> ToolInvocation:
    function_call = requested_tool["function"]
    tool_name = function_call["name"]
    arguments = json.loads(function_call["arguments"])
    result = execute_tool(tool_name=tool_name, arguments=arguments)
    return ToolInvocation(tool_name=tool_name, arguments=arguments, result=result)


def _tool_result_message(requested_tool: dict[str, Any], invocation: ToolInvocation) -> dict[str, Any]:
    return {
        "role": ChatRole.TOOL.value,
        "tool_call_id": requested_tool["id"],
        "name": invocation.tool_name,
        "content": json.dumps(invocation.result),
    }
