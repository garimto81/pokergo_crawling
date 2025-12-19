"""Pattern Pydantic schemas for NAMS API."""
from datetime import datetime

from pydantic import BaseModel


class PatternBase(BaseModel):
    """Base pattern schema."""
    name: str
    priority: int
    regex: str
    extract_year: bool = True
    extract_region: str | None = None
    extract_type: str | None = None
    extract_episode: bool = True
    description: str | None = None
    is_active: bool = True


class PatternCreate(PatternBase):
    """Pattern creation schema."""
    pass


class PatternUpdate(BaseModel):
    """Pattern update schema."""
    name: str | None = None
    priority: int | None = None
    regex: str | None = None
    extract_year: bool | None = None
    extract_region: str | None = None
    extract_type: str | None = None
    extract_episode: bool | None = None
    description: str | None = None
    is_active: bool | None = None


class PatternResponse(PatternBase):
    """Pattern response schema."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PatternReorder(BaseModel):
    """Pattern reorder request."""
    pattern_ids: list[int]  # Ordered list of pattern IDs


class PatternTestRequest(BaseModel):
    """Pattern test request."""
    filename: str


class PatternTestResult(BaseModel):
    """Pattern test result."""
    matched: bool
    pattern_name: str | None = None
    extracted_year: str | None = None
    extracted_region: str | None = None
    extracted_type: str | None = None
    extracted_episode: int | None = None
    confidence: float = 0.0


class PatternAffectedFiles(BaseModel):
    """Files affected by a pattern."""
    pattern_id: int
    pattern_name: str
    affected_count: int
    sample_files: list[str]
