"""CLI entry point for running the attack scenario."""

import argparse
import asyncio
from pathlib import Path

from common.src.event_emitter import DEFAULT_EVENTS_PATH, EventEmitter
from runner.src.adapter import RealShieldedSystemAdapter
from runner.src.mock_system import MockShieldedSystem
from runner.src.runner import DEFAULT_TURN_DELAY_SECONDS, run_default_attack_scenario


def main() -> None:
    """Run the default attack scenario against the shielded system."""
    args = _parse_args()
    event_emitter = EventEmitter(args.events_path)
    system = MockShieldedSystem() if args.mock else RealShieldedSystemAdapter()

    asyncio.run(
        run_default_attack_scenario(
            shielded_system=system,
            event_emitter=event_emitter,
            turn_delay_seconds=args.delay,
        )
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the attack scenario against the shielded system.")
    parser.add_argument(
        "--events-path",
        type=Path,
        default=DEFAULT_EVENTS_PATH,
        help=f"JSONL event output path. Defaults to {DEFAULT_EVENTS_PATH}.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_TURN_DELAY_SECONDS,
        help="Seconds to wait between attack turns.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use the mock shielded system instead of the real LLM-backed one.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
