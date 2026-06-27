set dotenv-load

default:
    @just --list

test:
    uv run --extra dev pytest

lint:
    uv run --extra dev ruff check .

run delay="1" events_path="data/events/arena_events.jsonl":
    uv run python -m runner.src --delay {{delay}} --events-path {{events_path}}

smoke:
    #!/usr/bin/env bash
    set -euo pipefail
    events_path="/tmp/agent-shield-arena-stream-c-smoke.jsonl"
    rm -f "${events_path}"
    uv run python -m runner.src --delay 0 --events-path "${events_path}"
    event_count="$(awk 'END { print NR }' "${events_path}")"
    test "${event_count}" = "12"
    echo "Stream C smoke passed: ${event_count} events"
