"""SQLAlchemy models for NAMS database."""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# =============================================================================
# NEW MODELS (Phase 1: Category System)
# =============================================================================

class Category(Base):
    """카테고리 - 연도별 시리즈 단위 (WSOP 2022, WSOP Europe 2022 등)."""
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)  # WSOP_2022, WSOP_2022_EU
    name = Column(String(200), nullable=False)  # WSOP 2022, WSOP Europe 2022
    year = Column(Integer, nullable=False)
    region = Column(String(20))  # LV, EU, APAC, PARADISE, CYPRUS
    source = Column(String(20), default='NAS_ONLY')  # POKERGO, NAS_ONLY, HYBRID
    pokergo_category = Column(String(100))  # PokerGO 원본 카테고리명
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    entries = relationship("CategoryEntry", back_populates="category")

    __table_args__ = (
        Index('idx_categories_year', 'year'),
        Index('idx_categories_region', 'region'),
    )


class CategoryEntry(Base):
    """카테고리 항목 - 개별 콘텐츠 단위 (Main Event Day 1, Bracelet #1 등)."""
    __tablename__ = 'category_entries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey('categories.id'))
    entry_code = Column(String(100), unique=True, nullable=False)  # WSOP_2022_ME_D1
    display_title = Column(String(300))  # 2022 WSOP Main Event Day 1
    year = Column(Integer, nullable=False)
    event_type = Column(String(20))  # ME, BR, HU, GM, HR
    event_name = Column(String(200))  # Main Event, Bracelet Event
    sequence = Column(Integer)  # Day/Episode/Part 번호
    sequence_type = Column(String(20))  # DAY, EPISODE, PART

    # 매칭 정보
    source = Column(String(20), default='NAS_ONLY')  # POKERGO, NAS_ONLY
    pokergo_ep_id = Column(String(50))  # PokerGO 에피소드 ID
    pokergo_title = Column(String(300))  # PokerGO 원본 제목
    match_type = Column(String(20))  # EXACT, PARTIAL, MANUAL, NONE
    match_score = Column(Float)  # 매칭 점수 (0.0 ~ 1.0)

    # 검증 정보
    verified = Column(Boolean, default=False)
    verified_at = Column(DateTime)
    verified_by = Column(String(100))
    notes = Column(Text)

    # 통계 (캐시)
    file_count = Column(Integer, default=0)
    total_size_bytes = Column(BigInteger, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("Category", back_populates="entries")
    files = relationship(
        "NasFile",
        back_populates="category_entry",
        foreign_keys="NasFile.entry_id",
    )

    __table_args__ = (
        Index('idx_category_entries_category', 'category_id'),
        Index('idx_category_entries_year', 'year'),
        Index('idx_category_entries_match_type', 'match_type'),
        Index('idx_category_entries_verified', 'verified'),
    )


class Pattern(Base):
    """패턴 정의 - 파일명에서 메타데이터 추출 규칙."""
    __tablename__ = 'patterns'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)  # P0, P9-A, PARADISE 등
    priority = Column(Integer, nullable=False)  # 실행 순서 (낮을수록 우선)
    regex = Column(Text, nullable=False)  # 정규식
    extract_year = Column(Boolean, default=True)
    extract_region = Column(String(20))  # 고정 지역 (APAC, EU, PARADISE)
    extract_type = Column(String(50))  # 고정 타입 (main_event 등)
    extract_episode = Column(Boolean, default=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    matched_files = relationship("NasFile", back_populates="matched_pattern")


class Region(Base):
    """지역 정의."""
    __tablename__ = 'regions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)  # APAC, EU, PARADISE
    name = Column(String(100), nullable=False)  # Asia Pacific, Europe, Paradise
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    # Relationships
    files = relationship("NasFile", back_populates="region")
    groups = relationship("AssetGroup", back_populates="region")


class EventType(Base):
    """이벤트 타입 정의."""
    __tablename__ = 'event_types'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)  # ME, GM, HU, BR
    name = Column(String(100), nullable=False)  # Main Event, Grudge Match
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    # Relationships
    files = relationship("NasFile", back_populates="event_type")
    groups = relationship("AssetGroup", back_populates="event_type")


