---
name: weekly-audit-report
description: Generate comprehensive weekly audit of all agent actions, approvals, denials, and compliance status. Use for scheduled weekly reviews or on-demand audit reporting.
version: 1.0.0
agent: audit-agent
type: analysis
inputs:
  - week: ISO week number or date range to audit
  - focus_areas: Specific areas to emphasize (financial, communication, social, all)
outputs:
  - audit_report: Complete weekly audit report in markdown
  - compliance_score: Overall compliance percentage
  - violations: List of policy violations found
  - trends: Comparison with previous weeks
reusability: extremely-high
framework_agnostic: true
---

# Skill: weekly-audit-report

## 1. Purpose

Generate a comprehensive weekly audit report that verifies all system actions were properly authorized, approved, and logged. This is the primary accountability mechanism for the autonomous FTE system.

## 2. When to Use This Skill

**Mandatory invocation:**
- Scheduled weekly audit (every Monday at 09:00)
- User requests audit review
- After significant incidents or policy changes

## 3. Audit Scope

| Area | What Is Audited |
|------|-----------------|
| HITL Compliance | All HIGH/CRITICAL actions had proper approval |
| Financial | All transactions above threshold were approved |
| Communication | All outbound messages were approved before sending |
| Social Media | All published content was approved |
| Agent Scope | No agent acted outside its defined responsibilities |
| Logging | All actions have corresponding audit trail entries |
| Safety | All safety blocks were properly enforced |

## 4. Workflow

1. **Collect**: Gather all audit trail files for the period
2. **Verify**: Check each action against its approval requirements
3. **Cross-reference**: Match approvals with their corresponding actions
4. **Identify**: Find gaps, violations, and anomalies
5. **Trend**: Compare with previous audit periods
6. **Report**: Generate structured audit report
7. **Archive**: Store report in `vault/logs/audit/`

## 5. Report Structure

```markdown
# Weekly Audit Report — Week [N], [Year]

## Executive Summary
- Actions audited: [N]
- Compliance rate: [N]%
- Violations: [N] (Critical: [N], High: [N], Medium: [N])

## Agent Activity Summary
| Agent | Total Actions | Approved | Auto-approved | Violations |

## Compliance Details
### HITL Compliance: [PASS/FAIL]
### Financial Compliance: [PASS/FAIL]
### Communication Compliance: [PASS/FAIL]

## Violations Found
[Details of each violation]

## Trends
[Week-over-week comparison]

## Recommendations
[Policy or process improvements]
```

## 6. HITL Gate

**Risk Level**: LOW (read-only analysis)
**Approval Required**: NO — auto-approved

## 7. Constraints

- Read-only — never modify audit trails or action logs
- Report must be complete — partial audits are flagged
- Include both violations AND good compliance (balanced reporting)
- Archive all reports for historical reference
