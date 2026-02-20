---
name: route-message
description: Classify incoming messages by intent and route to the appropriate agent or human handler. Use when messages contain financial, scheduling, or cross-domain content.
version: 1.0.0
agent: communication-agent
type: routing
inputs:
  - message: The message content to classify and route
  - sender: Sender information
  - channel: Source channel (email, slack)
outputs:
  - classification: Message intent classification
  - target_agent: Agent to route to (or human)
  - extracted_context: Relevant data extracted for the target agent
  - confidence: Classification confidence score
reusability: extremely-high
framework_agnostic: true
---

# Skill: route-message

## 1. Purpose

Intelligently classify incoming messages by intent and route them to the appropriate agent with extracted context. This is the communication triage system.

## 2. When to Use This Skill

**Mandatory invocation:**
- Communication Agent detects a message with cross-domain content
- Message contains financial data (invoices, amounts, payment requests)
- Message contains scheduling requests (meetings, deadlines)
- Message intent is unclear and needs classification

## 3. Routing Rules

| Intent | Target Agent | Extracted Context |
|--------|-------------|-------------------|
| Invoice / payment | Finance Agent | Amount, vendor, due date |
| Expense report | Finance Agent | Items, amounts, categories |
| Meeting request | Calendar MCP | Date, time, participants, agenda |
| Social media inquiry | Social Media Agent | Platform, content type |
| Project status | Human | Project name, requester |
| Technical support | Human | Issue description |
| Unknown | Human | Full message for manual triage |

## 4. Workflow

1. **Parse**: Extract message content, metadata, attachments
2. **Classify**: Determine primary intent using keyword and pattern matching
3. **Extract**: Pull relevant data for the target agent
4. **Confidence**: Score classification confidence (high > 0.8, medium > 0.5, low < 0.5)
5. **Route**: If confidence is high, route automatically; otherwise, ask human

## 5. HITL Gate

**Risk Level**: LOW (classification only, no action taken)
**Approval Required**: NO for classification; YES if routing triggers an action

## 6. Constraints

- Never discard messages — if classification fails, route to human
- Log all routing decisions for audit trail
- If confidence < 0.5, always escalate to human
- Never route sensitive messages without checking classification twice
