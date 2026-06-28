"""Tests for the attack agent's structured output parsing."""

import json

from attack_agent.src.agent import _parse_decision

REASONING_TEXT = "Based on Round 1 failure at the verification gate, trying address update approach."
MESSAGE_TEXT = "Hi, I need to update my shipping address on file."


def _completion(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


class TestParseDecisionFirstTurn:
    def test_when_valid_first_turn_expect_output_with_message(self) -> None:
        # arrange
        payload = {"reasoning": REASONING_TEXT, "message": MESSAGE_TEXT}
        completion = _completion(json.dumps(payload))

        # act
        result = _parse_decision(completion, is_first_turn=True)

        # assert
        assert result is not None
        assert result.message == MESSAGE_TEXT
        assert result.reasoning == REASONING_TEXT

    def test_when_empty_message_on_first_turn_expect_none(self) -> None:
        # arrange
        payload = {"reasoning": REASONING_TEXT, "message": "  "}
        completion = _completion(json.dumps(payload))

        # act
        result = _parse_decision(completion, is_first_turn=True)

        # assert
        assert result is None


class TestParseDecisionSubsequentTurn:
    def test_when_message_action_expect_output_with_message(self) -> None:
        # arrange
        payload = {"reasoning": REASONING_TEXT, "action": "message", "message": MESSAGE_TEXT}
        completion = _completion(json.dumps(payload))

        # act
        result = _parse_decision(completion, is_first_turn=False)

        # assert
        assert result is not None
        assert result.message == MESSAGE_TEXT
        assert result.reasoning == REASONING_TEXT

    def test_when_stop_action_expect_none(self) -> None:
        # arrange
        payload = {"reasoning": "No viable approach left.", "action": "stop", "message": "Nothing to try."}
        completion = _completion(json.dumps(payload))

        # act
        result = _parse_decision(completion, is_first_turn=False)

        # assert
        assert result is None

    def test_when_empty_message_on_subsequent_turn_expect_none(self) -> None:
        # arrange
        payload = {"reasoning": REASONING_TEXT, "action": "message", "message": "  "}
        completion = _completion(json.dumps(payload))

        # act
        result = _parse_decision(completion, is_first_turn=False)

        # assert
        assert result is None
