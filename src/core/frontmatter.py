"""YAML frontmatter parser and writer for Obsidian-compatible Markdown files."""

from datetime import datetime, timezone
from typing import Any

import yaml


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from Markdown content.

    Args:
        content: Full Markdown file content with optional YAML frontmatter.

    Returns:
        Tuple of (metadata_dict, body_string). If no valid frontmatter found,
        returns (empty dict, original content).
    """
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    yaml_block = parts[1].strip()
    body = parts[2].lstrip("\n")

    try:
        metadata = yaml.safe_load(yaml_block)
        if not isinstance(metadata, dict):
            return {}, content
        return metadata, body
    except yaml.YAMLError:
        return {}, content


def write_frontmatter(metadata: dict[str, Any], body: str = "") -> str:
    """Write YAML frontmatter and body into Markdown content.

    Args:
        metadata: Dictionary of frontmatter fields.
        body: Markdown body content.

    Returns:
        Complete Markdown string with YAML frontmatter.
    """
    yaml_str = yaml.dump(metadata, default_flow_style=False, sort_keys=False, allow_unicode=True)
    result = f"---\n{yaml_str}---\n"
    if body:
        result += f"\n{body}"
    return result


def create_standard_metadata(
    type: str,
    source: str,
    priority: str = "MEDIUM",
    status: str = "new",
) -> dict[str, Any]:
    """Create standard metadata dict for vault items.

    Args:
        type: Item type (financial, communication, task, document, general, unknown).
        source: Origin source (filesystem_watcher, gmail_watcher, etc.).
        priority: Priority level (CRITICAL, HIGH, MEDIUM, LOW).
        status: Current status (new, triaged, planned, etc.).

    Returns:
        Dictionary with standard frontmatter fields including auto-generated timestamp.
    """
    return {
        "type": type,
        "source": source,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "priority": priority,
        "status": status,
    }
