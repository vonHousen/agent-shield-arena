"""CLI entry point for running the attack scenario."""

import asyncio
from pathlib import Path

import typer

from common.src.event_emitter import DEFAULT_EVENTS_PATH, EventEmitter
from runner.src.adapter import RealShieldedSystemAdapter
from runner.src.mock_system import MockShieldedSystem
from runner.src.runner import DEFAULT_TURN_DELAY_SECONDS, run_default_attack_scenario


def main(
    events_path: Path = typer.Option(DEFAULT_EVENTS_PATH, help=f"JSONL event output path. Defaults to {DEFAULT_EVENTS_PATH}."),
    delay: float = typer.Option(DEFAULT_TURN_DELAY_SECONDS, help="Seconds to wait between attack turns."),
    mock: bool = typer.Option(False, help="Use the mock shielded system instead of the real LLM-backed one."),
) -> None:
    """Run the default attack scenario against the shielded system."""
    if events_path.exists():
        events_path.unlink()
    event_emitter = EventEmitter(events_path)
    system = MockShieldedSystem() if mock else RealShieldedSystemAdapter()

    asyncio.run(
        run_default_attack_scenario(
            shielded_system=system,
            event_emitter=event_emitter,
            turn_delay_seconds=delay,
        )
    )


if __name__ == "__main__":
    typer.run(main)
