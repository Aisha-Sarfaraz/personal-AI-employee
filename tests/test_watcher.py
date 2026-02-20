"""
Comprehensive tests for watcher modules.

Covers:
  - BaseWatcher (src.watchers.base_watcher):
      * ABC cannot be instantiated directly
      * create_action_file creates .md in Inbox/ with required frontmatter fields
      * save_state persists _processed_ids to JSON
      * load_state restores _processed_ids from JSON
      * Dedup: same item ID not processed twice within a session
      * State persistence: save, new instance, load, verify IDs still tracked

  - FilesystemWatcher (src.watchers.filesystem_watcher):
      * Detects new text files in Watch/ via check_for_updates (directory scan)
      * Creates correct Inbox .md file with content from Watch/ file
      * Inbox file has correct frontmatter fields (source: filesystem_watcher)
      * Binary file detected -> Inbox item with type:unknown, body "[Binary file — cannot display]"
      * Empty file -> type:unknown
      * Dedup: same file not processed twice across check_for_updates calls
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
import yaml

# Ensure project root is on sys.path so `src` is importable regardless of
# how pytest is invoked.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.watchers.base_watcher import BaseWatcher
from src.watchers.filesystem_watcher import FilesystemWatcher


# ---------------------------------------------------------------------------
# Vault structure helpers
# ---------------------------------------------------------------------------

_VAULT_DIRS = ("Inbox", "Watch", "state")

_REQUIRED_FRONTMATTER_KEYS = {"id", "type", "source", "timestamp", "priority", "status"}


def _make_vault(tmp_path: Path) -> Path:
    """Create a minimal vault directory and return its root Path."""
    vault_root = tmp_path / "vault"
    for folder in _VAULT_DIRS:
        (vault_root / folder).mkdir(parents=True, exist_ok=True)
    return vault_root


def _parse_frontmatter(file_path: Path) -> tuple[dict, str]:
    """
    Parse YAML frontmatter delimited by ``---`` lines from *file_path*.

    Returns:
        (metadata_dict, body_string). metadata is empty dict if no frontmatter.
    """
    content = file_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    try:
        metadata = yaml.safe_load(parts[1].strip()) or {}
    except yaml.YAMLError:
        return {}, content

    body = parts[2].lstrip("\n")
    return metadata, body


def _list_inbox_files(vault_root: Path) -> list[Path]:
    """Return all .md files in Inbox/ under *vault_root*."""
    inbox = vault_root / "Inbox"
    if not inbox.is_dir():
        return []
    return sorted(inbox.glob("*.md"))


def _seed_text_file(directory: Path, name: str, content: str) -> Path:
    """Write a UTF-8 text file into *directory*. Returns the created Path."""
    path = directory / name
    path.write_text(content, encoding="utf-8")
    return path


def _seed_binary_file(directory: Path, name: str) -> Path:
    """Write a binary file (null bytes) into *directory*. Returns the created Path."""
    path = directory / name
    path.write_bytes(b"\x00\x01\x02\x03\xff\xfe")
    return path


# ---------------------------------------------------------------------------
# Concrete subclass for BaseWatcher (minimal implementation for testing)
# ---------------------------------------------------------------------------

class _ConcreteWatcher(BaseWatcher):
    """
    Minimal concrete subclass used only for testing BaseWatcher's non-abstract
    behaviour. check_for_updates always returns an empty list; tests that need
    items inject them directly.
    """

    def check_for_updates(self) -> list[dict]:  # type: ignore[override]
        return []


# ---------------------------------------------------------------------------
# BaseWatcher tests
# ---------------------------------------------------------------------------

class TestBaseWatcherCannotBeInstantiated:
    """BaseWatcher is an abstract base class and must not be directly instantiable."""

    def test_abc_raises_type_error_on_direct_instantiation(self):
        """Attempting to instantiate BaseWatcher must raise TypeError."""
        with pytest.raises(TypeError):
            BaseWatcher()  # type: ignore[abstract]


class TestBaseWatcherCreateActionFile:
    """Tests for BaseWatcher.create_action_file."""

    def test_creates_md_file_in_inbox(self, tmp_path):
        """create_action_file must create a .md file inside the Inbox/ directory."""
        vault_root = _make_vault(tmp_path)
        watcher = _ConcreteWatcher()
        item = {
            "id": "test-001",
            "type": "document",
            "source": "test_watcher",
            "body": "Some document content.",
        }

        created_path = watcher.create_action_file(str(vault_root), item)

        assert created_path, "create_action_file must return a non-empty path string"
        assert os.path.isfile(created_path), f"created file must exist at {created_path}"
        assert created_path.endswith(".md"), "created file must have .md extension"
        assert "Inbox" in created_path, "created file must reside inside the Inbox directory"

    def test_created_file_has_required_frontmatter_keys(self, tmp_path):
        """The .md file written by create_action_file must contain all required frontmatter keys."""
        vault_root = _make_vault(tmp_path)
        watcher = _ConcreteWatcher()
        item = {
            "id": "test-002",
            "type": "task",
            "source": "unit_test",
            "body": "Task body.",
        }

        created_path = watcher.create_action_file(str(vault_root), item)
        metadata, _ = _parse_frontmatter(Path(created_path))

        missing = _REQUIRED_FRONTMATTER_KEYS - metadata.keys()
        assert not missing, (
            f"Frontmatter is missing required keys: {missing}. Found: {set(metadata.keys())}"
        )

    def test_frontmatter_id_matches_item_id(self, tmp_path):
        """The frontmatter 'id' field must match the id supplied in the item dict."""
        vault_root = _make_vault(tmp_path)
        watcher = _ConcreteWatcher()
        item = {"id": "unique-id-xyz", "type": "general", "source": "test", "body": ""}

        created_path = watcher.create_action_file(str(vault_root), item)
        metadata, _ = _parse_frontmatter(Path(created_path))

        assert str(metadata.get("id")) == "unique-id-xyz"

    def test_frontmatter_source_matches_item_source(self, tmp_path):
        """The frontmatter 'source' field must match the source supplied in the item dict."""
        vault_root = _make_vault(tmp_path)
        watcher = _ConcreteWatcher()
        item = {"id": "src-test-001", "type": "general", "source": "my_custom_source", "body": ""}

        created_path = watcher.create_action_file(str(vault_root), item)
        metadata, _ = _parse_frontmatter(Path(created_path))

        assert metadata.get("source") == "my_custom_source"

    def test_frontmatter_type_is_present_and_string(self, tmp_path):
        """The frontmatter 'type' field must be a non-empty string."""
        vault_root = _make_vault(tmp_path)
        watcher = _ConcreteWatcher()
        item = {"id": "type-test-001", "type": "financial", "source": "bank", "body": ""}

        created_path = watcher.create_action_file(str(vault_root), item)
        metadata, _ = _parse_frontmatter(Path(created_path))

        assert isinstance(metadata.get("type"), str)
        assert metadata["type"], "type must not be empty"

    def test_frontmatter_timestamp_is_present(self, tmp_path):
        """The frontmatter 'timestamp' field must be present and non-empty."""
        vault_root = _make_vault(tmp_path)
        watcher = _ConcreteWatcher()
        item = {"id": "ts-test-001", "type": "general", "source": "test", "body": ""}

        created_path = watcher.create_action_file(str(vault_root), item)
        metadata, _ = _parse_frontmatter(Path(created_path))

        assert metadata.get("timestamp"), "timestamp must be present and non-empty"

    def test_frontmatter_priority_is_present(self, tmp_path):
        """The frontmatter 'priority' field must be present."""
        vault_root = _make_vault(tmp_path)
        watcher = _ConcreteWatcher()
        item = {"id": "pri-test-001", "type": "general", "source": "test", "body": ""}

        created_path = watcher.create_action_file(str(vault_root), item)
        metadata, _ = _parse_frontmatter(Path(created_path))

        assert "priority" in metadata

    def test_frontmatter_status_is_present(self, tmp_path):
        """The frontmatter 'status' field must be present."""
        vault_root = _make_vault(tmp_path)
        watcher = _ConcreteWatcher()
        item = {"id": "stat-test-001", "type": "general", "source": "test", "body": ""}

        created_path = watcher.create_action_file(str(vault_root), item)
        metadata, _ = _parse_frontmatter(Path(created_path))

        assert "status" in metadata

    def test_body_content_appears_in_file(self, tmp_path):
        """The item's body content must appear in the written .md file."""
        vault_root = _make_vault(tmp_path)
        watcher = _ConcreteWatcher()
        item = {
            "id": "body-test-001",
            "type": "document",
            "source": "test",
            "body": "This is the expected body content for testing.",
        }

        created_path = watcher.create_action_file(str(vault_root), item)
        _, body = _parse_frontmatter(Path(created_path))

        assert "This is the expected body content for testing." in body

    def test_returns_absolute_path_string(self, tmp_path):
        """create_action_file must return an absolute path as a str."""
        vault_root = _make_vault(tmp_path)
        watcher = _ConcreteWatcher()
        item = {"id": "path-test-001", "type": "general", "source": "test", "body": ""}

        result = watcher.create_action_file(str(vault_root), item)

        assert isinstance(result, str), "must return a str"
        assert os.path.isabs(result), "returned path must be absolute"


