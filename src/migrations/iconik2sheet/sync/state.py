"""Sync state management."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from config.settings import get_settings

# Checksum storage limits (to prevent unbounded growth)
MAX_CHECKSUMS = 10000
FULL_SYNC_INTERVAL_DAYS = 7


class SyncStateData(BaseModel):
    """Sync state data model."""

    last_sync_at: datetime | None = None
    last_sync_type: str | None = None
    total_assets: int = 0
    total_collections: int = 0

    # Incremental sync fields
    last_full_sync_at: datetime | None = None
    asset_checksums: dict[str, str] = Field(default_factory=dict)
    row_checksums: dict[str, str] = Field(default_factory=dict)


class SyncState:
    """Manages sync state persistence."""

    def __init__(self) -> None:
        settings = get_settings()
        self.state_file = Path(settings.state_file)
        self._data: SyncStateData | None = None

    @property
    def data(self) -> SyncStateData:
        """Get or load state data."""
        if self._data is None:
            self._data = self._load()
        return self._data

    def _load(self) -> SyncStateData:
        """Load state from file."""
        if not self.state_file.exists():
            return SyncStateData()

        try:
            with open(self.state_file, encoding="utf-8") as f:
                data = json.load(f)
                return SyncStateData(**data)
        except Exception:
            return SyncStateData()

    def save(self) -> None:
        """Save state to file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.data.model_dump(mode="json"), f, indent=2, default=str)

    def update(self, **kwargs: Any) -> None:
        """Update state fields and save."""
        for key, value in kwargs.items():
            if hasattr(self.data, key):
                setattr(self.data, key, value)
        self.save()

    def mark_sync_complete(self, sync_type: str, total_assets: int, total_collections: int) -> None:
        """Mark sync as complete."""
        self.update(
            last_sync_at=datetime.now(),
            last_sync_type=sync_type,
            total_assets=total_assets,
            total_collections=total_collections,
        )

    # ============================================================
    # Incremental sync methods
    # ============================================================

    def needs_asset_update(self, asset_id: str, current_checksum: str) -> bool:
        """Check if asset needs update based on checksum comparison.

        Args:
            asset_id: Asset ID to check
            current_checksum: Current checksum of asset data

        Returns:
            True if asset needs update (checksum changed or new)
        """
        return self.data.asset_checksums.get(asset_id) != current_checksum

    def update_asset_checksum(self, asset_id: str, checksum: str) -> None:
        """Update asset checksum in state.

        Args:
            asset_id: Asset ID
            checksum: New checksum value
        """
        self.data.asset_checksums[asset_id] = checksum

    def remove_asset_checksum(self, asset_id: str) -> None:
        """Remove asset checksum from state.

        Args:
            asset_id: Asset ID to remove
        """
        self.data.asset_checksums.pop(asset_id, None)

    def needs_row_update(self, asset_id: str, current_checksum: str) -> bool:
        """Check if row needs update based on checksum comparison.

        Args:
            asset_id: Asset ID (row key)
            current_checksum: Current checksum of row data

        Returns:
            True if row needs update (checksum changed or new)
        """
        return self.data.row_checksums.get(asset_id) != current_checksum

    def update_row_checksum(self, asset_id: str, checksum: str) -> None:
        """Update row checksum in state.

        Args:
            asset_id: Asset ID (row key)
            checksum: New checksum value
        """
        self.data.row_checksums[asset_id] = checksum

    def should_force_full_sync(self) -> bool:
        """Check if full sync should be forced.

        Returns:
            True if:
            - No asset checksums (first run)
            - Last full sync was more than FULL_SYNC_INTERVAL_DAYS ago
        """
        if not self.data.asset_checksums:
            return True

        if self.data.last_full_sync_at is None:
            return True

        days_since_full = (datetime.now() - self.data.last_full_sync_at).days
        return days_since_full >= FULL_SYNC_INTERVAL_DAYS

    def mark_full_sync_complete(self) -> None:
        """Mark that a full sync was completed."""
        self.data.last_full_sync_at = datetime.now()
        self.save()

    def clear_checksums(self) -> None:
        """Clear all checksums (for fresh full sync)."""
        self.data.asset_checksums = {}
        self.data.row_checksums = {}
        self.save()

    def get_checksum_stats(self) -> dict[str, int]:
        """Get statistics about stored checksums.

        Returns:
            Dict with asset_count, row_count
        """
        return {
            "asset_count": len(self.data.asset_checksums),
            "row_count": len(self.data.row_checksums),
        }
