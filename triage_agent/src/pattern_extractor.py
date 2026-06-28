"""Convert triage decisions into defender memory entries."""

from common.src.models import EvaluationVerdict, TriageDecision
from defender_agent.src.memory import DefenderMemoryEntry


def extract_defender_pattern(
    triage_decision: TriageDecision,
    verdict: EvaluationVerdict,
    trace_id: str,
    round_number: int,
) -> DefenderMemoryEntry:
    """Convert a defender-memory triage decision into a defender memory entry.

    Args:
        triage_decision: Triage decision classified as a defender-memory remediation.
        verdict: Evaluation verdict that identified the successful attack.
        trace_id: Identifier of the trace that produced the triage decision.
        round_number: Arena round that produced the successful attack.
    """
    if triage_decision.remediation_path != "defender_memory":
        raise ValueError("Only defender_memory triage decisions can be converted to defender memory.")

    return DefenderMemoryEntry(
        attack_intent=triage_decision.pattern_description,
        violated_rule=verdict.violated_rule,
        affected_component=triage_decision.affected_component,
        signals=[triage_decision.pattern_description],
        defensive_action=f"BLOCK activity matching this pattern: {triage_decision.pattern_description}",
        source_trace_id=trace_id,
        round_number=round_number,
    )
