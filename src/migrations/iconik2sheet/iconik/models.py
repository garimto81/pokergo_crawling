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

    # Subclip 관련 필드
    type: str | None = None  # "ASSET" or "SUBCLIP"
    time_start_milliseconds: int | None = None  # Subclip 시작 시간
    time_end_milliseconds: int | None = None  # Subclip 종료 시간
    original_asset_id: str | None = None  # Parent Asset ID (for subclips)


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


class IconikJob(BaseModel):
    """Iconik Job model for ISG/transfer/transcode jobs."""

    model_config = {"from_attributes": True}

    id: str
    title: str | None = None
    status: str  # STARTED, FINISHED, FAILED, ABORTED
    type: str  # TRANSFER, TRANSCODE, DELETE, ANALYZE, etc.
    object_id: str | None = None  # Related Asset ID
    object_type: str | None = None  # "assets", "collections", etc.
    progress: int = 0  # 0-100
    error_message: str | None = None
    message: str | None = None
    storage_id: str | None = None
    date_created: datetime | None = None
    date_modified: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class IconikJobSummary(BaseModel):
    """Job statistics summary for reporting."""

    total: int = 0
    started: int = 0
    finished: int = 0
    failed: int = 0
    aborted: int = 0
    by_type: dict[str, int] = {}
    by_storage: dict[str, int] = {}


class IconikAssetExport(BaseModel):
    """35-column export model matching GGmetadata_and_timestamps structure.

    This model represents the output format for Google Sheets export.
    Column names match GGmetadata_and_timestamps exactly.
    """

    # Basic info (2)
    id: str
    title: str

    # Timecode (4) - from Segments API
    time_start_ms: int | None = None
    time_end_ms: int | None = None
    time_start_S: float | None = None  # Calculated: ms / 1000
    time_end_S: float | None = None  # Calculated: ms / 1000

    # Metadata fields (29) - from Metadata API
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

    # Additional fields (9) - matching GGmetadata_and_timestamps
    SceneryObject: str | None = None
    gcvi_tags: str | None = None  # API field: _gcvi_tags (underscore removed for Pydantic)
    Badbeat: str | None = None
    Bluff: str | None = None
    Suckout: str | None = None
    Cooler: str | None = None
    RUNOUTTag: str | None = None
    PostFlop: str | None = None
    All_in: str | None = None  # Note: 'All-in' renamed to 'All_in' for Python compatibility
