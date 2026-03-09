"""generate_plan skill — wraps plan_task.py and optionally enriches plans with Claude reasoning."""

from __future__ import annotations

import os
from typing import Any

from src.skills import plan_task


_REASONING_HEADER = "## Reasoning\n\n"
_REASONING_PLACEHOLDER = (
    "This plan was generated from a template. "
    "Add ANTHROPIC_API_KEY and set dev_mode=false to enable AI reasoning."
)


def _call_claude(prompt: str) -> str:
    """Call Claude API and return the text response.

    Raises:
        Exception: If API call fails or anthropic package unavailable.
    """
    try:
        import anthropic  # type: ignore[import]
    except ImportError as exc:
        raise ImportError("anthropic package not installed") from exc

    model = os.environ.get("ANTHROPIC_PLAN_MODEL", "claude-haiku-4-5-20251001")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model=model,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _insert_reasoning(plan_content: str, reasoning: str) -> str:
    """Insert '## Reasoning' section after YAML frontmatter, before first heading."""
    reasoning_block = f"{_REASONING_HEADER}{reasoning}\n\n---\n\n"

    # Find end of frontmatter (second ---)
    parts = plan_content.split("---", 2)
    if len(parts) >= 3:
        # parts[0] = before first ---  (empty)
        # parts[1] = frontmatter content
        # parts[2] = body after second ---
        return f"---{parts[1]}---\n\n{reasoning_block}{parts[2].lstrip()}"

    # Fallback: prepend to content
    return f"{reasoning_block}{plan_content}"


def _enrich_plan_file(plan_path: str, item_context: str) -> bool:
    """Read plan file, call Claude, insert Reasoning section. Returns True on success."""
    try:
        with open(plan_path, encoding="utf-8") as f:
            content = f.read()

        prompt = (
            f"You are a business assistant. Given this context:\n\n{item_context}\n\n"
            f"Provide a concise reasoning section (2-4 sentences) explaining why these plan "
            f"steps are the right approach. Be specific and actionable."
        )
        reasoning = _call_claude(prompt)
        enriched = _insert_reasoning(content, reasoning)

        # Write back atomically
        import tempfile
        dir_path = os.path.dirname(plan_path)
        fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(enriched)
            os.replace(tmp_path, plan_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

        return True
    except Exception:
        return False


def run(vault_root: str, dev_mode: bool = True) -> dict[str, Any]:
    """Generate execution plans via plan_task.py, optionally enriching with Claude.

    Args:
        vault_root: Path to vault root directory.
        dev_mode: If True, skip Claude API calls (template plans only).

    Returns:
        Dict with keys: processed, claude_enriched, template_fallback, errors, skipped.
    """
    # Step 1: Delegate to plan_task.run() — generates template plans
    plan_result = plan_task.run(vault_root)

    processed = plan_result.get("processed", 0)
    skipped = plan_result.get("skipped", 0)
    errors = len(plan_result.get("errors", []))
    claude_enriched = 0
    template_fallback = 0

    # Step 2: If conditions met, enrich plans with Claude reasoning
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    should_enrich = bool(api_key) and not dev_mode

    if processed > 0:
        plans_dir = os.path.join(vault_root, "Plans")
        if os.path.isdir(plans_dir):
            plan_files = sorted(
                [f for f in os.listdir(plans_dir) if f.endswith(".md")],
                key=lambda f: os.path.getmtime(os.path.join(plans_dir, f)),
                reverse=True,
            )
            # Enrich the most recently created plans (up to processed count)
            recent_plans = plan_files[:processed]
            for plan_filename in recent_plans:
                plan_path = os.path.join(plans_dir, plan_filename)
                if should_enrich:
                    success = _enrich_plan_file(plan_path, item_context=plan_filename)
                    if success:
                        claude_enriched += 1
                    else:
                        template_fallback += 1
                else:
                    template_fallback += 1

    return {
        "processed": processed,
        "claude_enriched": claude_enriched,
        "template_fallback": template_fallback,
        "errors": errors,
        "skipped": skipped,
    }
