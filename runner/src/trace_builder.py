"""Build and persist evaluator traces from runner conversations."""

from pathlib import Path

from common.src.models import ConversationTurn, Role, Trace, TracedToolExecution
from runner.src.attack_source import ConversationHistory
from runner.src.models import ShieldedSystemResponse


def build_trace(
    scenario_name: str,
    strategy_name: str,
    history: ConversationHistory,
    responses: list[ShieldedSystemResponse],
) -> Trace:
    """Construct a structured evaluation trace from a completed conversation.

    Args:
        scenario_name: Scenario name emitted for the conversation.
        strategy_name: Attack strategy used to drive the conversation.
        history: Ordered conversation turns as role/content tuples.
        responses: Shielded system responses collected by the runner.
    """
    return Trace(
        scenario_name=scenario_name,
        strategy_name=strategy_name,
        conversation=[ConversationTurn(role=Role(role), content=content) for role, content in history],
        tool_executions=_trace_tool_executions(responses),
    )


def save_trace(trace: Trace, memory_round_dir: Path) -> Path:
    """Persist a trace as JSON under a round artifact directory.

    Args:
        trace: Trace to persist.
        memory_round_dir: Per-round memory artifact directory.
    """
    traces_dir = memory_round_dir / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    trace_path = traces_dir / f"{trace.trace_id}.json"
    trace_path.write_text(trace.model_dump_json(indent=2))
    return trace_path


def _trace_tool_executions(responses: list[ShieldedSystemResponse]) -> list[TracedToolExecution]:
    tool_executions: list[TracedToolExecution] = []
    for response in responses:
        for execution in response.tool_executions:
            tool_executions.append(
                TracedToolExecution(
                    tool_name=execution.tool_name,
                    arguments=execution.arguments,
                    result=execution.result,
                )
            )
    return tool_executions
