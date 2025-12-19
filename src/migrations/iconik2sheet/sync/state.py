"""Sync state management."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from config.settings import get_settings


class SyncStateData(BaseModel):
    """Sync state data model."""

    last_sync_at: datetime | None = None
    last_sync_type: str | None = None
    total_assets: int = 0
    total_collections: int = 0


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
            with open(self.state_file, "r", encoding="utf-8") as f:
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
