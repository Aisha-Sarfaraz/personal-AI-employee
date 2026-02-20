# Silver Tier — Quickstart & OAuth2 Setup

**Branch:** `002-silver-tier`
**Prerequisite:** Bronze Tier fully installed and verified (385 tests passing, SC-001–SC-009 green).

---

## Overview

Silver Tier adds three live communication channel watchers and four new AI skills.
Getting started requires:

1. Gmail OAuth2 credentials (Google Cloud Console)
2. Twilio account credentials (WhatsApp sandbox or production)
3. A working `ANTHROPIC_API_KEY` for the `generate_plan` skill
4. Optional: LinkedIn via `browser-mcp` (no API credentials required)

---

## Step 1 — Environment Variables

Copy the example env file and fill in all new Silver fields:

```bash
cp .env.example .env
```

Open `.env` and set:

```ini
# ── Gmail ────────────────────────────────────────────────
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REDIRECT_URI=http://localhost:8080/oauth2callback
GMAIL_TOKEN_FILE=vault/.gmail_token.json

# ── Twilio / WhatsApp ─────────────────────────────────────
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886   # Twilio sandbox number

# ── Claude API ───────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...

# ── Safety flags ─────────────────────────────────────────
DEV_MODE=true          # false = real email sends via email-mcp
REAL_EMAIL_ENABLED=false
OPT_OUT_LIST_PATH=vault/opt_out_list.txt
```

> **Never commit `.env` to git.** `.gitignore` already covers it.

---

## Step 2 — Install Python Dependencies

```bash
pip install -r requirements.txt
```

New Silver packages (added to `requirements.txt` during implementation):

| Package | Version | Purpose |
|---------|---------|---------|
| `google-auth` | ≥2.28 | Gmail OAuth2 token management |
| `google-auth-oauthlib` | ≥1.2 | OAuth2 flow helper |
| `google-api-python-client` | ≥2.120 | Gmail REST API |
| `twilio` | ≥9.0 | WhatsApp message polling |
| `anthropic` | ≥0.25 | Claude API for `generate_plan` skill |

---

## Step 3 — Gmail OAuth2 Setup

### 3a. Create Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g. `fte-employee-silver`)
3. Enable **Gmail API** under "APIs & Services → Library"

### 3b. Create OAuth2 credentials

1. Go to "APIs & Services → Credentials"
2. Click **"Create Credentials → OAuth client ID"**
3. Application type: **Desktop app**
4. Download the JSON; copy `client_id` and `client_secret` into `.env`

### 3c. Run the authorization flow (one-time)

```bash
python src/watchers/gmail_auth.py
```

This opens a browser window. Sign in with your Google account and grant the
`gmail.readonly` scope. The token is saved to `vault/.gmail_token.json`.

> Token refresh is automatic. If it expires, delete `vault/.gmail_token.json`
> and re-run the authorization flow.

### 3d. Verify

```bash
python -c "from src.watchers.gmail_watcher import GmailWatcher; w = GmailWatcher('vault'); print(w.check_for_updates())"
```

Expected output: a list of unread message dicts (possibly `[]` if inbox is empty).

---

## Step 4 — Twilio / WhatsApp Setup

### 4a. Twilio sandbox (development)

