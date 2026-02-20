"""Filesystem watcher using watchdog library for vault/Watch/ monitoring."""

import os
import queue
import threading
import time
from typing import Any

from watchdog.events import (
    FileSystemEventHandler,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
)
from watchdog.observers import Observer

from src.watchers.base_watcher import BaseWatcher

# Maximum file size to process (10 MB)
_MAX_FILE_BYTES = 10 * 1024 * 1024


class _WatchHandler(FileSystemEventHandler):
    """Queues file system events as (event_type, path) tuples."""

    def __init__(self) -> None:
        super().__init__()
        self._queue: queue.Queue[tuple[str, str]] = queue.Queue()

    def on_created(self, event: FileCreatedEvent) -> None:
        if not event.is_directory:
            self._queue.put(("created", event.src_path))

    def on_modified(self, event: FileModifiedEvent) -> None:
        if not event.is_directory:
            self._queue.put(("modified", event.src_path))

    def on_deleted(self, event: FileDeletedEvent) -> None:
        if not event.is_directory:
            self._queue.put(("deleted", event.src_path))

    def on_moved(self, event: FileMovedEvent) -> None:
        """Rename/move: old path deleted, new path created."""
        if not event.is_directory:
            self._queue.put(("deleted", event.src_path))
            self._queue.put(("created", event.dest_path))

    def get_queued(self) -> list[tuple[str, str]]:
        """Drain and return all queued (event_type, path) tuples."""
        events: list[tuple[str, str]] = []
        while not self._queue.empty():
            try:
                events.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return events


