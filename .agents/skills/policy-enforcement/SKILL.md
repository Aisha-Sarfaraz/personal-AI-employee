---
name: policy-enforcement
description: Runtime policy gate checks that validate actions against defined rules before execution. Use when any agent needs to verify an action is permitted by current policies before proceeding.
version: 1.0.0
agent: monitoring-agent
type: validation
inputs:
  - action: The action to validate
  - agent: The agent requesting the action
  - context: Additional context (amounts, targets, risk indicators)
outputs:
  - decision: ALLOW, DENY, or REQUIRE_APPROVAL
  - reason: Why the decision was made
  - policy_rule: Which policy rule triggered the decision
  - approval_level: Required approval level if REQUIRE_APPROVAL
reusability: extremely-high
framework_agnostic: true
---

# Skill: policy-enforcement

## 1. Purpose

Provide a runtime policy enforcement gate that validates every action against defined policy rules before execution. This is the zero-trust action gating mechanism that ensures no action bypasses safety policies.

## 2. When to Use This Skill

**Mandatory invocation:**
- Before ANY action that modifies external state (send, create, delete, post)
- Before financial transactions of any amount
- Before outbound communications
- When action risk level is uncertain

## 3. Policy Rule Engine

### Action Classification

| Action Category | Default Decision | Override Conditions |
|----------------|-----------------|---------------------|
| Read internal data | ALLOW | None |
| Write internal data | ALLOW | None |
| Read external data | ALLOW | Rate limits |
| Draft content | ALLOW | None |
| Send communication | REQUIRE_APPROVAL | Always |
| Financial transaction | REQUIRE_APPROVAL | Always |
| Publish content | REQUIRE_APPROVAL | Always |
| Delete data | REQUIRE_APPROVAL | Always |
| Modify permissions | DENY | Only with explicit override |
| Bulk operations | DENY | Only with explicit override |

### Financial Thresholds

| Amount Range | Decision |
|-------------|----------|
| $0 - $100 | REQUIRE_APPROVAL (notify) |
| $100 - $1,000 | REQUIRE_APPROVAL (explicit) |
| $1,000 - $10,000 | REQUIRE_APPROVAL (explicit + confirmation) |
| > $10,000 | DENY (requires manual override) |

## 4. Workflow

1. **Receive**: Accept action request with context
2. **Classify**: Determine action category and risk level
3. **Evaluate**: Apply policy rules in priority order
4. **Decide**: ALLOW, DENY, or REQUIRE_APPROVAL
5. **Log**: Record policy decision with reasoning
6. **Return**: Decision with explanation and required approval level

## 5. HITL Gate

This skill IS the HITL gate — it determines what goes to HITL.

## 6. Constraints

- Every policy decision MUST be logged (no silent allows/denies)
- DENY decisions include clear explanation for the user
- Policy rules are loaded from `policies.yaml` (not hardcoded)
- Safety thresholds (bulk operations, permission changes) cannot be overridden by policy file
- Idempotent — same action + context always produces same decision
