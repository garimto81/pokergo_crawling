"""
GGP POKERGO 폴더 스캔 스크립트.

X:\GGP Footage\POKERGO 폴더의 파일들을 스캔하여 NasFile DB에 등록합니다.
이 파일들은 PokerGO 타이틀과 직접 매칭되는 ORIGIN 소스입니다.
"""
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.database import get_db, NasFile, Region, EventType, AssetGroup


GGP_ROOT = Path(r"X:\GGP Footage\POKERGO")
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mxf', '.avi', '.mkv', '.wmv', '.m4v'}


def parse_ggp_filename(filepath: Path) -> dict:
    """Parse GGP filename to extract metadata.

    GGP filenames match PokerGO title format:
    - WSOP 2017 Main Event _ Episode 1.mp4
    - WSOP Europe 2009 Main Event Day 1.mp4
    - WSOP 2024 Bracelet Events - Episodes - Event #1...
    """
    filename = filepath.stem
    parent = filepath.parent.name  # WSOP 2017, WSOPE 2009, etc.

    meta = {
        'year': None,
        'region': 'LV',  # Default Las Vegas
        'event_type': None,
        'episode': None,
        'day': None,
        'event_num': None,
        'pokergo_title': None,
    }

    # Extract year from filename first (more reliable)
    m = re.search(r'WSOP[E]?\s*(\d{4})', filename, re.IGNORECASE)
    if m:
        meta['year'] = int(m.group(1))

    # Fallback: Extract year from parent folder
    if not meta['year']:
        m = re.search(r'(\d{4})', parent)
        if m:
            meta['year'] = int(m.group(1))

    # Extract region from filename or parent
    fname_lower = filename.lower()
    parent_lower = parent.lower()
    if 'europe' in fname_lower or 'wsope' in fname_lower or 'europe' in parent_lower or 'wsope' in parent_lower:
        meta['region'] = 'EU'
    elif 'apac' in fname_lower or 'apac' in parent_lower:
        meta['region'] = 'APAC'

    # Parse filename for event type and episode/event_num

    # Main Event Episode: "WSOP 2017 Main Event _ Episode 1"
    if 'main event' in fname_lower:
        meta['event_type'] = 'ME'
        m = re.search(r'episode\s*(\d+)', fname_lower)
        if m:
            meta['episode'] = int(m.group(1))
        else:
            # Day format: "Day 1"
            m = re.search(r'day\s*(\d+)', fname_lower)
            if m:
                meta['day'] = m.group(1)

    # Bracelet Event: "Event #10 $5K NLH" or "Bracelet Events - Episodes - Event #1"
    elif 'bracelet' in fname_lower or ('event' in fname_lower and '#' in fname_lower):
        meta['event_type'] = 'BR'
        m = re.search(r'event\s*#(\d+)', fname_lower)
        if m:
            meta['event_num'] = int(m.group(1))

    # High Roller
    elif 'high roller' in fname_lower:
        meta['event_type'] = 'HR'
        m = re.search(r'episode\s*(\d+)', fname_lower)
        if m:
            meta['episode'] = int(m.group(1))

    # Convert filename to PokerGO title format
    # WSOP 2017 Main Event _ Episode 1 -> WSOP 2017 Main Event | Episode 1
    # WSOP 2024 Bracelet Events - Episodes - Event #1 -> WSOP 2024 Bracelet Events | Episodes | Event #1
    pokergo_title = filename.replace(' _ ', ' | ').replace(' - ', ' | ').replace('  ', ' ')
    meta['pokergo_title'] = pokergo_title

    return meta


def scan_ggp_folder():
    """Scan GGP POKERGO folder and register files."""
    if not GGP_ROOT.exists():
        print(f"Error: GGP folder not found: {GGP_ROOT}")
        return

    db = next(get_db())

    # Get region and event type mappings
    regions = {r.code: r.id for r in db.query(Region).all()}
    event_types = {e.code: e.id for e in db.query(EventType).all()}

    # Scan files
    files = [f for f in GGP_ROOT.rglob('*')
             if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS]

    print(f"Found {len(files)} video files in GGP folder")

    # Statistics
    stats = defaultdict(int)
    added = 0
    skipped = 0

    for filepath in files:
        # Check if already exists
        full_path = str(filepath)
        existing = db.query(NasFile).filter(NasFile.full_path == full_path).first()
        if existing:
            skipped += 1
            continue

        # Parse metadata
        meta = parse_ggp_filename(filepath)

        # Get file info
        stat = filepath.stat()

        # Create NasFile record
        nas_file = NasFile(
            filename=filepath.name,
            extension=filepath.suffix.lower().lstrip('.'),
            size_bytes=stat.st_size,
            directory=str(filepath.parent),
            full_path=full_path,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            year=meta['year'],
            region_id=regions.get(meta['region']),
            event_type_id=event_types.get(meta['event_type']) if meta['event_type'] else None,
            episode=meta['episode'],
            event_num=meta.get('event_num'),
            stage=meta.get('day'),  # Store day as stage
            role='primary',  # GGP files are primary source
            role_priority=1,
        )

        db.add(nas_file)
        added += 1
        stats[f"{meta['year']}_{meta['region']}_{meta['event_type']}"] += 1

    db.commit()

    print(f"\n=== Scan Results ===")
    print(f"Added: {added}")
    print(f"Skipped (existing): {skipped}")
    print(f"\nBy Year/Region/Type:")
    for key, count in sorted(stats.items()):
        print(f"  {key}: {count}")

    return added


