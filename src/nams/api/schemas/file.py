"""File Pydantic schemas for NAMS API."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NasFileBase(BaseModel):
    """Base NAS file schema."""
    filename: str
    extension: str
    size_bytes: int
    directory: Optional[str] = None
    full_path: Optional[str] = None
    modified_at: Optional[datetime] = None


class NasFileCreate(NasFileBase):
    """NAS file creation schema."""
    year: Optional[int] = None
    region_id: Optional[int] = None
    event_type_id: Optional[int] = None
    episode: Optional[int] = None
    matched_pattern_id: Optional[int] = None
    extraction_confidence: Optional[float] = None


class NasFileUpdate(BaseModel):
    """NAS file update schema."""
    year: Optional[int] = None
    region_id: Optional[int] = None
    event_type_id: Optional[int] = None
    episode: Optional[int] = None
    asset_group_id: Optional[int] = None
    role: Optional[str] = None
    role_priority: Optional[int] = None


class NasFileOverride(BaseModel):
    """Manual override request."""
    year: Optional[int] = None
    region_id: Optional[int] = None
    event_type_id: Optional[int] = None
    episode: Optional[int] = None
    reason: str


class NasFileMoveRequest(BaseModel):
    """File move request."""
    target_group_id: int
    role: str = "backup"
    reason: Optional[str] = None


class NasFileBulkUpdate(BaseModel):
    """Bulk update request."""
    file_ids: list[int]
    year: Optional[int] = None
    region_id: Optional[int] = None
    event_type_id: Optional[int] = None
    asset_group_id: Optional[int] = None


class NasFileResponse(NasFileBase):
    """NAS file response schema."""
    id: int
    year: Optional[int] = None
    region_id: Optional[int] = None
    event_type_id: Optional[int] = None
    episode: Optional[int] = None
    matched_pattern_id: Optional[int] = None
    extraction_confidence: Optional[float] = None
    is_manual_override: bool = False
    override_reason: Optional[str] = None
    asset_group_id: Optional[int] = None
    role: str = "backup"
    role_priority: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    # Expanded fields (optional)
    region_code: Optional[str] = None
    event_type_code: Optional[str] = None
    pattern_name: Optional[str] = None
    group_id: Optional[str] = None
    size_formatted: Optional[str] = None

    class Config:
        from_attributes = True


class NasFileListResponse(BaseModel):
    """File list item (lighter version)."""
    id: int
    filename: str
    size_bytes: int
    size_formatted: str
    year: Optional[int] = None
    region_code: Optional[str] = None
    event_type_code: Optional[str] = None
    episode: Optional[int] = None
    group_id: Optional[str] = None
    role: str = "backup"
    is_manual_override: bool = False

    class Config:
        from_attributes = True


class FileFilter(BaseModel):
    """File filter parameters."""
    year: Optional[int] = None
    region_id: Optional[int] = None
    event_type_id: Optional[int] = None
    group_id: Optional[int] = None
    has_group: Optional[bool] = None
    is_primary: Optional[bool] = None
    is_manual_override: Optional[bool] = None
    search: Optional[str] = None
