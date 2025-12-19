"""Fix Archive file roles: change Primary to Backup.

This script:
1. Finds all Archive files with Primary role
2. Changes them to Backup role
3. Ensures Origin files remain as Primary

Usage:
    python scripts/fix_archive_roles.py [--dry-run]
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.database import get_db_context, NasFile


def get_folder_type(file: NasFile) -> str:
    """Determine folder type from directory or full_path."""
    directory = (file.directory or "").lower()
    full_path = (file.full_path or "").lower()

    if "archive" in directory or "z:/archive" in full_path:
        return "archive"
    elif "origin" in directory or "y:/wsop" in full_path:
        return "origin"
    else:
        return "unknown"


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("Archive 파일 역할 수정 (Primary -> Backup)")
    print("=" * 60)

    if dry_run:
        print("\n[DRY-RUN 모드] 실제 변경 없음\n")

    with get_db_context() as db:
        # Find all Archive files with Primary role
        all_files = db.query(NasFile).filter(NasFile.role == "primary").all()

        archive_primaries = []
        for f in all_files:
            if get_folder_type(f) == "archive":
                archive_primaries.append(f)

        print(f"Archive Primary 파일: {len(archive_primaries)}개\n")

        if not archive_primaries:
            print("수정할 파일 없음")
            return

        # Show sample files
        print("[변경 대상 샘플 (10개)]")
        print("-" * 60)
        for f in archive_primaries[:10]:
            print(f"  {f.filename[:50]} -> Backup")

        if len(archive_primaries) > 10:
            print(f"  ... and {len(archive_primaries) - 10} more")

        if not dry_run:
            print(f"\n변경 중...")

            for f in archive_primaries:
                f.role = "backup"
                f.role_priority = None

            db.commit()

            print(f"\n[완료] {len(archive_primaries)}개 파일 역할 변경됨")
        else:
            print(f"\n[DRY-RUN] {len(archive_primaries)}개 파일이 변경될 예정")
            print("실제 변경하려면: python scripts/fix_archive_roles.py")


if __name__ == "__main__":
    main()
