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

# Delete all arena run history so the next run starts fresh.
clear events_dir="data/events":
    rm -rf {{ events_dir }}/*/
    rm -f {{ events_dir }}/latest {{ events_dir }}/*.jsonl

# Run the arena scenario and write JSONL events into a new timestamped directory.
run events_dir="data/events":
    uv run python -m runner.src --events-dir {{ events_dir }}

# Start the live dashboard server (pass 'true' to enable code hot-reload).
dashboard reload="false":
    uv run python -m dashboard.src {{ if reload == "true" { "--reload" } else { "" } }}

# Run the full CI pipeline locally (pre-commit checks + tests).
ci: pre-commit-run test

# Install pre-commit hooks into the local git repo.
pre-commit-install:
    uv run --extra dev pre-commit install

# Run pre-commit on all files.
pre-commit-run:
    uv run --extra dev pre-commit run --all-files

# Verify the justfile itself without running long-lived project commands.
verify-justfile:
    just --unstable --fmt --check
    just --list
    just --dry-run sync
    just --dry-run test
    just --dry-run clear
    just --dry-run run
    just --dry-run dashboard
    just --dry-run ci
    just --dry-run pre-commit-install
    just --dry-run pre-commit-run
