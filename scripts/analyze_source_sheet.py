"""소스 시트 구조 분석 스크립트.

마이그레이션 대상 소스 시트의 탭, 컬럼, 데이터 구조를 분석합니다.

Source Spreadsheet ID: 1_RN_W_ZQclSZA0Iez6XniCXVtjkkd5HNZwiT6l-z6d4
Target Spreadsheet ID: 1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk
"""

import sys
import io
from typing import Any

# UTF-8 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SERVICE_ACCOUNT_FILE = r"D:\AI\claude01\json\service_account_key.json"

# Source Sheet (마이그레이션 소스)
SOURCE_SPREADSHEET_ID = "1_RN_W_ZQclSZA0Iez6XniCXVtjkkd5HNZwiT6l-z6d4"

# Target Sheet 35 컬럼 (비교용)
TARGET_COLUMNS = [
    "id", "title",
    "time_start_ms", "time_end_ms", "time_start_S", "time_end_S",
    "Description", "ProjectName", "ProjectNameTag", "SearchTag",
    "Year_", "Location", "Venue", "EpisodeEvent",
    "Source", "Scene", "GameType", "PlayersTags",
    "HandGrade", "HANDTag", "EPICHAND", "Tournament",
    "PokerPlayTags", "Adjective", "Emotion", "AppearanceOutfit",
    "SceneryObject", "_gcvi_tags", "Badbeat", "Bluff",
    "Suckout", "Cooler", "RUNOUTTag", "PostFlop", "All-in",
]


