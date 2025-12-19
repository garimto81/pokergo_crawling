"""File Pydantic schemas for NAMS API."""
from datetime import datetime

from pydantic import BaseModel


class NasFileBase(BaseModel):
    """Base NAS file schema."""
    filename: str
    extension: str
    size_bytes: int
    directory: str | None = None
    full_path: str | None = None
    modified_at: datetime | None = None


class NasFileCreate(NasFileBase):
    """NAS file creation schema."""
    year: int | None = None
    region_id: int | None = None
    event_type_id: int | None = None
    episode: int | None = None
    matched_pattern_id: int | None = None
    extraction_confidence: float | None = None


class NasFileUpdate(BaseModel):
    """NAS file update schema."""
    year: int | None = None
    region_id: int | None = None
    event_type_id: int | None = None
    episode: int | None = None
    asset_group_id: int | None = None
    role: str | None = None
    role_priority: int | None = None


class NasFileOverride(BaseModel):
    """Manual override request."""
    year: int | None = None
    region_id: int | None = None
    event_type_id: int | None = None
    episode: int | None = None
    reason: str


class NasFileMoveRequest(BaseModel):
    """File move request."""
    target_group_id: int
    role: str = "backup"
    reason: str | None = None


class NasFileBulkUpdate(BaseModel):
    """Bulk update request."""
    file_ids: list[int]
    year: int | None = None
    region_id: int | None = None
    event_type_id: int | None = None
    asset_group_id: int | None = None


class NasFileResponse(NasFileBase):
    """NAS file response schema."""
    id: int
    year: int | None = None
    region_id: int | None = None
    event_type_id: int | None = None
    episode: int | None = None
    matched_pattern_id: int | None = None
    extraction_confidence: float | None = None
    is_manual_override: bool = False
    override_reason: str | None = None
    asset_group_id: int | None = None
    role: str = "backup"
    role_priority: int | None = None
    created_at: datetime
    updated_at: datetime

    # Expanded fields (optional)
    region_code: str | None = None
    event_type_code: str | None = None
    pattern_name: str | None = None
    group_id: str | None = None
    size_formatted: str | None = None

    class Config:
        from_attributes = True


class NasFileListResponse(BaseModel):
    """File list item (lighter version)."""
    id: int
    filename: str
    size_bytes: int
    size_formatted: str
    year: int | None = None
    region_code: str | None = None
    event_type_code: str | None = None
    episode: int | None = None
    group_id: str | None = None
    role: str = "backup"
    is_manual_override: bool = False

    class Config:
        from_attributes = True


class FileFilter(BaseModel):
    """File filter parameters."""
    year: int | None = None
    region_id: int | None = None
    event_type_id: int | None = None
    group_id: int | None = None
    has_group: bool | None = None
    is_primary: bool | None = None
    is_manual_override: bool | None = None
    search: str | None = None
