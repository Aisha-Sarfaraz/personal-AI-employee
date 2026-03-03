"""Weekly CEO Briefing skill — generates Monday briefings from vault Logs/."""

from __future__ import annotations

import glob
import json
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


def _load_json_logs_for_social(vault_root: str) -> list[dict[str, Any]]:
    """Load Gold JSON-Lines log entries from vault/Logs/*.json for social action counting."""
    logs_dir = os.path.join(vault_root, "Logs")
    if not os.path.isdir(logs_dir):
        return []
    entries: list[dict[str, Any]] = []
    for log_file in glob.glob(os.path.join(logs_dir, "*.json")):
        try:
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except OSError:
            pass
    return entries


def _count_social_posts(vault_root: str) -> dict[str, int]:
    """Count social posts from Gold JSON-Lines audit logs."""
    social_types = {"post_facebook", "post_twitter", "generate_linkedin_post", "post_linkedin"}
    entries = _load_json_logs_for_social(vault_root)
    counts: dict[str, int] = {k: 0 for k in social_types}
    for entry in entries:
        action_type = entry.get("action_type", "")
        if action_type in social_types:
            counts[action_type] = counts.get(action_type, 0) + 1
    return counts


def _get_bottleneck_info(vault_root: str, sla_hours: int = 48) -> str:
    """Analyse Done/ items for SLA breaches (completed_at - created_at > sla_hours)."""
    done_dir = os.path.join(vault_root, "Done")
    if not os.path.isdir(done_dir):
        return "- No completed tasks this week."

    breaches: list[str] = []
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    for md_file in glob.glob(os.path.join(done_dir, "*.md")):
        try:
            with open(md_file, encoding="utf-8") as f:
                content = f.read()
            parts = content.split("---", 2)
            if len(parts) < 3:
                continue
            meta = yaml.safe_load(parts[1])
            if not isinstance(meta, dict):
                continue
            created_str = meta.get("created_at") or meta.get("timestamp", "")
            completed_str = meta.get("completed_at", "")
            if created_str and completed_str:
                created = datetime.fromisoformat(str(created_str).replace("Z", "+00:00"))
                completed = datetime.fromisoformat(str(completed_str).replace("Z", "+00:00"))
                delta_hours = (completed - created).total_seconds() / 3600
                if delta_hours > sla_hours:
                    item_id = meta.get("id", os.path.basename(md_file))
                    breaches.append(
                        f"- `{item_id}` took {delta_hours:.1f}h (SLA: {sla_hours}h)"
                    )
        except Exception:
            continue

    if breaches:
        return "\n".join(breaches[:5])  # top 5
    return "- No SLA breaches this week."


def _generate_gold_sections(vault_root: str) -> str:
    """Generate the 5 new Gold Tier sections for the weekly briefing."""
    from src.skills import accounting_audit

    # Run accounting audit (degrades gracefully on Odoo error)
    try:
        audit_result = accounting_audit.run(vault_root)
    except Exception:
        audit_result = {
            "revenue": None, "expenses": None, "suggestions": [],
            "error": "accounting_audit failed", "degraded": True,
        }

    degraded = audit_result.get("degraded", False)
    unavailable_msg = "[Data unavailable — Odoo offline]"

    # -- Revenue --
    if degraded or audit_result.get("revenue") is None:
        revenue_content = f"- MTD Total: {unavailable_msg}\n- Weekly Paid: {unavailable_msg}"
    else:
        rev = audit_result["revenue"]
        revenue_content = (
            f"- MTD Total: **${rev.get('mtd_total', 0.0):.2f}**\n"
            f"- Weekly Paid: **${rev.get('weekly_paid', 0.0):.2f}**"
        )

    # -- Expenses --
    if degraded or audit_result.get("expenses") is None:
        expenses_content = f"- Top Categories: {unavailable_msg}"
    else:
        exp = audit_result["expenses"]
        top_cats = exp.get("top_categories", [])
        if top_cats:
            cat_lines = "\n".join(
                f"  - **{c['category']}**: ${c['total']:.2f}"
                for c in top_cats[:5]
            )
            expenses_content = f"**Top 5 Expense Categories:**\n\n{cat_lines}"
        else:
            expenses_content = "- No expense data available."

    # -- Bottleneck --
    bottleneck_content = _get_bottleneck_info(vault_root)

    # -- Proactive Suggestions --
    suggestions = audit_result.get("suggestions", [])
    if suggestions:
        suggestions_content = "\n".join(f"- {s}" for s in suggestions[:5])
    elif degraded:
        suggestions_content = f"- {unavailable_msg}"
    else:
        suggestions_content = "- No flagged items this week."

    # -- Social Summary --
    social_counts = _count_social_posts(vault_root)
    total_social = sum(social_counts.values())
    linkedin_count = social_counts.get("generate_linkedin_post", 0) + social_counts.get("post_linkedin", 0)
    fb_count = social_counts.get("post_facebook", 0)
    tw_count = social_counts.get("post_twitter", 0)
    social_content = (
        f"- LinkedIn posts: **{linkedin_count}**\n"
        f"- Facebook posts: **{fb_count}**\n"
        f"- Twitter posts: **{tw_count}**\n"
        f"- Total social actions: **{total_social}**"
    )

    return f"""## Revenue

{revenue_content}

---

## Expenses

{expenses_content}

---

## Bottleneck

{bottleneck_content}

---

## Proactive Suggestions

{suggestions_content}

---

## Social Summary

{social_content}

---
"""


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

    # Gold Tier: generate 5 new sections
    gold_sections = _generate_gold_sections(vault_root)

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

{gold_sections}

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
