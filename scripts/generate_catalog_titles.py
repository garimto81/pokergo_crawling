"""Generate catalog titles for all asset groups.

This script:
1. Adds catalog_title columns to asset_groups table if not exists
2. Generates catalog titles for all groups (unmatched first, then all)
3. Prints statistics

Usage:
    python scripts/generate_catalog_titles.py
    python scripts/generate_catalog_titles.py --all  # Regenerate all titles
"""
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, inspect
from src.nams.api.database import get_db_context, AssetGroup
from src.nams.api.services.catalog_service import (
    generate_catalog_title,
    generate_titles_for_unmatched,
    generate_titles_for_all,
    parse_group_id,
)


def add_columns_if_not_exist():
    """Add catalog_title columns if they don't exist."""
    with get_db_context() as db:
        # Check if columns exist
        inspector = inspect(db.bind)
        columns = [col['name'] for col in inspector.get_columns('asset_groups')]

        if 'catalog_title' not in columns:
            print("Adding catalog_title column...")
            db.execute(text("ALTER TABLE asset_groups ADD COLUMN catalog_title VARCHAR(500)"))
            db.commit()
            print("  Done.")
        else:
            print("catalog_title column already exists.")

        if 'catalog_title_manual' not in columns:
            print("Adding catalog_title_manual column...")
            db.execute(text("ALTER TABLE asset_groups ADD COLUMN catalog_title_manual BOOLEAN DEFAULT 0"))
            db.commit()
            print("  Done.")
        else:
            print("catalog_title_manual column already exists.")


def print_statistics():
    """Print current statistics."""
    with get_db_context() as db:
        total = db.query(AssetGroup).count()
        with_title = db.query(AssetGroup).filter(
            AssetGroup.catalog_title != None,
            AssetGroup.catalog_title != ""
        ).count()
        manual_titles = db.query(AssetGroup).filter(
            AssetGroup.catalog_title_manual == True
        ).count()
        matched = db.query(AssetGroup).filter(
            AssetGroup.pokergo_episode_id != None
        ).count()
        unmatched = total - matched

        print(f"\n{'='*60}")
        print("현재 상태")
        print(f"{'='*60}")
        print(f"총 그룹:           {total:,}")
        print(f"  - PokerGO 매칭:  {matched:,} ({matched/total*100:.1f}%)")
        print(f"  - 미매칭:        {unmatched:,} ({unmatched/total*100:.1f}%)")
        print(f"\n카탈로그 제목:")
        print(f"  - 생성됨:        {with_title:,} ({with_title/total*100:.1f}%)")
        print(f"  - 수동 편집:     {manual_titles:,}")
        print(f"  - 미생성:        {total - with_title:,}")
        print(f"{'='*60}\n")


def preview_titles(limit: int = 20):
    """Preview generated titles without saving."""
    print(f"\n제목 미리보기 (상위 {limit}개):")
    print("-" * 80)

    with get_db_context() as db:
        groups = db.query(AssetGroup).filter(
            AssetGroup.pokergo_episode_id == None
        ).order_by(AssetGroup.year.desc()).limit(limit).all()

        for g in groups:
            title = generate_catalog_title(g, db)
            parsed = parse_group_id(g.group_id)
            print(f"  {g.group_id:25} → {title}")

    print("-" * 80)


def generate_titles(regenerate_all: bool = False):
    """Generate titles for groups."""
    with get_db_context() as db:
        if regenerate_all:
            print("\n모든 그룹에 대해 제목 재생성 중...")
            result = generate_titles_for_all(db, overwrite=True)
        else:
            print("\n미매칭 그룹에 대해 제목 생성 중...")
            result = generate_titles_for_unmatched(db)

        print(f"\n결과:")
        print(f"  - 처리 대상: {result.get('total', result.get('total_unmatched', 0)):,}")
        print(f"  - 생성됨:    {result['generated']:,}")
        if 'skipped' in result:
            print(f"  - 스킵:      {result['skipped']:,}")
        if result['errors']:
            print(f"  - 오류:      {len(result['errors']):,}")
            for err in result['errors'][:5]:
                print(f"    - {err['group_id']}: {err['error']}")


def show_sample_titles():
    """Show sample of generated titles by category."""
    print("\n생성된 제목 샘플:")
    print("=" * 80)

    with get_db_context() as db:
        # By region
        categories = [
            ("Historic (pre-2011)", "year < 2011"),
            ("Modern (2011+)", "year >= 2011"),
        ]

        for category_name, condition in categories:
            print(f"\n[{category_name}]")
            groups = db.query(AssetGroup).filter(
                text(condition),
                AssetGroup.catalog_title != None
            ).order_by(AssetGroup.year).limit(5).all()

            for g in groups:
                matched = "[Y]" if g.pokergo_episode_id else "[N]"
                print(f"  {matched} {g.group_id:25} | {g.catalog_title}")

    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Generate catalog titles for asset groups")
    parser.add_argument("--all", action="store_true", help="Regenerate all titles (except manual)")
    parser.add_argument("--preview", action="store_true", help="Preview titles without saving")
    parser.add_argument("--sample", action="store_true", help="Show sample of generated titles")
    args = parser.parse_args()

    print("=" * 60)
    print("NAMS 카탈로그 제목 생성기")
    print("=" * 60)

    # Step 1: Add columns if needed
    add_columns_if_not_exist()

    # Step 2: Print current state
    print_statistics()

    if args.preview:
        preview_titles()
        return

    if args.sample:
        show_sample_titles()
        return

    # Step 3: Generate titles
    generate_titles(regenerate_all=args.all)

    # Step 4: Print final state
    print_statistics()

    # Step 5: Show samples
    show_sample_titles()


if __name__ == "__main__":
    main()
