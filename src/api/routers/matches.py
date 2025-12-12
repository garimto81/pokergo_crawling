"""
Matches API Router
"""

from typing import Optional
from fastapi import APIRouter, HTTPException

from ..services import database
from ..schemas.match import (
    MatchResponse,
    MatchListResponse,
    MatchUpdate,
    BulkUpdateRequest,
    BulkUpdateResponse
)

router = APIRouter()


@router.get("", response_model=MatchListResponse)
async def get_matches(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    score_min: Optional[int] = None,
    score_max: Optional[int] = None,
    year: Optional[str] = None,
    event: Optional[str] = None,
    search: Optional[str] = None
):
    """매칭 목록 조회"""
    return database.get_matches(
        page=page,
        limit=limit,
        status=status,
        score_min=score_min,
        score_max=score_max,
        year=year,
        event=event,
        search=search
    )


@router.get("/{match_id}", response_model=MatchResponse)
async def get_match(match_id: int):
    """단일 매칭 조회"""
    match = database.get_match_by_id(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


@router.patch("/{match_id}", response_model=MatchResponse)
async def update_match(match_id: int, update: MatchUpdate):
    """매칭 업데이트"""
    existing = database.get_match_by_id(match_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Match not found")

    updates = {}
    if update.match_status:
        updates["match_status"] = update.match_status
    if update.youtube_video_id:
        updates["youtube_video_id"] = update.youtube_video_id
    if update.youtube_title:
        updates["youtube_title"] = update.youtube_title

    result = database.update_match(match_id, updates)
    return result


@router.post("/bulk-update", response_model=BulkUpdateResponse)
async def bulk_update(request: BulkUpdateRequest):
    """일괄 상태 업데이트"""
    if not request.ids:
        raise HTTPException(status_code=400, detail="No IDs provided")

    updated = database.bulk_update_matches(
        ids=request.ids,
        status=request.status,
        notes=request.notes
    )

    return {"updated": updated, "status": request.status}
