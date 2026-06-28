"""CLI entry point for running attack scenarios."""

import asyncio
from pathlib import Path

import typer

from common.src.event_emitter import DEFAULT_EVENTS_PATH, EventEmitter
from common.src.logging import DEFAULT_LOG_FILE, setup_logging
from runner.src.adapter import RealShieldedSystemAdapter
from runner.src.mock_system import MockShieldedSystem
from runner.src.runner import DEFAULT_TURN_DELAY_SECONDS, run_all_scenarios, run_attack_scenario
from runner.src.scenario import ALL_SCENARIOS


def main(
    events_path: Path = typer.Option(
        DEFAULT_EVENTS_PATH, help=f"JSONL event output path. Defaults to {DEFAULT_EVENTS_PATH}."
    ),
    delay: float = typer.Option(DEFAULT_TURN_DELAY_SECONDS, help="Seconds to wait between attack turns."),
    mock: bool = typer.Option(False, help="Use the mock shielded system instead of the real LLM-backed one."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable DEBUG-level logging."),
    log_file: Path = typer.Option(DEFAULT_LOG_FILE, help=f"Log file path. Defaults to {DEFAULT_LOG_FILE}."),
    scenario: str = typer.Option("all", help=f"Scenario to run. Options: all, {', '.join(ALL_SCENARIOS)}."),
) -> None:
    """Run attack scenarios against the shielded system."""
    setup_logging(verbose=verbose, log_file=log_file)

    if events_path.exists():
        events_path.unlink()
    event_emitter = EventEmitter(events_path)
    system = MockShieldedSystem() if mock else RealShieldedSystemAdapter()

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


if __name__ == "__main__":
    typer.run(main)
