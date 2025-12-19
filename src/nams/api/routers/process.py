"""Processing API router for NAMS (migration, scan, export, extract, group, match)."""
from enum import Enum
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from ..services.export import (
    GOOGLE_SHEETS_AVAILABLE,
    export_to_csv,
    export_to_google_sheets,
    export_to_json,
    get_csv_content,
)
from ..services.grouping import run_grouping
from ..services.matching import run_matching
from ..services.migration import run_migration
from ..services.pattern_engine import run_pattern_extraction
from ..services.scanner import FolderType, ScanConfig, ScanMode, run_scan

router = APIRouter()


# ============ Migration ============

class MigrationRequest(BaseModel):
    """Migration request parameters."""
    clear_existing: bool = False


class MigrationResponse(BaseModel):
    """Migration response."""
    success: bool
    message: str
    stats: dict


@router.post("/migrate", response_model=MigrationResponse)
async def migrate_json_data(request: MigrationRequest):
    """Import data from JSON files into database.

    This imports:
    - PokerGO episodes from data/pokergo/episodes.json
    - Asset groups and files from data/asset_groups/groups.json
    """
    try:
        stats = run_migration(clear_existing=request.clear_existing)

        if stats['errors']:
            return MigrationResponse(
                success=False,
                message=f"Migration completed with errors: {', '.join(stats['errors'])}",
                stats=stats,
            )

        return MigrationResponse(
            success=True,
            message=f"Successfully imported {stats['pokergo_episodes']} episodes, {stats['groups']} groups, {stats['files']} files",
            stats=stats,
        )
    except Exception as e:
        return MigrationResponse(
            success=False,
            message=f"Migration failed: {str(e)}",
            stats={'error': str(e)},
        )


# ============ NAS Scan ============

class ScanModeEnum(str, Enum):
    """Scan mode enum for API."""
    INCREMENTAL = "incremental"
    FULL = "full"


class FolderTypeEnum(str, Enum):
    """Folder type enum for API."""
    ORIGIN = "origin"
    ARCHIVE = "archive"
    BOTH = "both"


class ScanRequest(BaseModel):
    """NAS scan request parameters."""
    mode: ScanModeEnum = ScanModeEnum.INCREMENTAL
    folder_type: FolderTypeEnum = FolderTypeEnum.BOTH
    origin_path: str = "Z:/WSOP"
    archive_path: str = "Z:/Archive"


class ScanResponse(BaseModel):
    """NAS scan response."""
    success: bool
    message: str
    stats: dict


@router.post("/scan", response_model=ScanResponse)
async def scan_nas(request: ScanRequest):
    """Scan NAS folders for video files.

    Args:
        mode: 'incremental' (추가분만) or 'full' (전체 재스캔)
        folder_type: 'origin', 'archive', or 'both'
        origin_path: Path to origin folder (default: Z:/WSOP)
        archive_path: Path to archive folder (default: Z:/Archive)
    """
    try:
        config = ScanConfig(
            origin_path=request.origin_path,
            archive_path=request.archive_path,
            mode=ScanMode(request.mode.value),
            folder_type=FolderType(request.folder_type.value),
        )

        stats = run_scan(config)

        if stats['errors']:
            return ScanResponse(
                success=False,
                message=f"Scan completed with errors: {', '.join(stats['errors'])}",
                stats=stats,
            )

        return ScanResponse(
            success=True,
            message=f"Scanned {stats['origin_files']} origin + {stats['archive_files']} archive files. Added {stats['new_files']} new files.",
            stats=stats,
        )
    except Exception as e:
        return ScanResponse(
            success=False,
            message=f"Scan failed: {str(e)}",
            stats={'error': str(e)},
        )


# ============ Export ============

class ExportFormat(str, Enum):
    """Export format."""
    CSV = "csv"
    JSON = "json"
    GOOGLE_SHEETS = "google_sheets"


class ExportRequest(BaseModel):
    """Export request parameters."""
    format: ExportFormat = ExportFormat.CSV
    sheet_name: Optional[str] = "NAMS Export"


class ExportResponse(BaseModel):
    """Export response."""
    success: bool
    message: str
    file_path: Optional[str] = None
    url: Optional[str] = None
    details: Optional[dict] = None


@router.post("/export", response_model=ExportResponse)
async def export_data(request: ExportRequest):
    """Export data to CSV, JSON, or Google Sheets.

    Args:
        format: 'csv', 'json', or 'google_sheets'
        sheet_name: Sheet name for Google Sheets export
    """
    try:
        if request.format == ExportFormat.CSV:
            file_path = export_to_csv()
            if file_path:
                return ExportResponse(
                    success=True,
                    message=f"Exported to CSV: {file_path}",
                    file_path=file_path,
                )
            return ExportResponse(
                success=False,
                message="No data to export",
            )

        elif request.format == ExportFormat.JSON:
            file_path = export_to_json()
            if file_path:
                return ExportResponse(
                    success=True,
                    message=f"Exported to JSON: {file_path}",
                    file_path=file_path,
                )
            return ExportResponse(
                success=False,
                message="No data to export",
            )

        elif request.format == ExportFormat.GOOGLE_SHEETS:
            if not GOOGLE_SHEETS_AVAILABLE:
                return ExportResponse(
                    success=False,
                    message="Google Sheets API not available",
                    details={
                        "help": "Install: pip install google-api-python-client google-auth"
                    }
                )

            result = export_to_google_sheets(request.sheet_name or "NAMS Export")
            if result["success"]:
                return ExportResponse(
                    success=True,
                    message=f"Exported to Google Sheets: {result.get('rows_updated', 0)} rows",
                    url=result.get("url"),
                    details=result,
                )
            return ExportResponse(
                success=False,
                message=result.get("error", "Export failed"),
                details=result,
            )

    except Exception as e:
        return ExportResponse(
            success=False,
            message=f"Export failed: {str(e)}",
        )


