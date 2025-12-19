"""Add match_category field and populate values for all groups.

This script:
1. Adds match_category column to asset_groups table if not exists
2. Calculates and sets match_category for all groups

Usage:
    python scripts/add_match_category.py
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect, text

from src.nams.api.database import get_db_context
from src.nams.api.services.matching import (
    MATCH_CATEGORY_MATCHED,
    MATCH_CATEGORY_NAS_ONLY_HISTORIC,
    MATCH_CATEGORY_NAS_ONLY_MODERN,
    MATCH_CATEGORY_POKERGO_ONLY,
    get_matching_summary,
    update_match_categories,
)


def add_column_if_not_exist():
    """Add match_category column if it doesn't exist."""
    with get_db_context() as db:
        inspector = inspect(db.bind)
        columns = [col['name'] for col in inspector.get_columns('asset_groups')]

        if 'match_category' not in columns:
            print("Adding match_category column...")
            db.execute(text("ALTER TABLE asset_groups ADD COLUMN match_category VARCHAR(50)"))
            db.commit()
            print("  Done.")
        else:
            print("match_category column already exists.")


def print_statistics():
    """Print current statistics."""
    with get_db_context() as db:
        summary = get_matching_summary(db)

        print(f"\n{'='*60}")
        print("4분류 매칭 현황")
        print(f"{'='*60}")
        print(f"\nNAS Groups ({summary['total_nas_groups']}개):")
        print(f"  - MATCHED:           {summary[MATCH_CATEGORY_MATCHED]:>5} (PokerGO 매칭됨)")
        historic = summary[MATCH_CATEGORY_NAS_ONLY_HISTORIC]
        print(f"  - NAS_ONLY_HISTORIC: {historic:>5} (2011년 이전)")
        print(f"  - NAS_ONLY_MODERN:   {summary[MATCH_CATEGORY_NAS_ONLY_MODERN]:>5} (2011년 이후)")
        print(f"\nPokerGO Episodes ({summary['total_pokergo_episodes']}개):")
        print(f"  - POKERGO_ONLY:      {summary[MATCH_CATEGORY_POKERGO_ONLY]:>5} (NAS 없음)")
        print(f"{'='*60}\n")


def main():
    print("=" * 60)
    print("NAMS 4분류 매칭 카테고리 설정")
    print("=" * 60)

    # Step 1: Add column if needed
    add_column_if_not_exist()

    # Step 2: Update match categories
    print("\n매칭 카테고리 계산 중...")
    with get_db_context() as db:
        stats = update_match_categories(db)

    print("\n처리 결과:")
    print(f"  - 총 그룹:              {stats['total']}")
    print(f"  - MATCHED:              {stats[MATCH_CATEGORY_MATCHED]}")
    print(f"  - NAS_ONLY_HISTORIC:    {stats[MATCH_CATEGORY_NAS_ONLY_HISTORIC]}")
    print(f"  - NAS_ONLY_MODERN:      {stats[MATCH_CATEGORY_NAS_ONLY_MODERN]}")

    # Step 3: Print final statistics
    print_statistics()


if __name__ == "__main__":
    main()