def get_sheets_service() -> Any:
    """Google Sheets API 서비스 객체 생성."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


def get_row_count(service: Any, spreadsheet_id: str, sheet_title: str) -> int:
    """시트의 전체 행 수 조회."""
    try:
        # A열 전체 조회하여 행 수 파악
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_title}'!A:A",
        ).execute()
        values = result.get("values", [])
        return len(values)
    except Exception:
        return 0


def analyze_column_mapping(source_headers: list[str]) -> dict[str, Any]:
    """소스 컬럼과 타겟 컬럼 매핑 분석."""
    target_lower = {col.lower(): col for col in TARGET_COLUMNS}

    matched = []
    unmatched = []

    for header in source_headers:
        header_lower = header.lower().strip()
        if header in TARGET_COLUMNS:
            matched.append((header, header))  # 정확 매칭
        elif header_lower in target_lower:
            matched.append((header, target_lower[header_lower]))  # 대소문자 무시 매칭
        else:
            unmatched.append(header)

    return {
        "matched": matched,
        "unmatched": unmatched,
        "coverage": len(matched) / len(source_headers) * 100 if source_headers else 0,
    }


def analyze_spreadsheet(service: Any, spreadsheet_id: str) -> dict[str, Any]:
    """스프레드시트 구조 분석.

    Args:
        service: Google Sheets API 서비스
        spreadsheet_id: 스프레드시트 ID

    Returns:
        분석 결과 딕셔너리
    """
    print("=" * 80)
    print("Source Sheet Structure Analysis")
    print("=" * 80)

    spreadsheet = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id
    ).execute()

    title = spreadsheet.get("properties", {}).get("title", "N/A")
    print(f"\nSpreadsheet ID: {spreadsheet_id}")
    print(f"Title: {title}")

    sheets = spreadsheet.get("sheets", [])
    print(f"\nTotal Tabs: {len(sheets)}")

    total_rows = 0
    all_headers = set()
    analysis_results = []

    # 각 시트별 상세 분석
    for idx, sheet in enumerate(sheets, 1):
        sheet_title = sheet["properties"]["title"]
        sheet_id = sheet["properties"]["sheetId"]

        print(f"\n{'─' * 80}")
        print(f"Tab {idx}: {sheet_title} (ID: {sheet_id})")
        print(f"{'─' * 80}")

        # 전체 행 수 조회
        row_count = get_row_count(service, spreadsheet_id, sheet_title)

        # 헤더 및 데이터 샘플 조회 (A1:AZ6 범위 - 더 넓은 범위)
        range_name = f"'{sheet_title}'!A1:AZ6"

        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()

            values = result.get("values", [])

            if not values:
                print("  [WARN] No data")
                continue

            headers = values[0] if values else []
            data_rows = len(values) - 1 if len(values) > 1 else 0

            print(f"\n  Columns: {len(headers)}")
            print(f"  Total Rows: {row_count} (Header + {row_count - 1} data rows)")

            # 헤더 출력
            print(f"\n  Headers:")
            for col_idx, header in enumerate(headers, 1):
                print(f"    {col_idx:2d}. {header}")

            # 컬럼 매핑 분석
            mapping = analyze_column_mapping(headers)
            print(f"\n  Column Mapping Analysis:")
            print(f"    Matched: {len(mapping['matched'])} columns ({mapping['coverage']:.1f}%)")

            if mapping["matched"]:
                print("    Matched columns:")
                for src, tgt in mapping["matched"][:10]:  # 최대 10개만 표시
                    marker = "[OK]" if src == tgt else "[CASE]"
                    print(f"      {marker} {src} -> {tgt}")
                if len(mapping["matched"]) > 10:
                    print(f"      ... and {len(mapping['matched']) - 10} more")

            if mapping["unmatched"]:
                print(f"    Unmatched: {len(mapping['unmatched'])} columns")
                for header in mapping["unmatched"][:10]:
                    print(f"      [SKIP] {header}")
                if len(mapping["unmatched"]) > 10:
                    print(f"      ... and {len(mapping['unmatched']) - 10} more")

            # 데이터 샘플 출력 (최대 2행)
            if data_rows > 0:
                print(f"\n  Sample Data ({min(2, data_rows)} rows):")
                for row_idx, row in enumerate(values[1:3], 1):
                    print(f"\n    Row {row_idx}:")
                    for col_idx, cell in enumerate(row[:10]):  # 처음 10개 컬럼만
                        if cell:
                            col_name = headers[col_idx] if col_idx < len(headers) else f"Col{col_idx + 1}"
                            cell_preview = str(cell)[:50] + "..." if len(str(cell)) > 50 else cell
                            print(f"      {col_name}: {cell_preview}")

            # 결과 저장
            all_headers.update(headers)
            total_rows += row_count - 1  # 헤더 제외
            analysis_results.append({
                "tab_name": sheet_title,
                "tab_id": sheet_id,
                "columns": len(headers),
                "rows": row_count - 1,
                "headers": headers,
                "mapping": mapping,
            })

        except Exception as e:
            print(f"  [ERROR] {e}")

    # 요약
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"\nTotal Tabs: {len(analysis_results)}")
    print(f"Total Data Rows: {total_rows}")
    print(f"Unique Columns: {len(all_headers)}")

    print(f"\nTabs Overview:")
    for result in analysis_results:
        match_rate = result["mapping"]["coverage"]
        print(f"  - {result['tab_name']}: {result['rows']} rows, {result['columns']} cols, {match_rate:.0f}% match")

    # 타겟 35컬럼 커버리지
    all_matched = set()
    for result in analysis_results:
        for src, tgt in result["mapping"]["matched"]:
            all_matched.add(tgt)

    target_coverage = len(all_matched) / len(TARGET_COLUMNS) * 100
    print(f"\nTarget Column Coverage: {len(all_matched)}/{len(TARGET_COLUMNS)} ({target_coverage:.1f}%)")

    missing_target = set(TARGET_COLUMNS) - all_matched
    if missing_target:
        print(f"Missing Target Columns ({len(missing_target)}):")
        for col in sorted(missing_target):
            print(f"  - {col}")

    print(f"\n{'=' * 80}")
    print("Analysis Complete")
    print(f"{'=' * 80}\n")

    return {
        "spreadsheet_id": spreadsheet_id,
        "title": title,
        "tabs": analysis_results,
        "total_rows": total_rows,
        "all_headers": list(all_headers),
        "target_coverage": target_coverage,
        "missing_target_columns": list(missing_target),
    }


def main() -> None:
    """메인 함수."""
    try:
        service = get_sheets_service()
        result = analyze_spreadsheet(service, SOURCE_SPREADSHEET_ID)

        # 컬럼 매핑 제안 출력
        print("\nSuggested Column Mapping (for column_mapper.py):")
        print("=" * 50)
        print("COLUMN_MAPPING = {")
        for tab in result["tabs"]:
            if tab["mapping"]["matched"]:
                print(f"    # {tab['tab_name']}")
                for src, tgt in tab["mapping"]["matched"]:
                    if src != tgt:
                        print(f'    "{src}": "{tgt}",')
        print("}")

    except Exception as e:
        print(f"[ERROR] {e}")
        raise


if __name__ == "__main__":
    main()
