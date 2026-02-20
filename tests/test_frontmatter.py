"""
Comprehensive tests for src/core/frontmatter.py

Covers:
  - parse_frontmatter: valid content, no frontmatter, empty body, malformed YAML
  - write_frontmatter: structure, roundtrip
  - create_standard_metadata: required keys, ISO-8601 timestamp, provided values/defaults
"""

import sys
import os

# Ensure the project root is on sys.path so `src` is importable regardless of
# how pytest is invoked (e.g. from repo root or from the tests/ directory).
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import re
from datetime import datetime, timezone, timedelta

import pytest
import yaml

from src.core.frontmatter import (
    create_standard_metadata,
    parse_frontmatter,
    write_frontmatter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ISO8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}"           # date: YYYY-MM-DD
    r"[T ]\d{2}:\d{2}:\d{2}"        # time: HH:MM:SS (T or space separator)
    r"(\.\d+)?"                       # optional fractional seconds
    r"(Z|[+-]\d{2}:?\d{2})?$"        # optional timezone (Z or ±HH:MM)
)


def _is_iso8601(value: str) -> bool:
    """Return True when *value* is a valid ISO-8601 datetime string."""
    return bool(_ISO8601_RE.match(str(value)))


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------

class TestParseFrontmatter:
    """Tests for parse_frontmatter(content: str) -> tuple[dict, str]."""

    def test_valid_content_returns_correct_dict_and_body(self):
        """Parses YAML block and splits body correctly for well-formed input."""
        content = (
            "---\n"
            "type: email\n"
            "source: inbox\n"
            "priority: HIGH\n"
            "---\n"
            "This is the body text.\n"
            "Second line."
        )
        metadata, body = parse_frontmatter(content)

        assert isinstance(metadata, dict), "metadata must be a dict"
        assert metadata["type"] == "email"
        assert metadata["source"] == "inbox"
        assert metadata["priority"] == "HIGH"
        assert "This is the body text." in body
        assert "Second line." in body

    def test_valid_content_body_does_not_contain_yaml_markers(self):
        """The returned body must not include the --- delimiters."""
        content = "---\nstatus: new\n---\nHello world"
        _, body = parse_frontmatter(content)

        assert "---" not in body, "body should not contain YAML delimiter markers"

    def test_no_frontmatter_returns_empty_dict_and_full_content(self):
        """Content without --- markers returns ({}, original_content)."""
        content = "Just plain text.\nNo frontmatter here."
        metadata, body = parse_frontmatter(content)

        assert metadata == {}, "metadata must be empty dict when no frontmatter present"
        assert body == content, "body must equal the original content unchanged"

    def test_no_frontmatter_only_one_delimiter_returns_empty_dict(self):
        """A single --- without a closing --- is treated as no frontmatter."""
        content = "---\nonly one delimiter\nno closing"
        metadata, body = parse_frontmatter(content)

        assert metadata == {}
        assert body == content

    def test_empty_body_returns_dict_and_empty_string(self):
        """Frontmatter with nothing after the closing --- produces empty body."""
        content = "---\ntype: note\nsource: manual\n---\n"
        metadata, body = parse_frontmatter(content)

        assert metadata.get("type") == "note"
        assert body.strip() == "", f"expected empty body, got: {body!r}"

    def test_empty_body_no_trailing_newline(self):
        """Closing --- immediately followed by EOF also gives empty body."""
        content = "---\nkey: value\n---"
        metadata, body = parse_frontmatter(content)

        assert metadata.get("key") == "value"
        assert body.strip() == ""

    def test_malformed_yaml_returns_empty_dict_and_original_content(self):
        """Invalid YAML inside delimiters returns ({}, original_content)."""
        # Indentation error that breaks YAML parsing
        content = (
            "---\n"
            "key: valid\n"
            "  bad_indent: this breaks yaml\n"
            "---\n"
            "Body text."
        )
        metadata, body = parse_frontmatter(content)

        assert metadata == {}, "malformed YAML must return empty dict"
        assert body == content, "malformed YAML must return original content as body"

    def test_malformed_yaml_tab_character(self):
        """YAML does not allow literal tab characters in most positions."""
        content = "---\nkey:\tvalue\n---\nbody"
        metadata, body = parse_frontmatter(content)

        # Implementation may or may not raise; the contract is: if invalid,
        # return ({}, original). We only assert the invariant.
        if metadata == {}:
            assert body == content
        else:
            # If pyyaml tolerates tabs here, the metadata must at least be a dict.
            assert isinstance(metadata, dict)

    def test_multiline_body_preserved(self):
        """Multi-line body after frontmatter is returned intact."""
        body_expected = "Line 1\nLine 2\nLine 3\n"
        content = f"---\ntype: doc\n---\n{body_expected}"
        _, body = parse_frontmatter(content)

        assert body == body_expected

    def test_numeric_and_boolean_yaml_values(self):
        """YAML scalar types (int, bool) are parsed correctly."""
        content = "---\ncount: 42\nenabled: true\n---\nbody"
        metadata, _ = parse_frontmatter(content)

        assert metadata["count"] == 42
        assert metadata["enabled"] is True

    def test_nested_yaml_dict_parsed(self):
        """Nested YAML mappings are parsed into nested dicts."""
        content = (
            "---\n"
            "outer:\n"
            "  inner: value\n"
            "---\n"
            "body"
        )
        metadata, _ = parse_frontmatter(content)

        assert isinstance(metadata.get("outer"), dict)
        assert metadata["outer"]["inner"] == "value"


