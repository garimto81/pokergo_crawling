"""FastAPI application entry point for NAMS."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_database
from .routers import patterns, settings, files, groups, stats, process

# Initialize database on startup
init_database()

# Create FastAPI app
app = FastAPI(
    title="NAMS - NAS Asset Management System",
    description="NAS 파일 메타데이터 추출, 그룹화, PokerGO 매칭 통합 관리",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(stats.router, prefix="/api/stats", tags=["Statistics"])
app.include_router(patterns.router, prefix="/api/patterns", tags=["Patterns"])
app.include_router(settings.router, prefix="/api", tags=["Settings"])
app.include_router(files.router, prefix="/api/files", tags=["Files"])
app.include_router(groups.router, prefix="/api/groups", tags=["Groups"])
app.include_router(process.router, prefix="/api/process", tags=["Processing"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "NAMS API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
