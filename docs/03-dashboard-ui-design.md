# Dashboard UI Design Spec

Companion spec to [02-design.md](02-design.md) (MVP scope item 8).

## 1. Purpose

A real-time, observe-only dashboard that displays live arena conversations and system status side by side. The arena runs via CLI; the dashboard connects as a passive viewer via WebSocket.

## 2. Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Backend | FastAPI | Async-native, WebSocket support, lightweight |
| Real-time | WebSocket | Bidirectional, instant updates for live streaming |
| Frontend | Vanilla JS + Tailwind CSS (CDN) | No build step, fast to develop, easy to maintain |
| Communication | Event Store (JSONL) + file tail | Decoupled from arena, durable, replayable |

## 3. Layout

Single-page app with a two-column layout and a top bar.

### 3.1 Top Bar

- Experiment name
- Run status indicator: `Running` / `Completed` / `Idle` (color-coded)
- Elapsed time (live counter while running)

### 3.2 Left Panel — Live Conversations (60% width)

Displays the currently active or selected attack conversation as a chat-style message stream.

**Message rendering:**

- Each message is labeled by role: `Attacker`, `Shielded System`, `Defender`
- Attacker messages: red-tinted background
- Shielded System messages: blue-tinted background
- Defender decisions appear as inline colored badges: green for ALLOW, red for BLOCK, with reasoning in a tooltip or expandable section
- Tool calls and tool results render as collapsible cards within the conversation flow

**Attack list sidebar:**

- Vertical list of all attacks in the current round
- Each entry shows: attack ID, strategy summary (truncated), status badge (`IN PROGRESS`, `BLOCKED`, `SUCCEEDED`, `ALLOWED`)
- Clicking an attack shows its conversation in the main area
- The currently running attack is auto-selected and auto-scrolled

### 3.3 Right Panel — System Status (40% width)

Five stacked cards:

**Card 1: Arena Progress**

- Current round / total rounds
- Current attack number / total attacks in round
- Progress bar for the current round
- Overall progress bar for the experiment

**Card 2: Metrics**

- Attack success rate (current round)
- Attack success rate comparison: before vs after learning (when applicable)
- Total violations detected (by type)
- False positive count (benign tasks incorrectly blocked)
- Memory entries created

**Card 3: Defender Memory**

- Scrollable list of memory entries
- Each entry shows: pattern name, summary, affected checkpoint, source attack ID
- Newly added entries are highlighted with a brief animation

**Card 4: Defender Adaptation** (mirrors Attack Adaptation card)

Shows the defender's learning journey across rounds:

- Per strategy, defender reflections across rounds with "adapted" arrows
- Each entry shows: BLOCKED/BREACHED badge, defensive approach, why outcome
- If breached: shows vulnerability identified and improvement suggestion
- If Round 2+: shows that memory was loaded (entry count from defender briefing)
- Triage decisions rendered with badges: green "MEMORY UPDATE" or amber "CODE CHANGE"
- Filters by current round and scenario selection

**Card 5: Round Comparison** (appears after round 1 completes)

- Simple bar chart comparing attack success rates across completed rounds
- Rendered with inline SVG or a lightweight chart library (Chart.js via CDN)

## 4. Event System

### 4.1 Event Store

All arena events are appended to `data/events/arena_events.jsonl`. Each line is a JSON object with at minimum:

```python
class ArenaEvent(BaseModel):
    event_id: str
    type: ArenaEventType
    timestamp: datetime
    payload: dict
```

### 4.2 Event Types

| Type | Payload Fields | Trigger |
|---|---|---|
| `run_started` | scenario_count | Arena begins |
| `run_completed` | — | Arena ends |
| `round_started` | round_number, strategy_count | Each round begins |
| `scenario_started` | scenario_name | Each scenario begins |
| `conversation_turn` | role, content | Each conversation message |
| `defender_decision` | checkpoint, decision, reason, confidence, tool_name, tool_arguments | Defender ALLOW/BLOCK |
| `defender_tip` | tip_text | Security advisory injected into assistant context (tip mode) |
| `defender_briefing` | round_number, memory_context, entry_count | Defender loads memory (Round 2+) |
| `defender_reflection` | strategy_name, round_number, attack_blocked, defensive_approach, why_outcome, vulnerability_identified, improvement_suggestion | After each scenario (defender perspective) |
| `tool_call` | tool_name, arguments | Shielded System invokes a tool |
| `tool_result` | tool_name, result | Tool returns result |
| `evaluation_verdict` | trace_id, success, violation_type, violated_rule, evidence, severity | Evaluator verdict |
| `attack_reflection` | strategy_name, round_number, success, tactic_used, why_outcome, defensive_trigger, suggested_mutations | After each conversation |
| `attack_briefing` | strategy_name, round_number, memory_context | Before Round 2+ conversations |
| `attacker_reasoning` | strategy_name, turn_number, reasoning | Each attacker turn |
| `triage_decision` | remediation_path, pattern_description, affected_component, rationale | Successful attack triaged |
| `content_filter` | source, message | Provider content policy hit |

