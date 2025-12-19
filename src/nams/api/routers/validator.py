"""Catalog Validator API endpoints."""
import json
import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..database.models import (
    AuditLog,
    Category,
    CategoryEntry,
    NasFile,
    ScanHistory,
)

router = APIRouter(prefix="/api/validator", tags=["validator"])


# =============================================================================
# Pydantic Schemas
# =============================================================================

class ValidatorEntryResponse(BaseModel):
    """검증 항목 응답."""
    id: int
    entry_code: str
    display_title: Optional[str]
    pokergo_title: Optional[str]
    year: int
    event_type: Optional[str]
    category_id: Optional[int]
    category_name: Optional[str]
    match_type: Optional[str]
    match_score: Optional[float]
    verified: bool
    verified_at: Optional[datetime]
    verified_by: Optional[str]
    file_count: int
    total_size_gb: float

    class Config:
        from_attributes = True


class EntryFileResponse(BaseModel):
    """항목 파일 정보."""
    id: int
    filename: str
    full_path: str
    size_bytes: int
    size_gb: float
    drive: Optional[str]
    role: Optional[str]
    extension: str


class ValidatorEntryDetailResponse(BaseModel):
    """검증 항목 상세 (파일 목록 포함)."""
    entry: ValidatorEntryResponse
    files: List[EntryFileResponse]
    changes: List[dict]


class ValidatorUpdateRequest(BaseModel):
    """제목/카테고리 수정 요청."""
    display_title: Optional[str] = None
    category_id: Optional[int] = None


class VerifyRequest(BaseModel):
    """검증 완료 요청."""
    verified_by: str = "admin"
    notes: Optional[str] = None


class PlayRequest(BaseModel):
    """영상 재생 요청."""
    file_id: int


class ValidatorStatsResponse(BaseModel):
    """검증 통계."""
    total_entries: int
    verified_entries: int
    pending_entries: int
    verification_rate: float
    entries_by_year: dict
    recent_verifications: int  # 최근 24시간


