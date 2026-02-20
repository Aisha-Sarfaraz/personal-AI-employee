"""
Comprehensive tests for src.core.vault module.

Covers:
- write_file (atomic creation and overwrite)
- read_file (success and FileNotFoundError)
- move_file (basic move and destination directory creation)
- list_folder (.md filtering and empty folder)
- read_frontmatter_file (parsing)
- write_frontmatter_file (creation)
- roundtrip write_frontmatter_file -> read_frontmatter_file
"""

import os
import pytest

from src.core.vault import (
    read_file,
    write_file,
    move_file,
    list_folder,
    read_frontmatter_file,
    write_frontmatter_file,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_vault(tmp_path: pytest.TempPathFactory) -> str:
    """
    Create a minimal vault directory structure under tmp_path and return
    the vault root as a string.

    Layout created:
        <tmp_path>/vault/
            notes/          -- general notes folder
            archive/        -- secondary folder for move tests
    """
    vault_root = tmp_path / "vault"
    (vault_root / "notes").mkdir(parents=True)
    (vault_root / "archive").mkdir(parents=True)
    return str(vault_root)


def seed_file(vault_root: str, relative_path: str, content: str) -> None:
    """Write a file directly (bypassing vault module) to pre-seed test state."""
    full_path = os.path.join(vault_root, relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as fh:
        fh.write(content)


def frontmatter_block(metadata: dict) -> str:
    """Build a minimal YAML frontmatter block string from a plain dict."""
    import yaml  # available via pyyaml in requirements.txt

    return f"---\n{yaml.dump(metadata, default_flow_style=False)}---\n"


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------

class TestWriteFile:
    """Tests for write_file."""

    def test_creates_file_with_correct_content(self, tmp_path):
        """write_file must create the file and store exactly the supplied content."""
        vault_root = make_vault(tmp_path)
        write_file(vault_root, "notes/hello.md", "# Hello World\n")

        full_path = os.path.join(vault_root, "notes", "hello.md")
        assert os.path.isfile(full_path), "file should exist after write_file"
        with open(full_path, "r", encoding="utf-8") as fh:
            assert fh.read() == "# Hello World\n"

    def test_write_is_atomic_temp_then_replace(self, tmp_path):
        """
        Atomicity: the final file must exist and no leftover temp file should
        remain next to it after a successful write_file call.
        """
        vault_root = make_vault(tmp_path)
        write_file(vault_root, "notes/atomic.md", "content")

        notes_dir = os.path.join(vault_root, "notes")
        files = os.listdir(notes_dir)
        # Only the target file; no .tmp / partial artefacts
        assert "atomic.md" in files
        temp_files = [f for f in files if f != "atomic.md"]
        assert temp_files == [], f"unexpected temp files left behind: {temp_files}"

    def test_overwrites_existing_file(self, tmp_path):
        """write_file called twice on the same path must store the latest content."""
        vault_root = make_vault(tmp_path)
        write_file(vault_root, "notes/overwrite.md", "original content")
        write_file(vault_root, "notes/overwrite.md", "updated content")

        full_path = os.path.join(vault_root, "notes", "overwrite.md")
        with open(full_path, "r", encoding="utf-8") as fh:
            assert fh.read() == "updated content"

    def test_creates_intermediate_directories(self, tmp_path):
        """write_file should create missing parent directories automatically."""
        vault_root = make_vault(tmp_path)
        write_file(vault_root, "deep/nested/dir/note.md", "nested")

        full_path = os.path.join(vault_root, "deep", "nested", "dir", "note.md")
        assert os.path.isfile(full_path)


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------

class TestReadFile:
    """Tests for read_file."""

    def test_returns_file_content(self, tmp_path):
        """read_file must return the exact bytes that were written."""
        vault_root = make_vault(tmp_path)
        seed_file(vault_root, "notes/read_me.md", "some content\nline two\n")

        result = read_file(vault_root, "notes/read_me.md")
        assert result == "some content\nline two\n"

    def test_raises_file_not_found_for_missing_file(self, tmp_path):
        """read_file must raise FileNotFoundError when the path does not exist."""
        vault_root = make_vault(tmp_path)

        with pytest.raises(FileNotFoundError):
            read_file(vault_root, "notes/does_not_exist.md")

    def test_returns_empty_string_for_empty_file(self, tmp_path):
        """read_file on a zero-byte file must return an empty string, not None."""
        vault_root = make_vault(tmp_path)
        seed_file(vault_root, "notes/empty.md", "")

        result = read_file(vault_root, "notes/empty.md")
        assert result == ""

    def test_preserves_unicode_content(self, tmp_path):
        """read_file must handle multi-byte UTF-8 characters correctly."""
        vault_root = make_vault(tmp_path)
        unicode_content = "# タイトル\n\nBody: emoji \U0001f4dd\n"
        seed_file(vault_root, "notes/unicode.md", unicode_content)

        assert read_file(vault_root, "notes/unicode.md") == unicode_content


# ---------------------------------------------------------------------------
# move_file
# ---------------------------------------------------------------------------

class TestMoveFile:
    """Tests for move_file."""

    def test_moves_file_between_existing_folders(self, tmp_path):
        """move_file must relocate the file and remove it from the source."""
        vault_root = make_vault(tmp_path)
        seed_file(vault_root, "notes/to_move.md", "moving along")

        move_file(vault_root, "notes/to_move.md", "archive/to_move.md")

        src = os.path.join(vault_root, "notes", "to_move.md")
        dst = os.path.join(vault_root, "archive", "to_move.md")
        assert not os.path.exists(src), "source must not exist after move"
        assert os.path.isfile(dst), "destination must exist after move"

    def test_moved_file_content_is_preserved(self, tmp_path):
        """move_file must not corrupt file content during the operation."""
        vault_root = make_vault(tmp_path)
        original = "# Important Note\n\nDo not lose me."
        seed_file(vault_root, "notes/preserve.md", original)

        move_file(vault_root, "notes/preserve.md", "archive/preserve.md")

        dst = os.path.join(vault_root, "archive", "preserve.md")
        with open(dst, "r", encoding="utf-8") as fh:
            assert fh.read() == original

    def test_creates_destination_directory_if_missing(self, tmp_path):
        """move_file must create any missing parent directories for the destination."""
        vault_root = make_vault(tmp_path)
        seed_file(vault_root, "notes/new_dest.md", "content")

        # "new_folder" does not exist yet
        move_file(vault_root, "notes/new_dest.md", "new_folder/new_dest.md")

        dst = os.path.join(vault_root, "new_folder", "new_dest.md")
        assert os.path.isfile(dst)


# ---------------------------------------------------------------------------
# list_folder
# ---------------------------------------------------------------------------

class TestListFolder:
    """Tests for list_folder."""

    def test_returns_only_md_files(self, tmp_path):
        """list_folder must include .md files and exclude all other extensions."""
        vault_root = make_vault(tmp_path)
        seed_file(vault_root, "notes/alpha.md", "")
        seed_file(vault_root, "notes/beta.md", "")
        seed_file(vault_root, "notes/readme.txt", "")
        seed_file(vault_root, "notes/config.yaml", "")

        result = list_folder(vault_root, "notes")
        result_names = sorted(result)

        assert result_names == ["alpha.md", "beta.md"], (
            f"expected only .md files, got {result_names}"
        )

    def test_returns_empty_list_for_empty_folder(self, tmp_path):
        """list_folder on a folder with no .md files must return an empty list."""
        vault_root = make_vault(tmp_path)
        # notes/ exists but has no files

        result = list_folder(vault_root, "notes")
        assert result == []

    def test_returns_empty_list_when_only_non_md_files_present(self, tmp_path):
        """list_folder must return [] when all files have non-.md extensions."""
        vault_root = make_vault(tmp_path)
        seed_file(vault_root, "notes/image.png", "")
        seed_file(vault_root, "notes/data.json", "")

        result = list_folder(vault_root, "notes")
        assert result == []

    def test_returns_all_md_files_in_folder(self, tmp_path):
        """list_folder must return every .md file present in the folder."""
        vault_root = make_vault(tmp_path)
        names = [f"note_{i}.md" for i in range(5)]
        for name in names:
            seed_file(vault_root, f"notes/{name}", "")

        result = list_folder(vault_root, "notes")
        assert sorted(result) == sorted(names)


# ---------------------------------------------------------------------------
# read_frontmatter_file
# ---------------------------------------------------------------------------

class TestReadFrontmatterFile:
    """Tests for read_frontmatter_file."""

    def test_returns_parsed_metadata_and_body(self, tmp_path):
        """read_frontmatter_file must parse YAML front matter and return body text."""
        vault_root = make_vault(tmp_path)
        raw = (
            "---\n"
            "title: My Note\n"
            "tags:\n"
            "  - python\n"
            "  - testing\n"
            "---\n"
            "This is the body.\n"
        )
        seed_file(vault_root, "notes/fm_note.md", raw)

        metadata, body = read_frontmatter_file(vault_root, "notes/fm_note.md")

        assert metadata["title"] == "My Note"
        assert metadata["tags"] == ["python", "testing"]
        assert body.strip() == "This is the body."

    def test_metadata_is_dict(self, tmp_path):
        """The metadata return value must always be a dict."""
        vault_root = make_vault(tmp_path)
        raw = "---\nkey: value\n---\nbody\n"
        seed_file(vault_root, "notes/dict_check.md", raw)

        metadata, _ = read_frontmatter_file(vault_root, "notes/dict_check.md")
        assert isinstance(metadata, dict)

    def test_body_is_string(self, tmp_path):
        """The body return value must always be a str."""
        vault_root = make_vault(tmp_path)
        raw = "---\nkey: value\n---\nbody text\n"
        seed_file(vault_root, "notes/str_check.md", raw)

        _, body = read_frontmatter_file(vault_root, "notes/str_check.md")
        assert isinstance(body, str)

    def test_handles_empty_body(self, tmp_path):
        """read_frontmatter_file must succeed when the body after frontmatter is empty."""
        vault_root = make_vault(tmp_path)
        raw = "---\ntitle: No Body\n---\n"
        seed_file(vault_root, "notes/no_body.md", raw)

        metadata, body = read_frontmatter_file(vault_root, "notes/no_body.md")
        assert metadata["title"] == "No Body"
        assert body.strip() == ""

    def test_handles_numeric_and_boolean_metadata(self, tmp_path):
        """YAML types (int, bool) in frontmatter must be returned with correct Python types."""
        vault_root = make_vault(tmp_path)
        raw = "---\ncount: 42\nactive: true\n---\nbody\n"
        seed_file(vault_root, "notes/types.md", raw)

        metadata, _ = read_frontmatter_file(vault_root, "notes/types.md")
        assert metadata["count"] == 42
        assert metadata["active"] is True


# ---------------------------------------------------------------------------
# write_frontmatter_file
# ---------------------------------------------------------------------------

class TestWriteFrontmatterFile:
    """Tests for write_frontmatter_file."""

    def test_creates_file_with_frontmatter_block(self, tmp_path):
        """write_frontmatter_file must produce a file that starts with --- delimiters."""
        vault_root = make_vault(tmp_path)
        write_frontmatter_file(
            vault_root,
            "notes/new_fm.md",
            {"title": "Created", "draft": False},
            "Body text here.\n",
        )

        full_path = os.path.join(vault_root, "notes", "new_fm.md")
        assert os.path.isfile(full_path)
        with open(full_path, "r", encoding="utf-8") as fh:
            content = fh.read()

        assert content.startswith("---"), "file must open with YAML frontmatter delimiter"
        assert "title:" in content
        assert "Body text here." in content

    def test_metadata_keys_appear_in_file(self, tmp_path):
        """Every key supplied in metadata must appear in the written file."""
        vault_root = make_vault(tmp_path)
        metadata = {"author": "Alice", "version": 3, "published": True}
        write_frontmatter_file(vault_root, "notes/keys.md", metadata, "body\n")

        full_path = os.path.join(vault_root, "notes", "keys.md")
        with open(full_path, "r", encoding="utf-8") as fh:
            content = fh.read()

        assert "author:" in content
        assert "version:" in content
        assert "published:" in content

    def test_body_appears_after_closing_delimiter(self, tmp_path):
        """The body text must appear after the closing --- delimiter."""
        vault_root = make_vault(tmp_path)
        write_frontmatter_file(
            vault_root, "notes/body_pos.md", {"k": "v"}, "The body content.\n"
        )

        full_path = os.path.join(vault_root, "notes", "body_pos.md")
        with open(full_path, "r", encoding="utf-8") as fh:
            content = fh.read()

        # Find the second occurrence of ---
        first_delim = content.index("---")
        closing_delim = content.index("---", first_delim + 3)
        body_section = content[closing_delim:]
        assert "The body content." in body_section


# ---------------------------------------------------------------------------
# Roundtrip: write_frontmatter_file -> read_frontmatter_file
# ---------------------------------------------------------------------------

class TestFrontmatterRoundtrip:
    """Roundtrip tests ensuring write followed by read recovers identical data."""

    def test_simple_roundtrip(self, tmp_path):
        """Writing then reading frontmatter must recover the original metadata and body."""
        vault_root = make_vault(tmp_path)
        original_metadata = {"title": "Roundtrip Note", "priority": 1}
        original_body = "This is the roundtrip body.\n"

        write_frontmatter_file(
            vault_root, "notes/roundtrip.md", original_metadata, original_body
        )
        recovered_metadata, recovered_body = read_frontmatter_file(
            vault_root, "notes/roundtrip.md"
        )

        assert recovered_metadata["title"] == original_metadata["title"]
        assert recovered_metadata["priority"] == original_metadata["priority"]
        assert recovered_body.strip() == original_body.strip()

    def test_roundtrip_with_list_values(self, tmp_path):
        """List values in metadata must survive a write-read roundtrip intact."""
        vault_root = make_vault(tmp_path)
        metadata = {"tags": ["alpha", "beta", "gamma"], "title": "List Test"}
        body = "List roundtrip body.\n"

        write_frontmatter_file(vault_root, "notes/list_rt.md", metadata, body)
        recovered_metadata, _ = read_frontmatter_file(vault_root, "notes/list_rt.md")

        assert recovered_metadata["tags"] == ["alpha", "beta", "gamma"]

    def test_roundtrip_with_multiline_body(self, tmp_path):
        """Multiline body text must survive a write-read roundtrip without truncation."""
        vault_root = make_vault(tmp_path)
        metadata = {"title": "Multiline"}
        body = "Line one.\nLine two.\nLine three.\n"

        write_frontmatter_file(vault_root, "notes/multiline.md", metadata, body)
        _, recovered_body = read_frontmatter_file(vault_root, "notes/multiline.md")

        assert "Line one." in recovered_body
        assert "Line two." in recovered_body
        assert "Line three." in recovered_body

    def test_roundtrip_with_special_characters_in_body(self, tmp_path):
        """Special characters and Unicode in body must survive roundtrip unchanged."""
        vault_root = make_vault(tmp_path)
        metadata = {"title": "Unicode"}
        body = "Special: <>&\"'\nEmoji: \U0001f4dd\nJapanese: \u65e5\u672c\u8a9e\n"

        write_frontmatter_file(vault_root, "notes/special.md", metadata, body)
        _, recovered_body = read_frontmatter_file(vault_root, "notes/special.md")

        assert "Special: <>&\"'" in recovered_body
        assert "\U0001f4dd" in recovered_body
        assert "\u65e5\u672c\u8a9e" in recovered_body

    def test_roundtrip_preserves_boolean_metadata(self, tmp_path):
        """Boolean metadata values must survive roundtrip as Python bools."""
        vault_root = make_vault(tmp_path)
        metadata = {"published": True, "draft": False, "title": "Booleans"}
        body = "Boolean roundtrip.\n"

        write_frontmatter_file(vault_root, "notes/booleans.md", metadata, body)
        recovered_metadata, _ = read_frontmatter_file(vault_root, "notes/booleans.md")

        assert recovered_metadata["published"] is True
        assert recovered_metadata["draft"] is False

    def test_roundtrip_empty_metadata(self, tmp_path):
        """An empty metadata dict must be accepted and round-trip to an empty dict."""
        vault_root = make_vault(tmp_path)
        write_frontmatter_file(vault_root, "notes/no_meta.md", {}, "Just a body.\n")
        recovered_metadata, recovered_body = read_frontmatter_file(
            vault_root, "notes/no_meta.md"
        )

        assert isinstance(recovered_metadata, dict)
        assert "Just a body." in recovered_body
