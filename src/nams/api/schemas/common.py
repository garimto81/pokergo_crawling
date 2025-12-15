"""Common Pydantic schemas for NAMS API."""
from typing import Optional, Generic, TypeVar
from pydantic import BaseModel
from datetime import datetime

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = 1
    page_size: int = 50


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None


# Region schemas
class RegionBase(BaseModel):
    """Base region schema."""
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool = True


class RegionCreate(RegionBase):
    """Region creation schema."""
    pass


class RegionUpdate(BaseModel):
    """Region update schema."""
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class RegionResponse(RegionBase):
    """Region response schema."""
    id: int

    class Config:
        from_attributes = True


# Event Type schemas
class EventTypeBase(BaseModel):
    """Base event type schema."""
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool = True


class EventTypeCreate(EventTypeBase):
    """Event type creation schema."""
    pass


class EventTypeUpdate(BaseModel):
    """Event type update schema."""
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class EventTypeResponse(EventTypeBase):
    """Event type response schema."""
    id: int

    class Config:
        from_attributes = True


# Stats schemas
class OverviewStats(BaseModel):
    """Overview statistics."""
    total_files: int
    total_groups: int
    total_size_bytes: int
    total_size_formatted: str
    matched_files: int
    unmatched_files: int
    match_rate: float
    pokergo_matched_groups: int
    pokergo_match_rate: float


class YearStats(BaseModel):
    """Statistics by year."""
    year: int
    file_count: int
    group_count: int
    size_bytes: int
    size_formatted: str


class RegionStats(BaseModel):
    """Statistics by region."""
    region_code: str
    region_name: str
    file_count: int
    group_count: int
    size_bytes: int
