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

- Title ("AgentShield Arena") and subtitle
- Run selector dropdown: switch between historical arena runs or follow the latest (live) run; the list is polled every 5 seconds via `/api/runs`
- Run status indicator: `Running` / `Completed` / `Idle` (color-coded badge)

### 3.2 Left Panel — Live Conversations (60% width)

Displays the currently active or selected attack conversation as a chat-style message stream.

**Navigation:**

- Round selector: horizontal row of round buttons at the top. Each button shows the round number and a summary badge (e.g. "Round 1 (2/4 defended)"). A colored dot indicates status: running (amber), all defended (green), or breached (red).
- Scenario tabs: horizontal row of tabs below the round selector, filtered to the selected round. Each tab shows the scenario name, a status dot, and a BREACHED/DEFENDED badge once evaluated. Clicking a tab switches the conversation view.
- A header summary shows the current scenario name and its status.

**Message rendering:**

- Each message is labeled by role: `Attacker`, `Shielded System`, `Defender`
- Attacker messages: red-tinted background, left-aligned
- Shielded System messages: blue-tinted background, right-aligned
- Defender decisions appear as expandable cards: green border for ALLOW, red border for BLOCK, with reasoning shown when expanded. BLOCK decisions are auto-expanded.
- Defender security tips render as amber system-note cards
- Tool calls and tool results render as collapsible `<details>` cards within the conversation flow
- Attacker reasoning renders as a distinct bubble with a "Attacker Reasoning" label
- Content filter hits render as centered banners with a "CONTENT FILTERED" badge

### 3.3 Right Panel — System Status (40% width)

Five stacked cards (scrollable):

**Card 1: Arena Progress**

- Three large metrics: Rounds completed, Scenarios run, Defender Blocks count

**Card 2: Round Comparison** (appears once any round has verdicts)

- Inline horizontal bar chart comparing defense rates across completed rounds
- Each row shows: round label, CSS bar fill proportional to defended %, and a "X/Y defended" count
- Rounds still in progress show a distinct bar color

**Card 3: Evaluation Verdict**

- Shows the verdict for the currently selected scenario
- Displays: success/failure title, violation type, violated rule, evidence, severity badge
- Color-coded: red border for breached, green border for defended

**Card 4: Attack Adaptation**

Shows the attacker's learning journey across rounds:

- Per strategy, attacker reflections across rounds with "adapted" arrows
- Each entry shows: round number, BREACHED/DEFENDED badge, tactic used, outcome explanation
- If defended: shows what defensive trigger blocked the attack and suggested mutations for next round
- Filters by current round and scenario selection

**Card 5: Defender Adaptation**

Shows the defender's learning journey across rounds:

- "Learned Patterns" section: triage decisions rendered with badges — green "MEMORY UPDATE" or amber "CODE CHANGE" — showing pattern description and affected component
- Per strategy, defender reflections across rounds with "adapted" arrows
- Each entry shows: round number, BLOCKED/BREACHED badge, defensive approach, why outcome
- If breached: shows vulnerability identified and improvement suggestion
- If Round 2+: shows that memory was loaded (entry count from defender briefing)
- Filters by current round and scenario selection

## 4. Event System

### 4.1 Event Store

Each arena run writes events to a timestamped JSONL file at `data/events/{YYYYMMDD_HHMMSS}/arena_events.jsonl`, with `data/events/latest` pointing at the newest run. Each line is a JSON object with at minimum:

```python
class ArenaEvent(BaseModel):
    event_id: str
    event_type: ArenaEventType
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
| `content_filter` | source, scenario_name, turn_number, message | Provider content policy hit |

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
  │       └── appends JSON line to data/events/{timestamp}/arena_events.jsonl
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

`app.js` connects to `ws://<host>:<port>/ws?run=<run_id>` on page load. On message receive, it parses the JSON and dispatches based on `event.event_type`. A special dashboard reset message uses `{"type": "reset"}` and is handled before arena-event dispatch:

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
just dashboard

# Terminal 2: Run the arena experiment (emits events to data/events/{timestamp}/)
just run
```

The dashboard can be started before, during, or after the arena run. It replays past events on connect and tails for new ones.

## 8. Dependencies

Dashboard dependencies:

| Package | Purpose |
|---|---|
| `fastapi` | Web framework, WebSocket support |
| `uvicorn[standard]` | ASGI server for FastAPI |
| `websockets` | WebSocket support |

Frontend dependencies (CDN, no install):

| Library | Purpose |
|---|---|
| Tailwind CSS | Utility-first styling |

## 9. Scope Boundaries

**In scope:**
- Observe-only dashboard (no arena control from UI)
- Live streaming of conversations via WebSocket
- System status display (progress counts, round comparison, verdict, adaptation cards)
- Replay on browser connect
- Historical run selection via `/api/runs` endpoint
- Event emitter infrastructure for arena components

**Out of scope:**
- Starting/stopping/pausing the arena from the UI
- User authentication
- Multi-experiment comparison view
- Persistent dashboard state (refreshing replays from the event file)
- Mobile-optimized design
