---
name: draft-email-response
description: Draft contextual email replies based on inbox content and conversation history. Use when the Communication Agent needs to compose a response to an incoming email.
version: 1.0.0
agent: communication-agent
type: action
inputs:
  - email_content: The original email to respond to
  - sender_info: Sender name, email, relationship context
  - conversation_history: Previous emails in the thread (if any)
  - tone_preference: Desired tone (formal, casual, professional)
outputs:
  - draft_response: Complete email draft ready for HITL approval
  - suggested_subject: Suggested reply subject line
  - action_items: Extracted action items from the email
reusability: extremely-high
framework_agnostic: true
---

# Skill: draft-email-response

## 1. Purpose

Draft professional, context-aware email responses that match the sender's tone and address all points raised in the incoming email. Every draft is presented to the human for review and approval before sending.

## 2. When to Use This Skill

**Mandatory invocation:**
- Communication Agent receives an email that requires a response
- User explicitly requests a reply to a specific email
- Scheduled follow-up emails are due

**Trigger conditions:**
- `email.received` event with `requires_response: true`
- User command: "Reply to [email]", "Draft a response to [sender]"

## 3. Workflow

1. **Parse**: Extract sender, subject, body, attachments, thread context
2. **Analyze**: Identify questions asked, action items, deadlines, tone
3. **Classify**: Determine response type (acknowledgment, answer, follow-up, decline)
4. **Draft**: Compose response addressing all identified points
5. **Review**: Self-check against quality criteria
6. **Present**: Show draft to human via HITL gate with approval request

## 4. Quality Criteria

- Addresses every question or point raised in the original email
- Matches the formality level of the incoming message
- Includes clear action items or next steps when applicable
- Does not make commitments without flagging them
- Does not share confidential information
- Professional greeting and sign-off appropriate to relationship

## 5. HITL Gate

**Risk Level**: HIGH (outbound communication)
**Approval Required**: YES — always before sending
**Presented to human**: Full draft with original email context

## 6. Constraints

- Never auto-send — always require HITL approval
- Never include confidential data not already in the thread
- Never make financial commitments without flagging
- Never use reply-all without explicit instruction
- Maximum response length: match the original email's length unless more detail is needed
