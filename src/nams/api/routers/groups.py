"""Group management API router for NAMS."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from ..database import get_db, AssetGroup, NasFile, Region, EventType
from ..schemas import (
    AssetGroupResponse,
    AssetGroupListResponse,
    AssetGroupDetailResponse,
    AssetGroupCreate,
    AssetGroupUpdate,
    GroupSetPrimaryRequest,
    GroupMergeRequest,
    GroupSplitRequest,
    MessageResponse,
    PaginatedResponse,
    NasFileListResponse,
)

router = APIRouter()


def format_size(bytes_size: int) -> str:
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} PB"


@router.get("", response_model=PaginatedResponse[AssetGroupListResponse])
async def list_groups(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    year: Optional[int] = None,
    region_id: Optional[int] = None,
    event_type_id: Optional[int] = None,
    has_pokergo_match: Optional[bool] = None,
    match_category: Optional[str] = None,
    has_backup: Optional[bool] = None,
    min_file_count: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get paginated group list with filters."""
    query = db.query(AssetGroup).options(
        joinedload(AssetGroup.region),
        joinedload(AssetGroup.event_type),
    )

    # Apply filters
    if year:
        query = query.filter(AssetGroup.year == year)
    if region_id:
        query = query.filter(AssetGroup.region_id == region_id)
    if event_type_id:
        query = query.filter(AssetGroup.event_type_id == event_type_id)
    if has_pokergo_match is not None:
        if has_pokergo_match:
            query = query.filter(AssetGroup.pokergo_episode_id.isnot(None))
        else:
            query = query.filter(AssetGroup.pokergo_episode_id.is_(None))
    if match_category:
        query = query.filter(AssetGroup.match_category == match_category)
    if has_backup is not None:
        query = query.filter(AssetGroup.has_backup == has_backup)
    if min_file_count:
        query = query.filter(AssetGroup.file_count >= min_file_count)
    if search:
        query = query.filter(AssetGroup.group_id.ilike(f"%{search}%"))

    # Get total count
    total = query.count()

    # Paginate
    offset = (page - 1) * page_size
    groups = query.order_by(AssetGroup.year.desc(), AssetGroup.group_id).offset(offset).limit(page_size).all()

    # Transform to response
    items = []
    for g in groups:
        items.append(AssetGroupListResponse(
            id=g.id,
            group_id=g.group_id,
            year=g.year,
            region_code=g.region.code if g.region else None,
            event_type_code=g.event_type.code if g.event_type else None,
            episode=g.episode,
            catalog_title=g.catalog_title,
            match_category=g.match_category,
            file_count=g.file_count,
            total_size_formatted=format_size(g.total_size_bytes or 0),
            has_backup=g.has_backup,
            has_pokergo_match=g.pokergo_episode_id is not None,
        ))

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{group_id}", response_model=AssetGroupDetailResponse)
async def get_group(group_id: int, db: Session = Depends(get_db)):
    """Get group details with files."""
    group = db.query(AssetGroup).options(
        joinedload(AssetGroup.region),
        joinedload(AssetGroup.event_type),
    ).filter(AssetGroup.id == group_id).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Get files in this group
    files = db.query(NasFile).options(
        joinedload(NasFile.region),
        joinedload(NasFile.event_type),
    ).filter(NasFile.asset_group_id == group_id).order_by(
        NasFile.role.desc(),  # primary first
        NasFile.role_priority,
        NasFile.filename,
    ).all()

    file_items = []
    for f in files:
        file_items.append(NasFileListResponse(
            id=f.id,
            filename=f.filename,
            size_bytes=f.size_bytes,
            size_formatted=format_size(f.size_bytes),
            year=f.year,
            region_code=f.region.code if f.region else None,
            event_type_code=f.event_type.code if f.event_type else None,
            episode=f.episode,
            group_id=group.group_id,
            role=f.role,
            is_manual_override=f.is_manual_override,
        ))

    return AssetGroupDetailResponse(
        id=group.id,
        group_id=group.group_id,
        year=group.year,
        region_id=group.region_id,
        event_type_id=group.event_type_id,
        episode=group.episode,
        pokergo_episode_id=group.pokergo_episode_id,
        pokergo_title=group.pokergo_title,
        pokergo_match_score=group.pokergo_match_score,
        file_count=group.file_count,
        total_size_bytes=group.total_size_bytes or 0,
        has_backup=group.has_backup,
        created_at=group.created_at,
        updated_at=group.updated_at,
        region_code=group.region.code if group.region else None,
        event_type_code=group.event_type.code if group.event_type else None,
        total_size_formatted=format_size(group.total_size_bytes or 0),
        files=file_items,
    )