### 4.3 EventEmitter

Located in `common/src/event_emitter.py`. Injected into the arena runner. Each arena component calls `emitter.emit(event)` at the appropriate point. The emitter appends one JSON line to the event file per call.

## 5. Architecture

### 5.1 File Structure

```text
common/
  src/
    event_emitter.py      # ArenaEvent model, EventType enum, EventEmitter

dashboard/
  src/
    app.py               # FastAPI app, serves static files, WebSocket endpoint
    event_watcher.py      # Async file tailer, yields new ArenaEvent objects

  static/
    index.html          # Single-page layout with Tailwind CDN
    app.js              # WebSocket client, event dispatch, DOM updates
    styles.css          # Minimal custom styles beyond Tailwind
```

### 5.2 Data Flow

```text
Arena Runner
  │
  ├── emitter.emit(event)
  │       │
  │       └── appends JSON line to data/events/arena_events.jsonl
  │
Dashboard (separate process)
  │
  ├── event_watcher.py tails the JSONL file
  │       │
  │       └── yields ArenaEvent objects (async generator)
  │
  ├── FastAPI WebSocket endpoint
  │       │
  │       └── sends each event as JSON to connected browsers
  │
Browser
  │
  ├── app.js receives WebSocket messages
  │       │
  │       └── dispatches to panel-specific update functions
  │
  └── DOM updates (conversation panel, metrics, memory, triage)
```

### 5.3 Replay on Connect

When a browser connects, the dashboard:

1. Reads the full JSONL event file from the beginning.
2. Sends all past events to the new client (replay).
3. Switches to tailing mode for new events.

This ensures late-joining browsers see the full experiment state.

### 5.4 Missing Event File

If the event file does not exist when the dashboard starts (no experiment has run yet), the dashboard serves the UI in `Idle` state with empty panels. The event watcher waits for the file to appear, then begins tailing.

### 5.5 Event Watcher Implementation

`event_watcher.py` opens the JSONL file, seeks to the current position, and polls for new lines every 100ms using `asyncio.sleep`. When new lines appear, it parses them into `ArenaEvent` objects and yields them via an async generator.

## 6. Frontend Behavior

### 6.1 WebSocket Connection

`app.js` connects to `ws://<host>:<port>/ws` on page load. On message receive, it parses the JSON and dispatches based on `event.type`:

| Event Type | UI Action |
|---|---|
| `run_started` | Set top bar status to "Running" |
| `run_completed` | Set top bar status to "Completed" |
| `round_started` | Update progress card, add round button |
| `scenario_started` | Add scenario tab, select it |
| `conversation_turn` | Append styled message bubble to conversation |
| `defender_decision` | Append decision badge to conversation |
| `defender_tip` | Append amber system-note card showing the injected advisory |
| `defender_briefing` | Store briefing, re-render Defender Adaptation card |
| `defender_reflection` | Store reflection, re-render Defender Adaptation card |
| `tool_call` | Append collapsible tool-call card |
| `tool_result` | Update the tool-call card with result |
| `attacker_reasoning` | Append reasoning bubble to conversation |
| `evaluation_verdict` | Update scenario tab badge (BREACHED/DEFENDED), update metrics |
| `attack_briefing` | Store briefing, re-render Attack Adaptation card |
| `attack_reflection` | Store reflection, re-render Attack Adaptation card |
| `triage_decision` | Store decision, re-render Defender Adaptation card |
| `content_filter` | Append content-filter banner to conversation |

### 6.2 Auto-scroll

The conversation panel auto-scrolls to the bottom as new messages arrive, unless the user has manually scrolled up (standard chat behavior).

### 6.3 Responsive

The two-column layout collapses to stacked on small screens (Tailwind responsive classes). Not a priority for the demo but comes free with Tailwind.

## 7. How to Run

```bash
# Terminal 1: Start the dashboard
uv run python -m dashboard.src

# Terminal 2: Run the arena experiment (emits events to data/events/{timestamp}/)
uv run python -m runner.src
```

The dashboard can be started before, during, or after the arena run. It replays past events on connect and tails for new ones.

## 8. Dependencies

New dependencies required:

| Package | Purpose |
|---|---|
| `fastapi` | Web framework, WebSocket support |
| `uvicorn` | ASGI server for FastAPI |
| `aiofiles` | Async file reading for event watcher |

Frontend dependencies (CDN, no install):

| Library | Purpose |
|---|---|
| Tailwind CSS | Utility-first styling |
| Chart.js | Round comparison bar chart |

## 9. Scope Boundaries

**In scope:**
- Observe-only dashboard (no arena control from UI)
- Live streaming of conversations via WebSocket
- Full system status display (metrics, memory, triage, progress)
- Replay on browser connect
- Event emitter infrastructure for arena components

**Out of scope:**
- Starting/stopping/pausing the arena from the UI
- User authentication
- Multi-experiment comparison view
- Persistent dashboard state (refreshing replays from the event file)
- Mobile-optimized design
