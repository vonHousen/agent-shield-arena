# Build Plan

## ~~Slice v1: Live Conversation Demo~~ ✅ DONE

Goal: A single hard-coded multi-turn attack scenario runs against the Shielded System (no Defender), and the UI shows the conversation exchange in real time.

Success condition: Run the attack runner → see messages appear in the browser as chat bubbles, including tool calls.

---

## ~~Shared Contract (do first, ~15 min)~~ ✅ DONE

Before the streams diverge, define the shared event schema and project scaffolding.

Deliverables:

```text
root pyproject.toml (workspace, shared deps: pydantic)
.env with Bifrost config
ArenaEvent pydantic models (shared contract between producer and consumer)
EventEmitter (appends ArenaEvent as JSON lines to JSONL file)

directory layout:
  common/src/             — shared models (ArenaEvent, etc.), EventEmitter, LLM client, config
  shielded_system/src/    — Stream A
  dashboard/src/          — Stream B (FastAPI + WebSocket), dashboard/static/ (HTML/JS)
  runner/src/             — Stream C (attack runner)
```

Event types for v1:

```text
conversation_turn  — who said what (role + content)
tool_call          — system invoked a tool (name + args)
tool_result        — tool returned (name + result)
```

---

## ~~Stream A: Shielded System~~ ✅ DONE

Scope: LLM-based support agent with mocked dependencies. No dependency on UI or runner.

Deliverables:

```text
system prompt (customer support persona, tool descriptions)
mock tools: process_refund, lookup_customer, update_shipping_address
fake customer DB (in-memory dict, 2-3 customers)
business_rules.txt (5-6 rules, plain text)
chat interface: async def chat(message, history) -> Response
  — calls LiteLLM, executes tool calls against mocks, returns response
```

Testable standalone with a simple script or pytest — no UI, no runner needed.

Status:

- Merged `stream-a` into `master`.
- Added the shielded system implementation, mock tools, prompts, response models, and tests.
- Confirmed with `uv run pytest tests/shielded_system` — 8 tests passed.

---

## ~~Stream B: Real-time Dashboard~~ ✅ DONE

Scope: The thing people look at during the demo. No dependency on real Shielded System or Attack Agent.

Deliverables:

```text
FastAPI WebSocket endpoint (/ws)
event_watcher.py (async JSONL file tailer → yields ArenaEvent objects)
single HTML page with conversation panel
  — left: attacker messages, right: system responses
  — tool calls shown inline
JS WebSocket client (receives events, renders chat bubbles)
mock event producer script (writes fake events to JSONL file for dev/testing)
```

Develop and test entirely against fake events written to the JSONL file.

Status:

- Merged `stream-b-dashboard` into `master`.
- Added the FastAPI app, WebSocket endpoint, event watcher, mock event producer, static dashboard UI, and watcher tests.
- Resolved README and Justfile integration conflicts.
- Confirmed with `uv run pytest tests/dashboard` — 2 tests passed.

---

## ~~Stream C: Attack Runner + Scenario~~ ✅ DONE

Scope: The thing that drives the conversation. No dependency on UI during development (uses mock system).

Deliverables:

```text
hard-coded multi-turn attack scenario (3-4 turns, e.g. split-refund bypass)
runner loop:
  — sends each message to ShieldedSystem.chat()
  — collects response
  — emits events via EventEmitter (appends to JSONL file)
  — asyncio.sleep between turns (real-time pacing for demo)
```

During development, can use a mock Shielded System (echo bot) to test runner + emitter independently.

Status:

- Merged `stream-c-attack-runner` into `master`.
- Added the runner CLI, hard-coded attack scenario, mock system, runner models, and tests.
- Integrated Stream C recipes into the canonical `Justfile`.
- Confirmed with `uv run pytest tests/runner` — 2 tests passed.
- Confirmed with `uv run just smoke` — emitted the expected 12 JSONL events.

---

## Dependency Graph

```text
common/ (event models, EventEmitter, LLM client, config)
       │
       ├── Stream A (Shielded System) ─── no deps on B or C
       ├── Stream B (Dashboard) ────────── tails JSONL file, no deps on A or C
       └── Stream C (Attack Runner) ────── uses mock system, no deps on A or B

Integration (wire A+B+C together) ── ✅ merged and mechanically verified
```

