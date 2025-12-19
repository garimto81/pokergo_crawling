#!/usr/bin/env python
"""Phase 1: DB Migration - AssetGroup to Category System.

이 스크립트는 기존 AssetGroup 기반 구조를 새로운 Category/CategoryEntry 구조로 마이그레이션합니다.

주요 작업:
1. 새 테이블 생성 (categories, category_entries)
2. NasFile에 새 컬럼 추가 (file_id, entry_id, path_history, ...)
3. AssetGroup 데이터를 CategoryEntry로 변환
4. NasFile 데이터 업데이트 (file_id 생성, drive/folder 추출)
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

from src.nams.api.database.models import (
    Base, Category, CategoryEntry, NasFile, AssetGroup, Region, EventType
)

# DB 경로 (실제 위치: src/nams/data/nams.db)
DB_PATH = project_root / "src" / "nams" / "data" / "nams.db"
BACKUP_PATH = project_root / "src" / "nams" / "data" / f"nams_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"


def create_backup():
    """기존 DB 백업."""
    import shutil
    if DB_PATH.exists():
        shutil.copy(DB_PATH, BACKUP_PATH)
        print(f"[OK] DB 백업 완료: {BACKUP_PATH}")
    else:
        print(f"[WARN] DB 파일 없음: {DB_PATH}")


def check_existing_tables(engine):
    """기존 테이블 확인."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\n[INFO] 기존 테이블: {tables}")
    return tables


