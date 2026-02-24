"""Weekly CEO Briefing skill — generates Monday briefings from vault Logs/."""

from __future__ import annotations

import glob
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

import yaml

from src.core.audit_logger import log_action
from src.core.vault import write_frontmatter_file


def _today() -> date:
    """Return current date (injectable for testing)."""
    return date.today()


def _load_logs_for_week(vault_root: str, week_start: date) -> list[dict[str, Any]]:
    """Parse audit log entries for the given Mon–Sun week."""
    logs_dir = os.path.join(vault_root, "Logs")
    if not os.path.isdir(logs_dir):
        return []

    week_end = week_start + timedelta(days=6)
    entries: list[dict[str, Any]] = []

    for log_file in sorted(glob.glob(os.path.join(logs_dir, "*.md"))):
        try:
            with open(log_file, encoding="utf-8") as f:
                content = f.read()
            parts = content.split("---")
            if len(parts) < 3:
                continue
            meta = yaml.safe_load(parts[1])
            if not isinstance(meta, dict):
                continue

            # Filter to this week
            ts_str = str(meta.get("timestamp", ""))
            if ts_str:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                entry_date = ts.date()
                if not (week_start <= entry_date <= week_end):
                    continue

            entries.append(meta)
        except Exception:
            continue

    return entries


def _count_by_action(entries: list[dict], keyword: str) -> int:
    return sum(1 for e in entries if keyword in str(e.get("action", "")))


def _generate_briefing_body(
    vault_root: str,
    week_start: date,
    entries: list[dict[str, Any]],
) -> str:
    """Build the full briefing markdown body with all 9 required sections."""
    week_end = week_start + timedelta(days=6)
    total = len(entries)
    channels = {}
    for e in entries:
        agent = e.get("agent", "unknown")
        channels[agent] = channels.get(agent, 0) + 1

    leads = _count_by_action(entries, "lead_detected")
    emails = _count_by_action(entries, "send_email") + _count_by_action(entries, "sent_email")
    linkedin = _count_by_action(entries, "linkedin_post")
    plans = _count_by_action(entries, "created_plan") + _count_by_action(entries, "plan")
    approvals = _count_by_action(entries, "approved") + _count_by_action(entries, "approval")
    quarantine = _count_by_action(entries, "quarantine")

    # Next-week recommendations (Claude if available, else template)
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        try:
            recommendations = _generate_recommendations_claude(entries, api_key)
        except Exception:
            recommendations = _template_recommendations(leads, emails, linkedin)
    else:
        recommendations = _template_recommendations(leads, emails, linkedin)

    # Channel list
    channel_list = "\n".join(
        f"  - **{agent}**: {count} actions" for agent, count in sorted(channels.items())
    ) or "  - No activity logged this week"

    body = f"""## 📅 Date Range

- **Week Start:** {week_start} (Monday)
- **Week End:** {week_end} (Sunday)
- **Total Log Entries:** {total}

---

## 📬 Items by Channel

{channel_list}

---

## 🎯 Leads Detected

- Leads identified this week: **{leads}**

---

## 📧 Emails Sent

- Emails dispatched: **{emails}**

---

## 🔗 LinkedIn Activity

- LinkedIn posts published: **{linkedin}**

---

## 📋 Plans Summary

- Plans created: **{plans}**

---

## ✅ Approvals

- Approval actions: **{approvals}**

---

## 🚫 Quarantine

- Items quarantined: **{quarantine}**

---

## 🔮 Next Week Recommendations

{recommendations}

---

*Generated automatically by weekly_briefing skill.*
"""
    return body


def _generate_recommendations_claude(entries: list[dict], api_key: str) -> str:
    """Generate next-week recommendations via Claude API."""
    try:
        import anthropic  # type: ignore[import]

        model = os.environ.get("ANTHROPIC_PLAN_MODEL", "claude-haiku-4-5-20251001")
        summary = f"{len(entries)} actions logged this week across {len(set(e.get('agent', '') for e in entries))} agents."
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=256,
            messages=[{
                "role": "user",
                "content": f"Based on this activity summary: {summary}\nProvide 2-3 concise recommendations for next week.",
            }],
        )
        return msg.content[0].text
    except Exception:
        return _template_recommendations(0, 0, 0)


def _template_recommendations(leads: int, emails: int, linkedin: int) -> str:
    recs = ["- Review and respond to any pending leads in Needs_Action/"]
    if emails > 0:
        recs.append("- Follow up on sent emails that await replies")
    if linkedin > 0:
        recs.append("- Monitor LinkedIn post engagement and plan next content")
    else:
        recs.append("- Consider publishing a LinkedIn post to maintain presence")
    return "\n".join(recs)


def run(vault_root: str) -> dict[str, Any]:
    """Generate the weekly CEO briefing if today is Monday and briefing doesn't exist.

    Args:
        vault_root: Path to vault root directory.

    Returns:
        Dict with keys: processed, briefing_file, week_start, errors, skipped.
    """
    today = _today()

    # Guard 1: Only run on Monday (weekday 0)
    if today.weekday() != 0:
        return {"processed": 0, "briefing_file": None, "week_start": None, "errors": [], "skipped": 1}

    # Determine this Monday
    week_start = today - timedelta(days=today.weekday())
    briefing_filename = f"BRIEFING_{week_start}.md"
    briefing_path = os.path.join(vault_root, "Briefings", briefing_filename)

    # Guard 2: Skip if already generated this week
    if os.path.exists(briefing_path):
        return {"processed": 0, "briefing_file": briefing_path, "week_start": str(week_start), "errors": [], "skipped": 1}

    # Determine previous week for log aggregation
    prev_week_start = week_start - timedelta(days=7)
    entries = _load_logs_for_week(vault_root, prev_week_start)

    # Generate briefing
    try:
        body = _generate_briefing_body(vault_root, prev_week_start, entries)
        metadata: dict[str, Any] = {
            "id": f"BRIEFING_{week_start}",
            "type": "weekly_briefing",
            "week_start": str(week_start),
            "week_end": str(week_start + timedelta(days=6)),
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "log_entries_processed": len(entries),
        }

        os.makedirs(os.path.join(vault_root, "Briefings"), exist_ok=True)
        write_frontmatter_file(vault_root, f"Briefings/{briefing_filename}", metadata, body)

        # LOW audit entry
        try:
            log_action(
                vault_root=vault_root,
                agent="weekly_briefing",
                action="briefing_created",
                risk_tier="LOW",
                status="success",
                details=f"Week of {prev_week_start}; {len(entries)} entries",
            )
        except Exception:
            pass

        return {
            "processed": max(1, len(entries)),
            "briefing_file": briefing_path,
            "week_start": str(week_start),
            "errors": [],
            "skipped": 0,
        }

    except Exception as exc:
        return {
            "processed": 0,
            "briefing_file": None,
            "week_start": str(week_start),
            "errors": [str(exc)],
            "skipped": 0,
        }