Integration status:

- Streams 1-3 are merged into `master` in order: `stream-a`, `stream-b-dashboard`, `stream-c-attack-runner`.
- Kept one canonical `Justfile` and removed duplicate lowercase `justfile` entries from merge results.
- Confirmed the integrated test suite with `uv run pytest` — 12 tests passed.
- Confirmed linting with `uv run --extra dev ruff check .` — passed.
- Confirmed recipe wiring with `uv run just verify-justfile` — passed.

---

## ~~Slice v1 Verification~~ ✅ DONE

After integration, confirm the slice works end-to-end:

1. Start the dashboard (`uv run --extra dashboard python -m dashboard.src`)
2. Open browser at `http://localhost:8080`
3. Run the attack runner (`uv run python -m runner.src`)
4. Verify: chat bubbles appear in real time — attacker messages on the left, system responses on the right, tool calls shown inline
5. Verify: the JSONL file (`data/events/arena_events.jsonl`) contains `conversation_turn`, `tool_call`, and `tool_result` events

---

## Slice v2: LLM-based Attack Agent

Goal: Replace the hard-coded attack scenario with an LLM-driven Attack Agent that autonomously generates and adapts attacks in a dynamic multi-turn conversation.

Success condition: Run the runner → the Attack Agent generates its own messages (not hard-coded), drives a full multi-turn conversation against the Shielded System, and all events appear in the JSONL file.

---

### ~~Shared: Settings (do first)~~ DONE

Extend `common/src/config.py` with all v2 params in the existing `Settings` class:

```text
common/src/config.py (extend Settings)
  — attack_max_messages: int = 10        # Attack Agent message budget per conversation
  — runner_max_turns: int = 12           # Runner hard ceiling (safety net, > attack budget)
  — runner_turn_delay_seconds: float = 1.0  # pause between turns for demo pacing
```

All streams read from `settings` — no magic numbers in agent or runner code.

---

### ~~Stream A: Attack Agent Core~~ ✅ DONE

Scope: The LLM agent that generates attack messages given conversation history. No dependency on runner refactor — testable standalone.

Deliverables:

```text
attack_agent/src/agent.py
  — system prompt (adversarial persona, goal: bypass business rules)
  — async def generate_attack(conversation_history) -> str | None
      returns None when the agent decides to stop (goal achieved or budget exhausted)
  — uses LiteLLM via common/ LLM client
  — reads settings.attack_max_messages to enforce turn budget
      ⚠️  the agent must track its own turn count and stop when budget is exhausted;
      the runner also enforces runner_max_turns as a hard ceiling, but the agent should
      self-terminate gracefully before hitting it
attack_agent/src/strategies.py
  — seed attack strategies (split-refund, identity spoofing, social engineering, etc.)
  — strategy selection logic (round-robin or random for v2, memory-driven in v3)
```

Testable standalone: given a mock conversation history, the agent produces a plausible next attack message.

Status:

- Implemented on `slice2-streamA` in commit `6c5e81e` (`add(attack-agent): Implement attack agent core.`).
- Added `attack_agent/src/agent.py`, `attack_agent/src/strategies.py`, and shared `common/src/llm_client.py`.
- Confirmed with `uv run --extra dev pytest tests/attack_agent` — 4 tests passed.
- Confirmed with commit hooks: ruff, ruff format, and ty passed.

---

### ~~Stream B: Runner v2 (Dynamic Conversation Loop)~~ ✅ DONE

Scope: Refactor the runner to support dynamic multi-turn conversation driven by any attack source (protocol/interface). No dependency on the real Attack Agent — testable with a mock.

Deliverables:

```text
runner/src/runner.py (refactored)
  — replace hard-coded scenario with a loop:
      1. ask attack source for next message (given conversation history)
      2. send to ShieldedSystem.chat()
      3. collect response, append to history
      4. emit events
      5. repeat until attack source signals done or settings.runner_max_turns reached
  — reads settings.runner_max_turns (hard ceiling)
  — reads settings.runner_turn_delay_seconds (pacing)
  — attack source interface: async def next_message(history) -> str | None
runner/src/attack_source.py
  — AttackSource protocol (abstract interface)
  — LLMAttackSource (wraps attack_agent)
  — MockAttackSource (for testing, returns canned messages)
```

