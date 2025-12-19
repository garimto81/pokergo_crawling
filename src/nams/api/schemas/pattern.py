"""Pattern Pydantic schemas for NAMS API."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PatternBase(BaseModel):
    """Base pattern schema."""
    name: str
    priority: int
    regex: str
    extract_year: bool = True
    extract_region: Optional[str] = None
    extract_type: Optional[str] = None
    extract_episode: bool = True
    description: Optional[str] = None
    is_active: bool = True


class PatternCreate(PatternBase):
    """Pattern creation schema."""
    pass


class PatternUpdate(BaseModel):
    """Pattern update schema."""
    name: Optional[str] = None
    priority: Optional[int] = None
    regex: Optional[str] = None
    extract_year: Optional[bool] = None
    extract_region: Optional[str] = None
    extract_type: Optional[str] = None
    extract_episode: Optional[bool] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


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
    pattern_name: Optional[str] = None
    extracted_year: Optional[str] = None
    extracted_region: Optional[str] = None
    extracted_type: Optional[str] = None
    extracted_episode: Optional[int] = None
    confidence: float = 0.0


class PatternAffectedFiles(BaseModel):
    """Files affected by a pattern."""
    pattern_id: int
    pattern_name: str
    affected_count: int
    sample_files: list[str]
