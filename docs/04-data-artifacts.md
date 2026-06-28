# Data Artifacts

## Overview

Each arena run produces three kinds of persistent artifacts:

| Artifact | Purpose | Format | Consumer |
|----------|---------|--------|----------|
| **Events** | Real-time stream of everything that happens during a run | JSONL (append-only) | Dashboard (live UI) |
| **Traces** | Structured snapshot of one completed conversation | JSON (one file per conversation) | Evaluator (judge input) |
| **Memory** | Cumulative logs of attack outcomes and learned defender patterns across rounds | JSONL (append-only) | Attack Agent and Defender prompt enrichment |

### How they relate

```
┌─────────────────── Arena Run ───────────────────┐
│                                                  │
│  Round 1                                         │
│    Strategy "split-refund"                       │
│      ├─ conversation happens (multiple turns)    │
│      │    └─ each turn emits EVENTS             │
│      ├─ conversation ends                        │
│      │    └─ full conversation saved as TRACE   │
│      ├─ evaluator judges the trace               │
│      │    └─ verdict emitted as EVENT           │
│      ├─ reflector produces tactical feedback     │
│      │    └─ analyzes trace + verdict → how/why │
│      └─ outcome + reflection stored in MEMORY   │
│           └─ used to enrich future prompts       │
│                                                  │
│  Round 2                                         │
│    Strategy "split-refund" (memory-enriched)     │
│      ├─ AttackAgent reads MEMORY for this        │
│      │  strategy → tactical reflections inform   │
│      │  what to try next and what to avoid       │
│      └─ ... same flow as above ...               │
│                                                  │
└──────────────────────────────────────────────────┘
```

## Events

**What:** A flat, ordered stream of everything that happens during an arena session. Every message, tool call, evaluation verdict, and lifecycle marker is appended as one JSON line.

**Why:** Powers the real-time dashboard. The dashboard tails this file via WebSocket and renders chat bubbles, tool calls, and verdict badges as they appear.

**Shape:** Each line is an `ArenaEvent` with `event_id`, `timestamp`, `event_type`, and `payload`.

| Event type | Payload fields | Emitted when |
|---|---|---|
| `run_started` | `scenario_count` | Arena begins |
| `run_completed` | — | Arena ends |
| `round_started` | `round_number`, `strategy_count` | A new round begins |
| `scenario_started` | `scenario_name` | A strategy conversation begins |
| `conversation_turn` | `role`, `content` | Attacker or shielded system sends a message |
| `tool_call` | `tool_name`, `arguments` | Shielded system invokes a tool |
| `tool_result` | `tool_name`, `result` | Tool returns a result |
| `evaluation_verdict` | `trace_id`, `success`, `violation_type`, `violated_rule`, `evidence`, `severity` | Evaluator judges a completed trace |
| `attack_reflection` | `strategy_name`, `round_number`, `success`, `tactic_used`, `why_outcome`, `defensive_trigger`, `suggested_mutations` | After each conversation |
| `attack_briefing` | `strategy_name`, `round_number`, `memory_context` | Before Round 2+ conversations (memory loaded) |
| `attacker_reasoning` | `strategy_name`, `turn_number`, `reasoning` | Each attacker turn |
| `defender_decision` | `checkpoint`, `decision`, `reason`, `confidence`, `tool_name`, `tool_arguments` | Defender checkpoint fires |
| `defender_tip` | `tip_text` | Security advisory injected (tip mode) |
| `defender_briefing` | `round_number`, `memory_context`, `entry_count` | Defender loads memory at Round 2+ start |
| `defender_reflection` | `strategy_name`, `round_number`, `attack_blocked`, `defensive_approach`, `why_outcome`, `vulnerability_identified`, `improvement_suggestion` | After each conversation (defender perspective) |
| `triage_decision` | `remediation_path`, `pattern_description`, `affected_component`, `rationale` | Successful attack triaged |
| `content_filter` | `source`, `message` | Provider content policy hit |

**Key property:** Events are write-once and never modified. The file only grows during a run.

## Traces

**What:** A structured JSON snapshot of one completed conversation (all turns + all tool executions), frozen at the moment the conversation ends.

**Why:** The evaluator needs a self-contained document to judge. Events are interleaved across multiple concurrent scenarios and contain lifecycle noise — traces are clean, per-conversation bundles.

**Shape:** A `Trace` object with `trace_id`, `scenario_name`, `strategy_name`, `conversation` (list of turns, where each assistant turn carries its `tool_executions`), and `timestamp`. A `tool_executions` property on `Trace` provides a flattened list across all turns for convenience.

**Key property:** Traces are immutable after creation. They serve as the evaluator's input and as an audit trail for debugging evaluator judgments.

## Memory

**What:** JSONL memory files scoped to one arena run. `attack_memory.jsonl` records one attack outcome per evaluated conversation. `defender_memory.jsonl` records generalized exploit patterns learned from triage when the Defender is enabled.

