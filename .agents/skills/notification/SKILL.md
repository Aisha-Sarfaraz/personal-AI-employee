---
name: notification
description: Alert the human operator across available channels when system events require attention. Use for urgent alerts, approval requests, and status notifications.
version: 1.0.0
type: system
inputs:
  - message: Notification content
  - severity: Notification severity (info, warning, error, critical)
  - source_agent: Agent that triggered the notification
  - action_required: Whether human action is needed
  - channel_preference: Preferred notification channel (auto, slack, email, console)
outputs:
  - delivered: Whether notification was successfully delivered
  - channel_used: Which channel was used
  - acknowledged: Whether human acknowledged (if tracking available)
reusability: extremely-high
framework_agnostic: true
---

# Skill: notification

## 1. Purpose

Deliver timely notifications to the human operator through the most appropriate channel. Ensures the human is always aware of important system events, approval requests, and issues requiring attention.

## 2. When to Use This Skill

**Mandatory invocation:**
- HITL approval is requested (action awaiting human decision)
- Monitoring Agent detects CRITICAL or ERROR condition
- Audit Agent finds compliance violation
- Agent encounters unrecoverable error
- Scheduled notifications (daily summary, weekly audit)

## 3. Channel Selection

| Severity | Default Channel | Fallback Channel |
|----------|----------------|-----------------|
| INFO | Console log | Filesystem (vault/notifications/) |
| WARNING | Console log | Slack (if configured) |
| ERROR | Slack | Email |
| CRITICAL | Slack + Email | Console + Filesystem |

## 4. Notification Format

```markdown
## [SEVERITY] Notification from [Agent]

**Time:** [timestamp]
**Source:** [agent_name]
**Category:** [approval_request | alert | status | error]

**Message:**
[notification content]

**Action Required:** [YES/NO]
[If YES: description of what the human needs to do]

**Context:**
[Additional context to help human decide/act]
```

## 5. Workflow

1. **Receive**: Accept notification request with severity and content
2. **Channel Select**: Determine best channel based on severity and availability
3. **Format**: Structure notification in channel-appropriate format
4. **Deliver**: Send via selected channel (MCP server)
5. **Fallback**: If primary channel fails, try fallback
6. **Log**: Record notification delivery status
7. **Track**: Monitor for acknowledgment (if available)

## 6. Constraints

- CRITICAL notifications must attempt ALL available channels
- Never suppress notifications — always deliver or log failure
- Rate limit: max 10 notifications per minute per channel (prevent spam)
- Batch low-severity notifications (INFO) into periodic digests
- All notification deliveries are logged for audit trail
- Never include credentials or secrets in notification content
