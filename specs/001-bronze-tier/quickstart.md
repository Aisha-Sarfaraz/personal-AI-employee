# Quickstart: Bronze Tier

## Prerequisites

- Python 3.10+
- Node.js 18+ (for PM2)
- PM2 (`npm install -g pm2`)

## Setup

```bash
# Clone and enter project
cd fte-employe

# Install Python dependencies
pip install -r requirements.txt

# Verify vault structure exists
ls vault/Inbox vault/Needs_Action vault/Plans vault/Done vault/Logs vault/Pending_Approval vault/Approved vault/Rejected vault/Watch
```

## Run the System

### Option 1: Direct (development)

```bash
python src/orchestrator.py
```

### Option 2: PM2 (daemon)

```bash
pm2 start ecosystem.config.js
pm2 logs fte-orchestrator
```

## Test the Pipeline

1. **Drop a file:**
   ```bash
   echo "Please process this invoice for $500 from vendor ABC" > vault/Watch/test_invoice.txt
   ```

2. **Watch the pipeline:** Items flow through: `Inbox → Needs_Action → Plans → Pending_Approval`

3. **Approve (if needed):** In Obsidian or file manager, move `APPROVAL_REQUIRED_*.md` from `vault/Pending_Approval/` to `vault/Approved/`

4. **Check completion:** Item appears in `vault/Done/`, audit log in `vault/Logs/`

5. **View dashboard:** Open `vault/Dashboard.md` in Obsidian

## Run Tests

```bash
python -m pytest tests/ -v
```

## Key Files

| File | Purpose |
|------|---------|
| `config/settings.yaml` | All configuration |
| `vault/Company_Handbook.md` | Business rules |
| `vault/Dashboard.md` | System status (auto-generated) |
| `vault/Business_Goals.md` | Business objectives |

## DEV_MODE

Bronze runs in `dev_mode: true` by default. All external actions (send email, create invoice, etc.) are **simulated** — logged but not executed. To verify, check `vault/Logs/` for entries with `simulated: true`.
