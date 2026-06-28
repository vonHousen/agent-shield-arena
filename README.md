# AgentShield Arena

[Demo video](https://youtu.be/KvL2YOh7yb4)

**Self-improving** guardrails system for any customer-facing AI agent. An **Attack Agent** probes the **Shielded System** as a black box to discover both universal LLM vulnerabilities and system-specific business-rule violations. A **Defender** learns generalized patterns from every successful attack. Each round produces better attacks *and* better defenses — the system gets stronger over time, not weaker. The adversarial loop runs in development (the **Arena**); the hardened Defender then ships as the Shielded System's runtime guardrails in production — it *is* the guardrails, not a layer on top of them.

![Arena Architecture](docs/assets/arena-diagram.svg)

## Documentation

Documentation is in the [docs](docs/) directory. The most important documents are:

- [Project Brief](docs/01-project-brief.md) - problem statement, terminology, product vision
- [Design](docs/02-design.md) - architecture, components, arena loop, MVP scope
- [Architecture Diagrams](docs/assets/) - visual SVG diagrams of the Arena and production runtime

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

## Logging

Both the runner and dashboard write structured logs to `data/logs/` via Python's `logging` module:

- **Runner** → `data/logs/arena.log`
- **Dashboard** → `data/logs/dashboard.log`

Pass `--verbose` for DEBUG-level output or `--log-file <path>` to override the default location.

## Quick Start

Use `just` as task runner (use `just --list` to list all recipes).

### Prepare prerequisites

```bash
cp .env.example .env   # add your API keys
uv sync
just pre-commit-install
```

### Run the Arena

Run in separate terminals:

```bash
just dashboard reload=true  # start the live dashboard (http://127.0.0.1:8080)
just run                    # run the Arena demo → data/events/arena_events.jsonl
```
