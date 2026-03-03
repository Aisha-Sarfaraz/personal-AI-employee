# Gold Tier Quickstart Guide

**Feature**: 003-gold-tier
**Date**: 2026-02-25
**Audience**: Developer setting up the Gold Tier for the first time

---

## Prerequisites

- Silver Tier fully installed and running (531 tests pass)
- Docker Desktop installed and running (for Odoo)
- Python 3.10+ with pip
- A Meta Business account with a Facebook Page and linked Instagram Business account
- A Twitter/X Developer account (Free tier)

---

## Step 1 — Install New Dependencies

```bash
pip install -r requirements.txt
```

New Gold Tier packages added to `requirements.txt`:
- `tweepy>=4.14` — Twitter API v2 client
- `requests>=2.31` — already present in Silver (Odoo JSON-RPC calls)
- `mcp>=1.0` — already present in Silver (email-mcp); used for Odoo MCP server

---

## Step 2 — Start Odoo via Docker Compose

```bash
docker compose -f docker-compose.odoo.yml up -d
```

This starts:
- **Odoo Community 19**: `http://localhost:8069`
- **PostgreSQL 16**: internal to Docker network

### First-Time Odoo Setup

1. Open `http://localhost:8069` in browser
2. Create database: name `fte_db`, email `admin@example.com`, password of your choice
3. Install the **Accounting** module from Apps
4. Note your admin **UID** (usually `1`; confirm via Settings → Technical → Users)

### Get Odoo UID

```bash
# One-time lookup — returns your numeric user ID
curl -s -X POST http://localhost:8069/web/dataset/call_kw \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","id":1,"params":{"service":"common","method":"authenticate","args":["fte_db","admin@example.com","YOUR_PASSWORD",{}]}}' | python -m json.tool
# Result: {"id":1,"result":1}  ← "result" is your UID
```

---

## Step 3 — Configure Meta Graph API (Facebook + Instagram)

### Get a Long-Lived Page Access Token