def check_column_exists(engine, table_name: str, column_name: str) -> bool:
    """컬럼 존재 여부 확인."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate_schema(engine):
    """스키마 마이그레이션 - 새 테이블 및 컬럼 추가."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # 1. 새 테이블 생성 (categories, category_entries)
    if 'categories' not in existing_tables:
        print("[INFO] categories 테이블 생성...")
        Base.metadata.tables['categories'].create(engine)
        print("[OK] categories 테이블 생성 완료")
    else:
        print("[SKIP] categories 테이블 이미 존재")

    if 'category_entries' not in existing_tables:
        print("[INFO] category_entries 테이블 생성...")
        Base.metadata.tables['category_entries'].create(engine)
        print("[OK] category_entries 테이블 생성 완료")
    else:
        print("[SKIP] category_entries 테이블 이미 존재")

    # 2. NasFile에 새 컬럼 추가
    new_columns = [
        ('file_id', 'VARCHAR(500)'),
        ('drive', 'VARCHAR(10)'),
        ('folder', 'VARCHAR(20)'),
        ('path_history', 'TEXT'),
        ('last_seen_at', 'DATETIME'),
        ('entry_id', 'INTEGER'),
    ]

    with engine.connect() as conn:
        for col_name, col_type in new_columns:
            if not check_column_exists(engine, 'nas_files', col_name):
                print(f"[INFO] nas_files.{col_name} 컬럼 추가...")
                conn.execute(text(f"ALTER TABLE nas_files ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"[OK] nas_files.{col_name} 컬럼 추가 완료")
            else:
                print(f"[SKIP] nas_files.{col_name} 컬럼 이미 존재")

    print("\n[OK] 스키마 마이그레이션 완료")


def generate_file_id(filename: str) -> str:
    """파일명 기반 고유 식별자 생성."""
    return filename.lower().strip()


def extract_drive_folder(full_path: str) -> tuple:
    """경로에서 드라이브와 폴더 추출."""
    if not full_path:
        return None, None

    # 드라이브 추출 (X:, Y:, Z:)
    drive = full_path[:2] if len(full_path) >= 2 and full_path[1] == ':' else None

    # 폴더 유형 추출
    path_lower = full_path.lower()
    if 'pokergo' in path_lower or drive == 'X:':
        folder = 'pokergo'
    elif 'backup' in path_lower or 'origin' in path_lower or drive == 'Y:':
        folder = 'origin'
    elif 'archive' in path_lower or drive == 'Z:':
        folder = 'archive'
    else:
        folder = 'unknown'

    return drive, folder


def get_region_code(region_id: int, session) -> str:
    """Region ID를 코드로 변환."""
    if not region_id:
        return 'LV'  # 기본값
    region = session.query(Region).filter(Region.id == region_id).first()
    return region.code if region else 'LV'


def get_event_type_code(event_type_id: int, session) -> str:
    """EventType ID를 코드로 변환."""
    if not event_type_id:
        return None
    etype = session.query(EventType).filter(EventType.id == event_type_id).first()
    return etype.code if etype else None


def migrate_data(session):
    """데이터 마이그레이션 - AssetGroup → Category/CategoryEntry."""

    # 1. NasFile 데이터 업데이트 (file_id, drive, folder)
    print("\n[Phase 1] NasFile 데이터 업데이트...")
    files = session.query(NasFile).all()
    updated_files = 0

    for f in files:
        changed = False

        # file_id 생성
        if not f.file_id:
            f.file_id = generate_file_id(f.filename)
            changed = True

        # drive/folder 추출
        if not f.drive or not f.folder:
            drive, folder = extract_drive_folder(f.full_path)
            if drive:
                f.drive = drive
            if folder:
                f.folder = folder
            changed = True

        # last_seen_at 설정
        if not f.last_seen_at:
            f.last_seen_at = datetime.utcnow()
            changed = True

        if changed:
            updated_files += 1

    session.commit()
    print(f"[OK] NasFile 업데이트: {updated_files}개")

    # 2. AssetGroup → Category/CategoryEntry 변환
    print("\n[Phase 2] AssetGroup → Category/CategoryEntry 변환...")

    groups = session.query(AssetGroup).all()
    categories_created = {}  # {code: Category}
    entries_created = 0

    for group in groups:
        # Region 코드 조회
        region_code = get_region_code(group.region_id, session)
        event_type_code = get_event_type_code(group.event_type_id, session)

        # Category 코드 생성 (WSOP_2022, WSOP_2022_EU 등)
        if region_code and region_code != 'LV':
            cat_code = f"WSOP_{group.year}_{region_code}"
            cat_name = f"WSOP {region_code} {group.year}"
        else:
            cat_code = f"WSOP_{group.year}"
            cat_name = f"WSOP {group.year}"

        # Category 생성 (없으면)
        if cat_code not in categories_created:
            existing_cat = session.query(Category).filter(Category.code == cat_code).first()
            if not existing_cat:
                category = Category(
                    code=cat_code,
                    name=cat_name,
                    year=group.year,
                    region=region_code,
                    source='HYBRID' if group.pokergo_episode_id else 'NAS_ONLY',
                )
                session.add(category)
                session.flush()  # ID 생성
                categories_created[cat_code] = category
            else:
                categories_created[cat_code] = existing_cat

        category = categories_created[cat_code]

        # CategoryEntry 생성
        # Entry 코드 생성 (WSOP_2022_ME_01 등)
        if event_type_code:
            if group.episode:
                entry_code = f"{cat_code}_{event_type_code}_{group.episode:02d}"
            elif group.event_num:
                entry_code = f"{cat_code}_{event_type_code}_E{group.event_num:02d}"
            else:
                entry_code = f"{cat_code}_{event_type_code}"
        else:
            entry_code = f"{cat_code}_{group.episode or 1:02d}" if group.episode else cat_code

        # 중복 방지
        existing_entry = session.query(CategoryEntry).filter(CategoryEntry.entry_code == entry_code).first()
        if existing_entry:
            # 이미 존재하면 해당 entry 사용
            entry = existing_entry
        else:
            # 매칭 유형 결정
            if group.pokergo_episode_id:
                if group.pokergo_match_score and group.pokergo_match_score >= 0.9:
                    match_type = 'EXACT'
                else:
                    match_type = 'PARTIAL'
                source = 'POKERGO'
            else:
                match_type = 'NONE'
                source = 'NAS_ONLY'

            # Display title 결정
            display_title = group.pokergo_title or group.catalog_title
            if not display_title:
                # 기본 제목 생성
                event_name = {'ME': 'Main Event', 'BR': 'Bracelet', 'HU': 'Heads Up', 'GM': 'Grudge Match'}.get(event_type_code, '')
                seq_str = f" Day {group.episode}" if group.episode else ""
                display_title = f"{cat_name} {event_name}{seq_str}".strip()

            entry = CategoryEntry(
                category_id=category.id,
                entry_code=entry_code,
                display_title=display_title,
                year=group.year,
                event_type=event_type_code,
                sequence=group.episode or group.part,
                sequence_type='DAY' if group.episode else ('PART' if group.part else None),
                source=source,
                pokergo_ep_id=group.pokergo_episode_id,
                pokergo_title=group.pokergo_title,
                match_type=match_type,
                match_score=group.pokergo_match_score,
            )
            session.add(entry)
            session.flush()  # ID 생성
            entries_created += 1

        # NasFile 연결
        for nas_file in group.files:
            nas_file.entry_id = entry.id

    session.commit()
    print(f"[OK] Category 생성: {len(categories_created)}개")
    print(f"[OK] CategoryEntry 생성: {entries_created}개")

    return len(categories_created), entries_created


def verify_migration(session):
    """마이그레이션 결과 검증."""
    print("\n" + "=" * 60)
    print("마이그레이션 결과 검증")
    print("=" * 60)

    # 테이블별 카운트
    categories_count = session.query(Category).count()
    entries_count = session.query(CategoryEntry).count()
    files_count = session.query(NasFile).count()
    files_with_entry = session.query(NasFile).filter(NasFile.entry_id.isnot(None)).count()
    files_with_file_id = session.query(NasFile).filter(NasFile.file_id.isnot(None)).count()

    # 기존 테이블
    groups_count = session.query(AssetGroup).count()

    print(f"\n[새 스키마]")
    print(f"  - categories: {categories_count}개")
    print(f"  - category_entries: {entries_count}개")

    print(f"\n[NasFile 업데이트]")
    print(f"  - 전체: {files_count}개")
    print(f"  - file_id 설정: {files_with_file_id}개 ({files_with_file_id/files_count*100:.1f}%)")
    print(f"  - entry_id 연결: {files_with_entry}개 ({files_with_entry/files_count*100:.1f}%)")

    print(f"\n[기존 스키마 (보존)]")
    print(f"  - asset_groups: {groups_count}개")

    # 매칭 유형별 분포
    print(f"\n[매칭 유형 분포]")
    for match_type in ['EXACT', 'PARTIAL', 'MANUAL', 'NONE', None]:
        count = session.query(CategoryEntry).filter(CategoryEntry.match_type == match_type).count()
        label = match_type or 'NULL'
        print(f"  - {label}: {count}개")

    # 연도별 분포
    print(f"\n[연도별 카테고리 (상위 10)]")
    from sqlalchemy import func
    year_dist = session.query(
        Category.year, func.count(Category.id)
    ).group_by(Category.year).order_by(Category.year.desc()).limit(10).all()
    for year, count in year_dist:
        print(f"  - {year}: {count}개")


def main():
    """메인 실행."""
    print("=" * 60)
    print("NAMS Phase 1: DB Migration to Category System")
    print("=" * 60)
    print(f"\nDB 경로: {DB_PATH}")

    # 1. DB 백업
    print("\n[Step 1] DB 백업...")
    create_backup()

    # 2. 엔진 생성
    engine = create_engine(f"sqlite:///{DB_PATH}")

    # 3. 기존 테이블 확인
    check_existing_tables(engine)

    # 4. 스키마 마이그레이션
    print("\n[Step 2] 스키마 마이그레이션...")
    migrate_schema(engine)

    # 5. 데이터 마이그레이션
    print("\n[Step 3] 데이터 마이그레이션...")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        categories, entries = migrate_data(session)

        # 6. 결과 검증
        verify_migration(session)

        print("\n" + "=" * 60)
        print("[SUCCESS] 마이그레이션 완료!")
        print("=" * 60)

    except Exception as e:
        session.rollback()
        print(f"\n[ERROR] 마이그레이션 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
