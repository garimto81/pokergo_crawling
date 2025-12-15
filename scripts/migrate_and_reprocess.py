#!/usr/bin/env python
"""
NAMS Database Migration and Reprocess Script

1. Add new columns to nas_files table (stage, event_num, season, buyin, gtd, version)
2. Add new regions (LA, CYPRUS, LONDON)
3. Replace old patterns with new 14 patterns
4. Reprocess all files with new patterns
"""

import sys
from pathlib import Path

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
from src.nams.api.database.session import DB_PATH, get_db_context
from src.nams.api.database.models import Pattern, Region
from src.nams.api.services.pattern_engine import reprocess_all_files


def migrate_database():
    """Add new columns to nas_files table."""
    print("\n[1/4] Database Migration")
    print("=" * 50)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # New columns to add
    new_columns = [
        ("stage", "VARCHAR(20)"),
        ("event_num", "INTEGER"),
        ("season", "INTEGER"),
        ("buyin", "VARCHAR(20)"),
        ("gtd", "VARCHAR(20)"),
        ("version", "VARCHAR(20)"),
    ]

    # Check existing columns
    cursor.execute("PRAGMA table_info(nas_files)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    added = 0
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE nas_files ADD COLUMN {col_name} {col_type}")
                print(f"  [+] Added column: {col_name}")
                added += 1
            except sqlite3.OperationalError as e:
                print(f"  [!] Error adding {col_name}: {e}")
        else:
            print(f"  [=] Column exists: {col_name}")

    conn.commit()
    conn.close()

    print(f"\n  Result: {added} columns added")
    return added


def update_regions():
    """Add new regions if they don't exist."""
    print("\n[2/4] Update Regions")
    print("=" * 50)

    new_regions = [
        {"code": "LA", "name": "Los Angeles", "description": "WSOP Circuit LA events"},
        {"code": "CYPRUS", "name": "Cyprus", "description": "WSOP Super Circuit / MPP Cyprus events"},
        {"code": "LONDON", "name": "London", "description": "WSOP Super Circuit London events"},
    ]

    added = 0
    with get_db_context() as db:
        for r in new_regions:
            existing = db.query(Region).filter(Region.code == r["code"]).first()
            if not existing:
                db.add(Region(**r))
                print(f"  [+] Added region: {r['code']}")
                added += 1
            else:
                print(f"  [=] Region exists: {r['code']}")
        db.commit()

    print(f"\n  Result: {added} regions added")
    return added


def replace_patterns():
    """Delete old patterns and insert new ones."""
    print("\n[3/4] Replace Patterns")
    print("=" * 50)

    new_patterns = [
        {
            "name": "WSOP_BR_LV_2025_ME",
            "priority": 1,
            "regex": r"WSOP.*Bracelet.*LAS.?VEGAS.*2025.*MAIN.?EVENT",
            "extract_year": True,
            "extract_region": "LV",
            "extract_type": "ME",
            "extract_episode": False,
            "description": "2025 Las Vegas Main Event",
        },
        {
            "name": "WSOP_BR_LV_2025_SIDE",
            "priority": 2,
            "regex": r"WSOP.*Bracelet.*LAS.?VEGAS.*2025.*BRACELET.?SIDE",
            "extract_year": True,
            "extract_region": "LV",
            "extract_type": "BR",
            "extract_episode": False,
            "description": "2025 Las Vegas Side Events",
        },
        {
            "name": "WSOP_BR_EU_2025",
            "priority": 3,
            "regex": r"WSOP.*Bracelet.*EUROPE.*2025",
            "extract_year": True,
            "extract_region": "EU",
            "extract_type": None,
            "extract_episode": False,
            "description": "2025 WSOP Europe",
        },
        {
            "name": "WSOP_BR_EU",
            "priority": 4,
            "regex": r"WSOP.*Bracelet.*EUROPE",
            "extract_year": True,
            "extract_region": "EU",
            "extract_type": None,
            "extract_episode": True,
            "description": "WSOP Europe (2008-2024)",
        },
        {
            "name": "WSOP_BR_PARADISE",
            "priority": 5,
            "regex": r"WSOP.*Bracelet.*PARADISE",
            "extract_year": True,
            "extract_region": "PARADISE",
            "extract_type": None,
            "extract_episode": False,
            "description": "WSOP Paradise",
        },
        {
            "name": "WSOP_BR_LV",
            "priority": 6,
            "regex": r"WSOP.*Bracelet.*LAS.?VEGAS",
            "extract_year": True,
            "extract_region": "LV",
            "extract_type": None,
            "extract_episode": False,
            "description": "WSOP Las Vegas (2021-2024)",
        },
        {
            "name": "WSOP_CIRCUIT_LA",
            "priority": 7,
            "regex": r"WSOP.*Circuit.*LA",
            "extract_year": True,
            "extract_region": "LA",
            "extract_type": None,
            "extract_episode": True,
            "description": "WSOP Circuit LA",
        },
        {
            "name": "WSOP_CIRCUIT_SUPER",
            "priority": 8,
            "regex": r"WSOP.*Super.?Circuit",
            "extract_year": True,
            "extract_region": None,
            "extract_type": None,
            "extract_episode": False,
            "description": "WSOP Super Circuit (London, Cyprus)",
        },
        {
            "name": "WSOP_ARCHIVE_PRE2016",
            "priority": 9,
            "regex": r"WSOP.*ARCHIVE.*PRE-?2016",
            "extract_year": True,
            "extract_region": "LV",
            "extract_type": None,
            "extract_episode": True,
            "description": "WSOP Archive Pre-2016 (1973-2016)",
        },
        {
            "name": "PAD",
            "priority": 10,
            "regex": r"PAD.*(pad-s\d{2}-ep\d{2}|PAD_S\d{2}_EP\d{2})",
            "extract_year": False,
            "extract_region": None,
            "extract_type": None,
            "extract_episode": True,
            "description": "Poker After Dark",
        },
        {
            "name": "GOG",
            "priority": 11,
            "regex": r"GOG.*E\d{2}[_\-]GOG",
            "extract_year": False,
            "extract_region": None,
            "extract_type": None,
            "extract_episode": True,
            "description": "Game of Gold",
        },
        {
            "name": "MPP_ME",
            "priority": 12,
            "regex": r"MPP.*Main.?Event",
            "extract_year": True,
            "extract_region": "CYPRUS",
            "extract_type": "ME",
            "extract_episode": False,
            "description": "MPP Main Event",
        },
        {
            "name": "MPP",
            "priority": 13,
            "regex": r"MPP.*\$\d+[MK]?\s*GTD",
            "extract_year": True,
            "extract_region": "CYPRUS",
            "extract_type": None,
            "extract_episode": False,
            "description": "Merit Poker Premier",
        },
        {
            "name": "GGMILLIONS",
            "priority": 14,
            "regex": r"GGMillions.*Super.*High.*Roller",
            "extract_year": False,
            "extract_region": None,
            "extract_type": "HR",
            "extract_episode": False,
            "description": "GGMillions Super High Roller",
        },
    ]

    with get_db_context() as db:
        # Delete all existing patterns
        deleted = db.query(Pattern).delete()
        print(f"  [-] Deleted {deleted} old patterns")
        db.commit()

        # Insert new patterns
        for p in new_patterns:
            db.add(Pattern(**p))
        db.commit()
        print(f"  [+] Inserted {len(new_patterns)} new patterns")

    print(f"\n  Result: {len(new_patterns)} patterns active")
    return len(new_patterns)


def run_reprocess():
    """Reprocess all files with new patterns."""
    print("\n[4/4] Reprocess All Files")
    print("=" * 50)

    with get_db_context() as db:
        # Check file count
        from src.nams.api.database.models import NasFile
        total_files = db.query(NasFile).count()

        if total_files == 0:
            print("  [!] No files in database to reprocess")
            print("  [!] Run NAS scan first to import files")
            return {"processed": 0, "matched": 0, "updated": 0}

        print(f"  Processing {total_files} files...")

        # Import and run reprocess
        from src.nams.api.services.pattern_engine import reprocess_all_files
        stats = reprocess_all_files(db)

        print(f"\n  Results:")
        print(f"    - Processed: {stats['processed']}")
        print(f"    - Matched:   {stats['matched']}")
        print(f"    - Updated:   {stats['updated']}")

        return stats


def main():
    print("=" * 60)
    print("NAMS Database Migration & Reprocess")
    print("=" * 60)
    print(f"\nDatabase: {DB_PATH}")

    # Check if DB exists
    if not DB_PATH.exists():
        print("\n[!] Database does not exist. Creating...")
        from src.nams.api.database.init_db import init_database
        init_database()

    # Step 1: Migrate database (add columns)
    migrate_database()

    # Step 2: Update regions
    update_regions()

    # Step 3: Replace patterns
    replace_patterns()

    # Step 4: Reprocess files
    stats = run_reprocess()

    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)

    return stats


if __name__ == "__main__":
    main()
