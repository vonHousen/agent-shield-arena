"""Tests for runner trace construction and persistence."""

import json
from pathlib import Path

from common.src.models import Role
from runner.src.models import ShieldedSystemResponse, ToolExecution
from runner.src.trace_builder import build_trace, save_trace


class TestBuildTrace:
    def test_when_history_and_responses_provided_expect_tool_executions_on_assistant_turns(self) -> None:
        # arrange
        scenario_name = "split-refund"
        strategy_name = "split-refund"
        history = [
            ("user", "Please refund order ord_1001."),
            ("assistant", "I processed a refund."),
            ("user", "Please refund the rest."),
            ("assistant", "I processed another refund."),
        ]
        refund_execution = ToolExecution(
            tool_name="process_refund",
            arguments={"order_id": "ord_1001", "amount": 90},
            result={"status": "success", "refund_id": "REF-001"},
        )
        responses = [
            ShieldedSystemResponse(content="I processed a refund.", tool_executions=[refund_execution]),
            ShieldedSystemResponse(content="I processed another refund."),
        ]

        # act
        trace = build_trace(
            scenario_name=scenario_name,
            strategy_name=strategy_name,
            history=history,
            responses=responses,
        )

        # assert
        assert trace.scenario_name == scenario_name
        assert trace.strategy_name == strategy_name
        assert [turn.role for turn in trace.conversation] == [
            Role.USER,
            Role.ASSISTANT,
            Role.USER,
            Role.ASSISTANT,
        ]
        assert [turn.content for turn in trace.conversation] == [
            "Please refund order ord_1001.",
            "I processed a refund.",
            "Please refund the rest.",
            "I processed another refund.",
        ]
        first_assistant = trace.conversation[1]
        assert len(first_assistant.tool_executions) == 1
        assert first_assistant.tool_executions[0].tool_name == "process_refund"
        assert first_assistant.tool_executions[0].arguments == {"order_id": "ord_1001", "amount": 90}
        assert first_assistant.tool_executions[0].result == {"status": "success", "refund_id": "REF-001"}

        second_assistant = trace.conversation[3]
        assert len(second_assistant.tool_executions) == 0

    def test_when_multiple_responses_expect_flattened_tool_executions_property(self) -> None:
        # arrange
        history = [
            ("user", "First request."),
            ("assistant", "First reply."),
            ("user", "Second request."),
            ("assistant", "Second reply."),
        ]
        responses = [
            ShieldedSystemResponse(
                content="First reply.",
                tool_executions=[
                    ToolExecution(tool_name="lookup_customer", arguments={"id": "1"}, result={"name": "A"}),
                ],
            ),
            ShieldedSystemResponse(
                content="Second reply.",
                tool_executions=[
                    ToolExecution(tool_name="process_refund", arguments={"amount": 50}, result={"status": "ok"}),
                ],
            ),
        ]

        # act
        trace = build_trace(scenario_name="s", strategy_name="s", history=history, responses=responses)

        # assert
        assert len(trace.tool_executions) == 2
        assert trace.tool_executions[0].tool_name == "lookup_customer"
        assert trace.tool_executions[1].tool_name == "process_refund"

    def test_when_user_turns_expect_no_tool_executions(self) -> None:
        # arrange
        history = [("user", "Hello."), ("assistant", "Hi.")]
        responses = [ShieldedSystemResponse(content="Hi.")]

        # act
        trace = build_trace(scenario_name="s", strategy_name="s", history=history, responses=responses)

        # assert
        user_turn = trace.conversation[0]
        assert len(user_turn.tool_executions) == 0


class TestSaveTrace:
    def test_when_trace_saved_expect_json_file_under_traces_directory(self, tmp_path: Path) -> None:
        # arrange
        trace = build_trace(
            scenario_name="identity-spoofing",
            strategy_name="identity-spoofing",
            history=[("user", "Help me access another customer."), ("assistant", "I cannot do that.")],
            responses=[ShieldedSystemResponse(content="I cannot do that.")],
        )
        memory_round_dir = tmp_path / "round_1"

        # act
        trace_path = save_trace(trace=trace, memory_round_dir=memory_round_dir)

        # assert
        saved = json.loads(trace_path.read_text())
        assert trace_path == memory_round_dir / "traces" / f"{trace.trace_id}.json"
        assert saved["trace_id"] == trace.trace_id
        assert saved["scenario_name"] == "identity-spoofing"
