---
last_updated: 2026-01-01
version: "1.0"
owner: human
---

# Company Handbook

> Edit this file to define your business rules. The AI Employee reads it before every action.

---

## Communication Rules

- Always be polite and professional in all outbound messages.
- Do not contact anyone on the Opt_Out_List.md.
- All AI-drafted emails must include the footer: "This message was drafted with AI assistance."
- Response SLA: Reply to client emails within 24 hours.
- Do not send bulk emails to more than 10 recipients without explicit approval.

---

## Financial Thresholds

| Action | Threshold | Risk Level | Approval |
|--------|-----------|------------|----------|
| Payment — recurring known vendor | < $50 | LOW | Auto |
| Payment — new payee | Any amount | HIGH | Required |
| Payment | $100 – $500 | HIGH | Required |
| Payment | > $500 | CRITICAL | Required + confirm |
| Invoice creation | Any | HIGH | Required |
| Subscription cancellation | Any | HIGH | Required |

> HARD LIMIT: Any financial action > $15,000 is DENIED. Do not process.

---

## Social Media Rules

- Do not post content that is political, religious, or controversial.
- All AI-drafted social posts must include `#AIAssisted` tag.
- Post frequency: Maximum 1 LinkedIn post per 3 days.
- Do not reply to social media DMs without human approval.

---

## Data & Privacy Rules

- Never share client contact details in logs or public-facing content.
- Do not store banking credentials or payment tokens in the vault.
- Delete processed items from /Watch/ after they have been moved to /Inbox/.

---

## Behavioral Constraints

- Do not take irreversible actions (delete, payment, post) without HITL approval.
- Quarantine any plan that fails 3 or more times — do not retry indefinitely.
- Always log every action to vault/Logs/ with timestamp and outcome.
- If uncertain about an action, write a Pending_Approval file and wait for human decision.
