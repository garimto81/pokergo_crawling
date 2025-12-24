"""Migration execution script.

Usage:
    python -m scripts.migrate                     # Dry run (default)
    python -m scripts.migrate --execute           # Execute migration
    python -m scripts.migrate --execute --mode overwrite  # Overwrite mode
"""

import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    print("Sheet-to-Sheet Migration")
    print("=" * 60)
    print(f"Mode: {args.mode}")
    print(f"Execute: {args.execute}")

    migrator = SheetMigrator()

    if not args.execute:
        print("\n[DRY RUN MODE]")
        result = migrator.run(dry_run=True, mode=args.mode)
        print("\n" + result.to_report())

        if result.success:
            print("\nTo execute the migration, run:")
            print(f"  python -m scripts.migrate --execute --mode {args.mode}")
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