class AssetGroup(Base):
    """Asset Group - 동일 콘텐츠 파일 그룹."""
    __tablename__ = 'asset_groups'

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String(50), unique=True, nullable=False)  # 2011_ME_25 or 2023_BR_E37
    year = Column(Integer, nullable=False)
    region_id = Column(Integer, ForeignKey('regions.id'))
    event_type_id = Column(Integer, ForeignKey('event_types.id'))
    episode = Column(Integer)
    event_num = Column(Integer)  # For Bracelet Events: Event #37 → 37
    part = Column(Integer)  # Part number (CLASSIC era: Part 1, Part 2)

    # PokerGO 매칭
    pokergo_episode_id = Column(String(100))
    pokergo_title = Column(String(500))
    pokergo_match_score = Column(Float)

    # 카탈로그 제목 (자동 생성 또는 수동 편집)
    catalog_title = Column(String(500))  # 생성된 표준 제목
    catalog_title_manual = Column(Boolean, default=False)  # 수동 편집 여부

    # 매칭 분류 (4분류 체계)
    match_category = Column(String(50))  # MATCHED, NAS_ONLY_HISTORIC, NAS_ONLY_MODERN, POKERGO_ONLY

    # 통계 (캐시)
    file_count = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)
    has_backup = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    region = relationship("Region", back_populates="groups")
    event_type = relationship("EventType", back_populates="groups")
    files = relationship("NasFile", back_populates="asset_group")

    __table_args__ = (
        Index('idx_asset_groups_year', 'year'),
    )


class NasFile(Base):
    """NAS 파일 정보."""
    __tablename__ = 'nas_files'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 파일 식별 (file_id = 파일명 기반, 경로 변경에도 유지)
    file_id = Column(String(500), unique=True, index=True)  # 파일명 기반 고유 식별자
    filename = Column(String(500), nullable=False)
    extension = Column(String(10), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    directory = Column(String(1000))
    full_path = Column(String(1500), unique=True)
    modified_at = Column(DateTime)

    # 드라이브/폴더 정보
    drive = Column(String(10))  # X:, Y:, Z:
    folder = Column(String(20))  # pokergo, origin, archive

    # 경로 변경 추적
    path_history = Column(Text)  # JSON: [{"old_path": ..., "new_path": ..., "changed_at": ...}]
    last_seen_at = Column(DateTime)  # 마지막 스캔 시 발견

    # 추출된 메타데이터 (자동 또는 수동)
    year = Column(Integer)
    region_id = Column(Integer, ForeignKey('regions.id'))
    event_type_id = Column(Integer, ForeignKey('event_types.id'))
    episode = Column(Integer)

    # 확장 메타데이터 (새 패턴 규칙)
    stage = Column(String(20))           # D1A, D2, FT, FINAL, S1
    event_num = Column(Integer)          # Event #13 → 13
    season = Column(Integer)             # PAD S12 → 12
    buyin = Column(String(20))           # $100K, $5K
    gtd = Column(String(20))             # $5M GTD → 5M
    version = Column(String(20))         # NC (No Commentary), NB, CLEAN
    part = Column(Integer)               # Part number (CLASSIC era: Part 1, Part 2)

    # 매칭 패턴 정보
    matched_pattern_id = Column(Integer, ForeignKey('patterns.id'))
    extraction_confidence = Column(Float)  # 0.0 ~ 1.0

    # 수동 오버라이드
    is_manual_override = Column(Boolean, default=False)
    override_reason = Column(Text)

    # 제외 조건 (체크박스 표시용 - 파일은 저장됨)
    is_excluded = Column(Boolean, default=False)  # 제외 조건 해당 여부
    exclusion_reason = Column(String(200))  # 제외 이유 (Size < 1GB, Contains 'clip' 등)
    exclusion_rule_id = Column(Integer, ForeignKey('exclusion_rules.id'))  # 적용된 규칙

    # 그룹 소속 (기존 - AssetGroup 연결)
    asset_group_id = Column(Integer, ForeignKey('asset_groups.id'))
    role = Column(String(20), default='backup')  # PRIMARY, BACKUP, EXCLUDED
    role_priority = Column(Integer)  # 1, 2, 3...

    # 새 카테고리 시스템 연결
    entry_id = Column(Integer, ForeignKey('category_entries.id'))  # CategoryEntry 참조

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    region = relationship("Region", back_populates="files")
    event_type = relationship("EventType", back_populates="files")
    matched_pattern = relationship("Pattern", back_populates="matched_files")
    asset_group = relationship("AssetGroup", back_populates="files")
    category_entry = relationship("CategoryEntry", back_populates="files", foreign_keys=[entry_id])

    __table_args__ = (
        Index('idx_nas_files_year', 'year'),
        Index('idx_nas_files_group', 'asset_group_id'),
        Index('idx_nas_files_entry', 'entry_id'),
        Index('idx_nas_files_drive', 'drive'),
    )


class AuditLog(Base):
    """변경 이력."""
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False)  # nas_file, asset_group, pattern
    entity_id = Column(Integer, nullable=False)
    action = Column(String(20), nullable=False)  # create, update, delete, move
    old_values = Column(Text)  # JSON string
    new_values = Column(Text)  # JSON string
    changed_by = Column(String(100))
    changed_at = Column(DateTime, default=datetime.utcnow)
    reason = Column(Text)

    __table_args__ = (
        Index('idx_audit_logs_entity', 'entity_type', 'entity_id'),
    )


