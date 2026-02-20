---
name: summarize-inbox
description: Aggregate and summarize unread messages across email and Slack channels. Use when the user wants a communication overview or the system needs to triage incoming messages.
version: 1.0.0
agent: communication-agent
type: analysis
inputs:
  - channels: List of channels to summarize (email, slack, or all)
  - time_range: Time period to cover (today, this_week, custom)
  - priority_filter: Minimum priority to include (all, high, critical)
outputs:
  - summary: Structured summary grouped by priority and category
  - action_items: Extracted action items with deadlines
  - routing_suggestions: Messages recommended for routing to other agents
reusability: extremely-high
framework_agnostic: true
---

# Skill: summarize-inbox

## 1. Purpose

Provide a clear, prioritized summary of all unread communications across channels. Helps the user quickly understand what needs attention without reading every message.

## 2. When to Use This Skill

**Mandatory invocation:**
- User requests "check my messages", "inbox summary", "what's new"
- Scheduled daily summary generation
- Communication Agent needs to triage incoming messages

## 3. Workflow

1. **Fetch**: Pull unread messages from configured channels via MCP servers
2. **Classify**: Categorize by sender type (client, vendor, internal, personal)
3. **Prioritize**: Score urgency (critical, high, medium, low)
4. **Extract**: Pull out action items, deadlines, questions
5. **Route**: Identify messages that should go to other agents (finance, social)
6. **Summarize**: Generate structured summary organized by priority

## 4. Summary Format

```markdown
## Inbox Summary — [Date]

### Critical (requires immediate attention)
- [Sender]: [Subject] — [Action needed] — [Deadline]

### High Priority
- [Sender]: [Subject] — [Brief summary]

### Normal
- [N] messages from [categories] — [themes]

### Action Items
- [ ] [Action] — from [sender] — due [date]

### Routing Suggestions
- [Message] → Finance Agent (contains invoice)
- [Message] → Calendar (meeting request)
```

## 5. HITL Gate

**Risk Level**: LOW (read-only operation)
**Approval Required**: NO — auto-approved

## 6. Constraints

- Read-only — never modify, delete, or mark messages as read
- Never include full message bodies in summary (privacy)
- Include sender and subject only — user clicks through for details
