"""NAS scan incremental state management.

Tracks file fingerprints (mtime + size) to detect changes
between scans without requiring full file comparison.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

# State file location
STATE_FILE = Path(__file__).parent.parent / "data" / "nams" / "scan_state.json"


@dataclass
class IncrementalScanState:
    """State for incremental NAS scanning.

    Stores file fingerprints to detect changes between scans.
    Fingerprint format: "mtime:size" for fast comparison.
    """

    last_scan_at: str | None = None
    file_fingerprints: dict[str, str] = field(default_factory=dict)
    # key: full_path, value: "mtime:size"

    @classmethod
    def load(cls) -> "IncrementalScanState":
        """Load state from file."""
        if not STATE_FILE.exists():
            return cls()

        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        except (json.JSONDecodeError, TypeError, KeyError):
            return cls()

    def save(self) -> None:
        """Save state to file."""
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    def calculate_fingerprint(self, mtime: float, size: int) -> str:
        """Calculate file fingerprint from mtime and size.

        Args:
            mtime: File modification time (timestamp)
            size: File size in bytes

        Returns:
            Fingerprint string in format "mtime:size"
        """
        return f"{mtime}:{size}"

    def is_changed(self, full_path: str, fingerprint: str) -> bool:
        """Check if file has changed based on fingerprint.

        Args:
            full_path: Full file path
            fingerprint: Current fingerprint

        Returns:
            True if file is new or changed
        """
        return self.file_fingerprints.get(full_path) != fingerprint

    def update(self, full_path: str, fingerprint: str) -> None:
        """Update fingerprint for a file.

        Args:
            full_path: Full file path
            fingerprint: New fingerprint
        """
        self.file_fingerprints[full_path] = fingerprint

    def remove(self, full_path: str) -> None:
        """Remove fingerprint for a file.

        Args:
            full_path: Full file path to remove
        """
        self.file_fingerprints.pop(full_path, None)

    def mark_scan_complete(self) -> None:
        """Mark current scan as complete."""
        self.last_scan_at = datetime.now().isoformat()
        self.save()

    def get_stats(self) -> dict[str, int]:
        """Get statistics about stored fingerprints.

        Returns:
            Dict with fingerprint_count, last_scan_at
        """
        return {
            "fingerprint_count": len(self.file_fingerprints),
            "last_scan_at": self.last_scan_at,
        }

    def clear(self) -> None:
        """Clear all fingerprints for fresh full scan."""
        self.file_fingerprints = {}
        self.last_scan_at = None
        self.save()


def detect_changed_files(
    scanned_files: list[dict],
    state: IncrementalScanState,
) -> tuple[list[dict], list[dict], list[str]]:
    """Detect changed, new, and deleted files.

    Args:
        scanned_files: List of file dicts from current scan
            Each dict should have: full_path, modified_at (timestamp), size
        state: Current scan state with fingerprints

    Returns:
        Tuple of (new_files, changed_files, deleted_paths)
    """
    new_files = []
    changed_files = []
    current_paths = set()

    for file_info in scanned_files:
        full_path = file_info.get("full_path", "")
        mtime = file_info.get("modified_at", 0)
        size = file_info.get("size", 0)

        if not full_path:
            continue

        current_paths.add(full_path)
        fingerprint = state.calculate_fingerprint(mtime, size)

        existing_fp = state.file_fingerprints.get(full_path)

        if existing_fp is None:
            # New file
            new_files.append(file_info)
            state.update(full_path, fingerprint)
        elif existing_fp != fingerprint:
            # Changed file
            changed_files.append(file_info)
            state.update(full_path, fingerprint)
        # else: unchanged, skip

    # Detect deleted files
    deleted_paths = []
    for stored_path in list(state.file_fingerprints.keys()):
        if stored_path not in current_paths:
            deleted_paths.append(stored_path)
            state.remove(stored_path)

    return new_files, changed_files, deleted_paths
