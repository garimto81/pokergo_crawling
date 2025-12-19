"""Settings API router for NAMS (Regions, Event Types)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import AssetGroup, EventType, NasFile, Region, get_db
from ..schemas import (
    EventTypeCreate,
    EventTypeResponse,
    EventTypeUpdate,
    MessageResponse,
    RegionCreate,
    RegionResponse,
    RegionUpdate,
)

router = APIRouter()


# === REGIONS ===

@router.get("/regions", response_model=list[RegionResponse])
async def list_regions(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get all regions."""
    query = db.query(Region)
    if active_only:
        query = query.filter(Region.is_active == True)
    return query.all()


@router.get("/regions/{region_id}", response_model=RegionResponse)
async def get_region(region_id: int, db: Session = Depends(get_db)):
    """Get a specific region."""
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    return region


@router.post("/regions", response_model=RegionResponse)
async def create_region(data: RegionCreate, db: Session = Depends(get_db)):
    """Create a new region."""
    # Check for duplicate code
    existing = db.query(Region).filter(Region.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Region code already exists")

    region = Region(**data.model_dump())
    db.add(region)
    db.commit()
    db.refresh(region)
    return region


@router.put("/regions/{region_id}", response_model=RegionResponse)
async def update_region(
    region_id: int,
    data: RegionUpdate,
    db: Session = Depends(get_db)
):
    """Update a region."""
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    # Check for duplicate code if changing
    if data.code and data.code != region.code:
        existing = db.query(Region).filter(Region.code == data.code).first()
        if existing:
            raise HTTPException(status_code=400, detail="Region code already exists")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(region, key, value)

    db.commit()
    db.refresh(region)
    return region


@router.delete("/regions/{region_id}", response_model=MessageResponse)
async def delete_region(region_id: int, db: Session = Depends(get_db)):
    """Delete a region."""
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    # Check if region is in use
    file_count = db.query(func.count(NasFile.id)).filter(
        NasFile.region_id == region_id
    ).scalar()
    group_count = db.query(func.count(AssetGroup.id)).filter(
        AssetGroup.region_id == region_id
    ).scalar()

    if file_count > 0 or group_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Region is used by {file_count} files and {group_count} groups. Deactivate instead."
        )

    db.delete(region)
    db.commit()
    return MessageResponse(message=f"Region '{region.code}' deleted")


# === EVENT TYPES ===

@router.get("/event-types", response_model=list[EventTypeResponse])
async def list_event_types(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get all event types."""
    query = db.query(EventType)
    if active_only:
        query = query.filter(EventType.is_active == True)
    return query.all()


@router.get("/event-types/{type_id}", response_model=EventTypeResponse)
async def get_event_type(type_id: int, db: Session = Depends(get_db)):
    """Get a specific event type."""
    event_type = db.query(EventType).filter(EventType.id == type_id).first()
    if not event_type:
        raise HTTPException(status_code=404, detail="Event type not found")
    return event_type


@router.post("/event-types", response_model=EventTypeResponse)
async def create_event_type(data: EventTypeCreate, db: Session = Depends(get_db)):
    """Create a new event type."""
    # Check for duplicate code
    existing = db.query(EventType).filter(EventType.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Event type code already exists")

    event_type = EventType(**data.model_dump())
    db.add(event_type)
    db.commit()
    db.refresh(event_type)
    return event_type


@router.put("/event-types/{type_id}", response_model=EventTypeResponse)
async def update_event_type(
    type_id: int,
    data: EventTypeUpdate,
    db: Session = Depends(get_db)
):
    """Update an event type."""
    event_type = db.query(EventType).filter(EventType.id == type_id).first()
    if not event_type:
        raise HTTPException(status_code=404, detail="Event type not found")

    # Check for duplicate code if changing
    if data.code and data.code != event_type.code:
        existing = db.query(EventType).filter(EventType.code == data.code).first()
        if existing:
            raise HTTPException(status_code=400, detail="Event type code already exists")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(event_type, key, value)

    db.commit()
    db.refresh(event_type)
    return event_type


@router.delete("/event-types/{type_id}", response_model=MessageResponse)
async def delete_event_type(type_id: int, db: Session = Depends(get_db)):
    """Delete an event type."""
    event_type = db.query(EventType).filter(EventType.id == type_id).first()
    if not event_type:
        raise HTTPException(status_code=404, detail="Event type not found")

    # Check if event type is in use
    file_count = db.query(func.count(NasFile.id)).filter(
        NasFile.event_type_id == type_id
    ).scalar()
    group_count = db.query(func.count(AssetGroup.id)).filter(
        AssetGroup.event_type_id == type_id
    ).scalar()

    if file_count > 0 or group_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Event type is used by {file_count} files and {group_count} groups. Deactivate instead."
        )

    db.delete(event_type)
    db.commit()
    return MessageResponse(message=f"Event type '{event_type.code}' deleted")
