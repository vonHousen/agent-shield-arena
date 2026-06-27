"""Tests for the shielded-system chat loop."""

import json
from copy import deepcopy
from typing import Any

import pytest

from shielded_system.src.models import ChatMessage, ChatRole
from shielded_system.src.system import ShieldedSystem
from shielded_system.src.tools import reset_customer_db


class FakeLLMClient:
    """Fake async LLM client returning predefined completions."""

    def __init__(self, completions: list[dict[str, Any]]) -> None:
        self.completions = completions
        self.requests: list[dict[str, Any]] = []

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        """Return the next predefined completion.

        Args:
            messages: Chat messages sent to the LLM.
            tools: Tool schemas sent to the LLM.
        """
        self.requests.append({"messages": deepcopy(messages), "tools": deepcopy(tools)})
        return self.completions.pop(0)


class TestShieldedSystemChat:
    @pytest.mark.asyncio
    async def test_when_llm_returns_text_expect_response_without_tool_calls(self) -> None:
        # arrange
        assistant_message = "I can help with that."
        llm_client = FakeLLMClient(completions=[_completion(content=assistant_message)])
        shielded_system = ShieldedSystem(llm_client=llm_client, system_prompt="system prompt")

        # act
        response = await shielded_system.chat(message="hello")

        # assert
        assert response.message == assistant_message
        assert response.tool_calls == []
        assert llm_client.requests[0]["messages"] == [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "hello"},
        ]

    @pytest.mark.asyncio
    async def test_when_llm_requests_tool_expect_tool_result_sent_back_to_llm(self) -> None:
        # arrange
        reset_customer_db()
        customer_id = "cus_001"
        order_id = "ord_1001"
        amount = 30
        reason = "damaged"
        llm_client = FakeLLMClient(
            completions=[
                _completion(
                    content=None,
                    tool_calls=[
                        _tool_call(
                            name="process_refund",
                            arguments={
                                "customer_id": customer_id,
                                "order_id": order_id,
                                "amount": amount,
                                "reason": reason,
                            },
                        )
                    ],
                ),
                _completion(content="Your refund has been processed."),
            ]
        )
        shielded_system = ShieldedSystem(llm_client=llm_client, system_prompt="system prompt")

        # act
        response = await shielded_system.chat(message="Please refund my damaged item.")

        # assert
        assert response.message == "Your refund has been processed."
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].tool_name == "process_refund"
        assert response.tool_calls[0].arguments["amount"] == amount
        assert response.tool_calls[0].result["status"] == "processed"
        assert llm_client.requests[1]["messages"][-1]["role"] == "tool"
        assert '"status": "processed"' in llm_client.requests[1]["messages"][-1]["content"]

    @pytest.mark.asyncio
    async def test_when_history_provided_expect_history_sent_before_new_message(self) -> None:
        # arrange
        llm_client = FakeLLMClient(completions=[_completion(content="Sure.")])
        shielded_system = ShieldedSystem(llm_client=llm_client, system_prompt="system prompt")
        history = [
            ChatMessage(role=ChatRole.USER, content="Earlier question"),
            ChatMessage(role=ChatRole.ASSISTANT, content="Earlier answer"),
        ]

        # act
        await shielded_system.chat(message="Follow up", history=history)

        # assert
        assert llm_client.requests[0]["messages"] == [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "Earlier question"},
            {"role": "assistant", "content": "Earlier answer"},
            {"role": "user", "content": "Follow up"},
        ]


def _completion(content: str | None, tool_calls: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    message = {"role": "assistant", "content": content}
    if tool_calls is not None:
        message["tool_calls"] = tool_calls
    return {"choices": [{"message": message}]}


def _tool_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {"id": "call_001", "function": {"name": name, "arguments": _json_arguments(arguments)}}


def _json_arguments(arguments: dict[str, Any]) -> str:
    return json.dumps(arguments)