class TestBaseWatcherSaveState:
    """Tests for BaseWatcher.save_state."""

    def test_save_state_creates_json_file(self, tmp_path):
        """save_state must create a JSON file at the configured state_file path."""
        vault_root = _make_vault(tmp_path)
        state_file = str(vault_root / "state" / "watcher_state.json")

        watcher = _ConcreteWatcher()
        watcher._state_file = state_file
        watcher._processed_ids = {"item-001", "item-002"}

        watcher.save_state()

        assert os.path.isfile(state_file), "state file must exist after save_state"

    def test_save_state_persists_processed_ids(self, tmp_path):
        """save_state must write all _processed_ids to the JSON file."""
        vault_root = _make_vault(tmp_path)
        state_file = str(vault_root / "state" / "watcher_state.json")

        watcher = _ConcreteWatcher()
        watcher._state_file = state_file
        watcher._processed_ids = {"alpha", "beta", "gamma"}

        watcher.save_state()

        with open(state_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        # The JSON may store IDs as a list or under a key — extract all string values
        if isinstance(data, list):
            stored_ids = set(data)
        elif isinstance(data, dict):
            # Support {"processed_ids": [...]} or any top-level list value
            all_values = []
            for v in data.values():
                if isinstance(v, list):
                    all_values.extend(v)
                elif isinstance(v, str):
                    all_values.append(v)
            stored_ids = set(all_values)
        else:
            pytest.fail(f"Unexpected JSON structure: {type(data)}")

        assert {"alpha", "beta", "gamma"}.issubset(stored_ids), (
            f"Expected IDs not found in state file. Stored: {stored_ids}"
        )

    def test_save_state_overwrites_previous_state(self, tmp_path):
        """A second save_state call must replace any previously saved state."""
        vault_root = _make_vault(tmp_path)
        state_file = str(vault_root / "state" / "watcher_state.json")

        watcher = _ConcreteWatcher()
        watcher._state_file = state_file

        watcher._processed_ids = {"old-id-1", "old-id-2"}
        watcher.save_state()

        watcher._processed_ids = {"new-id-1"}
        watcher.save_state()

        raw = Path(state_file).read_text(encoding="utf-8")
        # old IDs must not appear
        assert "old-id-1" not in raw, "previous IDs must be replaced by second save"
        assert "old-id-2" not in raw, "previous IDs must be replaced by second save"
        assert "new-id-1" in raw


class TestBaseWatcherLoadState:
    """Tests for BaseWatcher.load_state."""

    def _write_state(self, state_file: str, ids: list[str]) -> None:
        """Helper: write a minimal state JSON file matching the expected format."""
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        # Try both formats: plain list and {"processed_ids": [...]}
        with open(state_file, "w", encoding="utf-8") as fh:
            json.dump({"processed_ids": ids}, fh)

    def test_load_state_restores_processed_ids(self, tmp_path):
        """load_state must populate _processed_ids from the JSON state file."""
        vault_root = _make_vault(tmp_path)
        state_file = str(vault_root / "state" / "watcher_state.json")
        self._write_state(state_file, ["id-aaa", "id-bbb", "id-ccc"])

        watcher = _ConcreteWatcher()
        watcher._state_file = state_file
        watcher._processed_ids = set()  # start empty

        watcher.load_state()

        assert "id-aaa" in watcher._processed_ids
        assert "id-bbb" in watcher._processed_ids
        assert "id-ccc" in watcher._processed_ids

    def test_load_state_with_missing_file_does_not_raise(self, tmp_path):
        """load_state on a nonexistent state file must not raise any exception."""
        vault_root = _make_vault(tmp_path)
        state_file = str(vault_root / "state" / "no_such_file.json")

        watcher = _ConcreteWatcher()
        watcher._state_file = state_file
        watcher._processed_ids = set()

        # Must not raise
        watcher.load_state()

        # processed_ids may remain empty or be initialised to empty set
        assert isinstance(watcher._processed_ids, set)

    def test_load_state_merges_or_replaces_existing_ids(self, tmp_path):
        """load_state with a populated state file results in those IDs being tracked."""
        vault_root = _make_vault(tmp_path)
        state_file = str(vault_root / "state" / "watcher_state.json")
        self._write_state(state_file, ["persisted-id-1", "persisted-id-2"])

        watcher = _ConcreteWatcher()
        watcher._state_file = state_file
        watcher._processed_ids = set()

        watcher.load_state()

        assert "persisted-id-1" in watcher._processed_ids
        assert "persisted-id-2" in watcher._processed_ids

    def test_load_state_returns_empty_set_for_empty_state_file(self, tmp_path):
        """load_state on a state file with an empty ID list yields an empty set."""
        vault_root = _make_vault(tmp_path)
        state_file = str(vault_root / "state" / "watcher_state.json")
        self._write_state(state_file, [])

        watcher = _ConcreteWatcher()
        watcher._state_file = state_file
        watcher._processed_ids = set()

        watcher.load_state()

        assert isinstance(watcher._processed_ids, set)
        assert len(watcher._processed_ids) == 0


class TestBaseWatcherDedup:
    """Tests for in-session deduplication via _processed_ids."""

    def test_processed_ids_starts_as_set(self, tmp_path):
        """A freshly constructed watcher must have _processed_ids as a set."""
        watcher = _ConcreteWatcher()
        assert isinstance(watcher._processed_ids, set)

    def test_same_item_id_not_duplicated_in_processed_ids(self, tmp_path):
        """Adding the same item ID twice must not result in duplicates in _processed_ids."""
        watcher = _ConcreteWatcher()
        watcher._processed_ids.add("dup-id")
        watcher._processed_ids.add("dup-id")

        assert watcher._processed_ids.count("dup-id") == 1 if hasattr(
            watcher._processed_ids, "count"
        ) else len([x for x in watcher._processed_ids if x == "dup-id"]) == 1

    def test_create_action_file_marks_id_as_processed(self, tmp_path):
        """After create_action_file, the item ID must appear in _processed_ids."""
        vault_root = _make_vault(tmp_path)
        watcher = _ConcreteWatcher()
        item = {"id": "mark-processed-001", "type": "general", "source": "test", "body": ""}

        watcher.create_action_file(str(vault_root), item)

        assert "mark-processed-001" in watcher._processed_ids

    def test_item_already_in_processed_ids_skipped_on_second_call(self, tmp_path):
        """
        If an item's id is already in _processed_ids, create_action_file must
        either skip creation or return None / empty string — ensuring no duplicate
        Inbox files are created.
        """
        vault_root = _make_vault(tmp_path)
        watcher = _ConcreteWatcher()
        item = {"id": "dedup-001", "type": "general", "source": "test", "body": "First"}

        # First call: creates the file
        first_result = watcher.create_action_file(str(vault_root), item)
        assert first_result, "First call must create the file"

        inbox_files_after_first = _list_inbox_files(vault_root)

        # Second call with same item: must not create a second Inbox file
        second_result = watcher.create_action_file(str(vault_root), item)

        inbox_files_after_second = _list_inbox_files(vault_root)

        assert len(inbox_files_after_second) == len(inbox_files_after_first), (
            "A second create_action_file call for the same ID must not produce an additional file"
        )


class TestBaseWatcherStatePersistence:
    """Roundtrip tests: save_state -> new instance -> load_state -> IDs still tracked."""

    def test_save_new_instance_load_roundtrip(self, tmp_path):
        """
        IDs recorded by one watcher instance must be recoverable by a fresh
        instance after save_state / load_state.
        """
        vault_root = _make_vault(tmp_path)
        state_file = str(vault_root / "state" / "roundtrip_state.json")

        # First instance: record some IDs and save
        watcher_a = _ConcreteWatcher()
        watcher_a._state_file = state_file
        watcher_a._processed_ids = {"roundtrip-id-1", "roundtrip-id-2", "roundtrip-id-3"}
        watcher_a.save_state()

        # Second (fresh) instance: load and verify
        watcher_b = _ConcreteWatcher()
        watcher_b._state_file = state_file
        watcher_b._processed_ids = set()
        watcher_b.load_state()

        assert "roundtrip-id-1" in watcher_b._processed_ids
        assert "roundtrip-id-2" in watcher_b._processed_ids
        assert "roundtrip-id-3" in watcher_b._processed_ids

    def test_create_action_file_then_persist_and_reload(self, tmp_path):
        """
        IDs added via create_action_file must survive a save/load cycle on a new
        instance, effectively preventing reprocessing across restarts.
        """
        vault_root = _make_vault(tmp_path)
        state_file = str(vault_root / "state" / "persist_test.json")

        # Instance A: process items, save
        watcher_a = _ConcreteWatcher()
        watcher_a._state_file = state_file
        items = [
            {"id": "persist-item-1", "type": "general", "source": "test", "body": "one"},
            {"id": "persist-item-2", "type": "general", "source": "test", "body": "two"},
        ]
        for item in items:
            watcher_a.create_action_file(str(vault_root), item)
        watcher_a.save_state()

        # Instance B: load state and confirm IDs present
        watcher_b = _ConcreteWatcher()
        watcher_b._state_file = state_file
        watcher_b._processed_ids = set()
        watcher_b.load_state()

        assert "persist-item-1" in watcher_b._processed_ids
        assert "persist-item-2" in watcher_b._processed_ids


class TestBaseWatcherPollInterval:
    """Tests for poll_interval attribute."""

    def test_poll_interval_is_integer(self):
        """poll_interval must be an integer."""
        watcher = _ConcreteWatcher()
        assert isinstance(watcher.poll_interval, int)

    def test_poll_interval_is_positive(self):
        """poll_interval must be a positive number (> 0)."""
        watcher = _ConcreteWatcher()
        assert watcher.poll_interval > 0

    def test_poll_interval_can_be_set(self):
        """poll_interval must be settable to a custom value."""
        watcher = _ConcreteWatcher()
        watcher.poll_interval = 30
        assert watcher.poll_interval == 30


class TestBaseWatcherStateFileAttribute:
    """Tests for _state_file attribute."""

    def test_state_file_attribute_exists(self):
        """_state_file must be present on a freshly constructed watcher."""
        watcher = _ConcreteWatcher()
        assert hasattr(watcher, "_state_file"), "_state_file attribute must exist"

    def test_state_file_is_string(self):
        """_state_file must be a str (file path)."""
        watcher = _ConcreteWatcher()
        assert isinstance(watcher._state_file, str)

    def test_state_file_can_be_overridden(self, tmp_path):
        """_state_file can be overridden to a custom path."""
        watcher = _ConcreteWatcher()
        custom_path = str(tmp_path / "custom_state.json")
        watcher._state_file = custom_path
        assert watcher._state_file == custom_path


# ---------------------------------------------------------------------------
# FilesystemWatcher tests
# ---------------------------------------------------------------------------

class TestFilesystemWatcherCheckForUpdates:
    """Tests for FilesystemWatcher.check_for_updates (directory scan path)."""

    def test_detects_new_text_file_in_watch_directory(self, tmp_path):
        """
        Placing a text file in Watch/ and calling check_for_updates must return
        at least one item referencing that file.
        """
        vault_root = _make_vault(tmp_path)
        watch_dir = vault_root / "Watch"
        _seed_text_file(watch_dir, "hello.txt", "Hello, watcher!")

        watcher = FilesystemWatcher(vault_root=str(vault_root))
        items = watcher.check_for_updates()

        assert len(items) >= 1, "check_for_updates must return at least one item"
        filenames = [os.path.basename(item.get("path", item.get("name", ""))) for item in items]
        assert any("hello.txt" in name for name in filenames), (
            f"'hello.txt' not found in returned items. Got: {filenames}"
        )

    def test_returns_list_of_dicts(self, tmp_path):
        """check_for_updates must always return a list of dicts."""
        vault_root = _make_vault(tmp_path)
        _seed_text_file(vault_root / "Watch", "sample.txt", "content")

        watcher = FilesystemWatcher(vault_root=str(vault_root))
        items = watcher.check_for_updates()

        assert isinstance(items, list), "check_for_updates must return a list"
        for item in items:
            assert isinstance(item, dict), f"each item must be a dict, got {type(item)}"

    def test_returns_empty_list_for_empty_watch_directory(self, tmp_path):
        """check_for_updates on an empty Watch/ directory must return an empty list."""
        vault_root = _make_vault(tmp_path)
        # Watch/ exists but is empty

        watcher = FilesystemWatcher(vault_root=str(vault_root))
        items = watcher.check_for_updates()

        assert items == [], f"expected empty list for empty Watch/, got {items}"

    def test_multiple_files_all_detected(self, tmp_path):
        """All files present in Watch/ must be included in check_for_updates results."""
        vault_root = _make_vault(tmp_path)
        watch_dir = vault_root / "Watch"
        file_names = ["alpha.txt", "beta.md", "gamma.log"]
        for name in file_names:
            _seed_text_file(watch_dir, name, f"Content of {name}")

        watcher = FilesystemWatcher(vault_root=str(vault_root))
        items = watcher.check_for_updates()

        detected_names = [os.path.basename(item.get("path", item.get("name", ""))) for item in items]
        for name in file_names:
            assert any(name in d for d in detected_names), (
                f"Expected '{name}' to be detected. Detected: {detected_names}"
            )

    def test_item_dict_contains_path_or_name_key(self, tmp_path):
        """Each dict returned by check_for_updates must contain a 'path' or 'name' key."""
        vault_root = _make_vault(tmp_path)
        _seed_text_file(vault_root / "Watch", "test_file.txt", "data")

        watcher = FilesystemWatcher(vault_root=str(vault_root))
        items = watcher.check_for_updates()

        assert len(items) >= 1
        for item in items:
            has_path_info = "path" in item or "name" in item
            assert has_path_info, f"item must contain 'path' or 'name'. Got keys: {set(item.keys())}"


class TestFilesystemWatcherCreateInboxFile:
    """Tests for the Inbox .md file created by FilesystemWatcher processing."""

    def test_creates_inbox_md_file_for_text_file(self, tmp_path):
        """
        Processing a text file from Watch/ must produce exactly one .md file
        in the Inbox/ directory.
        """
        vault_root = _make_vault(tmp_path)
        _seed_text_file(vault_root / "Watch", "note.txt", "Note content here.")

        watcher = FilesystemWatcher(vault_root=str(vault_root))
        items = watcher.check_for_updates()

        assert items, "check_for_updates must return items"
        for item in items:
            watcher.create_action_file(str(vault_root), item)

        inbox_files = _list_inbox_files(vault_root)
        assert len(inbox_files) >= 1, "At least one .md file must be created in Inbox/"

    def test_inbox_file_contains_source_text_content(self, tmp_path):
        """The Inbox .md file must include the content of the original Watch/ file."""
        vault_root = _make_vault(tmp_path)
        expected_content = "This is the unique text content that must appear in Inbox."
        _seed_text_file(vault_root / "Watch", "content_file.txt", expected_content)

        watcher = FilesystemWatcher(vault_root=str(vault_root))
        items = watcher.check_for_updates()
        for item in items:
            watcher.create_action_file(str(vault_root), item)

        inbox_files = _list_inbox_files(vault_root)
        assert inbox_files, "Inbox must contain at least one file"

        all_content = " ".join(f.read_text(encoding="utf-8") for f in inbox_files)
        assert expected_content in all_content, (
            "Original file content must appear in the created Inbox .md file"
        )

    def test_inbox_file_has_filesystem_watcher_source_in_frontmatter(self, tmp_path):
        """
        The Inbox .md frontmatter must have source set to 'filesystem_watcher'
        (or a string containing 'filesystem').
        """
        vault_root = _make_vault(tmp_path)
        _seed_text_file(vault_root / "Watch", "source_check.txt", "content")

        watcher = FilesystemWatcher(vault_root=str(vault_root))
        items = watcher.check_for_updates()
        for item in items:
            watcher.create_action_file(str(vault_root), item)

        inbox_files = _list_inbox_files(vault_root)
        assert inbox_files, "Inbox must contain at least one file"

        metadata, _ = _parse_frontmatter(inbox_files[0])
        source = str(metadata.get("source", ""))
        assert "filesystem" in source.lower(), (
            f"Expected source to contain 'filesystem', got: {source!r}"
        )

    def test_inbox_file_has_all_required_frontmatter_keys(self, tmp_path):
        """The Inbox .md file must have all required frontmatter fields."""
        vault_root = _make_vault(tmp_path)
        _seed_text_file(vault_root / "Watch", "fm_check.txt", "body content")

        watcher = FilesystemWatcher(vault_root=str(vault_root))
        items = watcher.check_for_updates()
        for item in items:
            watcher.create_action_file(str(vault_root), item)

        inbox_files = _list_inbox_files(vault_root)
        assert inbox_files

        metadata, _ = _parse_frontmatter(inbox_files[0])
        missing = _REQUIRED_FRONTMATTER_KEYS - metadata.keys()
        assert not missing, (
            f"Inbox file missing required frontmatter keys: {missing}. "
            f"Present: {set(metadata.keys())}"
        )

    def test_inbox_filename_contains_file_name(self, tmp_path):
        """The Inbox .md filename must reference the original Watch/ filename."""
        vault_root = _make_vault(tmp_path)
        _seed_text_file(vault_root / "Watch", "myreport.txt", "report body")

        watcher = FilesystemWatcher(vault_root=str(vault_root))
        items = watcher.check_for_updates()
        for item in items:
            watcher.create_action_file(str(vault_root), item)

        inbox_files = _list_inbox_files(vault_root)
        assert inbox_files

        names = [f.name for f in inbox_files]
        assert any("myreport" in n for n in names), (
            f"Expected inbox filename to contain 'myreport'. Got: {names}"
        )


class TestFilesystemWatcherBinaryFile:
    """Tests for binary file handling in FilesystemWatcher."""

    def test_binary_file_produces_inbox_item_with_type_unknown(self, tmp_path):
        """
        A binary file in Watch/ must produce an Inbox .md with type set to 'unknown'.
        """
        vault_root = _make_vault(tmp_path)
        _seed_binary_file(vault_root / "Watch", "image.bin")

        watcher = FilesystemWatcher(vault_root=str(vault_root))
        items = watcher.check_for_updates()
        for item in items:
            watcher.create_action_file(str(vault_root), item)

        inbox_files = _list_inbox_files(vault_root)
        assert inbox_files, "binary file must still produce an Inbox entry"

        metadata, _ = _parse_frontmatter(inbox_files[0])
        assert metadata.get("type") == "unknown", (
            f"Binary file must produce type='unknown'. Got: {metadata.get('type')!r}"
        )

    def test_binary_file_inbox_body_is_cannot_display_message(self, tmp_path):
        """
        The Inbox .md body for a binary file must contain the canonical
        '[Binary file — cannot display]' message.
        """
        vault_root = _make_vault(tmp_path)
        _seed_binary_file(vault_root / "Watch", "data.bin")

        watcher = FilesystemWatcher(vault_root=str(vault_root))
        items = watcher.check_for_updates()
        for item in items:
            watcher.create_action_file(str(vault_root), item)

        inbox_files = _list_inbox_files(vault_root)
        assert inbox_files

        _, body = _parse_frontmatter(inbox_files[0])
        # Accept both the em-dash and hyphen variants for robustness
        assert "Binary file" in body and "cannot display" in body, (
            f"Binary file body must contain 'Binary file' and 'cannot display'. Got: {body!r}"
        )

    def test_binary_file_has_filesystem_watcher_source(self, tmp_path):
        """Binary file Inbox entries must still have source: filesystem_watcher."""
        vault_root = _make_vault(tmp_path)
        _seed_binary_file(vault_root / "Watch", "binary_source.bin")

        watcher = FilesystemWatcher(vault_root=str(vault_root))
        items = watcher.check_for_updates()
        for item in items:
            watcher.create_action_file(str(vault_root), item)

        inbox_files = _list_inbox_files(vault_root)
        assert inbox_files

        metadata, _ = _parse_frontmatter(inbox_files[0])
        source = str(metadata.get("source", ""))
        assert "filesystem" in source.lower(), (
            f"Binary file must still have filesystem source. Got: {source!r}"
        )


class TestFilesystemWatcherEmptyFile:
    """Tests for empty file handling in FilesystemWatcher."""

    def test_empty_file_produces_inbox_item_with_type_unknown(self, tmp_path):
        """An empty (zero-byte) file in Watch/ must produce an Inbox item with type='unknown'."""
        vault_root = _make_vault(tmp_path)
        _seed_text_file(vault_root / "Watch", "empty.txt", "")

        watcher = FilesystemWatcher(vault_root=str(vault_root))
        items = watcher.check_for_updates()
        for item in items:
            watcher.create_action_file(str(vault_root), item)

        inbox_files = _list_inbox_files(vault_root)
        assert inbox_files, "empty file must still produce an Inbox entry"

        metadata, _ = _parse_frontmatter(inbox_files[0])
        assert metadata.get("type") == "unknown", (
            f"Empty file must produce type='unknown'. Got: {metadata.get('type')!r}"
        )

    def test_empty_file_has_all_required_frontmatter_keys(self, tmp_path):
        """An empty file Inbox entry must still have all required frontmatter keys."""
        vault_root = _make_vault(tmp_path)
        _seed_text_file(vault_root / "Watch", "empty_fm.txt", "")

        watcher = FilesystemWatcher(vault_root=str(vault_root))
        items = watcher.check_for_updates()
        for item in items:
            watcher.create_action_file(str(vault_root), item)

        inbox_files = _list_inbox_files(vault_root)
        assert inbox_files

        metadata, _ = _parse_frontmatter(inbox_files[0])
        missing = _REQUIRED_FRONTMATTER_KEYS - metadata.keys()
        assert not missing, (
            f"Empty file Inbox entry missing required keys: {missing}"
        )


class TestFilesystemWatcherDedup:
    """Tests for deduplication across check_for_updates calls in FilesystemWatcher."""

    def test_same_file_not_returned_twice_across_calls(self, tmp_path):
        """
        A file processed in the first check_for_updates call must not appear
        again in a subsequent call (dedup via _processed_ids).
        """
        vault_root = _make_vault(tmp_path)
        _seed_text_file(vault_root / "Watch", "dedup_file.txt", "dedup content")

        watcher = FilesystemWatcher(vault_root=str(vault_root))

        # First call: should find the file
        first_items = watcher.check_for_updates()
        assert first_items, "first call must return the file"

        # Mark as processed (simulate what run() would do)
        for item in first_items:
            watcher.create_action_file(str(vault_root), item)

        # Second call: same file must not appear again
        second_items = watcher.check_for_updates()
        first_names = {os.path.basename(i.get("path", i.get("name", ""))) for i in first_items}
        second_names = {os.path.basename(i.get("path", i.get("name", ""))) for i in second_items}

        duplicates = first_names & second_names
        assert not duplicates, (
            f"These files appeared in both first and second calls (dedup failed): {duplicates}"
        )

    def test_only_one_inbox_file_created_for_same_source_file(self, tmp_path):
        """
        Calling check_for_updates + create_action_file twice for the same Watch/
        file must result in only one Inbox .md file.
        """
        vault_root = _make_vault(tmp_path)
        _seed_text_file(vault_root / "Watch", "once_only.txt", "should appear once")

        watcher = FilesystemWatcher(vault_root=str(vault_root))

        # Simulate two processing cycles
        for _ in range(2):
            items = watcher.check_for_updates()
            for item in items:
                watcher.create_action_file(str(vault_root), item)

        inbox_files = _list_inbox_files(vault_root)
        assert len(inbox_files) == 1, (
            f"Expected exactly 1 Inbox file after 2 cycles, got {len(inbox_files)}: "
            f"{[f.name for f in inbox_files]}"
        )

    def test_new_file_detected_after_first_processed(self, tmp_path):
        """
        After the first file is processed, a newly added second file must still
        be detected in the next check_for_updates call.
        """
        vault_root = _make_vault(tmp_path)
        watch_dir = vault_root / "Watch"

        _seed_text_file(watch_dir, "first.txt", "first content")

        watcher = FilesystemWatcher(vault_root=str(vault_root))

        # Process first file
        first_items = watcher.check_for_updates()
        for item in first_items:
            watcher.create_action_file(str(vault_root), item)

        # Add a second file
        _seed_text_file(watch_dir, "second.txt", "second content")

        # Second call: must find the new file
        second_items = watcher.check_for_updates()
        second_names = [os.path.basename(i.get("path", i.get("name", ""))) for i in second_items]

        assert any("second" in n for n in second_names), (
            f"'second.txt' must be detected in subsequent call. Got: {second_names}"
        )

    def test_dedup_persists_across_state_save_and_load(self, tmp_path):
        """
        After processing a file and saving state, a new watcher instance loading
        that state must not reprocess the same file.
        """
        vault_root = _make_vault(tmp_path)
        state_file = str(vault_root / "state" / "fs_dedup_state.json")
        _seed_text_file(vault_root / "Watch", "persist_dedup.txt", "content")

        # Instance A: process and save
        watcher_a = FilesystemWatcher(vault_root=str(vault_root))
        watcher_a._state_file = state_file
        items_a = watcher_a.check_for_updates()
        for item in items_a:
            watcher_a.create_action_file(str(vault_root), item)
        watcher_a.save_state()

        inbox_after_a = _list_inbox_files(vault_root)
        assert len(inbox_after_a) == 1, "Instance A should create exactly 1 Inbox file"

        # Instance B: load state, process same Watch/ dir again
        watcher_b = FilesystemWatcher(vault_root=str(vault_root))
        watcher_b._state_file = state_file
        watcher_b.load_state()

        items_b = watcher_b.check_for_updates()
        for item in items_b:
            watcher_b.create_action_file(str(vault_root), item)

        inbox_after_b = _list_inbox_files(vault_root)
        assert len(inbox_after_b) == 1, (
            "Instance B must not reprocess already-processed files. "
            f"Expected 1 Inbox file, got {len(inbox_after_b)}"
        )


class TestFilesystemWatcherAttributes:
    """Tests for FilesystemWatcher constructor and attributes."""

    def test_can_be_instantiated_with_vault_root(self, tmp_path):
        """FilesystemWatcher must be constructable with a vault_root argument."""
        vault_root = _make_vault(tmp_path)
        watcher = FilesystemWatcher(vault_root=str(vault_root))
        assert watcher is not None

    def test_is_subclass_of_base_watcher(self, tmp_path):
        """FilesystemWatcher must be a subclass of BaseWatcher."""
        vault_root = _make_vault(tmp_path)
        watcher = FilesystemWatcher(vault_root=str(vault_root))
        assert isinstance(watcher, BaseWatcher)

    def test_has_processed_ids_attribute(self, tmp_path):
        """FilesystemWatcher must expose _processed_ids as a set."""
        vault_root = _make_vault(tmp_path)
        watcher = FilesystemWatcher(vault_root=str(vault_root))
        assert hasattr(watcher, "_processed_ids")
        assert isinstance(watcher._processed_ids, set)

    def test_has_state_file_attribute(self, tmp_path):
        """FilesystemWatcher must expose _state_file as a str."""
        vault_root = _make_vault(tmp_path)
        watcher = FilesystemWatcher(vault_root=str(vault_root))
        assert hasattr(watcher, "_state_file")
        assert isinstance(watcher._state_file, str)

    def test_has_poll_interval_attribute(self, tmp_path):
        """FilesystemWatcher must expose poll_interval as a positive int."""
        vault_root = _make_vault(tmp_path)
        watcher = FilesystemWatcher(vault_root=str(vault_root))
        assert hasattr(watcher, "poll_interval")
        assert isinstance(watcher.poll_interval, int)
        assert watcher.poll_interval > 0

    def test_has_stability_wait_attribute(self, tmp_path):
        """FilesystemWatcher must expose stability_wait as a float."""
        vault_root = _make_vault(tmp_path)
        watcher = FilesystemWatcher(vault_root=str(vault_root))
        assert hasattr(watcher, "stability_wait")
        assert isinstance(watcher.stability_wait, float)

    def test_has_recursive_attribute(self, tmp_path):
        """FilesystemWatcher must expose recursive as a bool, defaulting to False."""
        vault_root = _make_vault(tmp_path)
        watcher = FilesystemWatcher(vault_root=str(vault_root))
        assert hasattr(watcher, "recursive")
        assert watcher.recursive is False

    def test_allowed_extensions_defaults_to_none(self, tmp_path):
        """allowed_extensions must default to None (allow all non-dotfiles)."""
        vault_root = _make_vault(tmp_path)
        watcher = FilesystemWatcher(vault_root=str(vault_root))
        assert watcher.allowed_extensions is None


# ---------------------------------------------------------------------------
# New feature tests
# ---------------------------------------------------------------------------

class TestFilesystemWatcherDeletion:
    """Tests for deletion handling: purging processed state on file deletion."""

    def test_on_file_deleted_removes_matching_processed_ids(self, tmp_path):
        """_on_file_deleted must remove all FILE_{name}_* IDs from processed_ids."""
        vault_root = _make_vault(tmp_path)
        watcher = FilesystemWatcher(vault_root=str(vault_root))

        watcher._processed_ids = {
            "FILE_report_1000000",
            "FILE_report_1000001",
            "FILE_other_9999999",
        }
        deleted_path = str(vault_root / "Watch" / "report.txt")
        watcher._on_file_deleted(os.path.normpath(deleted_path))

        assert "FILE_report_1000000" not in watcher._processed_ids
        assert "FILE_report_1000001" not in watcher._processed_ids
        assert "FILE_other_9999999" in watcher._processed_ids, "unrelated IDs must be kept"

    def test_on_file_deleted_does_not_raise_on_unknown_file(self, tmp_path):
        """_on_file_deleted must not raise even if no matching IDs exist."""
        vault_root = _make_vault(tmp_path)
        watcher = FilesystemWatcher(vault_root=str(vault_root))
        watcher._processed_ids = {"FILE_other_123"}

        deleted_path = str(vault_root / "Watch" / "nonexistent.txt")
        watcher._on_file_deleted(os.path.normpath(deleted_path))  # must not raise

        assert "FILE_other_123" in watcher._processed_ids

    def test_file_can_be_reprocessed_after_deletion_purge(self, tmp_path):
        """After _on_file_deleted purges state, a new file with same name is reprocessed."""
        vault_root = _make_vault(tmp_path)
        watch_dir = vault_root / "Watch"
        watcher = FilesystemWatcher(vault_root=str(vault_root))

        # Seed and process first version of the file
        fpath = _seed_text_file(watch_dir, "reprocess.txt", "version 1")
        items = watcher.check_for_updates()
        for item in items:
            watcher.create_action_file(str(vault_root), item)

        assert len(_list_inbox_files(vault_root)) == 1

        # Simulate deletion — purge state
        watcher._on_file_deleted(os.path.normpath(str(fpath)))

        # Re-create the file with same content (same mtime bucket possible, but state cleared)
        fpath.unlink()
        import time as _time
        _time.sleep(0.01)
        fpath = _seed_text_file(watch_dir, "reprocess.txt", "version 2")

        items2 = watcher.check_for_updates()
        for item in items2:
            watcher.create_action_file(str(vault_root), item)

        assert len(_list_inbox_files(vault_root)) >= 1, "reprocessed file must create new Inbox entry"


class TestFilesystemWatcherDebouncing:
    """Tests for event debouncing: rapid repeated events coalesce to one item."""

    def test_duplicate_events_in_queue_produce_single_item(self, tmp_path):
        """Multiple queued events for the same path must yield at most one item."""
        vault_root = _make_vault(tmp_path)
        watch_dir = vault_root / "Watch"
        _seed_text_file(watch_dir, "burst.txt", "burst content")

        watcher = FilesystemWatcher(vault_root=str(vault_root))

        # Manually queue the same path multiple times (simulating rapid OS events)
        fpath = str(watch_dir / "burst.txt")
        for _ in range(5):
            watcher._handler._queue.put(("modified", fpath))

        items = watcher.check_for_updates()

        names = [os.path.basename(i.get("path", i.get("name", ""))) for i in items]
        burst_count = sum(1 for n in names if "burst" in n)
        assert burst_count <= 1, (
            f"Debouncing failed: 'burst.txt' appeared {burst_count} times in items"
        )

    def test_last_event_type_wins_for_same_path(self, tmp_path):
        """When the same path has multiple queued events, the last event type is used."""
        vault_root = _make_vault(tmp_path)
        watch_dir = vault_root / "Watch"
        fpath = str(watch_dir / "event_order.txt")

        watcher = FilesystemWatcher(vault_root=str(vault_root))

        # Queue: created → modified → deleted (last = deleted)
        for event_type in ("created", "modified", "deleted"):
            watcher._handler._queue.put((event_type, fpath))

        # Drain the handler queue and build event_map like check_for_updates does
        event_map: dict[str, str] = {}
        for event_type, raw_path in watcher._handler.get_queued():
            norm = os.path.normpath(raw_path)
            event_map[norm] = event_type

        assert event_map.get(os.path.normpath(fpath)) == "deleted", (
            "Last event (deleted) must win when same path is queued multiple times"
        )


class TestFilesystemWatcherStabilityCheck:
    """Tests for the mtime-based stability check."""

    def test_is_stable_returns_true_when_stability_wait_is_zero(self, tmp_path):
        """With stability_wait=0, all files are considered stable immediately."""
        vault_root = _make_vault(tmp_path)
        fpath = _seed_text_file(vault_root / "Watch", "fresh.txt", "new content")

        watcher = FilesystemWatcher(vault_root=str(vault_root), stability_wait=0.0)
        assert watcher._is_stable(str(fpath)) is True

    def test_is_stable_returns_false_for_very_recent_file(self, tmp_path):
        """A file modified just now must fail the stability check when stability_wait > 0."""
        vault_root = _make_vault(tmp_path)
        fpath = _seed_text_file(vault_root / "Watch", "recent.txt", "content")

        watcher = FilesystemWatcher(vault_root=str(vault_root), stability_wait=60.0)
        assert watcher._is_stable(str(fpath)) is False, (
            "A just-written file must not pass stability check with 60s wait"
        )

    def test_is_stable_returns_false_for_missing_file(self, tmp_path):
        """_is_stable on a nonexistent path must return False (not raise)."""
        vault_root = _make_vault(tmp_path)
        watcher = FilesystemWatcher(vault_root=str(vault_root), stability_wait=1.0)
        assert watcher._is_stable(str(vault_root / "Watch" / "ghost.txt")) is False

    def test_recent_file_skipped_in_check_for_updates(self, tmp_path):
        """With a large stability_wait, a freshly-written file must be skipped."""
        vault_root = _make_vault(tmp_path)
        _seed_text_file(vault_root / "Watch", "unstable.txt", "not yet ready")

        watcher = FilesystemWatcher(vault_root=str(vault_root), stability_wait=9999.0)
        items = watcher.check_for_updates()

        names = [os.path.basename(i.get("path", i.get("name", ""))) for i in items]
        assert not any("unstable" in n for n in names), (
            "A file written moments ago must be skipped when stability_wait is very large"
        )


class TestFilesystemWatcherExtensionFilter:
    """Tests for the allowed_extensions filter."""

    def test_all_files_allowed_when_no_filter_set(self, tmp_path):
        """With allowed_extensions=None, all non-dotfiles are processed."""
        vault_root = _make_vault(tmp_path)
        watch_dir = vault_root / "Watch"
        _seed_text_file(watch_dir, "doc.txt", "text")
        _seed_text_file(watch_dir, "data.csv", "a,b")
        _seed_text_file(watch_dir, "note.md", "# hi")

        watcher = FilesystemWatcher(vault_root=str(vault_root), allowed_extensions=None)
        items = watcher.check_for_updates()

        names = [os.path.basename(i.get("path", i.get("name", ""))) for i in items]
        assert any("doc.txt" in n for n in names)
        assert any("data.csv" in n for n in names)
        assert any("note.md" in n for n in names)

    def test_only_allowed_extensions_processed(self, tmp_path):
        """With allowed_extensions set, only matching files are returned."""
        vault_root = _make_vault(tmp_path)
        watch_dir = vault_root / "Watch"
        _seed_text_file(watch_dir, "keep.txt", "keep")
        _seed_text_file(watch_dir, "skip.csv", "skip")
        _seed_text_file(watch_dir, "skip.xml", "skip")

        watcher = FilesystemWatcher(
            vault_root=str(vault_root),
            allowed_extensions={".txt"},
        )
        items = watcher.check_for_updates()

        names = [os.path.basename(i.get("path", i.get("name", ""))) for i in items]
        assert any("keep.txt" in n for n in names), "allowed extension must be included"
        assert not any("skip.csv" in n for n in names), ".csv must be excluded"
        assert not any("skip.xml" in n for n in names), ".xml must be excluded"

    def test_dotfiles_always_excluded(self, tmp_path):
        """Dotfiles must be excluded regardless of allowed_extensions setting."""
        vault_root = _make_vault(tmp_path)
        watch_dir = vault_root / "Watch"
        dot_file = watch_dir / ".hidden"
        dot_file.write_text("hidden", encoding="utf-8")

        watcher = FilesystemWatcher(vault_root=str(vault_root), allowed_extensions=None)
        assert watcher._is_allowed_extension(".hidden") is False

    def test_extension_filter_case_insensitive(self, tmp_path):
        """Extension matching must be case-insensitive (.TXT == .txt)."""
        vault_root = _make_vault(tmp_path)
        watch_dir = vault_root / "Watch"
        _seed_text_file(watch_dir, "UPPER.TXT", "content")

        watcher = FilesystemWatcher(
            vault_root=str(vault_root),
            allowed_extensions={".txt"},
        )
        assert watcher._is_allowed_extension("UPPER.TXT") is True


class TestFilesystemWatcherMaxFileSize:
    """Tests for the 10 MB max file size guard."""

    def test_oversized_file_returns_too_large_message(self, tmp_path):
        """A file exceeding _MAX_FILE_BYTES must return the 'too large' message."""
        from src.watchers.filesystem_watcher import _MAX_FILE_BYTES

        vault_root = _make_vault(tmp_path)
        big_file = vault_root / "Watch" / "huge.txt"
        # Write exactly MAX + 1 bytes
        big_file.write_bytes(b"x" * (_MAX_FILE_BYTES + 1))

        watcher = FilesystemWatcher(vault_root=str(vault_root))
        content, item_type = watcher._read_file_content(str(big_file))

        assert "too large" in content.lower(), (
            f"Expected 'too large' in content for oversized file. Got: {content!r}"
        )
        assert item_type == "unknown", "Oversized file must have type='unknown'"

    def test_normal_sized_file_reads_correctly(self, tmp_path):
        """A normal-sized file must be read as text with type='general'."""
        vault_root = _make_vault(tmp_path)
        fpath = _seed_text_file(vault_root / "Watch", "normal.txt", "hello world")

        watcher = FilesystemWatcher(vault_root=str(vault_root))
        content, item_type = watcher._read_file_content(str(fpath))

        assert content == "hello world"
        assert item_type == "general"


class TestFilesystemWatcherMoveEvent:
    """Tests for on_moved event handling via _WatchHandler."""

    def test_on_moved_queues_deleted_and_created(self, tmp_path):
        """on_moved must queue a 'deleted' event for src and 'created' for dest."""
        from src.watchers.filesystem_watcher import _WatchHandler
        from unittest.mock import MagicMock

        handler = _WatchHandler()

        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = "/watch/old_name.txt"
        mock_event.dest_path = "/watch/new_name.txt"

        handler.on_moved(mock_event)
        events = handler.get_queued()

        event_map = {path: etype for etype, path in events}
        assert event_map.get("/watch/old_name.txt") == "deleted", (
            "src_path must be queued as 'deleted'"
        )
        assert event_map.get("/watch/new_name.txt") == "created", (
            "dest_path must be queued as 'created'"
        )
