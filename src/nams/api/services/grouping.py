"""Auto-grouping service for NAMS."""
from collections import defaultdict
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import NasFile, AssetGroup, Region, EventType, get_db_context


def generate_group_id(
    year: int,
    region_code: Optional[str],
    event_type_code: Optional[str],
    episode: Optional[int]
) -> str:
    """Generate group ID from metadata.

    Format: {year}_{region}_{type}_{episode:02d}
    Examples:
        2014_APAC_ME_01
        2011_ME_25
        2024_PARADISE_ME_01
    """
    parts = [str(year)]

    if region_code:
        parts.append(region_code)

    if event_type_code:
        parts.append(event_type_code)

    if episode is not None:
        parts.append(f"{episode:02d}")

    return "_".join(parts)


def get_or_create_group(
    db: Session,
    year: int,
    region_id: Optional[int],
    event_type_id: Optional[int],
    episode: Optional[int],
    region_code: Optional[str] = None,
    event_type_code: Optional[str] = None,
) -> AssetGroup:
    """Get existing group or create new one."""
    # Get codes if not provided
    if region_id and not region_code:
        region = db.query(Region).get(region_id)
        region_code = region.code if region else None

    if event_type_id and not event_type_code:
        event_type = db.query(EventType).get(event_type_id)
        event_type_code = event_type.code if event_type else None

    # Generate group ID
    group_id = generate_group_id(year, region_code, event_type_code, episode)

    # Check if exists
    existing = db.query(AssetGroup).filter(AssetGroup.group_id == group_id).first()
    if existing:
        return existing

    # Create new group
    group = AssetGroup(
        group_id=group_id,
        year=year,
        region_id=region_id,
        event_type_id=event_type_id,
        episode=episode,
    )
    db.add(group)
    db.flush()  # Get ID

    return group


def assign_file_to_group(db: Session, file: NasFile, group: AssetGroup) -> bool:
    """Assign file to group and set role.

    Returns:
        True if file was updated
    """
    if file.asset_group_id == group.id:
        return False

    file.asset_group_id = group.id

    # Determine role based on existing files
    existing_primary = db.query(NasFile).filter(
        NasFile.asset_group_id == group.id,
        NasFile.role == 'primary'
    ).first()

    if not existing_primary and file.role == 'primary':
        # This file becomes primary
        file.role_priority = 1
    elif not existing_primary:
        # First file becomes primary
        file.role = 'primary'
        file.role_priority = 1
    else:
        # Subsequent files are backups
        max_priority = db.query(func.max(NasFile.role_priority)).filter(
            NasFile.asset_group_id == group.id
        ).scalar() or 0
        file.role = 'backup'
        file.role_priority = max_priority + 1

    return True


def update_group_stats(db: Session, group: AssetGroup):
    """Update group statistics."""
    files = db.query(NasFile).filter(NasFile.asset_group_id == group.id).all()

    group.file_count = len(files)
    group.total_size_bytes = sum(f.size_bytes for f in files)
    group.has_backup = any(f.role == 'backup' for f in files)


def run_auto_grouping(db: Session) -> dict:
    """Run auto-grouping on ungrouped files.

    Returns:
        Statistics about grouping
    """
    stats = {
        'processed': 0,
        'grouped': 0,
        'new_groups': 0,
        'skipped': 0,
    }

    # Get files without group that have year
    files = db.query(NasFile).filter(
        NasFile.asset_group_id == None,
        NasFile.year != None
    ).all()

    stats['processed'] = len(files)

    # Group files by their metadata
    file_groups = defaultdict(list)
    for file in files:
        key = (file.year, file.region_id, file.event_type_id, file.episode)
        file_groups[key].append(file)

    # Get region/event_type codes for group ID generation
    regions = {r.id: r.code for r in db.query(Region).all()}
    event_types = {e.id: e.code for e in db.query(EventType).all()}

    # Process each group
    groups_created = set()
    for (year, region_id, event_type_id, episode), group_files in file_groups.items():
        if not year:
            stats['skipped'] += len(group_files)
            continue

        region_code = regions.get(region_id)
        event_type_code = event_types.get(event_type_id)

        # Get or create group
        group = get_or_create_group(
            db, year, region_id, event_type_id, episode,
            region_code, event_type_code
        )

        if group.id not in groups_created:
            groups_created.add(group.id)
            stats['new_groups'] += 1

        # Assign files to group
        for file in group_files:
            if assign_file_to_group(db, file, group):
                stats['grouped'] += 1

        # Update group stats
        update_group_stats(db, group)

    db.commit()

    # Recalculate new_groups (only count newly created)
    stats['new_groups'] = len(groups_created)

    return stats


def run_grouping() -> dict:
    """Run auto-grouping on all ungrouped files."""
    with get_db_context() as db:
        return run_auto_grouping(db)
