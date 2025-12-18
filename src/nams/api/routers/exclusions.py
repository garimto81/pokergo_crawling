"""Exclusion Rules API router for NAMS."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db, ExclusionRule
from ..schemas import (
    ExclusionRuleResponse,
    ExclusionRuleCreate,
    ExclusionRuleUpdate,
    ExclusionRuleListResponse,
    ExclusionRuleTestRequest,
    ExclusionRuleTestResult,
    MessageResponse,
)

router = APIRouter()


@router.get("", response_model=ExclusionRuleListResponse)
async def list_exclusion_rules(
    active_only: bool = False,
    rule_type: str = None,
    db: Session = Depends(get_db)
):
    """Get all exclusion rules."""
    query = db.query(ExclusionRule)
    if active_only:
        query = query.filter(ExclusionRule.is_active == True)
    if rule_type:
        query = query.filter(ExclusionRule.rule_type == rule_type)

    rules = query.order_by(ExclusionRule.rule_type, ExclusionRule.id).all()
    return ExclusionRuleListResponse(items=rules, total=len(rules))


@router.get("/{rule_id}", response_model=ExclusionRuleResponse)
async def get_exclusion_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get a specific exclusion rule."""
    rule = db.query(ExclusionRule).filter(ExclusionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Exclusion rule not found")
    return rule


@router.post("", response_model=ExclusionRuleResponse)
async def create_exclusion_rule(data: ExclusionRuleCreate, db: Session = Depends(get_db)):
    """Create a new exclusion rule."""
    # Check for duplicate
    existing = db.query(ExclusionRule).filter(
        ExclusionRule.rule_type == data.rule_type,
        ExclusionRule.operator == data.operator,
        ExclusionRule.value == data.value
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Duplicate exclusion rule")

    rule = ExclusionRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=ExclusionRuleResponse)
async def update_exclusion_rule(
    rule_id: int,
    data: ExclusionRuleUpdate,
    db: Session = Depends(get_db)
):
    """Update an exclusion rule."""
    rule = db.query(ExclusionRule).filter(ExclusionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Exclusion rule not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rule, key, value)

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", response_model=MessageResponse)
async def delete_exclusion_rule(rule_id: int, db: Session = Depends(get_db)):
    """Delete an exclusion rule."""
    rule = db.query(ExclusionRule).filter(ExclusionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Exclusion rule not found")

    db.delete(rule)
    db.commit()
    return MessageResponse(message=f"Exclusion rule deleted: {rule.rule_type} {rule.operator} {rule.value}")


@router.put("/{rule_id}/toggle", response_model=ExclusionRuleResponse)
async def toggle_exclusion_rule(rule_id: int, db: Session = Depends(get_db)):
    """Toggle exclusion rule active status."""
    rule = db.query(ExclusionRule).filter(ExclusionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Exclusion rule not found")

    rule.is_active = not rule.is_active
    db.commit()
    db.refresh(rule)
    return rule


@router.post("/test", response_model=ExclusionRuleTestResult)
async def test_exclusion_rule(data: ExclusionRuleTestRequest):
    """Test an exclusion rule against sample data."""
    would_exclude = False
    reason = ""

    if data.rule_type == "size":
        if data.sample_size_bytes is None:
            return ExclusionRuleTestResult(
                would_exclude=False,
                reason="No sample size provided"
            )
        threshold = int(data.value)
        if data.operator == "lt" and data.sample_size_bytes < threshold:
            would_exclude = True
            reason = f"Size {data.sample_size_bytes:,} bytes < {threshold:,} bytes"
        elif data.operator == "gt" and data.sample_size_bytes > threshold:
            would_exclude = True
            reason = f"Size {data.sample_size_bytes:,} bytes > {threshold:,} bytes"
        elif data.operator == "eq" and data.sample_size_bytes == threshold:
            would_exclude = True
            reason = f"Size equals {threshold:,} bytes"

    elif data.rule_type == "duration":
        if data.sample_duration_sec is None:
            return ExclusionRuleTestResult(
                would_exclude=False,
                reason="No sample duration provided"
            )
        threshold = int(data.value)
        if data.operator == "lt" and data.sample_duration_sec < threshold:
            would_exclude = True
            reason = f"Duration {data.sample_duration_sec}s < {threshold}s"
        elif data.operator == "gt" and data.sample_duration_sec > threshold:
            would_exclude = True
            reason = f"Duration {data.sample_duration_sec}s > {threshold}s"
        elif data.operator == "eq" and data.sample_duration_sec == threshold:
            would_exclude = True
            reason = f"Duration equals {threshold}s"

    elif data.rule_type == "keyword":
        if data.sample_filename is None:
            return ExclusionRuleTestResult(
                would_exclude=False,
                reason="No sample filename provided"
            )
        filename_lower = data.sample_filename.lower()
        keyword_lower = data.value.lower()
        if data.operator == "contains" and keyword_lower in filename_lower:
            would_exclude = True
            reason = f"Filename contains '{data.value}'"
        elif data.operator == "eq" and filename_lower == keyword_lower:
            would_exclude = True
            reason = f"Filename equals '{data.value}'"

    if not would_exclude:
        reason = "File would NOT be excluded by this rule"

    return ExclusionRuleTestResult(would_exclude=would_exclude, reason=reason)
