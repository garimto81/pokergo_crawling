"""File management API router for NAMS."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import AssetGroup, NasFile, get_db
from ..schemas import (
    MessageResponse,
    NasFileBulkUpdate,
    NasFileListResponse,
    NasFileMoveRequest,
    NasFileOverride,
    NasFileResponse,
    NasFileUpdate,
    PaginatedResponse,
)

router = APIRouter()


def format_size(bytes_size: int) -> str:
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} PB"


@router.get("", response_model=PaginatedResponse[NasFileListResponse])
async def list_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    year: Optional[int] = None,
    region_id: Optional[int] = None,
    event_type_id: Optional[int] = None,
    group_id: Optional[int] = None,
    has_group: Optional[bool] = None,
    is_primary: Optional[bool] = None,
    is_manual_override: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get paginated file list with filters."""
    query = db.query(NasFile).options(
        joinedload(NasFile.region),
        joinedload(NasFile.event_type),
        joinedload(NasFile.asset_group),
    )

    # Apply filters
    if year:
        query = query.filter(NasFile.year == year)
    if region_id:
        query = query.filter(NasFile.region_id == region_id)
    if event_type_id:
        query = query.filter(NasFile.event_type_id == event_type_id)
    if group_id:
        query = query.filter(NasFile.asset_group_id == group_id)
    if has_group is not None:
        if has_group:
            query = query.filter(NasFile.asset_group_id.isnot(None))
        else:
            query = query.filter(NasFile.asset_group_id.is_(None))
    if is_primary is not None:
        if is_primary:
            query = query.filter(NasFile.role == "primary")
        else:
            query = query.filter(NasFile.role != "primary")
    if is_manual_override is not None:
        query = query.filter(NasFile.is_manual_override == is_manual_override)
    if search:
        query = query.filter(NasFile.filename.ilike(f"%{search}%"))

    # Get total count
    total = query.count()

    # Paginate
    offset = (page - 1) * page_size
    files = query.order_by(NasFile.filename).offset(offset).limit(page_size).all()

    # Transform to response
    items = []
    for f in files:
        items.append(NasFileListResponse(
            id=f.id,
            filename=f.filename,
            size_bytes=f.size_bytes,
            size_formatted=format_size(f.size_bytes),
            year=f.year,
            region_code=f.region.code if f.region else None,
            event_type_code=f.event_type.code if f.event_type else None,
            episode=f.episode,
            group_id=f.asset_group.group_id if f.asset_group else None,
            role=f.role,
            is_manual_override=f.is_manual_override,
        ))

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{file_id}", response_model=NasFileResponse)
async def get_file(file_id: int, db: Session = Depends(get_db)):
    """Get file details."""
    file = db.query(NasFile).options(
        joinedload(NasFile.region),
        joinedload(NasFile.event_type),
        joinedload(NasFile.matched_pattern),
        joinedload(NasFile.asset_group),
    ).filter(NasFile.id == file_id).first()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    return NasFileResponse(
        id=file.id,
        filename=file.filename,
        extension=file.extension,
        size_bytes=file.size_bytes,
        directory=file.directory,
        full_path=file.full_path,
        modified_at=file.modified_at,
        year=file.year,
        region_id=file.region_id,
        event_type_id=file.event_type_id,
        episode=file.episode,
        matched_pattern_id=file.matched_pattern_id,
        extraction_confidence=file.extraction_confidence,
        is_manual_override=file.is_manual_override,
        override_reason=file.override_reason,
        asset_group_id=file.asset_group_id,
        role=file.role,
        role_priority=file.role_priority,
        created_at=file.created_at,
        updated_at=file.updated_at,
        region_code=file.region.code if file.region else None,
        event_type_code=file.event_type.code if file.event_type else None,
        pattern_name=file.matched_pattern.name if file.matched_pattern else None,
        group_id=file.asset_group.group_id if file.asset_group else None,
        size_formatted=format_size(file.size_bytes),
    )


@router.put("/{file_id}", response_model=NasFileResponse)
async def update_file(
    file_id: int,
    data: NasFileUpdate,
    db: Session = Depends(get_db)
):
    """Update file metadata."""
    file = db.query(NasFile).filter(NasFile.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(file, key, value)

    db.commit()
    db.refresh(file)

    # Return full response
    return await get_file(file_id, db)


@router.post("/{file_id}/override", response_model=NasFileResponse)
async def override_file(
    file_id: int,
    data: NasFileOverride,
    db: Session = Depends(get_db)
):
    """Manually override file metadata."""
    file = db.query(NasFile).filter(NasFile.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Apply override
    if data.year is not None:
        file.year = data.year
    if data.region_id is not None:
        file.region_id = data.region_id
    if data.event_type_id is not None:
        file.event_type_id = data.event_type_id
    if data.episode is not None:
        file.episode = data.episode

    file.is_manual_override = True
    file.override_reason = data.reason

    db.commit()
    db.refresh(file)

    return await get_file(file_id, db)


@router.post("/{file_id}/move", response_model=MessageResponse)
async def move_file(
    file_id: int,
    data: NasFileMoveRequest,
    db: Session = Depends(get_db)
):
    """Move file to a different group."""
    file = db.query(NasFile).filter(NasFile.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    target_group = db.query(AssetGroup).filter(
        AssetGroup.id == data.target_group_id
    ).first()
    if not target_group:
        raise HTTPException(status_code=404, detail="Target group not found")

    old_group_id = file.asset_group_id
    file.asset_group_id = data.target_group_id
    file.role = data.role

    # Update group statistics
    if old_group_id:
        old_group = db.query(AssetGroup).filter(AssetGroup.id == old_group_id).first()
        if old_group:
            old_group.file_count = db.query(func.count(NasFile.id)).filter(
                NasFile.asset_group_id == old_group_id
            ).scalar() or 0
            old_group.total_size_bytes = db.query(func.sum(NasFile.size_bytes)).filter(
                NasFile.asset_group_id == old_group_id
            ).scalar() or 0

    target_group.file_count = db.query(func.count(NasFile.id)).filter(
        NasFile.asset_group_id == data.target_group_id
    ).scalar() or 0
    target_group.total_size_bytes = db.query(func.sum(NasFile.size_bytes)).filter(
        NasFile.asset_group_id == data.target_group_id
    ).scalar() or 0

    db.commit()
    return MessageResponse(message=f"File moved to group '{target_group.group_id}'")


@router.post("/bulk-update", response_model=MessageResponse)
async def bulk_update_files(data: NasFileBulkUpdate, db: Session = Depends(get_db)):
    """Bulk update multiple files."""
    if not data.file_ids:
        raise HTTPException(status_code=400, detail="No files specified")

    files = db.query(NasFile).filter(NasFile.id.in_(data.file_ids)).all()
    if not files:
        raise HTTPException(status_code=404, detail="No files found")

    update_count = 0
    for file in files:
        if data.year is not None:
            file.year = data.year
        if data.region_id is not None:
            file.region_id = data.region_id
        if data.event_type_id is not None:
            file.event_type_id = data.event_type_id
        if data.asset_group_id is not None:
            file.asset_group_id = data.asset_group_id
        update_count += 1

    db.commit()
    return MessageResponse(message=f"Updated {update_count} files")
