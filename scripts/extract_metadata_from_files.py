#!/usr/bin/env python
"""NasFile 파일명에서 메타데이터 추출.

패턴 매칭이 되지 않은 파일들의 파일명/경로에서 year, region, event_type, episode를 추출합니다.
"""
import sys
import re
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.nams.api.database.session import get_db_context
from src.nams.api.database.models import NasFile, Region, EventType


# 연도 추출 패턴
YEAR_PATTERNS = [
    r'(?:19|20)(\d{2})[-_]',       # 2024_ or 2024-
    r'[-_](?:19|20)(\d{2})[-_]',   # _2024_ or -2024-
    r'WS(\d{2})[-_]',              # WS24_ (2024)
    r'WSOP(\d{2})[-_]',            # WSOP24_ (2024)
    r'WSOPE?(\d{2})[-_]',          # WSOPE24_ (2024)
    r'(?:19|20)(\d{2})',           # 2024 anywhere
]

# 지역 추출 패턴
REGION_PATTERNS = {
    'EU': [r'europe', r'wsope', r'_eu_', r'_eu\d', r'-eu-'],
    'APAC': [r'apac', r'asia', r'_ap_'],
    'PARADISE': [r'paradise', r'_pad_', r'pad\d{2}'],
    'CYPRUS': [r'cyprus', r'_cyp_'],
    'LA': [r'circuit.*la', r'la.*circuit'],
    'LONDON': [r'london'],
}

# 이벤트 타입 추출 패턴
EVENT_TYPE_PATTERNS = {
    'ME': [r'main[-_]?event', r'_me[-_]', r'_me\d', r'wsop\d{2}_me'],
    'BR': [r'bracelet', r'_br[-_]', r'event[-_]?\d+'],
    'HU': [r'heads[-_]?up', r'_hu[-_]', r'_hu\d'],
    'GM': [r'grudge[-_]?match', r'_gm[-_]', r'_gm\d'],
    'HR': [r'high[-_]?roller', r'_hr[-_]', r'_hr\d', r'super.*high.*roller'],
    'MB': [r'mystery[-_]?bounty', r'_mb[-_]'],
}

# Episode/Day 추출 패턴
EPISODE_PATTERNS = [
    r'[-_]d(\d+)',          # _D1, _D2
    r'day[-_]?(\d+)',       # Day1, Day_1
    r'ep[-_]?(\d+)',        # Ep1, Ep_1
    r'episode[-_]?(\d+)',   # Episode1
    r'[-_](\d{1,2})[-_]?(?:of|$)',  # _1_of, _1.mp4
    r'[-_]e(\d+)',          # _E1
]


def extract_year(filename: str, full_path: str) -> int:
    """파일명/경로에서 연도 추출."""
    text = (filename + ' ' + (full_path or '')).lower()

    # 직접 4자리 연도 찾기
    match = re.search(r'(19[7-9]\d|20[0-2]\d)', text)
    if match:
        year = int(match.group(1))
        if 1973 <= year <= 2025:
            return year

    # 2자리 연도 찾기 (WS24 등)
    for pattern in YEAR_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            yy = int(match.group(1))
            year = 2000 + yy if yy < 50 else 1900 + yy
            if 1973 <= year <= 2025:
                return year

    return None


def extract_region(filename: str, full_path: str) -> str:
    """파일명/경로에서 지역 추출."""
    text = (filename + ' ' + (full_path or '')).lower()

    for region_code, patterns in REGION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return region_code

    return 'LV'  # 기본값


def extract_event_type(filename: str, full_path: str) -> str:
    """파일명/경로에서 이벤트 타입 추출."""
    text = (filename + ' ' + (full_path or '')).lower()

    for event_code, patterns in EVENT_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return event_code

    return None


def extract_episode(filename: str, full_path: str) -> int:
    """파일명/경로에서 에피소드 번호 추출."""
    text = (filename + ' ' + (full_path or '')).lower()

    for pattern in EPISODE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            ep = int(match.group(1))
            if 1 <= ep <= 50:
                return ep

    return None


def get_region_id(code: str, session) -> int:
    """Region 코드로 ID 조회."""
    region = session.query(Region).filter(Region.code == code).first()
    return region.id if region else None


def get_event_type_id(code: str, session) -> int:
    """EventType 코드로 ID 조회."""
    if not code:
        return None
    etype = session.query(EventType).filter(EventType.code == code).first()
    return etype.id if etype else None


def extract_metadata():
    """모든 NasFile에서 메타데이터 추출."""

    print("=" * 60)
    print("NasFile 메타데이터 추출")
    print("=" * 60)

    with get_db_context() as session:
        # year가 없는 파일만 처리
        files = session.query(NasFile).filter(NasFile.year.is_(None)).all()

        if not files:
            print("[INFO] 모든 파일에 year가 있습니다.")
            return 0

        print(f"\n[INFO] 처리 대상: {len(files)}개 (year=None)")

        updated = 0
        still_none = 0

        for f in files:
            year = extract_year(f.filename, f.full_path)

            if year:
                f.year = year
                f.region_id = get_region_id(extract_region(f.filename, f.full_path), session)
                f.event_type_id = get_event_type_id(extract_event_type(f.filename, f.full_path), session)
                f.episode = extract_episode(f.filename, f.full_path)
                updated += 1
            else:
                still_none += 1

        session.commit()

        print(f"\n[OK] 메타데이터 추출: {updated}개")
        print(f"[WARN] year 추출 실패: {still_none}개")

        # 결과 검증
        print("\n[결과 검증]")
        total = session.query(NasFile).count()
        with_year = session.query(NasFile).filter(NasFile.year.isnot(None)).count()
        print(f"  - 전체: {total}개")
        print(f"  - year 있음: {with_year}개 ({with_year/total*100:.1f}%)")

        # year 추출 실패 샘플
        no_year = session.query(NasFile).filter(NasFile.year.is_(None)).limit(10).all()
        if no_year:
            print(f"\n[year 추출 실패 샘플]")
            for f in no_year:
                print(f"  - {f.filename}")

        return updated


def main():
    """메인 실행."""
    extracted = extract_metadata()

    if extracted > 0:
        print("\n[INFO] link_files_to_entries.py를 다시 실행하세요.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
