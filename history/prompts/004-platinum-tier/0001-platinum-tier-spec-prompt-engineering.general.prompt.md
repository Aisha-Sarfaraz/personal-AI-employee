---
id: "0001"
title: Platinum Tier Specification Prompt Engineering
stage: general
date: 2026-03-03
surface: agent
model: claude-sonnet-4-6
feature: 004-platinum-tier
branch: 003-gold-tier
user: Aisha-Sarfaraz
command: "You are a professional prompt engineer. Deeply read and analyze Documents.md, then write a high-level prompt for the Platinum Tier specification."
labels: ["prompt-engineering","platinum-tier","spec","cloud-deployment","two-zone-architecture"]
links:
  spec: specs/004-platinum-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - history/prompts/004-platinum-tier/0001-platinum-tier-spec-prompt-engineering.general.prompt.md
tests:
  - "n/a — prompt engineering task, no tests"
---

## Prompt

You are a professional prompt engineer. Deeply read and analyze Documents.md, then write a high-level prompt for the Platinum Tier specification.

## Response snapshot

Analysed Documents.md (1,081 lines) and all three prior tier specs (Bronze, Silver, Gold).

Key inputs extracted:
- Platinum Tier definition: Documents.md lines 135–155 (Cloud VM, two-zone, vault sync, Odoo cloud, A2A Phase 2, demo gate)
- Established 13-section spec format from specs/003-gold-tier/spec.md
- SC numbering convention: SC-033–SC-042 follows SC-001–SC-032
- Additive-only principle: all Gold/Silver/Bronze code preserved unchanged

Produced a complete, copy-paste-ready `/sp.specify` prompt covering:
- R1: Cloud VM deployment (Oracle Cloud Free ARM, systemd, PM2)
- R2: Two-zone work-zone specialization (AGENT_ZONE guard on every skill)
- R3: Git-synced vault with claim-by-move protocol + domain-scoped folders
- R4: Odoo on Cloud VM (HTTPS, Let's Encrypt, daily backups, health check)
- R5: A2A upgrade path documented as Phase 2 future work only
- R6: Production hardening (heartbeat, alerting, zero-downtime restart)
- 6 clarifications (C1–C6) with informed defaults
- 10 success criteria SC-033–SC-042
- Verbatim minimum passing demo gate
- Full 16-section spec format instructions

## Outcome

- ✅ Impact: Complete Platinum Tier specification prompt ready for `/sp.specify`; covers all Documents.md Platinum requirements; consistent with prior tier spec format
- 🧪 Tests: n/a — prompt engineering deliverable
- 📁 Files: PHR at history/prompts/004-platinum-tier/0001-platinum-tier-spec-prompt-engineering.general.prompt.md
- 🔁 Next prompts: `/sp.specify <paste prompt above>` to generate specs/004-platinum-tier/spec.md; then `/sp.clarify` → `/sp.plan` → `/sp.tasks` → `/sp.implement`
- 🧠 Reflection: Two-zone AGENT_ZONE guard is the critical architectural primitive — every skill must check it at entry. Claim-by-move race condition is the highest implementation risk. A2A must stay Phase 2 only to keep Platinum scope manageable.

## Evaluation notes (flywheel)

- Failure modes observed: None — read-only prompt engineering task with no execution risk
- Graders run and results (PASS/FAIL): Prompt covers all 6 Documents.md Platinum requirements; all 10 SCs are measurable
- Prompt variant (if applicable): null
- Next experiment: Run `/sp.specify` with this prompt; adjust C1–C6 clarifications based on user answers
