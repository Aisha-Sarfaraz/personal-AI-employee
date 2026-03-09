"""Tests for WhatsAppWatcher (Playwright-based WhatsApp Web automation).

All tests run in dry-run / mock mode — no browser, no network.
"""

import json
import os
import pytest

from src.watchers.whatsapp_watcher import WhatsAppWatcher


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def vault(tmp_path):
    """Minimal vault layout for watcher tests."""
    (tmp_path / "state").mkdir()
    (tmp_path / "Watch" / "whatsapp_mock").mkdir(parents=True)
    (tmp_path / "Inbox").mkdir()
    return tmp_path


@pytest.fixture()
def watcher(vault):
    return WhatsAppWatcher(str(vault), poll_interval=120, dry_run=True)


def _write_mock(vault, filename, data):
    path = vault / "Watch" / "whatsapp_mock" / filename
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------


class TestDryRunMode:
    def test_dry_run_flag_true(self, vault):
        w = WhatsAppWatcher(str(vault), dry_run=True)
        assert w.dry_run is True

    def test_env_var_overrides(self, vault, monkeypatch):
        monkeypatch.setenv("DRY_RUN", "true")
        w = WhatsAppWatcher(str(vault), dry_run=False)
        assert w.dry_run is True

    def test_env_var_false_when_not_set(self, vault, monkeypatch):
        monkeypatch.delenv("DRY_RUN", raising=False)
        # Session path absent → falls back to mock regardless
        w = WhatsAppWatcher(str(vault), dry_run=False,
                            session_path="/nonexistent/session")
        assert w.dry_run is False  # flag is False; mock triggered by missing session dir

    def test_no_session_dir_returns_mock(self, vault):
        _write_mock(vault, "msg.json", {
            "MessageSid": "SM001",
            "From": "Alice",
            "Body": "urgent payment needed",
        })
        w = WhatsAppWatcher(str(vault), session_path="/nonexistent/session", dry_run=False)
        items = w.check_for_updates()
        assert len(items) == 1
        assert items[0]["source"] == "whatsapp"


# ---------------------------------------------------------------------------
# Mock item loading
# ---------------------------------------------------------------------------


class TestMockItemLoading:
    def test_empty_mock_dir_returns_empty(self, watcher):
        items = watcher.check_for_updates()
        assert items == []

    def test_loads_single_mock_message(self, watcher, vault):
        _write_mock(vault, "msg.json", {
            "MessageSid": "SM001",
            "From": "Bob",
            "Body": "I'm interested in pricing",
        })
        items = watcher.check_for_updates()
        assert len(items) == 1
        item = items[0]
        assert item["id"] == "WA_SM001"
        assert item["source"] == "whatsapp"
        assert "Bob" in item["body"]
        assert "pricing" in item["body"].lower()

    def test_loads_multiple_mock_messages(self, watcher, vault):
        for i in range(3):
            _write_mock(vault, f"msg{i}.json", {
                "MessageSid": f"SM00{i}",
                "From": f"Contact{i}",
                "Body": f"urgent request number {i}",
            })
        items = watcher.check_for_updates()
        assert len(items) == 3

    def test_invalid_json_skipped(self, watcher, vault):
        (vault / "Watch" / "whatsapp_mock" / "bad.json").write_text("not json")
        _write_mock(vault, "good.json", {
            "MessageSid": "SM999",
            "From": "Carol",
            "Body": "urgent help needed",
        })
        items = watcher.check_for_updates()
        assert len(items) == 1

    def test_alternate_field_names(self, watcher, vault):
        """Accepts body/from_number in addition to Body/From."""
        _write_mock(vault, "alt.json", {
            "message_sid": "SM100",
            "from_number": "Dave",
            "body": "I need an invoice",
        })
        items = watcher.check_for_updates()
        assert len(items) == 1
        assert items[0]["id"] == "WA_SM100"


# ---------------------------------------------------------------------------
# Keyword filtering
# ---------------------------------------------------------------------------


class TestKeywordFiltering:
    def test_keyword_match_included(self, watcher, vault):
        _write_mock(vault, "m.json", {
            "MessageSid": "SM001",
            "From": "Eve",
            "Body": "Can you help with invoice processing?",
        })
        items = watcher.check_for_updates()
        assert len(items) == 1

    def test_no_keyword_match_excluded(self, watcher, vault):
        _write_mock(vault, "m.json", {
            "MessageSid": "SM002",
            "From": "Frank",
            "Body": "Good morning, how are you today?",
        })
        items = watcher.check_for_updates()
        assert len(items) == 0

    def test_keyword_in_sender_name_included(self, watcher, vault):
        _write_mock(vault, "m.json", {
            "MessageSid": "SM003",
            "From": "Invoice Department",
            "Body": "Please see attached",
        })
        items = watcher.check_for_updates()
        assert len(items) == 1

    def test_custom_keywords(self, vault):
        _write_mock(vault, "m.json", {
            "MessageSid": "SM004",
            "From": "Grace",
            "Body": "demo request for tomorrow",
        })
        w = WhatsAppWatcher(str(vault), dry_run=True, keywords=["demo"])
        items = w.check_for_updates()
        assert len(items) == 1

    def test_empty_keywords_list_allows_all(self, vault):
        _write_mock(vault, "m.json", {
            "MessageSid": "SM005",
            "From": "Hank",
            "Body": "just saying hello",
        })
        w = WhatsAppWatcher(str(vault), dry_run=True, keywords=[])
        items = w.check_for_updates()
        assert len(items) == 1


