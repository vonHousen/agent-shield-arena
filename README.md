# AgentShield Arena

**Self-improving** guardrails system for any customer-facing AI agent. An **Attack Agent** probes the **Shielded System** as a black box to discover both universal LLM vulnerabilities and system-specific business-rule violations. A **Defender** learns generalized patterns from every successful attack. Each round produces better attacks *and* better defenses — the system gets stronger over time, not weaker. The adversarial loop runs in development (the **Arena**); the hardened Defender then ships as the Shielded System's runtime guardrails in production — it *is* the guardrails, not a layer on top of them.

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

Single `pyproject.toml` at the root — all components are top-level packages imported directly (e.g. `from common.src.models import ArenaEvent`). No uv workspace or per-package installs; everything runs from the project root.

## Configuration

All runtime settings live in `common/src/config.py` as a Pydantic Settings class. Values are loaded from a `.env` file (or environment variables).

Usage in code:

```python
from common.src.config import settings

response = client.chat(model=settings.bifrost_model, ...)
```

## Quick Start

```bash
cp .env.example .env   # add your API keys
uv sync
just pre-commit-install
just <recipe>
```

Use `just` as task runner (use `just --list` to list all recipes).

```bash
just run         # run the Arena demo → data/events/arena_events.jsonl
just dashboard   # start the live dashboard (http://127.0.0.1:8080)
just ci          # full CI pipeline (lint + validate + tests)
```
