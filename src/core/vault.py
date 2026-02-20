"""Vault CRUD operations with atomic writes for Obsidian-compatible Markdown files."""

import os
import shutil
import tempfile
from typing import Any

from src.core.frontmatter import parse_frontmatter, write_frontmatter


def read_file(vault_root: str, relative_path: str) -> str:
    """Read file content from the vault.

    Args:
        vault_root: Absolute path to the vault directory.
        relative_path: Path relative to vault root.

    Returns:
        File content as string.

    Raises:
        FileNotFoundError: If file does not exist.
    """
    full_path = os.path.join(vault_root, relative_path)
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(vault_root: str, relative_path: str, content: str) -> None:
    """Write content to a file atomically (temp file + os.replace).

    Args:
        vault_root: Absolute path to the vault directory.
        relative_path: Path relative to vault root.
        content: Content to write.
    """
    full_path = os.path.join(vault_root, relative_path)
    dir_path = os.path.dirname(full_path)
    os.makedirs(dir_path, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, full_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def move_file(vault_root: str, from_path: str, to_path: str) -> None:
    """Move a file within the vault.

    Args:
        vault_root: Absolute path to the vault directory.
        from_path: Source path relative to vault root.
        to_path: Destination path relative to vault root.
    """
    src = os.path.join(vault_root, from_path)
    dst = os.path.join(vault_root, to_path)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)


def list_folder(vault_root: str, folder: str) -> list[str]:
    """List .md files in a vault folder.

    Args:
        vault_root: Absolute path to the vault directory.
        folder: Folder name relative to vault root.

    Returns:
        List of .md filenames (not full paths).
    """
    folder_path = os.path.join(vault_root, folder)
    if not os.path.isdir(folder_path):
        return []
    return [f for f in os.listdir(folder_path) if f.endswith(".md")]


def read_frontmatter_file(vault_root: str, relative_path: str) -> tuple[dict[str, Any], str]:
    """Read a file and parse its YAML frontmatter.

    Args:
        vault_root: Absolute path to the vault directory.
        relative_path: Path relative to vault root.

    Returns:
        Tuple of (metadata_dict, body_string).
    """
    content = read_file(vault_root, relative_path)
    return parse_frontmatter(content)


def write_frontmatter_file(
    vault_root: str,
    relative_path: str,
    metadata: dict[str, Any],
    body: str = "",
) -> None:
    """Write a frontmatter file atomically.

    Args:
        vault_root: Absolute path to the vault directory.
        relative_path: Path relative to vault root.
        metadata: YAML frontmatter dict.
        body: Markdown body content.
    """
    content = write_frontmatter(metadata, body)
    write_file(vault_root, relative_path, content)
