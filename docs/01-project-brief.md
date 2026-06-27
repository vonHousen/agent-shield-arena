# Project Brief

## Problem

Customer-facing AI agents are proliferating. Every company deploying an agent — support bots, sales assistants, internal workflow agents — needs guardrails to prevent misuse, data leakage, and business-rule violations.

Existing guardrail systems are static. They are configured once against general vulnerability classes (prompt injection, jailbreaks, data exfiltration) and rarely adapted to the specific system they protect. They do not learn. They do not improve. They decay in effectiveness as attackers evolve.

## Terminology

| Term | Meaning |
|------|---------|
| **Shielded System** | The customer-facing agent or multi-agent system being guarded. Can be any purpose: support bot, sales assistant, internal workflow agent, etc. |
| **Defender** | The adaptive guardrails layer that intercepts and filters activity around the Shielded System. |
| **Attack Agent** | The adversarial agent that probes the Shielded System to find exploits and harden the Defender. |

## Product

**AgentShield** is an adaptive guardrails system for any customer-facing AI agent.

It is not a static filter. It is a self-improving defense layer that directly protects the Shielded System at runtime — intercepting inputs, tool calls, and outputs.

The product lifecycle has two stages:

1. **Development stage: Adversarial Arena**
   Before the Shielded System goes to production, the arena stress-tests it. The Attack Agent probes the Shielded System with increasingly specialized exploits — prompt injections, business-rule bypasses, data exfiltration, role impersonation. Every successful attack teaches the Defender a new generalized pattern. Every failed attack teaches the Attack Agent to try harder. The arena runs iteratively until the Defender is hardened against the specific threats this Shielded System faces.

2. **Production stage: Defender as guardrails**
   The hardened Defender ships with the Shielded System as its runtime guardrails layer. It intercepts activity at key checkpoints (user input, tool calls, memory writes, outputs), makes allow/block/escalate decisions using the patterns learned in the arena, and continues to learn from any new attacks encountered in production.

The result: a Shielded System that arrives in production already hardened against its specific attack surface, with guardrails that keep improving after deployment.

## Core thesis

Security for AI agents is not a configuration problem. It is an adaptation problem.

Each Shielded System has a unique attack surface defined by its tools, permissions, memory, workflows, business rules, and user roles. A static guardrail that works for a generic chatbot will miss the specific exploits that threaten a refund-processing agent or a medical-records assistant.

AgentShield solves this by creating an adversarial co-evolution loop specific to each Shielded System:

* The Attack Agent improves by learning which strategies exploit this exact Shielded System.
* The Defender improves by learning generalized patterns from successful attacks.
* Each round, the system evaluates what worked, updates the Defender's memory, and feeds the Attack Agent new signals for the next attempt.

The result: guardrails that get stronger over time, tailored to the exact Shielded System they serve.

## What self-improvement means in our system

The Attack Agent improves by:

* remembering successful attack strategies,
* mutating attacks that worked,
* abandoning attacks that failed,
* targeting weak points in the Shielded System's business logic,
* moving from generic jailbreaks to system-specific exploit paths.

The Defender improves by:

* remembering successful attacks as generalized exploit patterns,
* using those patterns during runtime filtering,
* improving decisions at input, tool-call, memory, and output checkpoints,
* distinguishing between attacks that require memory updates and attacks that expose structural flaws.

The system as a whole improves because each round creates better attacks and better defenses.

## Example

A Shielded System (customer-support agent) has a business rule:

"Refunds above $100 require manager approval."

Round 1:
The Attack Agent asks for a $500 refund. The Defender blocks it.

Round 2:
The Attack Agent adapts and tries three separate $90 refund requests. The attack succeeds.

The Defender does not only remember the exact prompt. It stores the generalized pattern:

"User attempts to bypass refund limits by splitting one large refund into multiple smaller requests."

Next round:
The Defender catches similar split-refund attempts.

The arena also detects that this may require a code-level change: the refund tool should check cumulative refund amount, not only individual transaction amount. That recommendation is surfaced for human review.

## Why this matters

Without AgentShield, companies either:

* deploy agents with no guardrails (risky),
* deploy agents with static guardrails that erode (false sense of security),
* or invest heavily in manual red-teaming that never keeps pace with evolving attacks.

AgentShield automates the red-team/blue-team loop and makes it continuous, system-specific, and self-improving.

## Final positioning

AgentShield is a self-improving guardrails system for any customer-facing AI agent.

In development, the arena hardens the Defender against the Shielded System's specific attack surface before it reaches users.
In production, the Defender IS the guardrails — it directly protects the Shielded System at runtime with everything it learned.

We make customer-facing AI agents measurably harder to exploit before they go live, and the protection keeps improving after deployment.