1. Go to [Meta for Developers](https://developers.facebook.com/) → your app
2. Navigate to **Tools** → **Graph API Explorer**
3. Select your **Facebook Page** from the dropdown
4. Click **Generate Access Token** → grant required permissions:
   - `pages_manage_posts`
   - `pages_read_engagement`
   - `instagram_basic`
   - `instagram_content_publish`
5. Exchange for long-lived token (60 days):

```bash
curl "https://graph.facebook.com/v20.0/oauth/access_token\
?grant_type=fb_exchange_token\
&client_id=YOUR_APP_ID\
&client_secret=YOUR_APP_SECRET\
&fb_exchange_token=YOUR_SHORT_LIVED_TOKEN"
```

### Get Your Page ID and Instagram User ID

```bash
# Page ID
curl "https://graph.facebook.com/v20.0/me?fields=id,name&access_token=YOUR_LONG_LIVED_TOKEN"

# Instagram User ID (linked to Page)
curl "https://graph.facebook.com/v20.0/YOUR_PAGE_ID?fields=instagram_business_account&access_token=YOUR_LONG_LIVED_TOKEN"
```

### Token Refresh Reminder

Long-lived tokens expire after 60 days. Set a calendar reminder to refresh the token.
When a 401 error occurs, a `vault/Inbox/META_AUTH_ALERT_<ts>.md` item is created.
Repeat the exchange above and update `FACEBOOK_ACCESS_TOKEN` in `.env`.

---

## Step 4 — Configure Twitter/X API

### Create a Twitter Developer App

1. Go to [developer.twitter.com](https://developer.twitter.com) → Create App
2. Apply for **Free tier** access (read + write)
3. Generate **API Key + Secret** and **Access Token + Secret** with Read+Write permissions
4. Copy your **numeric Twitter User ID**:

```bash
# Get your numeric User ID (one-time lookup)
curl "https://api.twitter.com/2/users/by/username/YOUR_USERNAME" \
  -H "Authorization: Bearer YOUR_BEARER_TOKEN"
# Returns: {"data":{"id":"123456789","name":"Your Name","username":"your_handle"}}
```

---

## Step 5 — Configure `.env`

Copy `.env.example` to `.env` and fill in the Gold Tier values:

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
# === Odoo ===
ODOO_URL=http://localhost:8069
ODOO_DB=fte_db
ODOO_UID=1
ODOO_PASSWORD=your_odoo_admin_password

# === Meta / Facebook + Instagram ===
FACEBOOK_PAGE_ID=123456789012345
FACEBOOK_ACCESS_TOKEN=EAAxxxxx....(long-lived token)
INSTAGRAM_USER_ID=987654321098765

# === Twitter/X ===
TWITTER_BEARER_TOKEN=AAAAAAAAAAAAAAAAAxxxx....
TWITTER_API_KEY=xxxx
TWITTER_API_SECRET=xxxx
TWITTER_ACCESS_TOKEN=xxxx-xxxx
TWITTER_ACCESS_SECRET=xxxx
TWITTER_USER_ID=123456789     # your numeric user ID

# === Existing Silver vars (unchanged) ===
DEV_MODE=true
ANTHROPIC_API_KEY=sk-ant-...
# ... (all Silver vars remain)
```

---

## Step 6 — Enable Gold Features in `settings.yaml`

Add (or uncomment) the Gold stanzas in `config/settings.yaml`:

```yaml
# Gold Tier additions
odoo:
  url: "${ODOO_URL}"
  db: "${ODOO_DB}"
  poll_interval_s: 300

facebook:
  enabled: false          # set to true when ready to post
  frequency_days: 3

twitter:
  enabled: false          # set to true when ready to post
  tweets_per_day: 1

ralph_loop:
  max_iterations: 10

audit:
  retention_days: 90
  archive_dir: vault/Logs/Archive

sla:
  task_completion_hours: 48
```

---

## Step 7 — Register the Stop Hook

The Stop hook is registered automatically by `install_schedule.py`. Run once:

```bash
python -m src.skills.install_schedule
```

This installs:
- Windows Task Scheduler job (existing Silver behaviour)
- `.claude/hooks/Stop` → `hooks/stop_hook.py` (Gold addition)

Verify registration:
```bash
cat .claude/hooks/Stop    # should reference hooks/stop_hook.py
```

---

## Step 8 — Run Tests

```bash
# Full test suite (all Bronze + Silver + Gold)
python -m pytest tests/ -q

# Gold-only tests
python -m pytest tests/ -k "gold" -q

# Verify Bronze + Silver unchanged
python -m pytest tests/ -k "not gold" -q --tb=short
```

Expected: All 531 Silver + 385 Bronze + ~120 Gold tests pass.

---

## Step 9 — Start the Orchestrator (Dev Mode)

```bash
DEV_MODE=true python -m src.orchestrator
```

In dev mode:
- Finance Watcher reads `vault/Watch/finance_mock/*.json` instead of Odoo
- Facebook/Twitter watchers read mock files instead of live APIs
- No real Odoo, Meta, or Twitter HTTP calls are made
- All actions logged with `simulated: true`

---

## Step 10 — Drop a Test File (Smoke Test)

```bash
# Test Finance Watcher
cp vault/Watch/finance_mock/sample_transactions.json vault/Watch/finance_mock/test_$(date +%s).json
# Check vault/Accounting/Current_Month.md within 5 minutes

# Test Invoice Generation
echo "Please create an invoice for ACME Corp for $500 consulting services" \
  > vault/Watch/invoice_request.txt
# Check vault/Pending_Approval/INVOICE_*.md
```

---

## Troubleshooting

### Odoo connection refused

```
ERROR: Finance Watcher: ConnectionError — http://localhost:8069
```

1. Check Docker: `docker compose -f docker-compose.odoo.yml ps`
2. Restart if needed: `docker compose -f docker-compose.odoo.yml restart`
3. Finance Watcher will automatically use CSV fallback from `vault/Watch/finance_drop/`

### Meta token expired (401 error)

1. Check `vault/Inbox/META_AUTH_ALERT_*.md` for the alert
2. Repeat Step 3 token exchange above
3. Update `FACEBOOK_ACCESS_TOKEN` in `.env`
4. Restart orchestrator

### Twitter 401 (Unauthorized)

1. Check `vault/Inbox/TWITTER_AUTH_ALERT_*.md`
2. Regenerate Access Token + Secret in Twitter Developer Portal
3. Update `TWITTER_ACCESS_TOKEN` and `TWITTER_ACCESS_SECRET` in `.env`
4. Restart orchestrator

### Ralph loop stuck

```bash
cat vault/state/ralph_loop_state.json
# Check iteration count; if near max_iterations, monitor vault/Quarantine/
```

Force-complete by moving the plan file to `vault/Done/` manually.
