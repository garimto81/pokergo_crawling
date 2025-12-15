"""Pattern management API router for NAMS."""
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db, Pattern, NasFile
from ..schemas import (
    PatternResponse,
    PatternCreate,
    PatternUpdate,
    PatternReorder,
    PatternTestRequest,
    PatternTestResult,
    PatternAffectedFiles,
    MessageResponse,
)

router = APIRouter()


@router.get("", response_model=list[PatternResponse])
async def list_patterns(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get all patterns ordered by priority."""
    query = db.query(Pattern)
    if active_only:
        query = query.filter(Pattern.is_active == True)
    return query.order_by(Pattern.priority).all()


@router.get("/{pattern_id}", response_model=PatternResponse)
async def get_pattern(pattern_id: int, db: Session = Depends(get_db)):
    """Get a specific pattern."""
    pattern = db.query(Pattern).filter(Pattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return pattern


@router.post("", response_model=PatternResponse)
async def create_pattern(data: PatternCreate, db: Session = Depends(get_db)):
    """Create a new pattern."""
    # Validate regex
    try:
        re.compile(data.regex)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex: {str(e)}")

    # Check for duplicate name
    existing = db.query(Pattern).filter(Pattern.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Pattern name already exists")

    pattern = Pattern(**data.model_dump())
    db.add(pattern)
    db.commit()
    db.refresh(pattern)
    return pattern


@router.put("/{pattern_id}", response_model=PatternResponse)
async def update_pattern(
    pattern_id: int,
    data: PatternUpdate,
    db: Session = Depends(get_db)
):
    """Update a pattern."""
    pattern = db.query(Pattern).filter(Pattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    # Validate regex if provided
    if data.regex:
        try:
            re.compile(data.regex)
        except re.error as e:
            raise HTTPException(status_code=400, detail=f"Invalid regex: {str(e)}")

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pattern, key, value)

    db.commit()
    db.refresh(pattern)
    return pattern


@router.delete("/{pattern_id}", response_model=MessageResponse)
async def delete_pattern(pattern_id: int, db: Session = Depends(get_db)):
    """Delete a pattern."""
    pattern = db.query(Pattern).filter(Pattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    # Check if pattern is in use
    used_count = db.query(func.count(NasFile.id)).filter(
        NasFile.matched_pattern_id == pattern_id
    ).scalar()

    if used_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Pattern is used by {used_count} files. Deactivate instead."
        )

    db.delete(pattern)
    db.commit()
    return MessageResponse(message=f"Pattern '{pattern.name}' deleted")


@router.post("/reorder", response_model=MessageResponse)
async def reorder_patterns(data: PatternReorder, db: Session = Depends(get_db)):
    """Reorder patterns by updating priorities."""
    for idx, pattern_id in enumerate(data.pattern_ids):
        pattern = db.query(Pattern).filter(Pattern.id == pattern_id).first()
        if pattern:
            pattern.priority = idx + 1

    db.commit()
    return MessageResponse(message="Pattern priorities updated")


@router.post("/{pattern_id}/test", response_model=PatternTestResult)
async def test_pattern(
    pattern_id: int,
    data: PatternTestRequest,
    db: Session = Depends(get_db)
):
    """Test a pattern against a filename."""
    pattern = db.query(Pattern).filter(Pattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    try:
        regex = re.compile(pattern.regex, re.IGNORECASE)
        match = regex.search(data.filename.upper())

        if not match:
            return PatternTestResult(matched=False, confidence=0.0)

        # Extract values based on pattern configuration
        groups = match.groups()
        result = PatternTestResult(
            matched=True,
            pattern_name=pattern.name,
            confidence=0.8,
        )

        # Try to extract year (usually first group)
        if pattern.extract_year and len(groups) >= 1:
            year_str = groups[0]
            if year_str and year_str.isdigit():
                year = int(year_str)
                if year < 100:
                    year = 2000 + year if year <= 30 else 1900 + year
                result.extracted_year = str(year)

        # Set fixed region if configured
        if pattern.extract_region:
            result.extracted_region = pattern.extract_region

        # Set fixed type if configured
        if pattern.extract_type:
            result.extracted_type = pattern.extract_type

        # Try to extract episode (usually last numeric group)
        if pattern.extract_episode and len(groups) >= 2:
            for g in reversed(groups):
                if g and g.isdigit():
                    result.extracted_episode = int(g)
                    break

        return result

    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Regex error: {str(e)}")


@router.get("/{pattern_id}/affected", response_model=PatternAffectedFiles)
async def get_affected_files(pattern_id: int, db: Session = Depends(get_db)):
    """Get files that would be affected by this pattern."""
    pattern = db.query(Pattern).filter(Pattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    # Get files currently matched by this pattern
    files = db.query(NasFile).filter(
        NasFile.matched_pattern_id == pattern_id
    ).limit(10).all()

    return PatternAffectedFiles(
        pattern_id=pattern.id,
        pattern_name=pattern.name,
        affected_count=db.query(func.count(NasFile.id)).filter(
            NasFile.matched_pattern_id == pattern_id
        ).scalar() or 0,
        sample_files=[f.filename for f in files],
    )
