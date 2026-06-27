# AgentShield Arena

Adaptive guardrails system for customer-facing AI agents. Hardens a **Defender** through adversarial self-play (the Arena), then deploys it as the runtime guardrails layer.

## Documentation

Documentation is in the [docs](docs/) directory. The most important documents are:

- [Project Brief](docs/01-project-brief.md) - problem statement, terminology, product vision
- [Design](docs/02-design.md) - architecture, components, arena loop, MVP scope

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
