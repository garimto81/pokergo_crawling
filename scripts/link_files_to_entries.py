#!/usr/bin/env python
"""NasFile을 CategoryEntry에 연결하는 스크립트.

NasFile의 메타데이터(year, region, event_type, episode)를 기반으로
적절한 CategoryEntry를 찾아 연결합니다.
"""
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import func
from src.nams.api.database.session import get_db_context
from src.nams.api.database.models import (
    NasFile, CategoryEntry, Category, Region, EventType
)


def get_region_code(region_id: int, session) -> str:
    """Region ID를 코드로 변환."""
    if not region_id:
        return 'LV'
    region = session.query(Region).filter(Region.id == region_id).first()
    return region.code if region else 'LV'


def get_event_type_code(event_type_id: int, session) -> str:
    """EventType ID를 코드로 변환."""
    if not event_type_id:
        return None
    etype = session.query(EventType).filter(EventType.id == event_type_id).first()
    return etype.code if etype else None


def find_matching_entry(nas_file: NasFile, session) -> CategoryEntry:
    """NasFile에 매칭되는 CategoryEntry 찾기."""

    if not nas_file.year:
        return None

    region_code = get_region_code(nas_file.region_id, session)
    event_type_code = get_event_type_code(nas_file.event_type_id, session)

    # 1. 정확한 entry_code 매칭 시도
    if region_code and region_code != 'LV':
        cat_code = f"WSOP_{nas_file.year}_{region_code}"
    else:
        cat_code = f"WSOP_{nas_file.year}"

    # Entry 코드 생성
    if event_type_code:
        if nas_file.episode:
            entry_code = f"{cat_code}_{event_type_code}_{nas_file.episode:02d}"
        elif nas_file.event_num:
            entry_code = f"{cat_code}_{event_type_code}_E{nas_file.event_num:02d}"
        else:
            entry_code = f"{cat_code}_{event_type_code}"
    else:
        entry_code = f"{cat_code}_{nas_file.episode or 1:02d}" if nas_file.episode else cat_code

    # Entry 찾기
    entry = session.query(CategoryEntry).filter(CategoryEntry.entry_code == entry_code).first()
    if entry:
        return entry

    # 2. 유사 entry 찾기 (year + event_type 기반)
    query = session.query(CategoryEntry).filter(CategoryEntry.year == nas_file.year)

    if event_type_code:
        query = query.filter(CategoryEntry.event_type == event_type_code)

    if nas_file.episode:
        query = query.filter(CategoryEntry.sequence == nas_file.episode)

    entry = query.first()
    return entry


def assign_roles(session):
    """동일 Entry에 연결된 파일들의 역할(PRIMARY/BACKUP) 할당."""

    # Entry별로 파일 그룹화
    entries = session.query(CategoryEntry).filter(
        CategoryEntry.id.in_(
            session.query(NasFile.entry_id).filter(NasFile.entry_id.isnot(None)).distinct()
        )
    ).all()

    drive_priority = {'Z:': 1, 'Y:': 2, 'X:': 3}
    ext_priority = {'mp4': 1, 'mov': 2, 'mxf': 3}

    for entry in entries:
        files = session.query(NasFile).filter(
            NasFile.entry_id == entry.id,
            NasFile.is_excluded == False
        ).all()

        if not files:
            continue

        # 정렬 키: 드라이브 우선순위, 확장자 우선순위, 파일 크기 (큰 것 우선)
        def sort_key(f):
            return (
                drive_priority.get(f.drive, 9),
                ext_priority.get(f.extension, 9),
                -(f.size_bytes or 0)
            )

        sorted_files = sorted(files, key=sort_key)

        # 역할 할당
        for i, f in enumerate(sorted_files):
            if i == 0:
                f.role = 'PRIMARY'
            else:
                f.role = 'BACKUP'
            f.role_priority = i + 1

        # Entry 통계 업데이트
        entry.file_count = len(files)
        entry.total_size_bytes = sum(f.size_bytes or 0 for f in files)

    session.commit()


def link_files_to_entries():
    """NasFile을 CategoryEntry에 연결."""

    print("=" * 60)
    print("NasFile → CategoryEntry 연결")
    print("=" * 60)

    with get_db_context() as session:
        # Active 파일만 처리 (is_excluded=False)
        files = session.query(NasFile).filter(NasFile.is_excluded == False).all()

        print(f"\n[INFO] 처리 대상 파일: {len(files)}개")

        linked = 0
        not_linked = 0

        for f in files:
            entry = find_matching_entry(f, session)

            if entry:
                f.entry_id = entry.id
                linked += 1
            else:
                not_linked += 1

        session.commit()

        print(f"[OK] 연결 성공: {linked}개")
        print(f"[WARN] 연결 실패: {not_linked}개")

        # 역할 할당
        print("\n[INFO] 역할(PRIMARY/BACKUP) 할당 중...")
        assign_roles(session)
        print("[OK] 역할 할당 완료")

        # 결과 검증
        print("\n" + "=" * 60)
        print("결과 검증")
        print("=" * 60)

        total = session.query(NasFile).count()
        with_entry = session.query(NasFile).filter(NasFile.entry_id.isnot(None)).count()
        primary = session.query(NasFile).filter(NasFile.role == 'PRIMARY').count()
        backup = session.query(NasFile).filter(NasFile.role == 'BACKUP').count()

        print(f"\n[NasFile 상태]")
        print(f"  - 전체: {total}개")
        print(f"  - entry_id 연결: {with_entry}개 ({with_entry/total*100:.1f}%)")
        print(f"  - PRIMARY: {primary}개")
        print(f"  - BACKUP: {backup}개")

        # 연결 실패 샘플
        not_linked_files = session.query(NasFile).filter(
            NasFile.entry_id.is_(None),
            NasFile.is_excluded == False
        ).limit(10).all()

        if not_linked_files:
            print(f"\n[연결 실패 샘플 (최대 10개)]")
            for f in not_linked_files:
                region = get_region_code(f.region_id, session)
                etype = get_event_type_code(f.event_type_id, session)
                print(f"  - {f.filename}")
                print(f"    year={f.year}, region={region}, event_type={etype}, episode={f.episode}")


