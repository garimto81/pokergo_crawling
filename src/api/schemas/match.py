"""
Pydantic schemas for match data
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class MatchStatus(str, Enum):
    MATCHED = "MATCHED"
    LIKELY = "LIKELY"
    POSSIBLE = "POSSIBLE"
    NOT_UPLOADED = "NOT_UPLOADED"
    VERIFIED = "VERIFIED"
    WRONG_MATCH = "WRONG_MATCH"
    MANUAL_MATCH = "MANUAL_MATCH"
    UPLOAD_PLANNED = "UPLOAD_PLANNED"
    EXCLUDED = "EXCLUDED"


class MatchBase(BaseModel):
    nas_filename: str
    nas_directory: Optional[str] = None
    nas_size_bytes: Optional[int] = None
    youtube_video_id: Optional[str] = None
    youtube_title: Optional[str] = None
    match_score: int
    match_status: str
    match_details: Optional[str] = None


class MatchResponse(MatchBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MatchListResponse(BaseModel):
    items: list[MatchResponse]
    total: int
    page: int
    pages: int
    limit: int


class MatchUpdate(BaseModel):
    match_status: Optional[str] = None
    youtube_video_id: Optional[str] = None
    youtube_title: Optional[str] = None
    notes: Optional[str] = None


class BulkUpdateRequest(BaseModel):
    ids: list[int]
    status: str
    notes: Optional[str] = None


class BulkUpdateResponse(BaseModel):
    updated: int
    status: str


# Stats schemas
class StatusCount(BaseModel):
    MATCHED: int = 0
    LIKELY: int = 0
    POSSIBLE: int = 0
    NOT_UPLOADED: int = 0
    VERIFIED: int = 0
    MANUAL_MATCH: int = 0


class StatsSummary(BaseModel):
    total: int
    by_status: dict[str, int]
    match_rate: float
    avg_score: float


class CategoryCount(BaseModel):
    directory: str
    count: int
    files: list[dict]


class NotUploadedCategories(BaseModel):
    total: int
    categories: list[CategoryCount]


class ScoreDistribution(BaseModel):
    bins: list[int]
    counts: list[int]
