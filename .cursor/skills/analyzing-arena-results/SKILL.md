---
name: analyzing-arena-results
description: >-
  Analyze AgentShield Arena run results from data/ directory — attack success
  rates, defender block rates, strategy evolution across rounds, conversation
  traces, and memory entries. Use when the user asks to analyze arena results,
  review run outcomes, compute metrics, compare strategies, inspect traces,
  or understand attack/defense patterns from data/.
---

# Analyzing Arena Results

Use this skill to analyze the artifacts produced by arena runs. All data lives
under `data/` at the project root.

## Source-of-Truth References

| What | Authoritative source |
|---|---|
| Data artifacts & directory layout | [docs/04-data-artifacts.md](docs/04-data-artifacts.md) |
| Project context & terminology | [docs/01-project-brief.md](docs/01-project-brief.md) |
| Architecture & component design | [docs/02-design.md](docs/02-design.md) |
| Event & trace Pydantic models | [common/src/models.py](common/src/models.py) |
| Attack memory models | [attack_agent/src/memory.py](attack_agent/src/memory.py) |
| Defender memory models | [defender_agent/src/memory.py](defender_agent/src/memory.py) |
| Arena settings | [common/src/config.py](common/src/config.py) |
| Event emitter & run dir creation | [common/src/event_emitter.py](common/src/event_emitter.py) |
| Trace builder & save logic | [runner/src/trace_builder.py](runner/src/trace_builder.py) |
| Memory run dir creation | [runner/src/arena_artifacts.py](runner/src/arena_artifacts.py) |
| Business rules (shielded system) | [shielded_system/src/business_rules.txt](shielded_system/src/business_rules.txt) |
| Seed attack strategies | [attack_agent/src/strategies.py](attack_agent/src/strategies.py) |

When in doubt about a field name or type, check `common/src/models.py` — it is
the canonical schema for all events and traces.

## Quick Reference: Directory Layout

See [docs/04-data-artifacts.md](docs/04-data-artifacts.md) for the full
specification. Summary:

```
data/
├── events/{run_id}/arena_events.jsonl   # real-time event stream
├── events/latest -> {run_id}/           # symlink to most recent run
├── memory/{run_id}/
│   ├── attack_memory.jsonl              # cumulative attack outcomes
│   ├── defender_memory.jsonl            # learned defender patterns (when defender enabled)
│   └── round_{n}/traces/{trace_id}.json # one per conversation
├── memory/latest -> {run_id}/
└── logs/
    ├── arena.log
    └── dashboard.log
```

Run IDs are timestamps: `YYYYMMDD_HHMMSS`. Use `latest` symlink for the most
recent run, or list `data/events/` to pick a specific one.

## Loading Data

Use these snippets to load artifacts. Pydantic models for all schemas live in
[common/src/models.py](common/src/models.py),
[attack_agent/src/memory.py](attack_agent/src/memory.py), and
[defender_agent/src/memory.py](defender_agent/src/memory.py).

### Events (arena_events.jsonl)

```python
import json
from pathlib import Path

def load_events(run_id: str = "latest") -> list[dict]:
    path = Path(f"data/events/{run_id}/arena_events.jsonl")
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
```

Each event has: `event_id`, `timestamp`, `event_type`, `payload`.
Schema: `ArenaEvent` in [common/src/models.py](common/src/models.py).

### Traces (round_{n}/traces/*.json)

```python
def load_traces(run_id: str = "latest") -> list[dict]:
    base = Path(f"data/memory/{run_id}")
    return [json.loads(p.read_text()) for p in sorted(base.rglob("traces/*.json"))]
```

Each trace has: `trace_id`, `scenario_name`, `strategy_name`, `conversation` (list of turns), `timestamp`.
Schema: `Trace` in [common/src/models.py](common/src/models.py).

### Attack Memory (attack_memory.jsonl)

```python
def load_attack_memory(run_id: str = "latest") -> list[dict]:
    path = Path(f"data/memory/{run_id}/attack_memory.jsonl")
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
```

Each entry has: `entry_id`, `strategy_name`, `success` (bool), `violated_rule`, `affected_component`, `reflection` (tactical feedback object), `round_number`, `trace_id`.
Schema: `AttackMemoryEntry` / `TacticalReflection` in [attack_agent/src/memory.py](attack_agent/src/memory.py).

