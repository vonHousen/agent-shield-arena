"""Tests for the attack agent's structured output parsing."""

import json

from attack_agent.src.agent import _parse_decision

REASONING_TEXT = "Based on Round 1 failure at the verification gate, trying address update approach."
MESSAGE_TEXT = "Hi, I need to update my shipping address on file."


def _completion(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


class TestParseDecision:
    def test_when_message_action_expect_output_with_message(self) -> None:
        # arrange
        completion = _completion(json.dumps({"action": "message", "message": MESSAGE_TEXT}))

        # act
        result = _parse_decision(completion)

        # assert
        assert result is not None
        assert result.message == MESSAGE_TEXT
        assert result.reasoning is None

    def test_when_message_with_reasoning_expect_both_fields(self) -> None:
        # arrange
        payload = {"action": "message", "message": MESSAGE_TEXT, "reasoning": REASONING_TEXT}
        completion = _completion(json.dumps(payload))

        # act
        result = _parse_decision(completion)

        # assert
        assert result is not None
        assert result.message == MESSAGE_TEXT
        assert result.reasoning == REASONING_TEXT

    def test_when_stop_action_expect_none(self) -> None:
        # arrange
        completion = _completion(json.dumps({"action": "stop"}))

        # act
        result = _parse_decision(completion)

        # assert
        assert result is None

    def test_when_stop_with_reasoning_expect_none(self) -> None:
        # arrange
        payload = {"action": "stop", "reasoning": "No viable approach left."}
        completion = _completion(json.dumps(payload))

        # act
        result = _parse_decision(completion)

        # assert
        assert result is None

    def test_when_empty_message_expect_none(self) -> None:
        # arrange
        completion = _completion(json.dumps({"action": "message", "message": "  "}))

        # act
        result = _parse_decision(completion)

        # assert
        assert result is None