class PokergoEpisode(Base):
    """PokerGO 에피소드 (참조 데이터)."""
    __tablename__ = 'pokergo_episodes'

    id = Column(String(100), primary_key=True)
    title = Column(String(500))
    description = Column(Text)
    duration_sec = Column(Float)
    collection_title = Column(String(200))
    season_title = Column(String(200))
    aired_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class ExclusionRule(Base):
    """제외 규칙 - 스캔 시 파일 제외 조건."""
    __tablename__ = 'exclusion_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_type = Column(String(20), nullable=False)  # size, duration, keyword
    operator = Column(String(20), nullable=False)  # lt, gt, eq, contains
    value = Column(String(100), nullable=False)  # 1073741824, 3600, clip
    description = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =============================================================================
# VALIDATOR MODELS (Phase 1: Catalog Validator)
# =============================================================================

class ScanHistory(Base):
    """스캔 이력 - 일일 스캔 결과 기록."""
    __tablename__ = 'scan_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_type = Column(String(20), nullable=False)  # daily, manual, full
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String(20), default='running')  # running, completed, failed

    # 스캔 결과 통계
    new_files = Column(Integer, default=0)
    updated_files = Column(Integer, default=0)
    missing_files = Column(Integer, default=0)
    path_changes = Column(Integer, default=0)

    # 스캔 범위
    scanned_drives = Column(String(50))  # "Y:,Z:,X:"
    total_files_scanned = Column(Integer, default=0)
    total_size_scanned = Column(BigInteger, default=0)

    # 에러 정보
    error_message = Column(Text)

    __table_args__ = (
        Index('idx_scan_history_started', 'started_at'),
        Index('idx_scan_history_status', 'status'),
    )


class ValidationSession(Base):
    """검증 세션 - 사용자 작업 단위."""
    __tablename__ = 'validation_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_name = Column(String(100))
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)

    # 세션 통계
    entries_reviewed = Column(Integer, default=0)
    entries_verified = Column(Integer, default=0)
    entries_modified = Column(Integer, default=0)

    __table_args__ = (
        Index('idx_validation_sessions_user', 'user_name'),
    )
