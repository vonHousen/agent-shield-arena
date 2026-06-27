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

# Run Ruff lint checks.
lint:
    uv run --extra dev ruff check .

# Check Ruff formatting without modifying files.
format-check:
    uv run --extra dev ruff format --check .

# Format Python files with Ruff.
format:
    uv run --extra dev ruff format .

# Verify the justfile itself without running long-lived project commands.
verify-justfile:
    just --unstable --fmt --check
    just --list
    just --dry-run sync
    just --dry-run test
    just --dry-run lint
    just --dry-run format-check
    just --dry-run format
