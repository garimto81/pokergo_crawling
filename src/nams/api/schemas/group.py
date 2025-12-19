"""Group Pydantic schemas for NAMS API."""
from datetime import datetime

from pydantic import BaseModel


class AssetGroupBase(BaseModel):
    """Base asset group schema."""
    group_id: str
    year: int
    region_id: int | None = None
    event_type_id: int | None = None
    episode: int | None = None


class AssetGroupCreate(AssetGroupBase):
    """Asset group creation schema."""
    pass


class AssetGroupUpdate(BaseModel):
    """Asset group update schema."""
    year: int | None = None
    region_id: int | None = None
    event_type_id: int | None = None
    episode: int | None = None
    pokergo_episode_id: str | None = None
    pokergo_title: str | None = None
    pokergo_match_score: float | None = None
    catalog_title: str | None = None
    catalog_title_manual: bool | None = None


class AssetGroupResponse(AssetGroupBase):
    """Asset group response schema."""
    id: int
    pokergo_episode_id: str | None = None
    pokergo_title: str | None = None
    pokergo_match_score: float | None = None
    catalog_title: str | None = None
    catalog_title_manual: bool = False
    match_category: str | None = None  # MATCHED, NAS_ONLY_HISTORIC, NAS_ONLY_MODERN
    file_count: int = 0
    total_size_bytes: int = 0
    has_backup: bool = False
    created_at: datetime
    updated_at: datetime

    # Expanded fields
    region_code: str | None = None
    event_type_code: str | None = None
    total_size_formatted: str | None = None

    class Config:
        from_attributes = True


class AssetGroupListResponse(BaseModel):
    """Group list item (lighter version)."""
    id: int
    group_id: str
    year: int
    region_code: str | None = None
    event_type_code: str | None = None
    episode: int | None = None
    catalog_title: str | None = None
    match_category: str | None = None  # MATCHED, NAS_ONLY_HISTORIC, NAS_ONLY_MODERN
    file_count: int = 0
    total_size_formatted: str = "0 B"
    has_backup: bool = False
    has_pokergo_match: bool = False

    class Config:
        from_attributes = True


class AssetGroupDetailResponse(AssetGroupResponse):
    """Asset group detail with files."""
    files: list["NasFileListResponse"] = []


class GroupSetPrimaryRequest(BaseModel):
    """Set primary file request."""
    file_id: int


class GroupMergeRequest(BaseModel):
    """Merge groups request."""
    source_group_ids: list[int]
    target_group_id: int


class GroupSplitRequest(BaseModel):
    """Split group request."""
    file_ids: list[int]
    new_group_id: str


class GroupFilter(BaseModel):
    """Group filter parameters."""
    year: int | None = None
    region_id: int | None = None
    event_type_id: int | None = None
    has_pokergo_match: bool | None = None
    has_backup: bool | None = None
    min_file_count: int | None = None
    search: str | None = None


# Import at the end to avoid circular imports
from .file import NasFileListResponse  # noqa: E402

AssetGroupDetailResponse.model_rebuild()
