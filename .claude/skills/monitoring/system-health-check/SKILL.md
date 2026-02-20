---
name: system-health-check
description: Comprehensive health assessment of all system components including agents, watchers, MCP servers, and approval queues. Use for routine health checks or when diagnosing system issues.
version: 1.0.0
agent: monitoring-agent
type: analysis
inputs:
  - components: Components to check (all, agents, watchers, mcp, hitl)
  - verbose: Include detailed diagnostics (default false)
outputs:
  - health_report: Structured health status of all components
  - alerts: List of components in degraded or failed state
  - recommendations: Suggested actions for unhealthy components
reusability: extremely-high
framework_agnostic: true
---

# Skill: system-health-check

## 1. Purpose

Perform a comprehensive health assessment of all system components. Generates a structured health report that identifies degraded or failed components and suggests remediation actions.

## 2. When to Use This Skill

**Mandatory invocation:**
- Scheduled health check interval (default: every 5 minutes)
- User requests "system status" or "health check"
- After any component failure or restart
- Before executing critical operations

## 3. Health Check Matrix

| Component | Check Method | Healthy Indicator |
|-----------|-------------|-------------------|
| Watchers | Last event timestamp | Event within expected interval |
| Agents | Last execution log | No errors in last 10 executions |
| MCP Servers | Connection test | Responds within 5 seconds |
| HITL Queue | Pending count | < 10 pending items |
| Event Bus | Last processed event | Processing within 30 seconds |
| Disk | Available space | > 10% free |
| Logs | File size | < configured max size |

## 4. Workflow

1. **Enumerate**: List all registered components
2. **Check**: Run health check for each component
3. **Score**: Assign health status (healthy, degraded, failed, unknown)
4. **Aggregate**: Compute overall system health score
5. **Alert**: Generate alerts for non-healthy components
6. **Report**: Write health report to `vault/state/health.yaml`
7. **Notify**: If CRITICAL issues found, alert human immediately

## 5. Health Report Format

```yaml
timestamp: "2026-02-16T10:00:00Z"
overall_status: healthy | degraded | critical
components:
  watchers:
    email: { status: healthy, last_event: "2026-02-16T09:55:00Z" }
    file: { status: healthy, last_event: "2026-02-16T09:59:00Z" }
  agents:
    communication: { status: healthy, last_execution: "2026-02-16T09:50:00Z", error_rate: 0.0 }
    finance: { status: healthy, last_execution: "2026-02-16T09:45:00Z", error_rate: 0.0 }
  mcp_servers:
    filesystem: { status: healthy, response_ms: 12 }
    odoo: { status: degraded, response_ms: 4500, note: "slow response" }
  hitl:
    pending_count: 3
    oldest_pending: "2026-02-16T08:00:00Z"
alerts:
  - level: WARN
    component: odoo-mcp
    message: "Response time 4500ms exceeds 3000ms threshold"
```

## 6. HITL Gate

**Risk Level**: LOW (read-only monitoring)
**Approval Required**: NO — auto-approved

## 7. Constraints

- Read-only — never modify components, only observe
- Alert immediately on CRITICAL issues (do not batch)
- Health report must be idempotent (same state produces same report)
- Never expose credentials or secrets in health reports
