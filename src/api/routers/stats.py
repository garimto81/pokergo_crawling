"""
Stats API Router
"""

from fastapi import APIRouter

from ..services import database
from ..schemas.match import StatsSummary, NotUploadedCategories, ScoreDistribution

router = APIRouter()


@router.get("/summary", response_model=StatsSummary)
async def get_summary():
    """대시보드 통계 조회"""
    return database.get_stats_summary()


@router.get("/not-uploaded-categories", response_model=NotUploadedCategories)
async def get_not_uploaded_categories():
    """미업로드 카테고리별 분류"""
    return database.get_not_uploaded_categories()


@router.get("/score-distribution", response_model=ScoreDistribution)
async def get_score_distribution(bins: int = 10):
    """점수 분포 히스토그램"""
    return database.get_score_distribution(bins)
