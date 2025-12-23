"""Run full metadata sync - 전체 메타데이터 추출 (35개 컬럼)."""

import argparse
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sync.full_metadata_sync import FullMetadataSync


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Iconik to Sheet - Full Metadata Sync"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of assets to process (default: all)",
    )
    parser.add_argument(
        "--skip-sampling",
        action="store_true",
        help="Skip pre-sync sampling check",
    )
    parser.add_argument(
        "--mode",
        choices=["split", "combined"],
        default="split",
        help="Output mode: 'split' (2 sheets) or 'combined' (1 sheet, legacy). Default: split",
    )
    parser.add_argument(
        "--include-full",
        action="store_true",
        help="Also write to Iconik_Full_Metadata (for backwards compatibility with split mode)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Iconik to Sheet - Full Metadata Sync")
    print("=" * 60)
    print()
    print("This script extracts ALL metadata from Iconik API")
    print("including segments (timecodes) and metadata fields.")
    print()
    if args.mode == "split":
        print("Output: Iconik_General_Metadata + Iconik_Subclips_Metadata")
        print("        (General: 35 columns, Subclips: 37 columns)")
    else:
        print("Output: Iconik_Full_Metadata sheet (35 columns)")
        print("        Combined mode (legacy)")
    if args.include_full:
        print("        + Iconik_Full_Metadata (legacy backup)")
    if args.limit:
        print(f"        Limit: {args.limit} assets")
    print()

    sync = FullMetadataSync()
    result = sync.run(
        skip_sampling=args.skip_sampling,
        limit=args.limit,
        mode=args.mode,
        include_full=args.include_full,
    )

    print()
    print("Summary:")
    print(f"  Sync ID: {result['sync_id']}")
    print(f"  Status: {result['status']}")
    print(f"  Total Assets: {result['assets_processed']}")
    print(f"  General (ASSET): {result.get('general_assets', 0)}")
    print(f"  Subclips: {result.get('subclip_assets', 0)}")


if __name__ == "__main__":
    main()