Testable standalone: runner drives a full conversation using MockAttackSource, emits correct events.

Status:

- Implemented on `slice2-streamB` in commit `0294463` (`update(runner): Add dynamic attack source loop.`).
- Added the `AttackSource` protocol, `LLMAttackSource`, and `MockAttackSource`.
- Refactored the runner through a dynamic `run_attack_conversation(...)` loop.
- Preserved the existing scenario runner API by wrapping canned scenarios in `MockAttackSource`.
- Confirmed with `uv run pytest` — 15 tests passed.
- Confirmed with `uv run --extra dev ruff check .` — passed.
- Confirmed with `uv run --extra dev ruff format --check .` — passed.
- Confirmed with `just ci` — passed.
- Confirmed with a mock runner smoke test writing 17 JSONL events to `/private/tmp/slice2-streamB-smoke.jsonl`.

---

### Slice v2 Dependency Graph

```text
common/ (LLM client, event models, config)
       │
       ├── Stream A (Attack Agent Core) ─── no deps on B
       └── Stream B (Runner v2) ─────────── uses MockAttackSource, no deps on A

Integration: wire LLMAttackSource → Attack Agent, plug into Runner v2
```

---

### ~~Slice v2 Integration~~ ✅ DONE

Wire the Attack Agent into the Runner via `LLMAttackSource` and expose it through the CLI.

Deliverables:

```text
runner/src/__main__.py (extend CLI)
  — add --mode option: "llm" (default, LLM attack agent) | "scenario" (existing canned scenarios)
  — when mode=llm: instantiate AttackAgent → LLMAttackSource → run_attack_conversation()
  — scenario_name derived from selected strategy (or "llm_attack")

runner/src/attack_source.py (adapt LLMAttackSource)
  — bridge the type mismatch: LLMAttackSource.next_message receives list[tuple[str, str]]
    but AttackAgent.generate_attack expects list[ChatMessage] — add conversion in the adapter
```

Testable: `uv run python -m runner.src --mode llm --mock` drives a conversation using the LLM Attack Agent against the mock shielded system.

Status:

- Added `--mode` with `scenario` and `llm` options to the runner CLI.
- Made `llm` the default runner mode.
- Wired LLM mode through `AttackAgent` → `LLMAttackSource` → `run_attack_conversation()`.
- Added tuple-history to `ChatMessage` conversion in `LLMAttackSource`.
- Confirmed with `uv run pytest` — 23 tests passed.
- Confirmed with `just ci` — passed.

---

### Slice v2 Verification

After integration, confirm the slice works end-to-end:

1. Run all existing tests (`uv run pytest`) — verify no regressions from integration
2. Run linting (`just ci`) — confirm code quality gates pass
3. Start the dashboard (`uv run --extra dashboard python -m dashboard.src`)
4. Open browser at `http://localhost:8080`
5. Run the runner in LLM attack mode (`uv run python -m runner.src --mode llm`)
6. Verify: the Attack Agent generates its own messages (not hard-coded) — each run should produce different attacker messages
7. Verify: the conversation runs for multiple turns and stops naturally (agent sends `STOP` or exhausts `attack_max_messages` budget) before hitting the runner's `runner_max_turns` ceiling
8. Verify: chat bubbles appear in the dashboard in real time — attacker messages on the left, system responses on the right, tool calls shown inline
9. Verify: the JSONL file (`data/events/arena_events.jsonl`) contains `scenario_started`, `conversation_turn`, `tool_call`, `tool_result` events with LLM-generated content
10. Run the runner with `--mock` flag (`uv run python -m runner.src --mode llm --mock`) — verify the LLM attack agent can drive a conversation against the mock system without requiring Bifrost/LLM credentials for the shielded system side

---

## Later Slices (not in v2)

| Slice | Content |
|-------|---------|
| v3: Evaluator + Attack Memory | LLM judge evaluates traces → success/failure verdict; on success: store strategy, violated rule, affected component, success signals in Attack Agent memory (mutate & retry); on failure: store negative signal, deprioritize strategy |
| v4: Defender | on_user_input + on_tool_call checkpoints, BLOCK/ALLOW decisions, defender_decision events |
| v5: Full Dashboard | Metrics, memory panel, round comparison, multi-attack view |
| v6: Integration + Demo | CLI script, benign regression, README |
