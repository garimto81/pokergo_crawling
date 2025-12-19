"""Iconik data models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class IconikAsset(BaseModel):
    """Iconik Asset model."""

    id: str
    title: str
    external_id: str | None = None
    status: str = "ACTIVE"
    is_online: bool = True
    analyze_status: str | None = None
    archive_status: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class IconikMetadata(BaseModel):
    """Iconik Metadata model."""

    asset_id: str
    view_id: str
    fields: dict[str, Any] = {}


class IconikCollection(BaseModel):
    """Iconik Collection model."""

    id: str
    title: str
    parent_id: str | None = None
    is_root: bool = False
    created_at: datetime | None = None


class IconikPaginatedResponse(BaseModel):
    """Paginated API response."""

    objects: list[dict[str, Any]]
    page: int
    pages: int
    per_page: int
    total: int
    first_id: str | None = None
    last_id: str | None = None
