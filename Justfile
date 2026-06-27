set dotenv-load := true
set positional-arguments := true

# List available recipes.
default:
    @just --list

# Install project dependencies, including optional development and dashboard extras.
sync:
    uv sync --all-extras

# Run the pytest suite.
test:
    uv run --extra dev pytest

# Run only Shielded System tests.
test-stream-a:
    uv run pytest tests/shielded_system

# Run Ruff lint checks.
lint:
    uv run --extra dev ruff check .

# Check Ruff formatting without modifying files.
format-check:
    uv run --extra dev ruff format --check .

# Format Python files with Ruff.
format:
    uv run --extra dev ruff format .

# Run the Stream C scenario and write JSONL events.
run delay="1" events_path="data/events/arena_events.jsonl":
    uv run python -m runner.src --delay {{ delay }} --events-path {{ events_path }}

# Run Stream C with no delay and verify the expected event count.
smoke:
    #!/usr/bin/env bash
    set -euo pipefail
    events_path="/tmp/agent-shield-arena-stream-c-smoke.jsonl"
    rm -f "${events_path}"
    uv run python -m runner.src --delay 0 --events-path "${events_path}"
    event_count="$(awk 'END { print NR }' "${events_path}")"
    test "${event_count}" = "12"
    echo "Stream C smoke passed: ${event_count} events"

# Verify the justfile itself without running long-lived project commands.
verify-justfile:
    just --unstable --fmt --check
    just --list
    just --dry-run sync
    just --dry-run test
    just --dry-run test-stream-a
    just --dry-run lint
    just --dry-run format-check
    just --dry-run format
    just --dry-run run
    just --dry-run smoke
