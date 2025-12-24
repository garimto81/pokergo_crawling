"""Sheet-to-Sheet Migration Runner.

Wrapper script to run the sheet2sheet_migrate project from the project root.

Usage:
    python scripts/run_sheet_migration.py                      # Dry run
    python scripts/run_sheet_migration.py --execute            # Execute
    python scripts/run_sheet_migration.py --execute --mode overwrite  # Overwrite
    python scripts/run_sheet_migration.py --show-mapping       # Show column mapping
"""

import argparse
import sys
from pathlib import Path

# Add sheet2sheet_migrate to path
PROJECT_ROOT = Path(__file__).parent.parent
MIGRATE_ROOT = PROJECT_ROOT / "src" / "migrations" / "sheet2sheet_migrate"
sys.path.insert(0, str(MIGRATE_ROOT))

from migration.migrator import SheetMigrator


def main() -> None:
    """Run migration."""
    parser = argparse.ArgumentParser(
        description="Execute sheet-to-sheet migration"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute the migration (default is dry run)",
    )
    parser.add_argument(
        "--mode",
        choices=["append", "overwrite"],
        default="append",
        help="Migration mode (default: append)",
    )
    parser.add_argument(
        "--show-mapping",
        action="store_true",
        help="Show column mapping preview",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Sheet-to-Sheet Migration")
    print("Source: Archive Metadata -> Target: Iconik_Full_Metadata")
    print("=" * 60)

    migrator = SheetMigrator()

    # Show mapping preview
    if args.show_mapping:
        print("\nColumn Mapping Preview:")
        print("-" * 40)
        mapping = migrator.get_mapping_preview()

        if "error" in mapping:
            print(f"Error: {mapping['error']}")
            return

        print("\nDirect Mappings:")
        for src, tgt in mapping.get("direct_mappings", {}).items():
            print(f"  {src} -> {tgt}")

        print("\nPattern Mappings:")
        for pattern, tgt in mapping.get("pattern_mappings", {}).items():
            print(f"  {pattern} -> {tgt}")

        print("\nTab-Derived Fields:")
        for field in mapping.get("tab_derived", []):
            print(f"  {field}")

        print(f"\nMapping Coverage: {mapping.get('coverage', 0):.1f}%")
        print("-" * 40)

    # Run migration
    print(f"\nMode: {args.mode}")
    print(f"Execute: {args.execute}")

    if not args.execute:
        print("\n[DRY RUN MODE]")
        result = migrator.run(dry_run=True, mode=args.mode)
        print("\n" + result.to_report())

        if result.success:
            print("\nTo execute the migration, run:")
            print(f"  python scripts/run_sheet_migration.py --execute --mode {args.mode}")
        return

    # Confirm before executing
    if not args.force:
        if args.mode == "overwrite":
            print("\n[WARNING] Overwrite mode will clear existing data!")

        confirm = input("\nProceed with migration? (yes/no): ")
        if confirm.lower() not in ["yes", "y"]:
            print("Aborted.")
            return

    print("\n[EXECUTING MIGRATION]")
    result = migrator.run(dry_run=False, mode=args.mode)
    print("\n" + result.to_report())

    if result.success:
        print("\nMigration completed successfully!")
    else:
        print("\nMigration failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