def normalize_title(text: str) -> str:
    """Normalize title for comparison."""
    # Replace separators with space
    text = text.replace('|', ' ').replace('_', ' ').replace('-', ' ')
    # Remove $ and other special chars
    text = re.sub(r'[$,]', '', text)
    # Remove parentheses
    text = text.replace('(', '').replace(')', '')
    # Normalize "vs." to "vs"
    text = text.replace('vs.', 'vs')
    # Multiple spaces to single
    text = re.sub(r'\s+', ' ', text)
    return text.strip().lower()


def link_ggp_to_pokergo():
    """Link GGP files to PokerGO titles via matching."""
    import json

    db = next(get_db())

    # Load PokerGO data
    json_path = Path(__file__).parent.parent / 'data' / 'pokergo' / 'wsop_final.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        videos = json.load(f).get('videos', [])

    # Build PKG index by normalized title
    pkg_by_norm = {}
    pkg_by_key = {}  # (year, region, type, ep/event) -> title

    for v in videos:
        title = v.get('title', '')
        year = v.get('year', '')
        title_lower = title.lower()

        # Normalized title index
        norm = normalize_title(title)
        pkg_by_norm[norm] = title

        # Extract metadata for key-based matching
        year_int = int(year) if year else None
        region = 'EU' if 'europe' in title_lower else 'LV'

        # Main Event Episode
        if 'main event' in title_lower:
            m = re.search(r'episode\s*(\d+)', title_lower)
            if m and year_int:
                ep = int(m.group(1))
                pkg_by_key[(year_int, region, 'ME', ep)] = title

        # Bracelet Event
        m = re.search(r'event\s*#(\d+)', title_lower)
        if m and year_int:
            event_num = int(m.group(1))
            pkg_by_key[(year_int, region, 'BR', event_num)] = title

    # Get GGP files (from X:\GGP Footage\POKERGO)
    ggp_files = db.query(NasFile).filter(
        NasFile.directory.like('%GGP Footage%POKERGO%')
    ).all()

    print(f"\nLinking {len(ggp_files)} GGP files to PokerGO...")

    matched = 0
    matched_by_key = 0
    unmatched = []

    for f in ggp_files:
        # Normalize filename
        stem = Path(f.filename).stem
        norm = normalize_title(stem)

        pkg_title = None

        # Try direct normalized match
        if norm in pkg_by_norm:
            pkg_title = pkg_by_norm[norm]
            matched += 1

        # Try key-based match
        if not pkg_title:
            region = f.region.code if f.region else 'LV'
            event_type = f.event_type.code if f.event_type else None

            if f.year and event_type == 'ME' and f.episode:
                key = (f.year, region, 'ME', f.episode)
                if key in pkg_by_key:
                    pkg_title = pkg_by_key[key]
                    matched_by_key += 1

            elif f.year and event_type == 'BR' and f.event_num:
                key = (f.year, region, 'BR', f.event_num)
                if key in pkg_by_key:
                    pkg_title = pkg_by_key[key]
                    matched_by_key += 1

        if pkg_title:
            # Find or create AssetGroup
            group_id = f"{f.year}_{f.region.code if f.region else 'LV'}_{f.event_type.code if f.event_type else 'UNK'}_{f.episode or f.event_num or 0}"
            group = db.query(AssetGroup).filter(AssetGroup.group_id == group_id).first()

            if group:
                group.pokergo_title = pkg_title
                f.asset_group_id = group.id
        else:
            unmatched.append((f.filename, f.year, f.event_type.code if f.event_type else None))

    db.commit()

    print(f"Matched (normalized): {matched}")
    print(f"Matched (by key): {matched_by_key}")
    print(f"Total matched: {matched + matched_by_key}")
    print(f"Unmatched: {len(unmatched)}")

    if unmatched:
        print("\nUnmatched samples:")
        for fn, year, etype in unmatched[:10]:
            print(f"  [{year}|{etype}] {fn}")


def main():
    """Main entry point."""
    print("=" * 60)
    print("GGP POKERGO Folder Scanner")
    print("=" * 60)

    # Step 1: Scan and register files
    added = scan_ggp_folder()

    # Step 2: Link to PokerGO titles
    if added:
        link_ggp_to_pokergo()


if __name__ == '__main__':
    main()
