"""Analyze Master_Catalog for classification criteria."""

import os
import re
import sys
from pathlib import Path

# Fix Unicode output on Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))


def clean_title(title: str) -> str:
    """Remove emojis and non-ASCII characters for safe printing."""
    return re.sub(r'[^\x00-\x7F]+', '', title)

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config.settings import get_settings
from iconik import IconikClient

# UDM metadata 스프레드시트 (Master_Catalog 포함)
UDM_SPREADSHEET_ID = "1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4"


def get_sheets_service():
    """Get Google Sheets service."""
    settings = get_settings()
    credentials = service_account.Credentials.from_service_account_file(
        str(settings.sheets.service_account_path),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    return build("sheets", "v4", credentials=credentials)


def get_master_catalog_filenames() -> set[str]:
    """Get all filenames from Master_Catalog (without extension)."""
    service = get_sheets_service()

    # Master_Catalog 시트에서 Filename 컬럼 조회
    result = service.spreadsheets().values().get(
        spreadsheetId=UDM_SPREADSHEET_ID,
        range="Master_Catalog!A:Z",  # 전체 컬럼
    ).execute()

    values = result.get("values", [])
    if not values:
        print("Master_Catalog is empty")
        return set()

    headers = values[0]
    print(f"Master_Catalog columns: {headers}")

    # Filename 컬럼 인덱스 찾기
    filename_idx = None
    for i, h in enumerate(headers):
        if h.lower() == "filename":
            filename_idx = i
            break

    if filename_idx is None:
        print("Filename column not found!")
        return set()

    print(f"Filename column index: {filename_idx}")

    # 확장자 제외한 파일명 수집
    filenames = set()
    for row in values[1:]:
        if len(row) > filename_idx and row[filename_idx]:
            filename = row[filename_idx]
            # 확장자 제거
            name_without_ext = Path(filename).stem
            filenames.add(name_without_ext)

    print(f"Total unique filenames: {len(filenames)}")
    print(f"\nSample filenames (first 10):")
    for f in list(filenames)[:10]:
        print(f"  - {f}")

    return filenames


def analyze_classification(master_filenames: set[str]):
    """Analyze Iconik assets vs Master_Catalog filenames."""
    c = IconikClient()

    matched_general = []  # Master_Catalog에 있음 → General
    unmatched_possible_subclip = []  # Master_Catalog에 없음 → 아마도 Subclip

    print("\n" + "=" * 80)
    print("Analyzing Iconik assets against Master_Catalog...")
    print("=" * 80)

    for i, a in enumerate(c.get_all_assets()):
        if i >= 300:
            break

        if i % 100 == 0:
            print(f"  ... {i} scanned")

        # Iconik title과 Master_Catalog filename 비교
        title = a.title if a.title else ""

        # 매칭 체크 (정확히 일치)
        is_in_master = title in master_filenames

        # Segment 정보
        has_segment = False
        try:
            segs = c.get_asset_segments(a.id, raise_for_404=False)
            has_segment = any(s.get("segment_type") == "GENERIC" for s in segs)
        except Exception:
            pass

        info = {
            "id": a.id[:8],
            "title": title[:50],
            "type": a.type,
            "has_orig": bool(a.original_asset_id),
            "has_segment": has_segment,
            "in_master": is_in_master,
        }

        if is_in_master:
            matched_general.append(info)
        else:
            unmatched_possible_subclip.append(info)

    c.close()

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    print(f"\n[MATCHED - In Master_Catalog -> General] ({len(matched_general)})")
    for x in matched_general[:10]:
        t = clean_title(x['title'][:45])
        print(f"  {t:45} type={x['type']} seg={x['has_segment']}")

    print(f"\n[UNMATCHED - Not in Master_Catalog -> Subclip?] ({len(unmatched_possible_subclip)})")

    # Subclip 분석
    type_subclip = [x for x in unmatched_possible_subclip if x["type"] == "SUBCLIP"]
    type_asset_with_seg = [x for x in unmatched_possible_subclip if x["type"] == "ASSET" and x["has_segment"]]
    type_asset_no_seg = [x for x in unmatched_possible_subclip if x["type"] == "ASSET" and not x["has_segment"]]

    print(f"\n  [type=SUBCLIP] ({len(type_subclip)})")
    for x in type_subclip[:5]:
        print(f"    {clean_title(x['title'][:45])}")

    print(f"\n  [type=ASSET + has Segment] ({len(type_asset_with_seg)})")
    for x in type_asset_with_seg[:5]:
        print(f"    {clean_title(x['title'][:45])}")

    print(f"\n  [type=ASSET + no Segment] ({len(type_asset_no_seg)})")
    for x in type_asset_no_seg[:5]:
        print(f"    {clean_title(x['title'][:45])}")

    # 결론
    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print(f"""
분류 기준 제안:

1. Master_Catalog에 Filename 매칭되면 → General Metadata
   (실제 NAS 파일이 존재하는 원본 Asset)

2. Master_Catalog에 없으면 → Subclip Metadata
   - type=SUBCLIP: {len(type_subclip)}개
   - type=ASSET + Segment: {len(type_asset_with_seg)}개
   - type=ASSET + no Segment: {len(type_asset_no_seg)}개

주의: type=ASSET이지만 Master에 없는 경우가 {len(type_asset_with_seg) + len(type_asset_no_seg)}개 있음
    → 이것들이 문제의 Hand clip들일 가능성 높음
""")


def main():
    print("=" * 80)
    print("Master_Catalog Based Classification Analysis")
    print("=" * 80)

    # 1. Master_Catalog에서 Filename 목록 가져오기
    master_filenames = get_master_catalog_filenames()

    if not master_filenames:
        print("Failed to get Master_Catalog filenames")
        return

    # 2. Iconik assets와 비교 분석
    analyze_classification(master_filenames)


if __name__ == "__main__":
    main()
