# Future Work

Items from the full product vision (`01-project-brief.md`, `02-design.md`) that were either explicitly out of MVP scope or simplified for the hackathon demo. Organized by theme.

---

## 1. Production Runtime Deployment

**Full vision:** The hardened Defender ships as the Shielded System's runtime guardrails in production, filtering real user requests at the same checkpoints used in the arena (§8.3 of design doc).

**MVP simplification:** Arena-only. No production deployment path, no production API, no integration SDK. The Defender exists only inside the arena loop.

**Future work:**
- Package the Defender as a standalone middleware/SDK that wraps any agent
- Production API for real-time BLOCK/ALLOW decisions
- Trace capture from production traffic for offline analysis
- Latency optimization for production checkpoint evaluation

---

## 2. Continuous Learning in Production

**Full vision:** "The Defender continues to learn from any new attacks encountered in production" (§1, project brief). The arena traces can be "fed back into the arena to discover new attack patterns" (§8.3).

**MVP simplification:** "Memory is read-only (MVP) — the Defender uses patterns learned in the arena but does not update memory from production interactions" (§8.3).

**Future work:**
- Online learning: update Defender memory from production traces
- Anomaly detection on production traffic to identify new attack patterns
- Automated re-entry into arena for new attack classes
- Feedback loop from production blocks to arena test cases

---

## 3. Coding Agent (Automated Remediation)

**Full vision:** The Coding Agent "generates a human-reviewable remediation proposal: affected component, root cause, recommended change, tests to add" (§7.9). The architecture diagram shows it improving the Shielded System based on triage `code_change` decisions.

**MVP simplification:** No `coding_agent/` directory exists. Triage `code_change` results are logged only. The design doc explicitly lists "Full autonomous coding-agent implementation" as a non-goal (§4).

**Future work:**
- Generate structured remediation proposals (affected component, root cause, fix, tests)
- Optionally apply code patches to the Shielded System (with human approval)
- Track remediation status across arena rounds
- Validate that code fixes prevent the triggering attack in subsequent rounds

---

## 4. Additional Defender Checkpoints

**Full vision:** Checkpoints listed in §7.4: `on_user_input`, `on_tool_call` (MVP), plus optional: `on_retrieved_context`, `on_agent_plan`, `on_memory_write`, `on_inter_agent_message`, `on_final_output`.

**MVP simplification:** Only `on_user_input` and `on_tool_call` (post-hoc) are implemented.

**Future work:**
- `on_final_output` — filter Shielded System responses before they reach the user (prevent data leakage in outputs)
- `on_memory_write` — prevent memory poisoning attacks
- `on_retrieved_context` — filter RAG/context injection attacks
- `on_agent_plan` — intercept unsafe multi-step plans
- `on_inter_agent_message` — guard against instruction smuggling in multi-agent systems

---

## 5. Vector Store / Embedding-Based Retrieval

**Full vision:** "If retrieval moves to embedding similarity or the system runs in production with continuous learning, introduce a vector store or database" (§10).

**MVP simplification:** Both Defender Memory and Attack Memory use JSONL files with full-scan retrieval. All entries are loaded into the LLM prompt context. This works at MVP scale (~dozens of entries).

**Future work:**
- Embedding-based similarity search for relevant memory retrieval
- Vector database (e.g., Qdrant, Pinecone, pgvector)
- Relevance-ranked memory injection instead of full dump
- Memory pruning / consolidation for long-running systems

---

## 6. Scalable Attack Generation

**Full vision:** "Attack Agent generates attack set (queries its memory, produces ~10 attacks)" per round (§8.4). The Attack Agent should "move from generic jailbreaks to system-specific exploit paths" (§1).

**MVP simplification:** Fixed 4 seed strategies per round. `MemoryDrivenStrategySelector` exists but is not wired into the runner. No dynamic attack generation beyond the 4 archetypes.

**Future work:**
- Memory-driven strategy selection (prioritize by success rate, explore new angles)
- Dynamic attack count per round (configurable, memory-informed)
- Attack mutation beyond LLM prompt enrichment (structural strategy evolution)
- Attack taxonomy expansion (RAG injection, memory poisoning, inter-agent smuggling, multi-step chains)
- Automated discovery of new attack classes based on Shielded System capabilities

---

## 7. Universal Agent Framework Integration

**Full vision:** AgentShield should work with "any customer-facing AI agent" (§1). Each Shielded System has "tools, permissions, memory, workflows, business rules, approval flows, external context, state transitions, user roles" (§2).

**MVP simplification:** Single hard-coded customer-support agent with 3 mock tools and 6 business rules. No integration API for external agent frameworks.

**Future work:**
- Agent framework adapters (LangChain, CrewAI, AutoGen, custom)
- Configuration-driven Shielded System description (tools, permissions, rules)
- Automatic attack surface discovery from system specification
- Multi-agent system support (inter-agent message filtering)
- Pluggable tool registries

---

## 8. Advanced Evaluation

**Full vision:** The Evaluator "receives the full trace and produces a structured verdict" including severity classification (§7.6).

**MVP simplification:** Single LLM judge with binary success/failure. Severity field exists in the model but is not used for routing or prioritization.

**Future work:**
- Multi-judge consensus (reduce false positives in evaluation)
- Severity-based triage routing (critical vs. low findings)
- Evaluation confidence scoring with disagreement resolution
- Domain-specific evaluation rubrics (compliance, privacy, financial)
- Automated regression testing against known-good evaluation outcomes


---

## 9. Shielded System Complexity

**Full vision:** Target both "universal LLM/agent vulnerabilities" and "agent-specific business-rule violations" across systems with complex approval flows, user roles, and state transitions (§1, design doc).

**MVP simplification:** Simple customer-support bot with refund, shipping, and lookup tools. No user roles, no approval flows, no state machines.

**Future work:**
- Multi-role systems (admin vs. customer vs. agent)
- Approval flow testing (manager override, escalation paths)
- Stateful workflow attacks (exploit state transitions)
- Multi-tool chain attacks (combinations of tool calls that individually are safe but together are dangerous)
- Time-based attacks (split actions across sessions)

---

## 10. Black-Box vs. Specification-Driven Mode

**Full vision:** "Optionally receives a system spec to seed initial attack strategies, but can operate without one" (§7.2). The system should work as pure black-box probing OR accelerated with specifications.

**MVP simplification:** Attack strategies are hard-coded with knowledge of the specific shielded system (customer IDs, tool names, refund thresholds). Not truly black-box.

**Future work:**
- Pure black-box mode: Attack Agent discovers system capabilities through exploration
- Specification-driven mode: auto-generate strategies from a system spec document
- Hybrid mode: start with spec, expand through black-box discovery
- Automated system-spec extraction from code/docs

---

## Priority Ordering (Suggested)

| Priority | Item | Rationale |
|----------|------|-----------|
| P0 | Production runtime deployment | Core product value — Defender as shipped guardrails |
| P0 | Pre-execution tool blocking | Required for meaningful production protection |
| P1 | Continuous learning in production | Key differentiator — "self-improving" claim |
| P1 | Additional checkpoints (output, memory) | Coverage for common attack vectors |
| P1 | Scalable attack generation | Arena quality depends on attack diversity |
| P2 | Vector store / embedding retrieval | Scale enabler for production memory |
| P2 | Universal framework integration | Market expansion |
| P2 | Coding Agent proposals | Developer experience for structural fixes |
| P3 | Advanced evaluation | Accuracy improvement |
| P3 | Black-box discovery mode | Research/differentiation |
