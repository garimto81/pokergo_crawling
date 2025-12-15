"""SQLAlchemy models for NAMS database."""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, ForeignKey,
    DateTime, Index, create_engine
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


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
    group_id = Column(String(50), unique=True, nullable=False)  # 2011_ME_25
    year = Column(Integer, nullable=False)
    region_id = Column(Integer, ForeignKey('regions.id'))
    event_type_id = Column(Integer, ForeignKey('event_types.id'))
    episode = Column(Integer)

    # PokerGO 매칭
    pokergo_episode_id = Column(String(100))
    pokergo_title = Column(String(500))
    pokergo_match_score = Column(Float)

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
    filename = Column(String(500), nullable=False)
    extension = Column(String(10), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    directory = Column(String(1000))
    full_path = Column(String(1500), unique=True)
    modified_at = Column(DateTime)

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

    # 매칭 패턴 정보
    matched_pattern_id = Column(Integer, ForeignKey('patterns.id'))
    extraction_confidence = Column(Float)  # 0.0 ~ 1.0

    # 수동 오버라이드
    is_manual_override = Column(Boolean, default=False)
    override_reason = Column(Text)

    # 그룹 소속
    asset_group_id = Column(Integer, ForeignKey('asset_groups.id'))
    role = Column(String(20), default='backup')  # primary, backup
    role_priority = Column(Integer)  # 1, 2, 3...

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    region = relationship("Region", back_populates="files")
    event_type = relationship("EventType", back_populates="files")
    matched_pattern = relationship("Pattern", back_populates="matched_files")
    asset_group = relationship("AssetGroup", back_populates="files")

    __table_args__ = (
        Index('idx_nas_files_year', 'year'),
        Index('idx_nas_files_group', 'asset_group_id'),
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