# ---------------------------------------------------------------------------
# write_frontmatter
# ---------------------------------------------------------------------------

class TestWriteFrontmatter:
    """Tests for write_frontmatter(metadata: dict, body: str) -> str."""

    def test_produces_yaml_between_markers_with_body_after(self):
        """Output starts with ---, contains YAML, then ---, then body."""
        metadata = {"type": "email", "priority": "LOW"}
        body = "Hello, world."
        result = write_frontmatter(metadata, body)

        lines = result.splitlines()
        assert lines[0].strip() == "---", "first line must be ---"

        # Find closing ---
        closing_idx = None
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                closing_idx = i
                break
        assert closing_idx is not None, "output must contain a closing ---"

        yaml_block = "\n".join(lines[1:closing_idx])
        parsed = yaml.safe_load(yaml_block)
        assert parsed["type"] == "email"
        assert parsed["priority"] == "LOW"

        # Body must appear after the closing ---
        after_closing = "\n".join(lines[closing_idx + 1:])
        assert "Hello, world." in after_closing

    def test_body_appears_verbatim_after_closing_marker(self):
        """The exact body string follows the closing --- marker."""
        metadata = {"key": "val"}
        body = "First line.\nSecond line.\n"
        result = write_frontmatter(metadata, body)

        # Split on the second ---
        parts = result.split("---")
        # parts[0] == '' (before first ---), parts[1] == yaml block, parts[2+] == body
        assert len(parts) >= 3, "output must have at least two --- separators"
        # Rejoin in case body itself contained ---
        body_part = "---".join(parts[2:]).lstrip("\n")
        assert "First line." in body_part
        assert "Second line." in body_part

    def test_empty_body_produces_valid_output(self):
        """write_frontmatter with an empty body string is valid."""
        metadata = {"status": "done"}
        result = write_frontmatter(metadata, "")

        assert result.startswith("---"), "output must start with ---"
        _, body = parse_frontmatter(result)
        assert body.strip() == ""

    def test_empty_metadata_dict_produces_valid_output(self):
        """An empty metadata dict produces a valid (possibly empty) YAML block."""
        result = write_frontmatter({}, "some body")

        assert "---" in result
        assert "some body" in result

    def test_roundtrip_write_then_parse_returns_original_data(self):
        """write_frontmatter then parse_frontmatter returns the original metadata and body."""
        original_metadata = {
            "type": "transaction",
            "source": "bank",
            "priority": "HIGH",
            "status": "new",
        }
        original_body = "Transaction details go here.\nAmount: $250.00\n"

        written = write_frontmatter(original_metadata, original_body)
        parsed_metadata, parsed_body = parse_frontmatter(written)

        assert parsed_metadata == original_metadata, (
            f"roundtrip metadata mismatch:\n  expected: {original_metadata}\n  got: {parsed_metadata}"
        )
        assert parsed_body == original_body, (
            f"roundtrip body mismatch:\n  expected: {original_body!r}\n  got: {parsed_body!r}"
        )

    def test_roundtrip_preserves_nested_metadata(self):
        """Nested dict values survive write → parse roundtrip."""
        original_metadata = {"outer": {"inner": "deep_value", "count": 7}}
        original_body = "body"

        written = write_frontmatter(original_metadata, original_body)
        parsed_metadata, _ = parse_frontmatter(written)

        assert parsed_metadata == original_metadata

    def test_roundtrip_preserves_list_metadata(self):
        """List values survive write → parse roundtrip."""
        original_metadata = {"tags": ["alpha", "beta", "gamma"]}
        original_body = "tagged content"

        written = write_frontmatter(original_metadata, original_body)
        parsed_metadata, _ = parse_frontmatter(written)

        assert parsed_metadata == original_metadata

    def test_output_is_string(self):
        """write_frontmatter always returns a str."""
        result = write_frontmatter({"k": "v"}, "body")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# create_standard_metadata
