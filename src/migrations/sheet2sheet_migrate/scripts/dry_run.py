"""Dry run script for sheet migration.

Usage:
    python -m scripts.dry_run
    python -m scripts.dry_run --show-mapping
"""

import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from migration.migrator import SheetMigrator


def main() -> None:
    """Run migration dry run."""
    parser = argparse.ArgumentParser(description="Dry run sheet migration")
    parser.add_argument(
        "--show-mapping",
        action="store_true",
        help="Show column mapping preview",
    )
    parser.add_argument(
        "--mode",
        choices=["append", "overwrite"],
        default="append",
        help="Migration mode (default: append)",
    )

    args = parser.parse_args()

    print("Sheet-to-Sheet Migration - Dry Run")
    print("=" * 60)

    migrator = SheetMigrator()

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

        print(f"\nCoverage: {mapping.get('coverage', 0):.1f}%")
        print("-" * 40)

    print("\nRunning dry run...")
    result = migrator.run(dry_run=True, mode=args.mode)
    print("\n" + result.to_report())

    if result.success:
        print("\nTo execute the migration, run:")
        print(f"  python -m scripts.migrate --execute --mode {args.mode}")


if __name__ == "__main__":
    main()
