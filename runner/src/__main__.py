"""CLI entry point for running attack scenarios."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from attack_agent.src.agent import AttackAgent
from common.src.config import settings
from common.src.event_emitter import DEFAULT_EVENTS_PATH, EventEmitter
from common.src.logging import DEFAULT_LOG_FILE, setup_logging
from runner.src.adapter import RealShieldedSystemAdapter
from runner.src.attack_source import LLMAttackSource
from runner.src.mock_system import MockShieldedSystem
from runner.src.runner import run_all_scenarios, run_attack_conversation, run_attack_scenario
from runner.src.scenario import ALL_SCENARIOS

MODE_LLM = "llm"
MODE_SCENARIO = "scenario"
LLM_SCENARIO_NAME = "llm_attack"


def main(
    events_path: Path = typer.Option(
        DEFAULT_EVENTS_PATH, help=f"JSONL event output path. Defaults to {DEFAULT_EVENTS_PATH}."
    ),
    delay: float = typer.Option(settings.runner_turn_delay_seconds, help="Seconds to wait between attack turns."),
    mock: bool = typer.Option(False, help="Use the mock shielded system instead of the real LLM-backed one."),
    mode: Annotated[str, typer.Option(help=f"Attack mode. Options: {MODE_LLM}, {MODE_SCENARIO}.")] = MODE_LLM,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable DEBUG-level logging."),
    log_file: Path = typer.Option(DEFAULT_LOG_FILE, help=f"Log file path. Defaults to {DEFAULT_LOG_FILE}."),
    scenario: str = typer.Option("all", help=f"Scenario to run. Options: all, {', '.join(ALL_SCENARIOS)}."),
) -> None:
    """Run attack scenarios against the shielded system.

    Args:
        events_path: JSONL event output path.
        delay: Seconds to wait between attack turns.
        mock: Use the mock shielded system instead of the real LLM-backed one.
        mode: Attack mode, either canned scenarios or LLM-generated attacks.
        verbose: Enable DEBUG-level logging.
        log_file: Log file path.
        scenario: Canned scenario to run when mode is scenario.
    """
    setup_logging(verbose=verbose, log_file=log_file)
    _validate_mode(mode)

    if events_path.exists():
        events_path.unlink()
    event_emitter = EventEmitter(events_path)
    system = MockShieldedSystem() if mock else RealShieldedSystemAdapter()

    if mode == MODE_LLM:
        asyncio.run(
            run_attack_conversation(
                shielded_system=system,
                event_emitter=event_emitter,
                attack_source=LLMAttackSource(AttackAgent()),
                scenario_name=LLM_SCENARIO_NAME,
                turn_delay_seconds=delay,
            )
        )
        return

    if scenario == "all":
        asyncio.run(
            run_all_scenarios(
                shielded_system=system,
                event_emitter=event_emitter,
                turn_delay_seconds=delay,
            )
        )
    else:
        if scenario not in ALL_SCENARIOS:
            available = ", ".join(ALL_SCENARIOS)
            raise typer.BadParameter(f"Unknown scenario '{scenario}'. Available: all, {available}")
        asyncio.run(
            run_attack_scenario(
                shielded_system=system,
                event_emitter=event_emitter,
                messages=ALL_SCENARIOS[scenario],
                scenario_name=scenario,
                turn_delay_seconds=delay,
            )
        )


def _validate_mode(mode: str) -> None:
    if mode not in {MODE_SCENARIO, MODE_LLM}:
        raise typer.BadParameter(f"Unknown mode '{mode}'. Available: {MODE_SCENARIO}, {MODE_LLM}")


if __name__ == "__main__":
    typer.run(main)