### Defender Memory (defender_memory.jsonl)

```python
def load_defender_memory(run_id: str = "latest") -> list[dict]:
    path = Path(f"data/memory/{run_id}/defender_memory.jsonl")
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
```

Each entry has: `entry_id`, `attack_intent`, `violated_rule`, `affected_component`, `signals`, `defensive_action`, `source_trace_id`, `round_number`.
Schema: `DefenderMemoryEntry` in [defender_agent/src/memory.py](defender_agent/src/memory.py).

## Key Event Types

All payload models are defined in [common/src/models.py](common/src/models.py).

| `event_type` | What it tells you | Key payload fields |
|---|---|---|
| `run_started` | Arena kicked off | `scenario_count` |
| `round_started` | New round began | `round_number`, `strategy_count` |
| `scenario_started` | Strategy conversation began | `scenario_name` |
| `conversation_turn` | Message exchanged | `role`, `content`, `tool_executions` |
| `tool_call` / `tool_result` | Tool was invoked/returned | `tool_name`, `arguments` / `result` |
| `defender_decision` | Defender checkpoint fired | `checkpoint`, `decision` (ALLOW/BLOCK), `reason`, `confidence`, `tool_name` |
| `evaluation_verdict` | Evaluator judged a trace | `trace_id`, `success`, `violation_type`, `violated_rule`, `evidence`, `severity` |
| `attack_reflection` | Post-mortem analysis | `strategy_name`, `round_number`, `success`, `tactic_used`, `why_outcome`, `suggested_mutations` |
| `attacker_reasoning` | Per-turn chain-of-thought | `strategy_name`, `turn_number`, `reasoning` |
| `attack_briefing` | Memory injected for round 2+ | `strategy_name`, `round_number`, `memory_context` |
| `triage_decision` | Remediation routing | `remediation_path` (defender_memory/code_change), `pattern_description` |
| `content_filter` | Provider content policy hit | `source`, `message` |

## Common Analysis Patterns

### 1. Attack Success Rate Per Strategy

```python
from collections import defaultdict

memory = load_attack_memory()
stats = defaultdict(lambda: {"success": 0, "fail": 0})
for entry in memory:
    key = entry["strategy_name"]
    stats[key]["success" if entry["success"] else "fail"] += 1

for strategy, counts in stats.items():
    total = counts["success"] + counts["fail"]
    rate = counts["success"] / total if total else 0
    print(f"{strategy}: {rate:.0%} ({counts['success']}/{total})")
```

### 2. Attack Success Rate Per Round (evolution over time)

```python
from collections import defaultdict

memory = load_attack_memory()
by_round = defaultdict(lambda: {"success": 0, "total": 0})
for entry in memory:
    by_round[entry["round_number"]]["total"] += 1
    if entry["success"]:
        by_round[entry["round_number"]]["success"] += 1

for rnd in sorted(by_round):
    s, t = by_round[rnd]["success"], by_round[rnd]["total"]
    print(f"Round {rnd}: {s}/{t} ({s/t:.0%})")
```

### 3. Defender Block Rate

```python
events = load_events()
decisions = [e for e in events if e["event_type"] == "defender_decision"]
blocks = [d for d in decisions if d["payload"]["decision"] == "BLOCK"]
allows = [d for d in decisions if d["payload"]["decision"] == "ALLOW"]
print(f"Blocked: {len(blocks)}/{len(decisions)} ({len(blocks)/len(decisions):.0%})")
```

Split by checkpoint:

```python
for cp in ("on_user_input", "on_tool_call"):
    cp_decisions = [d for d in decisions if d["payload"]["checkpoint"] == cp]
    cp_blocks = [d for d in cp_decisions if d["payload"]["decision"] == "BLOCK"]
    print(f"  {cp}: {len(cp_blocks)}/{len(cp_decisions)} blocked")
```

### 4. Defender Confidence Distribution

```python
confidences = [d["payload"]["confidence"] for d in decisions if d["payload"].get("confidence") is not None]
print(f"Mean: {sum(confidences)/len(confidences):.2f}, Min: {min(confidences):.2f}, Max: {max(confidences):.2f}")
```

### 5. Which Tools Were Blocked

