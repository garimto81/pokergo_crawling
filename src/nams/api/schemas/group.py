"""Group Pydantic schemas for NAMS API."""
from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class AssetGroupBase(BaseModel):
    """Base asset group schema."""
    group_id: str
    year: int
    region_id: Optional[int] = None
    event_type_id: Optional[int] = None
    episode: Optional[int] = None


class AssetGroupCreate(AssetGroupBase):
    """Asset group creation schema."""
    pass


class AssetGroupUpdate(BaseModel):
    """Asset group update schema."""
    year: Optional[int] = None
    region_id: Optional[int] = None
    event_type_id: Optional[int] = None
    episode: Optional[int] = None
    pokergo_episode_id: Optional[str] = None
    pokergo_title: Optional[str] = None
    pokergo_match_score: Optional[float] = None


class AssetGroupResponse(AssetGroupBase):
    """Asset group response schema."""
    id: int
    pokergo_episode_id: Optional[str] = None
    pokergo_title: Optional[str] = None
    pokergo_match_score: Optional[float] = None
    file_count: int = 0
    total_size_bytes: int = 0
    has_backup: bool = False
    created_at: datetime
    updated_at: datetime

    # Expanded fields
    region_code: Optional[str] = None
    event_type_code: Optional[str] = None
    total_size_formatted: Optional[str] = None

    class Config:
        from_attributes = True


class AssetGroupListResponse(BaseModel):
    """Group list item (lighter version)."""
    id: int
    group_id: str
    year: int
    region_code: Optional[str] = None
    event_type_code: Optional[str] = None
    episode: Optional[int] = None
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
    year: Optional[int] = None
    region_id: Optional[int] = None
    event_type_id: Optional[int] = None
    has_pokergo_match: Optional[bool] = None
    has_backup: Optional[bool] = None
    min_file_count: Optional[int] = None
    search: Optional[str] = None


# Import at the end to avoid circular imports
from .file import NasFileListResponse
AssetGroupDetailResponse.model_rebuild()