@router.get("/export/csv", response_class=PlainTextResponse)
async def download_csv():
    """Download data as CSV file."""
    content = get_csv_content()
    return PlainTextResponse(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=nams_groups.csv"}
    )


@router.get("/export/google-sheets/status")
async def google_sheets_status():
    """Check Google Sheets API availability."""
    return {
        "available": GOOGLE_SHEETS_AVAILABLE,
        "message": "Google Sheets API is available" if GOOGLE_SHEETS_AVAILABLE else "Install: pip install google-api-python-client google-auth"
    }


# ============ Pattern Extraction ============

class ProcessResponse(BaseModel):
    """Generic processing response."""
    success: bool
    message: str
    stats: dict


@router.post("/extract", response_model=ProcessResponse)
async def extract_metadata():
    """Extract metadata from filenames using patterns.

    Processes files without pattern match and extracts:
    - year
    - region
    - event_type
    - episode
    """
    try:
        stats = run_pattern_extraction()
        return ProcessResponse(
            success=True,
            message=f"Processed {stats['processed']} files, matched {stats['matched']}, updated {stats['updated']}",
            stats=stats,
        )
    except Exception as e:
        return ProcessResponse(
            success=False,
            message=f"Extraction failed: {str(e)}",
            stats={'error': str(e)},
        )


# ============ Auto Grouping ============

@router.post("/group", response_model=ProcessResponse)
async def auto_group_files():
    """Auto-group files by metadata.

    Groups files with same year + region + event_type + episode
    into AssetGroups.
    """
    try:
        stats = run_grouping()
        return ProcessResponse(
            success=True,
            message=f"Processed {stats['processed']} files, grouped {stats['grouped']}, created {stats['new_groups']} new groups",
            stats=stats,
        )
    except Exception as e:
        return ProcessResponse(
            success=False,
            message=f"Grouping failed: {str(e)}",
            stats={'error': str(e)},
        )


# ============ PokerGO Matching ============

class MatchRequest(BaseModel):
    """Match request parameters."""
    min_score: float = 0.5


@router.post("/match", response_model=ProcessResponse)
async def match_pokergo(request: MatchRequest):
    """Match groups to PokerGO episodes.

    Uses title similarity and metadata to find matches.

    Args:
        min_score: Minimum score (0-1) to accept match (default: 0.5)
    """
    try:
        stats = run_matching(min_score=request.min_score)
        return ProcessResponse(
            success=True,
            message=f"Processed {stats['processed']} groups, matched {stats['matched']}",
            stats=stats,
        )
    except Exception as e:
        return ProcessResponse(
            success=False,
            message=f"Matching failed: {str(e)}",
            stats={'error': str(e)},
        )


# ============ Full Pipeline ============

class PipelineRequest(BaseModel):
    """Pipeline request parameters."""
    scan: bool = True
    scan_mode: ScanModeEnum = ScanModeEnum.INCREMENTAL
    folder_type: FolderTypeEnum = FolderTypeEnum.BOTH
    origin_path: str = "Y:/WSOP Backup"
    archive_path: str = "Z:/archive"
    extract: bool = True
    group: bool = True
    match: bool = True
    min_match_score: float = 0.5


@router.post("/pipeline", response_model=ProcessResponse)
async def run_full_pipeline(request: PipelineRequest):
    """Run full processing pipeline.

    Steps:
    1. Scan NAS folders (optional)
    2. Extract metadata using patterns
    3. Auto-group files
    4. Match groups to PokerGO episodes
    """
    all_stats = {}

    try:
        # 1. Scan
        if request.scan:
            config = ScanConfig(
                origin_path=request.origin_path,
                archive_path=request.archive_path,
                mode=ScanMode(request.scan_mode.value),
                folder_type=FolderType(request.folder_type.value),
            )
            all_stats['scan'] = run_scan(config)

        # 2. Extract
        if request.extract:
            all_stats['extract'] = run_pattern_extraction()

        # 3. Group
        if request.group:
            all_stats['group'] = run_grouping()

        # 4. Match
        if request.match:
            all_stats['match'] = run_matching(min_score=request.min_match_score)

        # Summary
        summary_parts = []
        if 'scan' in all_stats:
            summary_parts.append(f"scanned {all_stats['scan'].get('new_files', 0)} new files")
        if 'extract' in all_stats:
            summary_parts.append(f"extracted {all_stats['extract'].get('updated', 0)} metadata")
        if 'group' in all_stats:
            summary_parts.append(f"grouped {all_stats['group'].get('grouped', 0)} files")
        if 'match' in all_stats:
            summary_parts.append(f"matched {all_stats['match'].get('matched', 0)} groups")

        return ProcessResponse(
            success=True,
            message="Pipeline complete: " + ", ".join(summary_parts),
            stats=all_stats,
        )

    except Exception as e:
        return ProcessResponse(
            success=False,
            message=f"Pipeline failed: {str(e)}",
            stats={'error': str(e), **all_stats},
        )


# ============ Status ============

@router.get("/status")
async def get_processing_status():
    """Get current processing status."""
    return {
        "status": "idle",
        "google_sheets_available": GOOGLE_SHEETS_AVAILABLE,
        "last_migration": None,
        "last_scan": None,
        "last_export": None,
    }