@router.post("", response_model=AssetGroupResponse)
async def create_group(data: AssetGroupCreate, db: Session = Depends(get_db)):
    """Create a new group manually."""
    # Check for duplicate group_id
    existing = db.query(AssetGroup).filter(AssetGroup.group_id == data.group_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Group ID already exists")

    group = AssetGroup(**data.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)

    return await get_group(group.id, db)


@router.put("/{group_id}", response_model=AssetGroupResponse)
async def update_group(
    group_id: int,
    data: AssetGroupUpdate,
    db: Session = Depends(get_db)
):
    """Update a group."""
    group = db.query(AssetGroup).filter(AssetGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(group, key, value)

    db.commit()
    db.refresh(group)

    return await get_group(group_id, db)


@router.delete("/{group_id}", response_model=MessageResponse)
async def delete_group(group_id: int, db: Session = Depends(get_db)):
    """Delete a group (files become unassigned)."""
    group = db.query(AssetGroup).filter(AssetGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    group_name = group.group_id

    # Unassign all files
    db.query(NasFile).filter(NasFile.asset_group_id == group_id).update({
        "asset_group_id": None,
        "role": "backup",
        "role_priority": None,
    })

    db.delete(group)
    db.commit()

    return MessageResponse(message=f"Group '{group_name}' deleted, files unassigned")


@router.post("/{group_id}/set-primary", response_model=MessageResponse)
async def set_primary_file(
    group_id: int,
    data: GroupSetPrimaryRequest,
    db: Session = Depends(get_db)
):
    """Set a file as primary in a group."""
    group = db.query(AssetGroup).filter(AssetGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    file = db.query(NasFile).filter(
        NasFile.id == data.file_id,
        NasFile.asset_group_id == group_id,
    ).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not in this group")

    # Reset all files in group to backup
    db.query(NasFile).filter(NasFile.asset_group_id == group_id).update({
        "role": "backup",
    })

    # Set selected file as primary
    file.role = "primary"
    file.role_priority = 1

    # Update group has_backup flag
    backup_count = db.query(func.count(NasFile.id)).filter(
        NasFile.asset_group_id == group_id,
        NasFile.role == "backup",
    ).scalar()
    group.has_backup = backup_count > 0

    db.commit()

    return MessageResponse(message=f"File '{file.filename}' set as primary")


@router.post("/merge", response_model=MessageResponse)
async def merge_groups(data: GroupMergeRequest, db: Session = Depends(get_db)):
    """Merge multiple groups into one."""
    if not data.source_group_ids:
        raise HTTPException(status_code=400, detail="No source groups specified")

    target_group = db.query(AssetGroup).filter(
        AssetGroup.id == data.target_group_id
    ).first()
    if not target_group:
        raise HTTPException(status_code=404, detail="Target group not found")

    merged_count = 0
    for source_id in data.source_group_ids:
        if source_id == data.target_group_id:
            continue

        # Move files to target group
        files_moved = db.query(NasFile).filter(
            NasFile.asset_group_id == source_id
        ).update({
            "asset_group_id": data.target_group_id,
            "role": "backup",
        })

        if files_moved > 0:
            # Delete source group
            db.query(AssetGroup).filter(AssetGroup.id == source_id).delete()
            merged_count += 1

    # Update target group stats
    target_group.file_count = db.query(func.count(NasFile.id)).filter(
        NasFile.asset_group_id == data.target_group_id
    ).scalar() or 0
    target_group.total_size_bytes = db.query(func.sum(NasFile.size_bytes)).filter(
        NasFile.asset_group_id == data.target_group_id
    ).scalar() or 0
    target_group.has_backup = target_group.file_count > 1

    db.commit()

    return MessageResponse(message=f"Merged {merged_count} groups into '{target_group.group_id}'")


@router.post("/split", response_model=AssetGroupResponse)
async def split_group(data: GroupSplitRequest, db: Session = Depends(get_db)):
    """Split files from a group into a new group."""
    if not data.file_ids:
        raise HTTPException(status_code=400, detail="No files specified")

    # Check for duplicate group_id
    existing = db.query(AssetGroup).filter(AssetGroup.group_id == data.new_group_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="New group ID already exists")

    # Get first file to determine group properties
    first_file = db.query(NasFile).filter(NasFile.id == data.file_ids[0]).first()
    if not first_file:
        raise HTTPException(status_code=404, detail="File not found")

    old_group_id = first_file.asset_group_id

    # Create new group
    new_group = AssetGroup(
        group_id=data.new_group_id,
        year=first_file.year or 0,
        region_id=first_file.region_id,
        event_type_id=first_file.event_type_id,
        episode=first_file.episode,
    )
    db.add(new_group)
    db.flush()

    # Move files to new group
    db.query(NasFile).filter(NasFile.id.in_(data.file_ids)).update({
        "asset_group_id": new_group.id,
        "role": "backup",
    })

    # Update new group stats
    new_group.file_count = len(data.file_ids)
    new_group.total_size_bytes = db.query(func.sum(NasFile.size_bytes)).filter(
        NasFile.asset_group_id == new_group.id
    ).scalar() or 0
    new_group.has_backup = new_group.file_count > 1

    # Update old group stats if it exists
    if old_group_id:
        old_group = db.query(AssetGroup).filter(AssetGroup.id == old_group_id).first()
        if old_group:
            old_group.file_count = db.query(func.count(NasFile.id)).filter(
                NasFile.asset_group_id == old_group_id
            ).scalar() or 0
            old_group.total_size_bytes = db.query(func.sum(NasFile.size_bytes)).filter(
                NasFile.asset_group_id == old_group_id
            ).scalar() or 0
            old_group.has_backup = old_group.file_count > 1

    db.commit()

    return await get_group(new_group.id, db)
