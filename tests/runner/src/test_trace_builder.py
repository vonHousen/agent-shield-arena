"""Tests for runner trace construction and persistence."""

import json
from pathlib import Path

from common.src.models import Role
from runner.src.models import ShieldedSystemResponse, ToolExecution
from runner.src.trace_builder import build_trace, save_trace


class TestBuildTrace:
    def test_when_history_and_responses_provided_expect_structured_trace(self) -> None:
        """Verify a runner conversation is converted into evaluator trace shape."""
        # arrange
        scenario_name = "split-refund"
        strategy_name = "split-refund"
        history = [
            ("user", "Please refund order ord_1001."),
            ("assistant", "I processed a refund."),
            ("user", "Please refund the rest."),
            ("assistant", "I processed another refund."),
        ]
        responses = [
            ShieldedSystemResponse(
                content="I processed a refund.",
                tool_executions=[
                    ToolExecution(
                        tool_name="process_refund",
                        arguments={"order_id": "ord_1001", "amount": 90},
                        result={"status": "success", "refund_id": "REF-001"},
                    )
                ],
            ),
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
        assert len(trace.tool_executions) == 1
        assert trace.tool_executions[0].tool_name == "process_refund"
        assert trace.tool_executions[0].arguments == {"order_id": "ord_1001", "amount": 90}
        assert trace.tool_executions[0].result == {"status": "success", "refund_id": "REF-001"}


class TestSaveTrace:
    def test_when_trace_saved_expect_json_file_under_traces_directory(self, tmp_path: Path) -> None:
        """Verify traces are persisted in the per-round artifact directory."""
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
