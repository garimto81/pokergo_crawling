"""Migration service to import JSON data into NAMS database."""
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ..database import AssetGroup, EventType, NasFile, PokergoEpisode, Region, get_db_context

# Data paths
DATA_DIR = Path("D:/AI/claude01/pokergo_crawling/data")
NAS_FILES_JSON = DATA_DIR / "sources/nas/nas_files.json"
GROUPS_JSON = DATA_DIR / "asset_groups/groups.json"
POKERGO_EPISODES_JSON = DATA_DIR / "pokergo/episodes.json"


def load_json(path: Path) -> dict:
    """Load JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_region_id(db: Session, code: str) -> int | None:
    """Get region ID by code."""
    if not code:
        return None
    region = db.query(Region).filter(Region.code == code).first()
    return region.id if region else None


def get_event_type_id(db: Session, code: str) -> int | None:
    """Get event type ID by code."""
    if not code:
        return None
    event_type = db.query(EventType).filter(EventType.code == code).first()
    return event_type.id if event_type else None


def migrate_pokergo_episodes(db: Session) -> int:
    """Import PokerGO episodes from JSON."""
    if not POKERGO_EPISODES_JSON.exists():
        print(f"  [SKIP] PokerGO episodes file not found: {POKERGO_EPISODES_JSON}")
        return 0

    data = load_json(POKERGO_EPISODES_JSON)
    episodes = data.get('episodes', [])

    count = 0
    for ep in episodes:
        # Check if already exists
        existing = db.query(PokergoEpisode).filter(
            PokergoEpisode.id == ep['id']
        ).first()

        if existing:
            continue

        # Parse aired_at
        aired_at = None
        if ep.get('aired_at'):
            try:
                aired_at = datetime.fromisoformat(ep['aired_at'].replace('Z', '+00:00'))
            except:
                pass

        episode = PokergoEpisode(
            id=ep['id'],
            title=ep.get('title'),
            description=ep.get('description'),
            duration_sec=ep.get('duration_sec'),
            collection_title=ep.get('collection_title'),
            season_title=ep.get('season_title'),
            aired_at=aired_at,
        )
        db.add(episode)
        count += 1

    db.commit()
    return count


def migrate_groups_and_files(db: Session) -> tuple[int, int]:
    """Import asset groups and files from JSON."""
    if not GROUPS_JSON.exists():
        print(f"  [SKIP] Groups file not found: {GROUPS_JSON}")
        return 0, 0

    data = load_json(GROUPS_JSON)
    groups = data.get('groups', [])

    group_count = 0
    file_count = 0

    for g in groups:
        # Check if group already exists
        existing_group = db.query(AssetGroup).filter(
            AssetGroup.group_id == g['group_id']
        ).first()

        if existing_group:
            asset_group = existing_group
        else:
            # Get event type ID
            event_type_id = get_event_type_id(db, g.get('event_abbrev'))

            # Determine region from group_id
            region_code = None
            group_id = g['group_id']
            if 'APAC' in group_id:
                region_code = 'APAC'
            elif 'EU' in group_id:
                region_code = 'EU'
            elif 'PARADISE' in group_id:
                region_code = 'PARADISE'

            region_id = get_region_id(db, region_code)

            # Get PokerGO match info
            pokergo_match = g.get('pokergo_match', {})
            has_pokergo = g.get('has_pokergo_match', False)

            # Set pokergo_episode_id to "matched" if has_pokergo_match is true but no id
            pokergo_id = pokergo_match.get('id')
            if has_pokergo and pokergo_match.get('title') and not pokergo_id:
                pokergo_id = f"matched_{g['group_id']}"  # Generate a placeholder ID

            asset_group = AssetGroup(
                group_id=g['group_id'],
                year=int(g['year']) if g.get('year') else 0,
                region_id=region_id,
                event_type_id=event_type_id,
                episode=g.get('episode'),
                pokergo_episode_id=pokergo_id,
                pokergo_title=pokergo_match.get('title'),
                pokergo_match_score=pokergo_match.get('score', 1.0 if has_pokergo else None),
                file_count=g.get('stats', {}).get('file_count', 0),
                total_size_bytes=int(g.get('stats', {}).get('total_size_gb', 0) * 1024**3),
                has_backup=g.get('stats', {}).get('has_backup', False),
            )
            db.add(asset_group)
            db.flush()  # Get the ID
            group_count += 1

        # Add primary file
        primary = g.get('primary')
        if primary:
            file_count += add_file(db, primary, asset_group.id, 'primary', 1)

        # Add backup files
        for idx, backup in enumerate(g.get('backups', []), start=1):
            file_count += add_file(db, backup, asset_group.id, 'backup', idx + 1)

    db.commit()
    return group_count, file_count


def add_file(db: Session, file_data: dict, group_id: int, role: str, priority: int) -> int:
    """Add a file to the database."""
    filename = file_data.get('filename')
    if not filename:
        return 0

    # Check if already exists
    existing = db.query(NasFile).filter(
        NasFile.filename == filename,
        NasFile.asset_group_id == group_id
    ).first()

    if existing:
        return 0

    nas_file = NasFile(
        filename=filename,
        extension=file_data.get('extension', ''),
        size_bytes=file_data.get('size_bytes', 0),
        directory=file_data.get('directory'),
        full_path=file_data.get('origin'),
        asset_group_id=group_id,
        role=role,
        role_priority=priority,
    )
    db.add(nas_file)
    return 1


def run_migration(clear_existing: bool = False) -> dict:
    """Run full migration from JSON files to database.

    Args:
        clear_existing: If True, clear existing data before import

    Returns:
        Dictionary with migration statistics
    """
    stats = {
        'pokergo_episodes': 0,
        'groups': 0,
        'files': 0,
        'errors': [],
    }

    with get_db_context() as db:
        if clear_existing:
            print("[INFO] Clearing existing data...")
            db.query(NasFile).delete()
            db.query(AssetGroup).delete()
            db.query(PokergoEpisode).delete()
            db.commit()

        # 1. Import PokerGO episodes
        print("[Step 1/2] Importing PokerGO episodes...")
        try:
            stats['pokergo_episodes'] = migrate_pokergo_episodes(db)
            print(f"  [OK] Imported {stats['pokergo_episodes']} episodes")
        except Exception as e:
            stats['errors'].append(f"PokerGO import failed: {str(e)}")
            print(f"  [ERROR] {e}")

        # 2. Import groups and files
        print("[Step 2/2] Importing groups and files...")
        try:
            groups, files = migrate_groups_and_files(db)
            stats['groups'] = groups
            stats['files'] = files
            print(f"  [OK] Imported {groups} groups, {files} files")
        except Exception as e:
            stats['errors'].append(f"Groups import failed: {str(e)}")
            print(f"  [ERROR] {e}")

    return stats


if __name__ == "__main__":
    print("=" * 50)
    print("  NAMS Data Migration")
    print("=" * 50)

    stats = run_migration(clear_existing=True)

    print()
    print("=" * 50)
    print("  Migration Complete")
    print("=" * 50)
    print(f"  PokerGO Episodes: {stats['pokergo_episodes']}")
    print(f"  Asset Groups:     {stats['groups']}")
    print(f"  NAS Files:        {stats['files']}")
    if stats['errors']:
        print(f"  Errors:           {len(stats['errors'])}")
        for err in stats['errors']:
            print(f"    - {err}")
    print("=" * 50)