```python
blocked_tools = [d["payload"]["tool_name"] for d in blocks if d["payload"].get("tool_name")]
from collections import Counter
for tool, count in Counter(blocked_tools).most_common():
    print(f"  {tool}: {count} blocks")
```

### 6. Violated Rules Summary

```python
verdicts = [e for e in events if e["event_type"] == "evaluation_verdict"]
violations = [v for v in verdicts if v["payload"]["success"]]
from collections import Counter
rules = Counter(v["payload"]["violated_rule"] for v in violations if v["payload"]["violated_rule"])
for rule, count in rules.most_common():
    print(f"  {rule}: {count}")
```

### 7. Tactical Reflection Analysis

```python
memory = load_attack_memory()
for entry in memory:
    r = entry.get("reflection")
    if not r:
        continue
    status = "SUCCESS" if entry["success"] else "FAIL"
    print(f"[{status}] {entry['strategy_name']} R{entry['round_number']}")
    print(f"  Tactic: {r['tactic_used']}")
    print(f"  Outcome: {r['why_outcome'][:120]}...")
    if r.get("defensive_trigger"):
        print(f"  Blocked by: {r['defensive_trigger']}")
    if r.get("suggested_mutations"):
        print(f"  Mutations: {len(r['suggested_mutations'])} suggestions")
    print()
```

### 8. Conversation Length Distribution

```python
traces = load_traces()
for t in traces:
    turns = len(t["conversation"])
    tools = sum(len(turn.get("tool_executions", [])) for turn in t["conversation"])
    print(f"{t['strategy_name']}: {turns} turns, {tools} tool calls")
```

### 9. Cross-Artifact Join (Trace -> Verdict -> Memory)

Link a trace to its evaluation verdict and memory entry:

```python
events = load_events()
memory = load_attack_memory()

verdicts_by_trace = {e["payload"]["trace_id"]: e["payload"]
                     for e in events if e["event_type"] == "evaluation_verdict"}
memory_by_trace = {e["trace_id"]: e for e in memory}

traces = load_traces()
for t in traces:
    tid = t["trace_id"]
    verdict = verdicts_by_trace.get(tid, {})
    mem = memory_by_trace.get(tid, {})
    print(f"Trace {tid[:8]}... | strategy={t['strategy_name']} | "
          f"success={verdict.get('success')} | violated={verdict.get('violated_rule')}")
```

### 10. Listing Available Runs

```python
from pathlib import Path

runs = sorted(Path("data/events").iterdir())
for r in runs:
    if r.is_symlink():
        print(f"  {r.name} -> {r.resolve().name}")
    elif r.is_dir():
        print(f"  {r.name}")
```

## Arena Configuration Context

Default settings from [common/src/config.py](common/src/config.py):

| Setting | Default | Meaning |
|---|---|---|
| `arena_rounds` | 3 | Rounds per run |
| `attack_max_messages` | 6 | Attacker message budget per conversation |
| `runner_max_turns` | 8 | Hard turn ceiling |
| `defender_enabled` | True | Whether Defender was active |
| `defender_input_mode` | "tip" | BLOCK decisions → security advisory vs hard block |
| `mutate_successful_attacks` | False | Repeat winning tactics vs try mutations |

A full run produces `arena_rounds × 4 strategies` conversations. The 4 seed
strategies are defined in [attack_agent/src/strategies.py](attack_agent/src/strategies.py):
`split-refund`, `identity-spoofing`, `social-engineering`, `prompt-extraction`.
Business rules the shielded system enforces are in
[shielded_system/src/business_rules.txt](shielded_system/src/business_rules.txt).

## Tips

- **Incomplete runs**: If the run was interrupted, events may exist without
  matching traces or memory entries. Always check for missing data.
- **Defender modes**: In `tip` mode, `BLOCK` on user input injects a security
  advisory instead of hard-blocking — the shielded system may still comply.
  In `block` mode, blocked messages are replaced entirely.
- **Content filters**: `content_filter` events mean the LLM provider refused a
  request. These cause skipped scenarios — check for gaps.
- **Tool result status**: `"status": "blocked"` in a tool result means the
  Defender blocked `on_tool_call`. The shielded system may still claim success
  in its message despite the tool being blocked.