# ---------------------------------------------------------------------------
# Priority assignment
# ---------------------------------------------------------------------------


class TestPriorityAssignment:
    def test_urgent_keyword_gives_high_priority(self, watcher, vault):
        _write_mock(vault, "m.json", {
            "MessageSid": "SM010",
            "From": "Ivan",
            "Body": "This is urgent, need help now",
        })
        items = watcher.check_for_updates()
        assert items[0]["priority"] == "HIGH"

    def test_asap_gives_high_priority(self, watcher, vault):
        _write_mock(vault, "m.json", {
            "MessageSid": "SM011",
            "From": "Jane",
            "Body": "Need this asap please",
        })
        items = watcher.check_for_updates()
        assert items[0]["priority"] == "HIGH"

    def test_normal_keyword_gives_medium_priority(self, watcher, vault):
        _write_mock(vault, "m.json", {
            "MessageSid": "SM012",
            "From": "Karl",
            "Body": "Can you send an invoice for last month?",
        })
        items = watcher.check_for_updates()
        assert items[0]["priority"] == "MEDIUM"


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    def test_same_message_not_returned_twice(self, watcher, vault):
        _write_mock(vault, "m.json", {
            "MessageSid": "SM020",
            "From": "Leo",
            "Body": "urgent payment needed",
        })
        first = watcher.check_for_updates()
        assert len(first) == 1
        # Simulate second scan — processed IDs retained in memory
        second = watcher.check_for_updates()
        assert len(second) == 0

    def test_different_message_sid_returned(self, watcher, vault):
        for sid, body in [("SM030", "urgent help"), ("SM031", "urgent help")]:
            _write_mock(vault, f"{sid}.json", {
                "MessageSid": sid,
                "From": "Mia",
                "Body": body,
            })
        first = watcher.check_for_updates()
        assert len(first) == 2

    def test_processed_id_persists_across_instances(self, vault):
        _write_mock(vault, "m.json", {
            "MessageSid": "SM040",
            "From": "Ned",
            "Body": "urgent invoice needed",
        })
        w1 = WhatsAppWatcher(str(vault), dry_run=True)
        items1 = w1.check_for_updates()
        assert len(items1) == 1
        w1.save_state()

        # New instance loads state
        w2 = WhatsAppWatcher(str(vault), dry_run=True)
        w2.load_state()
        items2 = w2.check_for_updates()
        assert len(items2) == 0


# ---------------------------------------------------------------------------
# Item structure
# ---------------------------------------------------------------------------


class TestItemStructure:
    def test_required_keys_present(self, watcher, vault):
        _write_mock(vault, "m.json", {
            "MessageSid": "SM050",
            "From": "Olivia",
            "Body": "urgent payment question",
        })
        item = watcher.check_for_updates()[0]
        for key in ("id", "source", "body", "type", "priority", "filename", "tags"):
            assert key in item, f"Missing key: {key}"

    def test_source_is_whatsapp(self, watcher, vault):
        _write_mock(vault, "m.json", {
            "MessageSid": "SM051",
            "From": "Pete",
            "Body": "need invoice asap",
        })
        item = watcher.check_for_updates()[0]
        assert item["source"] == "whatsapp"

    def test_id_prefixed_with_wa(self, watcher, vault):
        _write_mock(vault, "m.json", {
            "MessageSid": "SM052",
            "From": "Quinn",
            "Body": "urgent help please",
        })
        item = watcher.check_for_updates()[0]
        assert item["id"].startswith("WA_")

    def test_filename_ends_with_md(self, watcher, vault):
        _write_mock(vault, "m.json", {
            "MessageSid": "SM053",
            "From": "Rose",
            "Body": "payment urgent",
        })
        item = watcher.check_for_updates()[0]
        assert item["filename"].endswith(".md")

    def test_tags_is_list(self, watcher, vault):
        _write_mock(vault, "m.json", {
            "MessageSid": "SM054",
            "From": "Sam",
            "Body": "invoice payment needed",
        })
        item = watcher.check_for_updates()[0]
        assert isinstance(item["tags"], list)

    def test_body_contains_sender_name(self, watcher, vault):
        _write_mock(vault, "m.json", {
            "MessageSid": "SM055",
            "From": "Tara",
            "Body": "urgent request here",
        })
        item = watcher.check_for_updates()[0]
        assert "Tara" in item["body"]


# ---------------------------------------------------------------------------
# Message ID generation
# ---------------------------------------------------------------------------


class TestMessageIdGeneration:
    def test_same_content_gives_same_id(self):
        id1 = WhatsAppWatcher._make_message_id("Alice", "urgent payment needed")
        id2 = WhatsAppWatcher._make_message_id("Alice", "urgent payment needed")
        assert id1 == id2

    def test_different_body_gives_different_id(self):
        id1 = WhatsAppWatcher._make_message_id("Alice", "urgent payment needed")
        id2 = WhatsAppWatcher._make_message_id("Alice", "please send invoice")
        assert id1 != id2

    def test_different_sender_gives_different_id(self):
        id1 = WhatsAppWatcher._make_message_id("Alice", "urgent")
        id2 = WhatsAppWatcher._make_message_id("Bob", "urgent")
        assert id1 != id2

    def test_id_is_string(self):
        result = WhatsAppWatcher._make_message_id("Alice", "test body")
        assert isinstance(result, str)

    def test_id_starts_with_wa(self):
        result = WhatsAppWatcher._make_message_id("Alice", "test body")
        assert result.startswith("WA_")
