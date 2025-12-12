"""
Matching Result Viewer API
PRD-0035 Implementation
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import stats, matches, export

app = FastAPI(
    title="PokerGO Content Matcher API",
    description="YouTube-NAS 매칭 결과 조회 및 관리 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 로컬 네트워크 접속 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(stats.router, prefix="/api/stats", tags=["Stats"])
app.include_router(matches.router, prefix="/api/matches", tags=["Matches"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])


@app.get("/")
async def root():
    return {
        "name": "PokerGO Content Matcher API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
