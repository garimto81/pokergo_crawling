"""Verify Origin/Archive synchronization status.

This script:
1. Identifies files in Origin vs Archive folders
2. Detects duplicates and role conflicts
3. Suggests role corrections (Origin=primary, Archive=backup)
4. Reports sync status summary

Usage:
    python scripts/verify_origin_archive_sync.py
"""
import sys
from pathlib import Path
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func
from src.nams.api.database import get_db_context, NasFile, AssetGroup


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


def format_size(bytes_size: int) -> str:
    """Format bytes to human readable."""
    if not bytes_size:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} PB"


def main():
    print("=" * 70)
    print("NAMS Origin/Archive 동기화 검증")
    print("=" * 70)

    with get_db_context() as db:
        # Get all files
        files = db.query(NasFile).all()

        # Categorize by folder type
        origin_files = []
        archive_files = []
        unknown_files = []

        for f in files:
            folder_type = get_folder_type(f)
            if folder_type == "origin":
                origin_files.append(f)
            elif folder_type == "archive":
                archive_files.append(f)
            else:
                unknown_files.append(f)

        # 1. Basic Stats
        print(f"\n[1] 폴더별 파일 분포")
        print("-" * 50)
        origin_size = sum(f.size_bytes or 0 for f in origin_files)
        archive_size = sum(f.size_bytes or 0 for f in archive_files)
        print(f"  Origin:  {len(origin_files):>5}개 ({format_size(origin_size)})")
        print(f"  Archive: {len(archive_files):>5}개 ({format_size(archive_size)})")
        if unknown_files:
            print(f"  Unknown: {len(unknown_files):>5}개")

        # 2. Role Distribution by Folder
        print(f"\n[2] 폴더별 역할(Role) 분포")
        print("-" * 50)

        origin_primary = sum(1 for f in origin_files if f.role == "primary")
        origin_backup = sum(1 for f in origin_files if f.role == "backup")
        archive_primary = sum(1 for f in archive_files if f.role == "primary")
        archive_backup = sum(1 for f in archive_files if f.role == "backup")

        print(f"  Origin:  Primary={origin_primary}, Backup={origin_backup}")
        print(f"  Archive: Primary={archive_primary}, Backup={archive_backup}")

        if archive_primary > 0:
            print(f"\n  [!] 경고: Archive에 Primary 역할 파일 {archive_primary}개")
            print(f"    -> Archive 파일은 Backup으로 변경 권장")

        # 3. Duplicate Detection (same filename in multiple locations)
        print(f"\n[3] 파일명 중복 분석")
        print("-" * 50)

        filename_to_files = defaultdict(list)
        for f in files:
            filename_to_files[f.filename].append(f)

        duplicates = {k: v for k, v in filename_to_files.items() if len(v) > 1}

        if duplicates:
            print(f"  중복 파일명: {len(duplicates)}개")
            print(f"\n  [상위 10개 중복 파일]")
            sorted_dups = sorted(duplicates.items(), key=lambda x: -len(x[1]))[:10]
            for filename, dup_files in sorted_dups:
                locations = []
                for f in dup_files:
                    folder = get_folder_type(f)
                    locations.append(f"{folder}({f.role[0]})")
                print(f"    {filename[:50]:50} x{len(dup_files)} - {', '.join(locations)}")
        else:
            print(f"  중복 파일 없음")

        # 4. Group Sync Status (groups with files from both origin and archive)
        print(f"\n[4] 그룹 동기화 상태")
        print("-" * 50)

        group_to_folders = defaultdict(lambda: {"origin": [], "archive": []})
        for f in files:
            if f.asset_group_id:
                folder = get_folder_type(f)
                group_to_folders[f.asset_group_id][folder].append(f)

        shared_groups = {
            gid: folders
            for gid, folders in group_to_folders.items()
            if folders["origin"] and folders["archive"]
        }

        origin_only_groups = sum(
            1 for folders in group_to_folders.values()
            if folders["origin"] and not folders["archive"]
        )
        archive_only_groups = sum(
            1 for folders in group_to_folders.values()
            if folders["archive"] and not folders["origin"]
        )

        print(f"  Origin만: {origin_only_groups}개 그룹")
        print(f"  Archive만: {archive_only_groups}개 그룹")
        print(f"  Origin+Archive 공유: {len(shared_groups)}개 그룹")

        if shared_groups:
            print(f"\n  [Origin+Archive 공유 그룹 목록]")
            for gid, folders in list(shared_groups.items())[:10]:
                group = db.query(AssetGroup).filter(AssetGroup.id == gid).first()
                group_name = group.group_id if group else f"ID={gid}"
                origin_cnt = len(folders["origin"])
                archive_cnt = len(folders["archive"])
                print(f"    {group_name[:40]:40} O:{origin_cnt} A:{archive_cnt}")

        # 5. Role Conflict Analysis
        print(f"\n[5] 역할(Role) 충돌 분석")
        print("-" * 50)

        conflicts = []
        for gid, folders in group_to_folders.items():
            all_files = folders["origin"] + folders["archive"]
            primary_files = [f for f in all_files if f.role == "primary"]
            if len(primary_files) > 1:
                group = db.query(AssetGroup).filter(AssetGroup.id == gid).first()
                conflicts.append({
                    "group": group.group_id if group else f"ID={gid}",
                    "primary_count": len(primary_files),
                    "files": primary_files
                })

        if conflicts:
            print(f"  [!] Primary 중복 그룹: {len(conflicts)}개")
            for c in conflicts[:5]:
                print(f"    {c['group']}: Primary {c['primary_count']}개")
                for f in c['files'][:3]:
                    folder = get_folder_type(f)
                    print(f"      - [{folder}] {f.filename[:40]}")
        else:
            print(f"  [OK] Primary 충돌 없음")

        # 6. Recommendations
        print(f"\n[6] 권장 조치")
        print("=" * 70)

        recommendations = []

        if archive_primary > 0:
            recommendations.append(
                f"1. Archive Primary → Backup 변경: {archive_primary}개 파일"
            )

        if len(duplicates) > 0:
            recommendations.append(
                f"2. 중복 파일 검토: {len(duplicates)}개 파일명"
            )

        if len(conflicts) > 0:
            recommendations.append(
                f"3. Primary 충돌 해결: {len(conflicts)}개 그룹"
            )

        if len(shared_groups) > 0:
            recommendations.append(
                f"4. 공유 그룹 동기화 검증: {len(shared_groups)}개 그룹"
            )

        if recommendations:
            for rec in recommendations:
                print(f"  {rec}")
        else:
            print(f"  [OK] 모든 동기화 상태 정상")

        # 7. Summary
        print(f"\n[요약]")
        print("=" * 70)
        print(f"  전체 파일: {len(files)}개")
        print(f"  Origin: {len(origin_files)}개 (Primary: {origin_primary})")
        print(f"  Archive: {len(archive_files)}개 (Primary: {archive_primary} <- 수정 필요)")
        print(f"  중복 파일명: {len(duplicates)}개")
        print(f"  Primary 충돌 그룹: {len(conflicts)}개")
        print(f"  공유 그룹 (Origin+Archive): {len(shared_groups)}개")


if __name__ == "__main__":
    main()
