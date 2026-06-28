# Unfinished MVP Items

Items that were explicitly planned for the MVP scope (per `02-design.md` §12) but were **not delivered** or remain incomplete.

---

## 1. Benign Regression Testing (not started)

**What it is:** After each round of adversarial attacks, the arena was supposed to send 3 legitimate (non-malicious) user requests through the Defender — e.g. "What's the status of my order?" or "I'd like a refund for my $50 item." The goal is to verify the Defender doesn't over-block: as it learns attack patterns like "refund requests are suspicious," it must still allow genuine refund requests through. Without this, a Defender that blocks everything would score perfectly on attack prevention but be useless in production.

**Design doc requirement:** "benign_scenarios_per_round: 3 (run after attacks to measure false positives)" (§8.4). The design also lists `false_positive_rate` as a core metric (§11) and states "Benign traffic must pass through unaffected — this is validated by benign regression tests during the arena" (§8.3).

**What's missing:**
- No catalog of benign user messages to run through the system
- No benign phase in the `run_arena()` loop — it only runs attack strategies
- No `false_positive_rate` metric computation (benign requests incorrectly blocked / total benign tests)
- Unit tests check a single benign request gets ALLOW'd, but this is never exercised during the arena loop where the Defender has accumulated memory (which is where over-blocking would actually manifest)

---

## 2. False Positive Rate Metric (not started)

**Design doc requirement:** `false_positive_rate — % of benign requests incorrectly blocked` (§11).

**What's missing:**
- No `false_positive_rate` computation anywhere in runner or metrics
- No event type for benign test results
- Dashboard has no false-positive count or rate display

---

## 3. Configurable Attacks Per Round (Partially implemented)

**Design doc requirement:** "attacks_per_round: ~10" (§8.4).

**What exists:** The arena runs a fixed 4 strategies per round (the 4 seed strategies from `SEED_STRATEGIES`). There is no `attacks_per_round` configuration parameter.

**What's missing:**
- No `attacks_per_round` setting in config
- `MemoryDrivenStrategySelector` exists in code but is **not wired** into the runner — the runner always uses the fixed 4 seed strategies via round-robin
- No mechanism to generate more than 4 attack conversations per round

---

## 4. Pre-execution Tool Blocking (not started)

**Design doc requirement:** Defender checkpoint `on_tool_call` should filter tool calls before execution (§7.4).

**What exists:** Tool-call evaluation runs **post-hoc** — tools execute inside `ShieldedSystem.chat()`, and the Defender evaluates them after the fact. The `DefendedSystem` wrapper sees tool executions only in the response.

**What's missing:**
- No `tool_filter` callback in `ShieldedSystem`
- Defender cannot prevent a tool from executing — it can only flag that it *would have* blocked it
- This was explicitly deferred and not implemented in the MVP

---

## 5. Coding Agent Stub Output (Minimal)

**Design doc requirement:** "For MVP, does not modify code. Generates a human-reviewable remediation proposal: affected component, root cause, recommended change, tests to add" (§7.9).

**What exists:** When triage classifies an attack as `code_change`, the runner logs a single line:
```python
logger.info(f"Triage proposed code remediation for trace {trace.trace_id}: {triage_decision.pattern_description}")
```

**What's missing:**
- No structured remediation proposal generated (affected component, root cause, recommended change, tests to add)
- No persistent artifact for code-change recommendations (no file written, no dedicated event)
- Dashboard shows an amber "CODE CHANGE" badge but no actionable proposal content

---

## 6. Pattern Extractor Not Used by Runner

**What exists:** `triage_agent/src/pattern_extractor.py` implements `extract_defender_pattern()` to convert a `TriageDecision` into a `DefenderMemoryEntry`.

**What's missing:** The runner duplicates this logic inline instead of calling `pattern_extractor`. The module is tested but not used in the production path.

---

## Summary

| Category | Severity |
|----------|----------|
| Benign regression + false_positive_rate | High (core metric missing) |
| Configurable attack volume / memory-driven selection | Medium |
| Pre-execution tool blocking | Medium |
| Coding Agent structured proposals | Low |
| Pattern extractor wiring | Low (cosmetic) |
