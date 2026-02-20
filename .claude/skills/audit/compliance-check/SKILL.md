---
name: compliance-check
description: Verify specific actions or time periods against policy rules and approval requirements. Use for targeted compliance investigation or spot checks.
version: 1.0.0
agent: audit-agent
type: analysis
inputs:
  - target: What to check (agent_name, action_type, date_range, or specific_action_id)
  - policy_rules: Specific policies to check against (or all)
outputs:
  - compliance_result: PASS or FAIL with details
  - violations: List of specific violations found
  - evidence: Supporting evidence for each finding
reusability: extremely-high
framework_agnostic: true
---

# Skill: compliance-check

## 1. Purpose

Perform targeted compliance verification on specific actions, agents, or time periods. Used for spot checks, investigation of suspected violations, and post-incident analysis.

## 2. When to Use This Skill

**Mandatory invocation:**
- User suspects a policy violation
- Monitoring Agent flags unusual agent behavior
- Post-incident investigation
- Before granting increased agent autonomy

## 3. Compliance Rules Checked

| Rule | Description | Severity if Violated |
|------|-------------|---------------------|
| HITL-001 | HIGH/CRITICAL actions require explicit approval | CRITICAL |
| HITL-002 | Approval must precede action execution | HIGH |
| SCOPE-001 | Agent acted within defined responsibilities | HIGH |
| FIN-001 | Transactions above threshold have approval | CRITICAL |
| FIN-002 | No duplicate transactions | HIGH |
| COMM-001 | Outbound messages have approval | HIGH |
| SOCIAL-001 | Published content has approval | HIGH |
| LOG-001 | Action has audit trail entry | MEDIUM |
| SAFETY-001 | Safety blocks were enforced | CRITICAL |

## 4. Workflow

1. **Scope**: Determine what to check (agent, action, period)
2. **Gather**: Collect relevant audit trail entries
3. **Check**: Apply each applicable policy rule
4. **Evidence**: Document supporting evidence for each finding
5. **Verdict**: PASS (no violations) or FAIL (violations found)
6. **Report**: Present findings with evidence and severity

## 5. HITL Gate

**Risk Level**: LOW (read-only investigation)
**Approval Required**: NO — auto-approved

## 6. Constraints

- Read-only investigation — never modify any records
- Include evidence for every finding (not just assertions)
- Distinguish between confirmed violations and suspicious patterns
- Log all compliance checks for meta-audit purposes