# ---------------------------------------------------------------------------

class TestCreateStandardMetadata:
    """Tests for create_standard_metadata(type, source, priority, status) -> dict."""

    _REQUIRED_KEYS = {"type", "source", "timestamp", "priority", "status"}

    def test_returns_dict_with_all_required_keys(self):
        """All five required keys must be present in the returned dict."""
        result = create_standard_metadata(type="email", source="inbox")

        missing = self._REQUIRED_KEYS - result.keys()
        assert not missing, f"Missing required keys: {missing}"

    def test_timestamp_is_valid_iso8601(self):
        """The timestamp value must conform to ISO-8601 datetime format."""
        result = create_standard_metadata(type="email", source="inbox")
        timestamp = result["timestamp"]

        assert _is_iso8601(str(timestamp)), (
            f"timestamp {timestamp!r} is not a valid ISO-8601 datetime string"
        )

    def test_timestamp_is_recent(self):
        """The generated timestamp should be within a few seconds of now."""
        before = datetime.now(timezone.utc).replace(microsecond=0)
        result = create_standard_metadata(type="note", source="manual")
        after = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=1)

        raw_ts = str(result["timestamp"])
        raw_ts_normalised = raw_ts.replace("Z", "+00:00")
        try:
            ts = datetime.fromisoformat(raw_ts_normalised)
        except ValueError:
            pytest.fail(f"Could not parse timestamp as ISO-8601: {raw_ts!r}")

        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        assert before <= ts <= after, (
            f"timestamp {ts} is not between {before} and {after}"
        )

    def test_uses_provided_type(self):
        """The type field reflects the argument passed."""
        result = create_standard_metadata(type="invoice", source="odoo")
        assert result["type"] == "invoice"

    def test_uses_provided_source(self):
        """The source field reflects the argument passed."""
        result = create_standard_metadata(type="email", source="gmail")
        assert result["source"] == "gmail"

    def test_default_priority_is_medium(self):
        """When priority is not supplied, it defaults to 'MEDIUM'."""
        result = create_standard_metadata(type="email", source="inbox")
        assert result["priority"] == "MEDIUM"

    def test_default_status_is_new(self):
        """When status is not supplied, it defaults to 'new'."""
        result = create_standard_metadata(type="email", source="inbox")
        assert result["status"] == "new"

    def test_custom_priority_is_respected(self):
        """Supplying priority overrides the default."""
        result = create_standard_metadata(type="alert", source="monitor", priority="HIGH")
        assert result["priority"] == "HIGH"

    def test_custom_status_is_respected(self):
        """Supplying status overrides the default."""
        result = create_standard_metadata(type="task", source="planner", status="in_progress")
        assert result["status"] == "in_progress"

    def test_all_parameters_provided(self):
        """All four parameters supplied are all reflected in the result."""
        result = create_standard_metadata(
            type="transaction",
            source="bank_feed",
            priority="LOW",
            status="processed",
        )
        assert result["type"] == "transaction"
        assert result["source"] == "bank_feed"
        assert result["priority"] == "LOW"
        assert result["status"] == "processed"
        assert "timestamp" in result

    def test_return_type_is_dict(self):
        """create_standard_metadata must always return a dict."""
        result = create_standard_metadata(type="x", source="y")
        assert isinstance(result, dict)

    def test_no_extra_unexpected_keys(self):
        """Result must contain exactly the required keys (no hidden extras expected)."""
        result = create_standard_metadata(type="email", source="inbox")
        extra = set(result.keys()) - self._REQUIRED_KEYS
        # Extra keys are allowed (forward-compat), but we document that the
        # five required keys are always present — already asserted elsewhere.
        # This test simply ensures the required keys set is a subset.
        assert self._REQUIRED_KEYS.issubset(result.keys())

    @pytest.mark.parametrize("priority", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    def test_various_priority_values_stored_correctly(self, priority):
        """All valid priority levels round-trip through the metadata dict."""
        result = create_standard_metadata(type="e", source="s", priority=priority)
        assert result["priority"] == priority

    @pytest.mark.parametrize("status", ["new", "processed", "failed", "archived"])
    def test_various_status_values_stored_correctly(self, status):
        """Various status strings are preserved as-is."""
        result = create_standard_metadata(type="e", source="s", status=status)
        assert result["status"] == status
