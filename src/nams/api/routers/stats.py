"""Statistics API router for NAMS."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import AssetGroup, EventType, NasFile, Region, get_db
from ..schemas import OverviewStats, RegionStats, YearStats
from ..services.matching import get_matching_summary

router = APIRouter()


def format_size(bytes_size: int) -> str:
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} PB"


@router.get("/overview", response_model=OverviewStats)
async def get_overview_stats(db: Session = Depends(get_db)):
    """Get overview statistics."""
    total_files = db.query(func.count(NasFile.id)).scalar() or 0
    total_groups = db.query(func.count(AssetGroup.id)).scalar() or 0
    total_size = db.query(func.sum(NasFile.size_bytes)).scalar() or 0

    matched_files = db.query(func.count(NasFile.id)).filter(
        NasFile.asset_group_id.isnot(None)
    ).scalar() or 0

    unmatched_files = total_files - matched_files
    match_rate = (matched_files / total_files * 100) if total_files > 0 else 0

    pokergo_matched = db.query(func.count(AssetGroup.id)).filter(
        AssetGroup.pokergo_episode_id.isnot(None)
    ).scalar() or 0

    pokergo_rate = (pokergo_matched / total_groups * 100) if total_groups > 0 else 0

    return OverviewStats(
        total_files=total_files,
        total_groups=total_groups,
        total_size_bytes=total_size,
        total_size_formatted=format_size(total_size),
        matched_files=matched_files,
        unmatched_files=unmatched_files,
        match_rate=round(match_rate, 1),
        pokergo_matched_groups=pokergo_matched,
        pokergo_match_rate=round(pokergo_rate, 1),
    )


@router.get("/by-year", response_model=list[YearStats])
async def get_stats_by_year(db: Session = Depends(get_db)):
    """Get statistics grouped by year."""
    # File stats by year
    file_stats = db.query(
        NasFile.year,
        func.count(NasFile.id).label('file_count'),
        func.sum(NasFile.size_bytes).label('size_bytes'),
    ).filter(NasFile.year.isnot(None)).group_by(NasFile.year).all()

    # Group stats by year
    group_stats = db.query(
        AssetGroup.year,
        func.count(AssetGroup.id).label('group_count'),
    ).group_by(AssetGroup.year).all()

    group_map = {g.year: g.group_count for g in group_stats}

    result = []
    for f in file_stats:
        result.append(YearStats(
            year=f.year,
            file_count=f.file_count,
            group_count=group_map.get(f.year, 0),
            size_bytes=f.size_bytes or 0,
            size_formatted=format_size(f.size_bytes or 0),
        ))

    return sorted(result, key=lambda x: x.year, reverse=True)


@router.get("/by-region", response_model=list[RegionStats])
async def get_stats_by_region(db: Session = Depends(get_db)):
    """Get statistics grouped by region."""
    # Query with region join
    stats = db.query(
        Region.code,
        Region.name,
        func.count(NasFile.id).label('file_count'),
        func.sum(NasFile.size_bytes).label('size_bytes'),
    ).outerjoin(NasFile, NasFile.region_id == Region.id).group_by(
        Region.id
    ).all()

    # Group counts
    group_stats = db.query(
        Region.code,
        func.count(AssetGroup.id).label('group_count'),
    ).outerjoin(AssetGroup, AssetGroup.region_id == Region.id).group_by(
        Region.id
    ).all()

    group_map = {g.code: g.group_count for g in group_stats}

    result = []
    for s in stats:
        result.append(RegionStats(
            region_code=s.code,
            region_name=s.name,
            file_count=s.file_count or 0,
            group_count=group_map.get(s.code, 0),
            size_bytes=s.size_bytes or 0,
        ))

    return result


@router.get("/unclassified")
async def get_unclassified_stats(db: Session = Depends(get_db)):
    """Get statistics for unclassified files."""
    # Files without group
    no_group = db.query(func.count(NasFile.id)).filter(
        NasFile.asset_group_id.is_(None)
    ).scalar() or 0

    # Files with UNK event type
    unk_type = db.query(EventType).filter(EventType.code == "UNK").first()
    unk_count = 0
    if unk_type:
        unk_count = db.query(func.count(NasFile.id)).filter(
            NasFile.event_type_id == unk_type.id
        ).scalar() or 0

    # Files without year
    no_year = db.query(func.count(NasFile.id)).filter(
        NasFile.year.is_(None)
    ).scalar() or 0

    # Files without episode
    no_episode = db.query(func.count(NasFile.id)).filter(
        NasFile.episode.is_(None)
    ).scalar() or 0

    return {
        "no_group": no_group,
        "unknown_type": unk_count,
        "no_year": no_year,
        "no_episode": no_episode,
    }


@router.get("/matching-summary")
async def get_matching_summary_stats(db: Session = Depends(get_db)):
    """Get 4-category matching summary.

    Returns:
        {
            "total_nas_groups": 716,
            "total_pokergo_episodes": 1095,
            "MATCHED": 409,
            "NAS_ONLY_HISTORIC": 307,
            "NAS_ONLY_MODERN": 0,
            "POKERGO_ONLY": 957
        }
    """
    return get_matching_summary(db)


@router.get("/sync-status")
async def get_sync_status(db: Session = Depends(get_db)):
    """Get Origin/Archive sync status.

    Returns folder distribution and role conflicts.
    """
    # Get all files with their directories
    files = db.query(NasFile).all()

    origin_count = 0
    archive_count = 0
    origin_primary = 0
    archive_primary = 0

    for f in files:
        directory = (f.directory or "").lower()
        full_path = (f.full_path or "").lower()

        is_archive = "archive" in directory or "z:/archive" in full_path
        is_origin = "origin" in directory or "y:/wsop" in full_path

        if is_archive:
            archive_count += 1
            if f.role == "primary":
                archive_primary += 1
        elif is_origin:
            origin_count += 1
            if f.role == "primary":
                origin_primary += 1

    # Count shared groups (groups with files from both origin and archive)
    from collections import defaultdict
    group_folders = defaultdict(lambda: {"origin": 0, "archive": 0})
    for f in files:
        if f.asset_group_id:
            directory = (f.directory or "").lower()
            full_path = (f.full_path or "").lower()
            is_archive = "archive" in directory or "z:/archive" in full_path

            if is_archive:
                group_folders[f.asset_group_id]["archive"] += 1
            else:
                group_folders[f.asset_group_id]["origin"] += 1

    shared_groups = sum(
        1 for g in group_folders.values() if g["origin"] > 0 and g["archive"] > 0
    )
    origin_only_groups = sum(
        1 for g in group_folders.values() if g["origin"] > 0 and g["archive"] == 0
    )
    archive_only_groups = sum(
        1 for g in group_folders.values() if g["origin"] == 0 and g["archive"] > 0
    )

    return {
        "origin_files": origin_count,
        "archive_files": archive_count,
        "origin_primary": origin_primary,
        "archive_primary": archive_primary,
        "shared_groups": shared_groups,
        "origin_only_groups": origin_only_groups,
        "archive_only_groups": archive_only_groups,
        "has_role_conflict": archive_primary > 0,
    }
