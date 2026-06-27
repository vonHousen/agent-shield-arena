# AgentShield Arena

Adaptive guardrails system for customer-facing AI agents. Hardens a **Defender** through adversarial self-play (the Arena), then deploys it as the runtime guardrails layer.

## Documentation

Documentation is in the [docs](docs/) directory. The most important documents are:

- [Project Brief](docs/01-project-brief.md) - problem statement, terminology, product vision
- [Design](docs/02-design.md) - architecture, components, arena loop, MVP scope

## Architecture

```text
shielded_system/        # The agent being protected
attack_agent/           # Attack generation and memory
defender_agent/         # Guardrails checkpoints and memory
evaluator/              # LLM judge
runner/                 # Arena orchestrator + CLI entry point
dashboard/
  src/                  # FastAPI + WebSocket backend
  static/               # Vanilla JS + Tailwind CDN frontend
common/                 # LLM client, event system, shared models, config
data/                   # Git-ignored runtime artifacts (JSONL files, traces)
```

See [Design Doc — Repository Architecture](docs/02-design.md#9-repository-architecture) for details.

## Quick Start

```bash
cp .env.example .env   # add your API keys
uv sync
uv run pytest
```

## Project Layout

Single `pyproject.toml` at the root — all components are top-level packages imported directly (e.g. `from common.src.models import ArenaEvent`). No uv workspace or per-package installs; everything runs from the project root.

## Development

Uses `uv` for packages and `just` as task runner.

```bash
just          # list available recipes
```

Available recipes:

- `just sync` - install all project extras.
- `just test` - run pytest through `uv`.
- `just lint` - run Ruff lint checks.
- `just format-check` - check Ruff formatting.
- `just format` - format Python files with Ruff.
- `just verify-justfile` - validate the justfile formatting and dry-run recipe commands.

Use `just verify-justfile` after editing recipes to confirm the task runner wiring still works without running long-lived commands.
