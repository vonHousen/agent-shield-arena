# Event Storage

## Overview

Every runner invocation (`python -m runner.src`) produces a stream of JSONL events that record the full arena session — scenario starts, conversation turns, tool calls, and run lifecycle markers. These events are the sole integration point between the runner and the dashboard.

## Directory layout

Each run is stored in its own timestamped directory under `data/events/`:

```
data/events/
  20260628_012133/
    arena_events.jsonl
  20260628_143500/
    arena_events.jsonl
  latest -> 20260628_143500/     (symlink)
```

- **Timestamped directories** (`YYYYMMDD_HHMMSS`) are created by [`create_run_dir()`](../common/src/event_emitter.py) at the start of each run.
- The **`latest` symlink** always points to the most recent run directory and is updated atomically on each run.
- The event file name is fixed: `arena_events.jsonl` (constant `EVENTS_FILENAME` in [`event_emitter.py`](../common/src/event_emitter.py)).

## Writing events

The [`EventEmitter`](../common/src/event_emitter.py) class appends serialized `ArenaEvent` objects as JSON lines. The runner CLI ([`runner/src/__main__.py`](../runner/src/__main__.py)) calls `create_run_dir()` to get a fresh file path, then passes it to `EventEmitter`.

## Event types

Defined as `EventType` in [`common/src/models.py`](../common/src/models.py):

| Event type | Payload | Emitted when |
|---|---|---|
| `run_started` | `scenario_count` | Arena begins |
| `run_completed` | — | Arena ends |
| `scenario_started` | `scenario_name` | A scenario begins |
| `conversation_turn` | `role`, `content` | Attacker or shielded system sends a message |
| `tool_call` | `tool_name`, `arguments` | Shielded system invokes a tool |
| `tool_result` | `tool_name`, `result` | Tool returns a result |

## Reading events (dashboard)

The dashboard ([`dashboard/src/app.py`](../dashboard/src/app.py)) provides two mechanisms:

1. **`GET /api/runs`** — lists all timestamped run directories, sorted newest-first.
2. **`/ws?run={id}`** — streams events from a specific run via WebSocket. Use `run=latest` (the default) to follow the `latest` symlink for live streaming.

The [`event_watcher`](../dashboard/src/event_watcher.py) tails the JSONL file, replaying existing content on connect and polling for new lines. When the file is deleted or truncated (e.g. the symlink flips to a new run), it emits a `ResetSignal` so the UI can clear its state.

## CLI recipes

| Recipe | Description |
|---|---|
| `just run` | Creates a new timestamped run directory and writes events |
| `just clear` | Removes all run directories and the `latest` symlink |
| `just dashboard` | Starts the dashboard server |
