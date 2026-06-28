"""CLI entry point for running attack scenarios."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from attack_agent.src.memory import AttackMemory
from common.src.config import settings
from common.src.event_emitter import DEFAULT_EVENTS_DIR, EventEmitter, create_run_dir
from common.src.logging import DEFAULT_LOG_FILE, setup_logging
from evaluator.src.evaluator import Evaluator
from runner.src.adapter import RealShieldedSystemAdapter
from runner.src.arena_artifacts import (
    ATTACK_MEMORY_FILENAME,
    DEFAULT_MEMORY_DIR,
    create_memory_run_dir,
)
from runner.src.mock_system import MockShieldedSystem
from runner.src.runner import run_all_scenarios, run_arena, run_attack_scenario
from runner.src.scenario import ALL_SCENARIOS
from shielded_system.src.tools import reset_customer_db

MODE_LLM = "llm"
MODE_SCENARIO = "scenario"
BUSINESS_RULES_PATH = Path("shielded_system/src/business_rules.txt")


def main(
    events_dir: Path = typer.Option(
        DEFAULT_EVENTS_DIR, help=f"Parent directory for timestamped run output. Defaults to {DEFAULT_EVENTS_DIR}."
    ),
    memory_dir: Path = typer.Option(
        DEFAULT_MEMORY_DIR, help=f"Parent directory for timestamped memory output. Defaults to {DEFAULT_MEMORY_DIR}."
    ),
    delay: float = typer.Option(settings.runner_turn_delay_seconds, help="Seconds to wait between attack turns."),
    mock: bool = typer.Option(False, help="Use the mock shielded system instead of the real LLM-backed one."),
    mode: Annotated[str, typer.Option(help=f"Attack mode. Options: {MODE_LLM}, {MODE_SCENARIO}.")] = MODE_LLM,
    rounds: int = typer.Option(settings.arena_rounds, help="Number of arena rounds to run in LLM mode."),
    no_defender: bool = typer.Option(False, "--no-defender", help="Run the arena without Defender guardrails."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable DEBUG-level logging."),
    log_file: Path = typer.Option(DEFAULT_LOG_FILE, help=f"Log file path. Defaults to {DEFAULT_LOG_FILE}."),
    scenario: str = typer.Option("all", help=f"Scenario to run. Options: all, {', '.join(ALL_SCENARIOS)}."),
) -> None:
    """Run attack scenarios against the shielded system.

    Args:
        events_dir: Parent directory for timestamped run output.
        memory_dir: Parent directory for timestamped memory output.
        delay: Seconds to wait between attack turns.
        mock: Use the mock shielded system instead of the real LLM-backed one.
        mode: Attack mode, either canned scenarios or LLM-generated attacks.
        rounds: Number of arena rounds to run in LLM mode.
        no_defender: Run without Defender guardrails.
        verbose: Enable DEBUG-level logging.
        log_file: Log file path.
        scenario: Canned scenario to run when mode is scenario.
    """
    setup_logging(verbose=verbose, log_file=log_file)
    _validate_mode(mode)
    _defender_enabled = settings.defender_enabled and not no_defender

    events_path = create_run_dir(events_dir)
    memory_run_dir = create_memory_run_dir(memory_dir=memory_dir, run_id=events_path.parent.name)
    reset_customer_db()
    event_emitter = EventEmitter(events_path)
    system = MockShieldedSystem() if mock else RealShieldedSystemAdapter()

    if mode == MODE_LLM:
        asyncio.run(
            run_arena(
                shielded_system=system,
                event_emitter=event_emitter,
                evaluator=Evaluator(),
                memory=AttackMemory(memory_run_dir / ATTACK_MEMORY_FILENAME),
                business_rules=_load_business_rules(),
                memory_run_dir=memory_run_dir,
                rounds=rounds,
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


def _load_business_rules() -> str:
    return BUSINESS_RULES_PATH.read_text()


if __name__ == "__main__":
    typer.run(main)
