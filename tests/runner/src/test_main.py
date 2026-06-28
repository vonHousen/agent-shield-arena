"""Tests for the runner CLI entry point."""

import json
from pathlib import Path

from runner.src import __main__ as runner_main


class FakeAttackAgent:
    """Attack agent test double for CLI integration tests."""

    def __init__(self) -> None:
        """Initialize generated message state."""
        self._messages = ["first generated attack", "second generated attack"]
        self._index = 0

    async def generate_attack(self, conversation_history: list[object]) -> str | None:
        """Return generated attack messages and then stop.

        Args:
            conversation_history: Conversation turns observed by the attack agent.
        """
        if self._index >= len(self._messages):
            return None

        message = self._messages[self._index]
        self._index += 1
        return message


class TestMain:
    def test_when_mode_omitted_expect_llm_mode_drives_conversation(self, tmp_path: Path, monkeypatch) -> None:
        """Verify LLM mode is the default runner mode."""
        # arrange
        events_path = tmp_path / "events.jsonl"
        monkeypatch.setattr(runner_main, "AttackAgent", FakeAttackAgent)

        # act
        runner_main.main(
            events_path=events_path,
            delay=0,
            mock=True,
            verbose=False,
            log_file=tmp_path / "arena.log",
            scenario="all",
        )

        # assert
        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        attacker_messages = [
            event["payload"]["content"]
            for event in events
            if event["event_type"] == "conversation_turn" and event["payload"]["role"] == "user"
        ]
        assert events[0]["payload"]["scenario_name"] == "llm_attack"
        assert attacker_messages == ["first generated attack", "second generated attack"]

    def test_when_mode_llm_and_mock_system_expect_generated_messages_drive_conversation(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Verify LLM mode wires AttackAgent through LLMAttackSource into the runner."""
        # arrange
        events_path = tmp_path / "events.jsonl"
        monkeypatch.setattr(runner_main, "AttackAgent", FakeAttackAgent)

        # act
        runner_main.main(
            events_path=events_path,
            delay=0,
            mock=True,
            mode="llm",
            verbose=False,
            log_file=tmp_path / "arena.log",
            scenario="all",
        )

        # assert
        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        attacker_messages = [
            event["payload"]["content"]
            for event in events
            if event["event_type"] == "conversation_turn" and event["payload"]["role"] == "user"
        ]
        assert events[0]["event_type"] == "scenario_started"
        assert events[0]["payload"]["scenario_name"] == "llm_attack"
        assert attacker_messages == ["first generated attack", "second generated attack"]

    def test_when_invalid_mode_expect_bad_parameter(self, tmp_path: Path) -> None:
        """Verify CLI mode validation rejects unknown modes."""
        # arrange
        invalid_mode = "unknown"

        # act/assert
        try:
            runner_main.main(
                events_path=tmp_path / "events.jsonl",
                delay=0,
                mock=True,
                mode=invalid_mode,
                verbose=False,
                log_file=tmp_path / "arena.log",
                scenario="all",
            )
        except Exception as error:
            assert str(error) == f"Unknown mode '{invalid_mode}'. Available: scenario, llm"
        else:
            raise AssertionError("Expected invalid mode to raise an exception.")