1. Sign up at [twilio.com](https://www.twilio.com)
2. Go to **Messaging → Try it out → Send a WhatsApp message**
3. Follow the sandbox join instructions from your phone
4. Copy **Account SID** and **Auth Token** from the Twilio Console dashboard
5. Note the sandbox sender number (usually `+14155238886`)

### 4b. Production WhatsApp Business (optional)

1. Apply for WhatsApp Business API approval in Twilio Console
2. Register your own phone number as the sender
3. Update `TWILIO_WHATSAPP_FROM` in `.env`

### 4c. Verify

```bash
python -c "from src.watchers.whatsapp_watcher import WhatsAppWatcher; w = WhatsAppWatcher('vault'); print(w.check_for_updates())"
```

> **Dev mode**: set `TWILIO_ACCOUNT_SID=mock` to use the built-in dry-run mock
> (returns synthetic test messages, no network calls).

---

## Step 5 — LinkedIn via browser-mcp

LinkedIn watching uses the `browser-mcp` Playwright integration already
configured in `.claude/settings.local.json`. No API credentials are needed.

### 5a. First-time login

```bash
# browser-mcp handles the login session automatically
# On first run the browser will open a LinkedIn login page
# Sign in manually — the session cookie is persisted for subsequent runs
```

### 5b. Verify

```bash
python -c "from src.watchers.linkedin_watcher import LinkedInWatcher; w = LinkedInWatcher('vault'); print(w.check_for_updates())"
```

> If the session cookie expires (typically every 30 days), re-login via the
> browser window that browser-mcp opens automatically.

---

## Step 6 — Install the Scheduler

The scheduler registers the orchestrator as a background service so it starts
automatically on boot.

```bash
# Windows
python src/install_schedule.py --install

# Linux / macOS
python src/install_schedule.py --install

# Verify
python src/install_schedule.py --status

# Remove
python src/install_schedule.py --uninstall
```

On Windows this creates a **Windows Task Scheduler** task named
`FTE-Employee-Orchestrator`. On Linux/macOS it adds a `crontab` entry.

---

## Step 7 — First Run

```bash
# Start in dev mode (no real emails, no real WhatsApp sends)
DEV_MODE=true python src/orchestrator.py
```

Watch the terminal — you should see all three new watchers initializing:

```
[orchestrator] Starting Silver Tier watchers…
[gmail_watcher] Initialized — poll interval 120s
[whatsapp_watcher] Initialized — poll interval 120s (mock mode)
[linkedin_watcher] Initialized — poll interval 120s (browser-mcp)
[filesystem_watcher] Watching vault/Watch/
```

Drop a test file to verify the filesystem pipeline still works:

```bash
cp tests/fixtures/invoice_request.txt vault/Watch/
```

For Gmail/WhatsApp, send yourself a real message (or use mock mode) and watch
the orchestrator pick it up within 2 minutes.

---

## Dev Mode vs Production Mode

| Flag | Effect |
|------|--------|
| `DEV_MODE=true` | All watchers use mocks. No real API calls. No emails sent. |
| `DEV_MODE=false` | Live Gmail/WhatsApp polling. Real email sends via `email-mcp`. |
| `REAL_EMAIL_ENABLED=false` | Even in live mode, email send is disabled (extra safety gate). |
| `ANTHROPIC_API_KEY` absent | `generate_plan` skill falls back to Bronze template logic. |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Gmail token expired` | Delete `vault/.gmail_token.json`, re-run `gmail_auth.py` |
| `Twilio 401 Unauthorized` | Check `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` in `.env` |
| `browser-mcp session expired` | Re-login to LinkedIn via the browser that browser-mcp opens |
| `ANTHROPIC_API_KEY missing` | Set key in `.env`; or use `DEV_MODE=true` for template fallback |
| Orchestrator not starting on boot | Re-run `python src/install_schedule.py --install` |
| WhatsApp messages not appearing | Confirm phone sent "join &lt;sandbox-keyword&gt;" to Twilio number |

---

## Verification Checklist (SC-010 – SC-020)

After setup, verify each Silver success criterion:

- [ ] **SC-010** — GmailWatcher starts and polls without crashing (`DEV_MODE=true`)
- [ ] **SC-011** — WhatsAppWatcher produces items (real or mock) without crashing
- [ ] **SC-012** — LinkedInWatcher returns engagement metrics via browser-mcp
- [ ] **SC-013** — detect_lead tags CRITICAL items containing lead keywords
- [ ] **SC-014** — generate_plan calls Claude API (or falls back to template)
- [ ] **SC-015** — generate_linkedin_post produces draft requiring HITL approval
- [ ] **SC-016** — weekly_briefing writes `vault/Briefings/BRIEFING_<date>.md`
- [ ] **SC-017** — install_schedule.py creates scheduler entry idempotently
- [ ] **SC-018** — Email send only fires when `DEV_MODE=false` and `REAL_EMAIL_ENABLED=true`
- [ ] **SC-019** — Quarantine policy: file quarantined after 3 processing failures
- [ ] **SC-020** — Full test suite passes (≥420 tests green, no regressions on 385 Bronze tests)

---

*Full specification: `specs/002-silver-tier/spec.md`*
*Bronze quickstart: `specs/001-bronze-tier/` (if present)*