class PaginatedResponse(BaseModel):
    """페이지네이션 응답."""
    items: List[ValidatorEntryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/pending", response_model=PaginatedResponse)
def get_pending_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    year: Optional[int] = None,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """미검증 항목 목록 조회."""
    query = db.query(CategoryEntry).filter(CategoryEntry.verified == False)

    # Filters
    if year:
        query = query.filter(CategoryEntry.year == year)
    if category_id:
        query = query.filter(CategoryEntry.category_id == category_id)
    if search:
        query = query.filter(
            CategoryEntry.display_title.ilike(f"%{search}%") |
            CategoryEntry.entry_code.ilike(f"%{search}%")
        )

    # Count
    total = query.count()
    total_pages = (total + page_size - 1) // page_size

    # Paginate
    entries = query.order_by(
        CategoryEntry.year.desc(),
        CategoryEntry.entry_code
    ).offset((page - 1) * page_size).limit(page_size).all()

    # Build response
    items = []
    for entry in entries:
        category = db.query(Category).filter(Category.id == entry.category_id).first()

        items.append(ValidatorEntryResponse(
            id=entry.id,
            entry_code=entry.entry_code,
            display_title=entry.display_title,
            pokergo_title=entry.pokergo_title,
            year=entry.year,
            event_type=entry.event_type,
            category_id=entry.category_id,
            category_name=category.name if category else None,
            match_type=entry.match_type,
            match_score=entry.match_score,
            verified=entry.verified,
            verified_at=entry.verified_at,
            verified_by=entry.verified_by,
            file_count=entry.file_count or 0,
            total_size_gb=(entry.total_size_bytes or 0) / (1024 ** 3),
        ))

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/entry/{entry_id}", response_model=ValidatorEntryDetailResponse)
def get_entry_detail(
    entry_id: int,
    db: Session = Depends(get_db),
):
    """검증 대상 Entry 상세 조회."""
    entry = db.query(CategoryEntry).filter(CategoryEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    category = db.query(Category).filter(Category.id == entry.category_id).first()

    # Get files
    files = db.query(NasFile).filter(NasFile.entry_id == entry_id).all()
    file_responses = [
        EntryFileResponse(
            id=f.id,
            filename=f.filename,
            full_path=f.full_path or "",
            size_bytes=f.size_bytes,
            size_gb=f.size_bytes / (1024 ** 3),
            drive=f.drive,
            role=f.role,
            extension=f.extension,
        )
        for f in files
    ]

    # Get change history from AuditLog
    changes = db.query(AuditLog).filter(
        AuditLog.entity_type == "category_entry",
        AuditLog.entity_id == entry_id,
    ).order_by(AuditLog.changed_at.desc()).limit(10).all()

    change_list = [
        {
            "id": c.id,
            "action": c.action,
            "old_values": json.loads(c.old_values) if c.old_values else {},
            "new_values": json.loads(c.new_values) if c.new_values else {},
            "changed_by": c.changed_by,
            "changed_at": c.changed_at.isoformat() if c.changed_at else None,
        }
        for c in changes
    ]

    entry_response = ValidatorEntryResponse(
        id=entry.id,
        entry_code=entry.entry_code,
        display_title=entry.display_title,
        pokergo_title=entry.pokergo_title,
        year=entry.year,
        event_type=entry.event_type,
        category_id=entry.category_id,
        category_name=category.name if category else None,
        match_type=entry.match_type,
        match_score=entry.match_score,
        verified=entry.verified,
        verified_at=entry.verified_at,
        verified_by=entry.verified_by,
        file_count=entry.file_count or 0,
        total_size_gb=(entry.total_size_bytes or 0) / (1024 ** 3),
    )

    return ValidatorEntryDetailResponse(
        entry=entry_response,
        files=file_responses,
        changes=change_list,
    )


@router.patch("/entry/{entry_id}", response_model=ValidatorEntryResponse)
def update_entry(
    entry_id: int,
    request: ValidatorUpdateRequest,
    db: Session = Depends(get_db),
):
    """제목/카테고리 수정."""
    entry = db.query(CategoryEntry).filter(CategoryEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Store old values for audit
    old_values = {}
    new_values = {}

    if request.display_title is not None and request.display_title != entry.display_title:
        old_values["display_title"] = entry.display_title
        new_values["display_title"] = request.display_title
        entry.display_title = request.display_title

    if request.category_id is not None and request.category_id != entry.category_id:
        old_values["category_id"] = entry.category_id
        new_values["category_id"] = request.category_id
        entry.category_id = request.category_id

    # Create audit log if changes were made
    if old_values:
        audit = AuditLog(
            entity_type="category_entry",
            entity_id=entry_id,
            action="update",
            old_values=json.dumps(old_values),
            new_values=json.dumps(new_values),
            changed_by="validator",
        )
        db.add(audit)

    entry.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)

    category = db.query(Category).filter(Category.id == entry.category_id).first()

    return ValidatorEntryResponse(
        id=entry.id,
        entry_code=entry.entry_code,
        display_title=entry.display_title,
        pokergo_title=entry.pokergo_title,
        year=entry.year,
        event_type=entry.event_type,
        category_id=entry.category_id,
        category_name=category.name if category else None,
        match_type=entry.match_type,
        match_score=entry.match_score,
        verified=entry.verified,
        verified_at=entry.verified_at,
        verified_by=entry.verified_by,
        file_count=entry.file_count or 0,
        total_size_gb=(entry.total_size_bytes or 0) / (1024 ** 3),
    )


@router.post("/entry/{entry_id}/verify", response_model=ValidatorEntryResponse)
def verify_entry(
    entry_id: int,
    request: VerifyRequest,
    db: Session = Depends(get_db),
):
    """검증 완료 처리."""
    entry = db.query(CategoryEntry).filter(CategoryEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Update verification status
    old_verified = entry.verified
    entry.verified = True
    entry.verified_at = datetime.utcnow()
    entry.verified_by = request.verified_by
    if request.notes:
        entry.notes = request.notes

    # Create audit log
    audit = AuditLog(
        entity_type="category_entry",
        entity_id=entry_id,
        action="verify",
        old_values=json.dumps({"verified": old_verified}),
        new_values=json.dumps({"verified": True, "verified_by": request.verified_by}),
        changed_by=request.verified_by,
    )
    db.add(audit)

    db.commit()
    db.refresh(entry)

    category = db.query(Category).filter(Category.id == entry.category_id).first()

    return ValidatorEntryResponse(
        id=entry.id,
        entry_code=entry.entry_code,
        display_title=entry.display_title,
        pokergo_title=entry.pokergo_title,
        year=entry.year,
        event_type=entry.event_type,
        category_id=entry.category_id,
        category_name=category.name if category else None,
        match_type=entry.match_type,
        match_score=entry.match_score,
        verified=entry.verified,
        verified_at=entry.verified_at,
        verified_by=entry.verified_by,
        file_count=entry.file_count or 0,
        total_size_gb=(entry.total_size_bytes or 0) / (1024 ** 3),
    )


@router.post("/entry/{entry_id}/play")
def play_video(
    entry_id: int,
    request: PlayRequest,
    db: Session = Depends(get_db),
):
    """시스템 기본 플레이어로 영상 재생."""
    # Get file
    file = db.query(NasFile).filter(NasFile.id == request.file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Verify file belongs to entry
    if file.entry_id != entry_id:
        raise HTTPException(status_code=400, detail="File does not belong to this entry")

    # Check file path exists
    file_path = file.full_path
    if not file_path:
        raise HTTPException(status_code=400, detail="File path is empty")

    # Try to play with system default player
    try:
        os.startfile(file_path)
        return {
            "success": True,
            "message": f"Playing: {file.filename}",
            "file_path": file_path,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to play: {str(e)}")


@router.get("/stats", response_model=ValidatorStatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """검증 진행 통계."""
    total = db.query(CategoryEntry).count()
    verified = db.query(CategoryEntry).filter(CategoryEntry.verified == True).count()
    pending = total - verified

    # By year
    year_stats = db.query(
        CategoryEntry.year,
        func.count(CategoryEntry.id).label("total"),
        func.sum(func.cast(CategoryEntry.verified, Integer)).label("verified")
    ).group_by(CategoryEntry.year).all()

    entries_by_year = {
        str(y.year): {"total": y.total, "verified": y.verified or 0}
        for y in year_stats
    }

    # Recent verifications (24 hours)
    from datetime import timedelta
    yesterday = datetime.utcnow() - timedelta(hours=24)
    recent = db.query(CategoryEntry).filter(
        CategoryEntry.verified_at >= yesterday
    ).count()

    return ValidatorStatsResponse(
        total_entries=total,
        verified_entries=verified,
        pending_entries=pending,
        verification_rate=verified / total if total > 0 else 0,
        entries_by_year=entries_by_year,
        recent_verifications=recent,
    )


# =============================================================================
# Scheduler Status Endpoints
# =============================================================================

@router.get("/scheduler/status")
def get_scheduler_status(db: Session = Depends(get_db)):
    """마지막 스캔 결과."""
    last_scan = db.query(ScanHistory).order_by(
        ScanHistory.started_at.desc()
    ).first()

    if not last_scan:
        return {
            "last_scan": None,
            "message": "No scan history found",
        }

    return {
        "last_scan": {
            "id": last_scan.id,
            "scan_type": last_scan.scan_type,
            "started_at": last_scan.started_at.isoformat() if last_scan.started_at else None,
            "completed_at": last_scan.completed_at.isoformat() if last_scan.completed_at else None,
            "status": last_scan.status,
            "new_files": last_scan.new_files,
            "updated_files": last_scan.updated_files,
            "missing_files": last_scan.missing_files,
            "path_changes": last_scan.path_changes,
            "scanned_drives": last_scan.scanned_drives,
            "error_message": last_scan.error_message,
        }
    }


@router.get("/scheduler/history")
def get_scheduler_history(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """스캔 이력 조회."""
    scans = db.query(ScanHistory).order_by(
        ScanHistory.started_at.desc()
    ).limit(limit).all()

    return {
        "items": [
            {
                "id": s.id,
                "scan_type": s.scan_type,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "status": s.status,
                "new_files": s.new_files,
                "updated_files": s.updated_files,
                "missing_files": s.missing_files,
                "path_changes": s.path_changes,
            }
            for s in scans
        ],
        "total": len(scans),
    }


# Import for Integer cast
from sqlalchemy import Integer
