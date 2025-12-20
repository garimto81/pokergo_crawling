"""Iconik data models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class IconikAsset(BaseModel):
    """Iconik Asset model."""

    model_config = {"from_attributes": True}

    id: str
    title: str
    external_id: str | None = None
    status: str = "ACTIVE"
    is_online: bool = True
    analyze_status: str | None = None
    archive_status: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


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


class IconikMetadataView(BaseModel):
    """Iconik Metadata View model."""

    id: str
    name: str
    description: str | None = None
    view_fields: list[dict[str, Any]] = []


class IconikSegment(BaseModel):
    """Iconik Segment model for timecodes."""

    id: str
    asset_id: str
    time_base: int | None = None  # Start time in milliseconds
    time_end: int | None = None  # End time in milliseconds
    segment_type: str = "GENERIC"


class IconikAssetExport(BaseModel):
    """26-column export model matching PRD specification.

    This model represents the output format for Google Sheets export.
    Column names match the PRD exactly.
    """

    # Basic info
    id: str
    title: str

    # Timecode (from Segments API)
    time_start_ms: int | None = None
    time_end_ms: int | None = None
    time_start_S: float | None = None  # Calculated: ms / 1000
    time_end_S: float | None = None  # Calculated: ms / 1000

    # Metadata fields (from Metadata API)
    Description: str | None = None
    ProjectName: str | None = None
    ProjectNameTag: str | None = None
    SearchTag: str | None = None
    Year_: int | None = None
    Location: str | None = None
    Venue: str | None = None
    EpisodeEvent: str | None = None
    Source: str | None = None
    Scene: str | None = None
    GameType: str | None = None
    PlayersTags: str | None = None
    HandGrade: str | None = None
    HANDTag: str | None = None
    EPICHAND: bool | None = None
    Tournament: str | None = None
    PokerPlayTags: str | None = None
    Adjective: str | None = None
    Emotion: str | None = None
    AppearanceOutfit: str | None = None
