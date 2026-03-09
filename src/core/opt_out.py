"""Opt-out checker — parses vault/Opt_Out_List.md for opted-out email addresses."""

from __future__ import annotations

import os


def is_opted_out(vault_root: str, email_address: str) -> bool:
    """Check whether an email address is in the opt-out list.

    Args:
        vault_root: Path to vault root directory.
        email_address: The email address to check.

    Returns:
        True if the address is opted out; False otherwise (including missing file).
    """
    opt_out_path = os.path.join(vault_root, "Opt_Out_List.md")
    if not os.path.exists(opt_out_path):
        return False

    try:
        with open(opt_out_path, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return False

    target = email_address.lower().strip()
    for line in content.splitlines():
        stripped = line.strip()
        # Only lines starting with "- " are entries
        if not stripped.startswith("- "):
            continue
        entry = stripped[2:].strip().lower()
        if entry == target:
            return True

    return False