**Why:** The Attack Agent reads attack memory entries for its current strategy to adapt its prompt in subsequent rounds. The Defender reads defender memory entries as known patterns to include in checkpoint prompts. Tactical reflections provide actionable intelligence: what tactic was tried, why it worked or failed, and what to try next.

**Shape:** Each line in `attack_memory.jsonl` is an `AttackMemoryEntry` with `entry_id`, `strategy_name`, `success`, `violated_rule`, `affected_component`, `reflection` (a `TacticalReflection` object with `tactic_used`, `why_outcome`, `defensive_trigger`, and `suggested_mutations`), `round_number`, and `trace_id`. Each line in `defender_memory.jsonl` is a `DefenderMemoryEntry` with generalized attack intent, signals, defensive action, source trace, and round number.

**Key property:** Memory grows across rounds within a single run. Round 2 reads entries from round 1; round 3 reads entries from rounds 1 and 2. This is the self-improvement mechanism.

## Directory layout

Both artifacts share the same timestamped run ID:

```
data/events/
  20260628_040614/
    arena_events.jsonl              ← event stream (all rounds)
  latest -> 20260628_040614/        ← symlink to most recent

data/memory/
  20260628_040614/
    attack_memory.jsonl             ← cumulative attack outcomes
    defender_memory.jsonl           ← learned defender patterns (when defender enabled)
    round_1/
      traces/
        5b126bad...d5b64077.json    ← one trace per strategy
        a2334...09437793.json
        ...
    round_2/
      traces/
        2dcbb0...46fdbac1.json
        ...
  latest -> 20260628_040614/        ← symlink to most recent
```

- **Timestamped event directories** (`YYYYMMDD_HHMMSS`) are created by [`create_run_dir()`](../common/src/event_emitter.py) at the start of each run.
- The memory directory uses the same timestamp, created by [`create_memory_run_dir()`](../runner/src/arena_artifacts.py).
- The **`latest` symlink** in both directories always points to the most recent run and is updated atomically.
- The event file name is fixed: `arena_events.jsonl` (constant `EVENTS_FILENAME` in [`event_emitter.py`](../common/src/event_emitter.py)).
- The memory file name is fixed: `attack_memory.jsonl` (constant `ATTACK_MEMORY_FILENAME` in [`arena_artifacts.py`](../runner/src/arena_artifacts.py)).

## Writing artifacts

### Events

The [`EventEmitter`](../common/src/event_emitter.py) class appends serialized `ArenaEvent` objects as JSON lines. The runner CLI ([`runner/src/__main__.py`](../runner/src/__main__.py)) calls `create_run_dir()` to get a fresh file path, then passes it to `EventEmitter`.

### Traces

The runner calls [`build_trace()`](../runner/src/trace_builder.py) after each conversation completes, then [`save_trace()`](../runner/src/trace_builder.py) to persist the JSON file under `round_{n}/traces/`.

### Memory

The runner calls [`AttackMemory.append()`](../attack_agent/src/memory.py) after the evaluator returns a verdict. The `AttackMemory` class handles file creation and JSONL serialization.

## Reading artifacts

### Events → Dashboard

The dashboard ([`dashboard/src/app.py`](../dashboard/src/app.py)) provides:

1. **`GET /api/runs`** — lists all timestamped run directories, sorted newest-first.
2. **`/ws?run={id}`** — streams events from a specific run via WebSocket. Use `run=latest` (the default) to follow the `latest` symlink for live streaming.

The [`event_watcher`](../dashboard/src/event_watcher.py) tails the JSONL file, replaying existing content on connect and polling for new lines.

### Memory → Attack Agent

The [`AttackAgent`](../attack_agent/src/agent.py) receives an `AttackMemory` instance at construction. When building its system prompt, it calls `memory.get_by_strategy(strategy_name)` and formats prior tactical reflections into the prompt — including what tactic was used, why it worked or failed, and defensive triggers encountered. Suggested mutations are always shown for failed attacks. For successful attacks, mutations are only shown when `mutate_successful_attacks=True` (default: `False`), so successful tactics are repeated as-is by default.

Note: memory enriches the Attack Agent's *prompt* (what tactics to try), but strategy *selection* (which strategies run each round) currently uses the fixed set of 4 seed strategies in order. A `MemoryDrivenStrategySelector` exists in code but is not wired into the runner.

### Memory → Defender

The [`Defender`](../defender_agent/src/defender.py) receives a `DefenderMemory` instance when defender mode is enabled. Before Round 2+ conversations, the runner emits a `defender_briefing` event when defender memory exists, and the Defender formats all learned patterns into its checkpoint prompts. The MVP uses full-scan JSONL retrieval.

## CLI recipes

| Recipe | Description |
|---|---|
| `just run` | 3-round arena (default), writes events + memory artifacts |
| `just run 2` | 2-round arena |
| `just clear` | Removes all event and memory run directories plus `latest` symlinks |
| `just dashboard` | Starts the dashboard server |
