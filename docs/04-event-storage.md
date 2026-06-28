# Event Storage

## Overview

Every runner invocation (`python -m runner.src`) produces a stream of JSONL events that record the full arena session — round starts, scenario starts, conversation turns, tool calls, evaluation verdicts, and run lifecycle markers. These events are the sole integration point between the runner and the dashboard.

Slice v3 also writes memory artifacts for the same run: structured traces for evaluator input and cumulative attack memory entries.

## Directory layout

Each run is stored in its own timestamped directory under `data/events/`:

```
data/events/
  20260628_012133/
    arena_events.jsonl
  20260628_143500/
    arena_events.jsonl
  latest -> 20260628_143500/     (symlink)

data/memory/
  20260628_143500/
    attack_memory.jsonl
    round_1/
      traces/
        7c2f0c2e5a874c8c9b79d8e706fe28ad.json
    round_2/
      traces/
        ...
  latest -> 20260628_143500/     (symlink)
```

- **Timestamped event directories** (`YYYYMMDD_HHMMSS`) are created by [`create_run_dir()`](../common/src/event_emitter.py) at the start of each run.
- The memory directory uses the same timestamp as the event directory, created by [`create_memory_run_dir()`](../runner/src/arena_artifacts.py).
- The **`latest` symlink** in both `data/events/` and `data/memory/` always points to the most recent run directory and is updated atomically on each run.
- The event file name is fixed: `arena_events.jsonl` (constant `EVENTS_FILENAME` in [`event_emitter.py`](../common/src/event_emitter.py)).
- The attack memory file name is fixed: `attack_memory.jsonl` (constant `ATTACK_MEMORY_FILENAME` in [`arena_artifacts.py`](../runner/src/arena_artifacts.py)).

## Writing events

The [`EventEmitter`](../common/src/event_emitter.py) class appends serialized `ArenaEvent` objects as JSON lines. The runner CLI ([`runner/src/__main__.py`](../runner/src/__main__.py)) calls `create_run_dir()` to get a fresh file path, then passes it to `EventEmitter`.

## Writing memory artifacts

The runner creates a matching `data/memory/{YYYYMMDD_HHMMSS}/` directory for each event run.

- `attack_memory.jsonl` receives one [`AttackMemoryEntry`](../attack_agent/src/memory.py) per evaluated conversation.
- `round_{n}/traces/{trace_id}.json` stores one [`Trace`](../common/src/models.py) per completed strategy conversation.
- Trace files include the conversation turns and tool executions submitted to the evaluator.

## Event types

Defined as `EventType` in [`common/src/models.py`](../common/src/models.py):

| Event type | Payload | Emitted when |
|---|---|---|
| `run_started` | `scenario_count` | Arena begins |
| `run_completed` | — | Arena ends |
| `round_started` | `round_number`, `strategy_count` | A v3 arena round begins |
| `scenario_started` | `scenario_name` | A scenario begins |
| `conversation_turn` | `role`, `content` | Attacker or shielded system sends a message |
| `tool_call` | `tool_name`, `arguments` | Shielded system invokes a tool |
| `tool_result` | `tool_name`, `result` | Tool returns a result |
| `evaluation_verdict` | `trace_id`, `success`, `violation_type`, `violated_rule`, `evidence`, `severity` | Evaluator judges a completed trace |

## Reading events (dashboard)

The dashboard ([`dashboard/src/app.py`](../dashboard/src/app.py)) provides two mechanisms:

1. **`GET /api/runs`** — lists all timestamped run directories, sorted newest-first.
2. **`/ws?run={id}`** — streams events from a specific run via WebSocket. Use `run=latest` (the default) to follow the `latest` symlink for live streaming.

The [`event_watcher`](../dashboard/src/event_watcher.py) tails the JSONL file, replaying existing content on connect and polling for new lines. When the file is deleted or truncated (e.g. the symlink flips to a new run), it emits a `ResetSignal` so the UI can clear its state.

## CLI recipes

| Recipe | Description |
|---|---|
| `just run` | Creates a new timestamped run directory and writes events |
| `just run 2` | Runs a two-round arena and writes matching event and memory artifacts |
| `just clear` | Removes all event and memory run directories plus `latest` symlinks |
| `just dashboard` | Starts the dashboard server |
