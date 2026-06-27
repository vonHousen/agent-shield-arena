default:
    @just --list

lint:
    uv run --extra dev ruff check .

test:
    uv run pytest

test-stream-a:
    uv run pytest tests/shielded_system
