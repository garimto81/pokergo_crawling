"""Pydantic schemas for Category and CategoryEntry."""
from datetime import datetime

from pydantic import BaseModel

# =============================================================================
# Category Schemas
# =============================================================================

class CategoryBase(BaseModel):
    """Category 기본 스키마."""
    code: str
    name: str
    year: int
    region: str | None = None
    source: str | None = 'NAS_ONLY'
    pokergo_category: str | None = None
    description: str | None = None


class CategoryResponse(CategoryBase):
    """Category 응답 스키마."""
    id: int
    entry_count: int | None = 0
    file_count: int | None = 0
    total_size_gb: float | None = 0.0
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    """Category 목록 응답."""
    items: list[CategoryResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# CategoryEntry Schemas
# =============================================================================

class CategoryEntryBase(BaseModel):
    """CategoryEntry 기본 스키마."""
    entry_code: str
    display_title: str | None = None
    year: int
    event_type: str | None = None
    event_name: str | None = None
    sequence: int | None = None
    sequence_type: str | None = None


class CategoryEntryResponse(CategoryEntryBase):
    """CategoryEntry 응답 스키마."""
    id: int
    category_id: int | None = None
    source: str | None = None
    pokergo_ep_id: str | None = None
    pokergo_title: str | None = None
    match_type: str | None = None
    match_score: float | None = None
    verified: bool = False
    verified_at: datetime | None = None
    verified_by: str | None = None
    notes: str | None = None
    file_count: int | None = 0
    total_size_bytes: int | None = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class CategoryEntryUpdate(BaseModel):
    """CategoryEntry 수정 스키마."""
    display_title: str | None = None
    pokergo_ep_id: str | None = None
    match_type: str | None = None
    verified: bool | None = None
    notes: str | None = None


class CategoryEntryVerifyRequest(BaseModel):
    """검증 요청 스키마."""
    verified_by: str | None = 'system'
    notes: str | None = None


class CategoryEntryBatchVerifyRequest(BaseModel):
    """일괄 검증 요청 스키마."""
    entry_ids: list[int]
    verified_by: str | None = 'system'


class CategoryEntryListResponse(BaseModel):
    """CategoryEntry 목록 응답."""
    items: list[CategoryEntryResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# File Info for Entry Detail
# =============================================================================

class EntryFileInfo(BaseModel):
    """Entry에 연결된 파일 정보."""
    id: int
    file_id: str | None = None
    filename: str
    drive: str | None = None
    folder: str | None = None
    size_bytes: int
    role: str | None = None
    is_excluded: bool = False

    class Config:
        from_attributes = True


class CategoryEntryDetailResponse(CategoryEntryResponse):
    """CategoryEntry 상세 응답 (파일 포함)."""
    category_name: str | None = None
    files: list[EntryFileInfo] = []


# =============================================================================
# Statistics Schemas
# =============================================================================

class MatchTypeStats(BaseModel):
    """매칭 유형별 통계."""
    exact: int = 0
    partial: int = 0
    manual: int = 0
    none: int = 0


class SourceStats(BaseModel):
    """Source별 통계."""
    pokergo: int = 0
    nas_only: int = 0


class KPIStats(BaseModel):
    """KPI 통계."""
    total_entries: int = 0
    total_files: int = 0
    active_files: int = 0

    # KPI 지표
    category_coverage: float = 0.0  # Entry 연결 파일 / Active 파일
    title_completeness: float = 0.0  # display_title 있는 Entry / 전체
    pokergo_utilization: float = 0.0  # source=POKERGO / 전체
    verification_rate: float = 0.0  # verified=true / 전체

    # 상세
    match_type_stats: MatchTypeStats = MatchTypeStats()
    source_stats: SourceStats = SourceStats()
    verification_needed: int = 0  # PARTIAL & not verified


class TitleGenerationResult(BaseModel):
    """제목 생성 결과."""
    total: int = 0
    improved: int = 0
    ai_generated: int = 0
    pattern_generated: int = 0
    unchanged: int = 0
    samples: list[dict] = []


# =============================================================================
# Content Explorer Tree Schemas
# =============================================================================

class TreeEntry(BaseModel):
    """트리 내 Entry 항목."""
    id: int
    entry_code: str
    display_title: str | None = None
    pokergo_title: str | None = None
    match_type: str | None = None
    match_score: float | None = None
    file_count: int = 0
    total_size_gb: float = 0.0


class TreeEventType(BaseModel):
    """트리 내 EventType 노드."""
    code: str
    name: str
    entry_count: int = 0
    exact_count: int = 0
    none_count: int = 0
    entries: list[TreeEntry] = []


class TreeCategory(BaseModel):
    """트리 내 Category 노드."""
    id: int
    code: str
    name: str
    region: str | None = None
    entry_count: int = 0
    exact_count: int = 0
    none_count: int = 0
    event_types: list[TreeEventType] = []


class TreeYear(BaseModel):
    """트리 내 Year 노드."""
    year: int
    entry_count: int = 0
    exact_count: int = 0
    none_count: int = 0
    total_size_gb: float = 0.0
    categories: list[TreeCategory] = []


class ContentTreeResponse(BaseModel):
    """Content Explorer 트리 전체 응답."""
    years: list[TreeYear]
    summary: dict = {}


class YearSummary(BaseModel):
    """연도별 요약."""
    year: int
    entry_count: int = 0
    exact_count: int = 0
    none_count: int = 0
    total_size_gb: float = 0.0
    categories: int = 0
