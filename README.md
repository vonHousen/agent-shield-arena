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

## Development

Uses `uv` for packages and `just` as task runner.

```bash
just          # list available recipes
```