def create_missing_entries():
    """연결되지 않은 파일들에 대해 새 CategoryEntry 생성."""

    print("\n" + "=" * 60)
    print("누락 Entry 생성")
    print("=" * 60)

    with get_db_context() as session:
        # 연결되지 않은 Active 파일
        orphan_files = session.query(NasFile).filter(
            NasFile.entry_id.is_(None),
            NasFile.is_excluded == False,
            NasFile.year.isnot(None)
        ).all()

        if not orphan_files:
            print("[OK] 모든 파일이 연결됨")
            return

        print(f"[INFO] 연결 필요한 파일: {len(orphan_files)}개")

        # 파일별로 Entry 생성
        created_entries = {}

        for f in orphan_files:
            region_code = get_region_code(f.region_id, session)
            event_type_code = get_event_type_code(f.event_type_id, session)

            # Category 코드
            if region_code and region_code != 'LV':
                cat_code = f"WSOP_{f.year}_{region_code}"
                cat_name = f"WSOP {region_code} {f.year}"
            else:
                cat_code = f"WSOP_{f.year}"
                cat_name = f"WSOP {f.year}"

            # Entry 코드
            if event_type_code:
                if f.episode:
                    entry_code = f"{cat_code}_{event_type_code}_{f.episode:02d}"
                elif f.event_num:
                    entry_code = f"{cat_code}_{event_type_code}_E{f.event_num:02d}"
                else:
                    entry_code = f"{cat_code}_{event_type_code}"
            else:
                entry_code = f"{cat_code}_{f.episode or 1:02d}" if f.episode else f"{cat_code}_01"

            # 이미 생성된 Entry면 재사용
            if entry_code in created_entries:
                f.entry_id = created_entries[entry_code].id
                continue

            # Category 찾기/생성
            category = session.query(Category).filter(Category.code == cat_code).first()
            if not category:
                category = Category(
                    code=cat_code,
                    name=cat_name,
                    year=f.year,
                    region=region_code,
                    source='NAS_ONLY'
                )
                session.add(category)
                session.flush()

            # Entry 생성
            event_names = {
                'ME': 'Main Event', 'BR': 'Bracelet', 'HU': 'Heads Up',
                'GM': 'Grudge Match', 'HR': 'High Roller'
            }
            event_name = event_names.get(event_type_code, '')
            seq_str = f" Day {f.episode}" if f.episode else ""
            display_title = f"{cat_name} {event_name}{seq_str}".strip()

            entry = CategoryEntry(
                category_id=category.id,
                entry_code=entry_code,
                display_title=display_title,
                year=f.year,
                event_type=event_type_code,
                sequence=f.episode or f.part,
                sequence_type='DAY' if f.episode else ('PART' if f.part else None),
                source='NAS_ONLY',
                match_type='NONE'
            )
            session.add(entry)
            session.flush()

            created_entries[entry_code] = entry
            f.entry_id = entry.id

        session.commit()
        print(f"[OK] 새 Entry 생성: {len(created_entries)}개")

        # 역할 재할당
        assign_roles(session)
        print("[OK] 역할 재할당 완료")


def main():
    """메인 실행."""
    print("\n" + "=" * 60)
    print("NAMS: NasFile → CategoryEntry 연결")
    print("=" * 60)

    # 1. 기존 Entry에 파일 연결
    link_files_to_entries()

    # 2. 누락된 파일에 대해 새 Entry 생성
    create_missing_entries()

    # 3. 최종 검증
    print("\n" + "=" * 60)
    print("최종 결과")
    print("=" * 60)

    with get_db_context() as session:
        total = session.query(NasFile).count()
        active = session.query(NasFile).filter(NasFile.is_excluded == False).count()
        with_entry = session.query(NasFile).filter(NasFile.entry_id.isnot(None)).count()
        entries = session.query(CategoryEntry).count()
        categories = session.query(Category).count()

        print(f"\n[최종 통계]")
        print(f"  - NasFile 전체: {total}개")
        print(f"  - NasFile Active: {active}개")
        print(f"  - entry_id 연결: {with_entry}개 ({with_entry/active*100:.1f}% of active)")
        print(f"  - Category: {categories}개")
        print(f"  - CategoryEntry: {entries}개")

    print("\n[SUCCESS] 연결 완료!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
