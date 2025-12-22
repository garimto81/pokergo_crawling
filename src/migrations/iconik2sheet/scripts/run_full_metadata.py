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
    args = parser.parse_args()

    print("=" * 60)
    print("Iconik to Sheet - Full Metadata Sync")
    print("=" * 60)
    print()
    print("This script extracts ALL metadata from Iconik API")
    print("including segments (timecodes) and metadata fields.")
    print()
    print("Output: Iconik_Full_Metadata sheet (35 columns)")
    print("        Matching GGmetadata_and_timestamps structure")
    if args.limit:
        print(f"        Limit: {args.limit} assets")
    print()

    sync = FullMetadataSync()
    result = sync.run(skip_sampling=args.skip_sampling, limit=args.limit)

    print()
    print("Summary:")
    print(f"  Sync ID: {result['sync_id']}")
    print(f"  Status: {result['status']}")
    print(f"  Assets: {result['assets_processed']}")


if __name__ == "__main__":
    main()