class FilesystemWatcher(BaseWatcher):
    """Watches vault/Watch/ for file changes using watchdog.

    Features:
    - Detects file creation, modification, deletion, and rename/move
    - Debounces rapid repeated events per path (last event wins)
    - Purges processed state on deletion so same filename can re-enter pipeline
    - Stability check: skips files modified too recently (mtime-based, non-blocking)
    - Auto-restarts the watchdog observer if it dies unexpectedly
    - Max file size guard: skips files larger than 10 MB
    - Extension filtering: optional allowlist of extensions to process
    - Configurable recursive subdirectory watching
    """

    def __init__(
        self,
        vault_root: str,
        poll_interval: int = 5,
        stability_wait: float = 0.0,
        allowed_extensions: set[str] | None = None,
        recursive: bool = False,
    ) -> None:
        super().__init__("filesystem_watcher", vault_root, poll_interval)
        self.watch_folder = os.path.join(vault_root, "Watch")
        self.stability_wait = stability_wait
        self.allowed_extensions = allowed_extensions  # None = allow all non-dotfiles
        self.recursive = recursive
        self._handler = _WatchHandler()
        self._observer: Observer | None = None
        self._observer_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Observer lifecycle
    # ------------------------------------------------------------------

    def start_observer(self) -> None:
        """Start the watchdog observer in a background thread."""
        os.makedirs(self.watch_folder, exist_ok=True)
        with self._observer_lock:
            self._observer = Observer()
            self._observer.schedule(
                self._handler, self.watch_folder, recursive=self.recursive
            )
            self._observer.daemon = True
            self._observer.start()

    def stop_observer(self) -> None:
        """Stop the watchdog observer."""
        with self._observer_lock:
            if self._observer is not None:
                self._observer.stop()
                self._observer.join(timeout=5)
                self._observer = None

    def _ensure_observer_alive(self) -> None:
        """Auto-restart the observer if it has died unexpectedly."""
        with self._observer_lock:
            if self._observer is not None and not self._observer.is_alive():
                self._observer = None
        if self._observer is None and self._running:
            self.start_observer()

    # ------------------------------------------------------------------
    # Core update detection
    # ------------------------------------------------------------------

    def check_for_updates(self) -> list[dict[str, Any]]:
        """Check for file changes in Watch/ folder.

        Steps:
        1. Auto-restart observer if dead.
        2. Drain watchdog event queue, debouncing per path (last event wins).
        3. Handle deletions: purge processed state for deleted files.
        4. Fallback directory scan for files missed before observer started.
        5. Apply stability, size, and extension filters.
        6. Return new unprocessed items.
        """
        self._ensure_observer_alive()

        # Step 1: Drain + debounce — last event type per path wins
        event_map: dict[str, str] = {}
        for event_type, raw_path in self._handler.get_queued():
            norm = os.path.normpath(raw_path)
            event_map[norm] = event_type

        # Step 2: Handle deletions — clear state so file can re-enter pipeline
        for norm_path, event_type in event_map.items():
            if event_type == "deleted":
                self._on_file_deleted(norm_path)

        # Step 3: Collect candidate paths from events + directory scan
        candidate_paths: set[str] = set()

        for norm_path, event_type in event_map.items():
            if event_type in ("created", "modified") and os.path.isfile(norm_path):
                candidate_paths.add(norm_path)

        if os.path.isdir(self.watch_folder):
            for fname in os.listdir(self.watch_folder):
                if fname.startswith("."):
                    continue
                fpath = os.path.normpath(os.path.join(self.watch_folder, fname))
                if os.path.isfile(fpath):
                    candidate_paths.add(fpath)

        # Step 4: Filter and build items
        items: list[dict[str, Any]] = []
        for fpath in candidate_paths:
            fname = os.path.basename(fpath)

            if not self._is_allowed_extension(fname):
                continue

            if not self._is_stable(fpath):
                continue

            item_id = self._make_item_id(fpath)
            if self.is_processed(item_id):
                continue

            content, item_type = self._read_file_content(fpath)
            items.append({
                "id": item_id,
                "name": fname,
                "path": fpath,
                "filename": fname,
                "content": content,
                "type": item_type,
                "priority": "MEDIUM",
                "tags": [],
            })

        return items

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _on_file_deleted(self, norm_path: str) -> None:
        """Purge processed IDs for a deleted file.

        Allows a new file with the same name to re-enter the pipeline
        instead of being silently skipped by the dedup check.
        """
        fname = os.path.basename(norm_path)
        name = os.path.splitext(fname)[0]
        prefix = f"FILE_{name}_"
        self._processed_ids = {
            pid for pid in self._processed_ids if not pid.startswith(prefix)
        }

    def _is_stable(self, filepath: str) -> bool:
        """Return True if the file has not been modified within stability_wait seconds.

        Non-blocking: uses mtime comparison rather than sleeping.
        Files that are still being written will be picked up on the next scan cycle.
        """
        if self.stability_wait <= 0:
            return True
        try:
            mtime = os.path.getmtime(filepath)
            return (time.time() - mtime) >= self.stability_wait
        except OSError:
            return False

    def _is_allowed_extension(self, filename: str) -> bool:
        """Return True if the extension is permitted.

        When allowed_extensions is None, all non-dotfiles are permitted.
        When set, only files whose extension (lowercased) is in the set pass.
        """
        if filename.startswith("."):
            return False
        if self.allowed_extensions is None:
            return True
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.allowed_extensions

    def _make_item_id(self, filepath: str) -> str:
        """Stable item ID from filename + mtime.

        Same file → same ID across scans (dedup).
        File overwritten → new mtime → new ID (re-processed).
        """
        fname = os.path.basename(filepath)
        name = os.path.splitext(fname)[0]
        try:
            mtime = int(os.path.getmtime(filepath))
        except OSError:
            mtime = 0
        return f"FILE_{name}_{mtime}"

    def _read_file_content(self, filepath: str) -> tuple[str, str]:
        """Read file content with guards for empty, oversized, and binary files."""
        try:
            size = os.path.getsize(filepath)
            if size == 0:
                return "[Empty file]", "unknown"
            if size > _MAX_FILE_BYTES:
                mb = size / (1024 * 1024)
                return f"[File too large — {mb:.1f} MB exceeds 10 MB limit]", "unknown"
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            return content, "general"
        except (UnicodeDecodeError, PermissionError):
            return "[Binary file — cannot display]", "unknown"
