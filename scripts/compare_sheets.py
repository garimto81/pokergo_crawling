"""Google Sheets 비교 분석 스크립트.

두 시트(GGmetadata_and_timestamps vs Iconik_Full_Metadata)를 비교하여
컬럼 구조, 행 누락, 값 차이를 분석합니다.

Usage:
    python scripts/compare_sheets.py
"""

import sys
import io
from dataclasses import dataclass, field
from typing import Any

# UTF-8 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from google.oauth2 import service_account
from googleapiclient.discovery import build

# 설정
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SERVICE_ACCOUNT_FILE = r"D:\AI\claude01\json\service_account_key.json"
SPREADSHEET_ID = "1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk"

SOURCE_SHEET = "GGmetadata_and_timestamps"  # 기존 (수동 입력)
TARGET_SHEET = "Iconik_Full_Metadata"  # 신규 (API 추출)
PRIMARY_KEY = "id"  # Asset ID 기준 비교


@dataclass
class ColumnDiff:
    """컬럼 차이 결과."""

    only_in_source: list[str] = field(default_factory=list)
    only_in_target: list[str] = field(default_factory=list)
    common: list[str] = field(default_factory=list)


@dataclass
class RowDiff:
    """행 값 차이 결과."""

    asset_id: str = ""
    field_name: str = ""
    source_value: str = ""
    target_value: str = ""
    diff_type: str = ""  # "value_mismatch" | "source_empty" | "target_empty"


@dataclass
class CompareStats:
    """비교 통계."""

    # 시트 정보
    source_sheet: str = ""
    target_sheet: str = ""

    # 컬럼 비교
    column_diff: ColumnDiff = field(default_factory=ColumnDiff)

    # 행 비교
    total_source_rows: int = 0
    total_target_rows: int = 0
    matched_rows: int = 0
    source_only_ids: list[str] = field(default_factory=list)
    target_only_ids: list[str] = field(default_factory=list)

    # 값 차이
    value_diffs: list[RowDiff] = field(default_factory=list)
    max_diffs: int = 100  # 최대 저장 개수

    # 필드별 빈 값 통계
    source_empty_target_filled: dict[str, int] = field(default_factory=dict)
    target_empty_source_filled: dict[str, int] = field(default_factory=dict)
    value_mismatches_by_field: dict[str, int] = field(default_factory=dict)


def get_sheets_service() -> Any:
    """Google Sheets API 서비스 객체 생성."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


def read_sheet(
    service: Any, spreadsheet_id: str, sheet_name: str
) -> tuple[list[str], list[dict]]:
    """시트 전체 읽기.

    Returns:
        (headers, rows) - 헤더 리스트와 dict 리스트
    """
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=sheet_name)
        .execute()
    )

    rows = result.get("values", [])
    if not rows:
        return [], []

    headers = rows[0]
    data = []
    for row in rows[1:]:
        # 행 길이가 헤더보다 짧으면 빈 문자열로 채움
        padded_row = row + [""] * (len(headers) - len(row))
        data.append(dict(zip(headers, padded_row)))

    return headers, data


def compare_columns(
    source_headers: list[str], target_headers: list[str]
) -> ColumnDiff:
    """컬럼 구조 비교."""
    source_set = set(source_headers)
    target_set = set(target_headers)

    return ColumnDiff(
        only_in_source=sorted(source_set - target_set),
        only_in_target=sorted(target_set - source_set),
        common=sorted(source_set & target_set),
    )


def compare_rows(
    source_rows: list[dict],
    target_rows: list[dict],
    stats: CompareStats,
) -> None:
    """행 데이터 비교 (Asset ID 기준)."""
    # ID 기준 인덱싱
    source_by_id = {row.get(PRIMARY_KEY, ""): row for row in source_rows if row.get(PRIMARY_KEY)}
    target_by_id = {row.get(PRIMARY_KEY, ""): row for row in target_rows if row.get(PRIMARY_KEY)}

    source_ids = set(source_by_id.keys())
    target_ids = set(target_by_id.keys())

    # 누락 행 분석
    stats.source_only_ids = sorted(source_ids - target_ids)
    stats.target_only_ids = sorted(target_ids - source_ids)

    # 공통 행 값 비교
    common_ids = source_ids & target_ids
    stats.matched_rows = len(common_ids)

    for asset_id in common_ids:
        analyze_value_diffs(
            asset_id,
            source_by_id[asset_id],
            target_by_id[asset_id],
            stats,
        )


def analyze_value_diffs(
    asset_id: str,
    source_row: dict,
    target_row: dict,
    stats: CompareStats,
) -> None:
    """단일 행의 값 비교."""
    # 공통 컬럼만 비교 (PRIMARY_KEY 제외)
    all_fields = set(source_row.keys()) | set(target_row.keys())

    for field_name in all_fields:
        if field_name == PRIMARY_KEY:
            continue

        source_val = str(source_row.get(field_name, "")).strip()
        target_val = str(target_row.get(field_name, "")).strip()

        # 빈 값 분석
        if not source_val and target_val:
            stats.source_empty_target_filled[field_name] = (
                stats.source_empty_target_filled.get(field_name, 0) + 1
            )
            add_diff(stats, asset_id, field_name, source_val, target_val, "source_empty")

        elif source_val and not target_val:
            stats.target_empty_source_filled[field_name] = (
                stats.target_empty_source_filled.get(field_name, 0) + 1
            )
            add_diff(stats, asset_id, field_name, source_val, target_val, "target_empty")

        elif source_val != target_val:
            stats.value_mismatches_by_field[field_name] = (
                stats.value_mismatches_by_field.get(field_name, 0) + 1
            )
            add_diff(stats, asset_id, field_name, source_val, target_val, "value_mismatch")


def add_diff(
    stats: CompareStats,
    asset_id: str,
    field_name: str,
    source_val: str,
    target_val: str,
    diff_type: str,
) -> None:
    """차이 기록 (최대 개수 제한)."""
    if len(stats.value_diffs) < stats.max_diffs:
        stats.value_diffs.append(
            RowDiff(
                asset_id=asset_id,
                field_name=field_name,
                source_value=source_val[:100] if source_val else "",
                target_value=target_val[:100] if target_val else "",
                diff_type=diff_type,
            )
        )


def print_report(stats: CompareStats) -> None:
    """콘솔 리포트 출력."""
    print("=" * 70)
    print("SHEETS COMPARISON REPORT")
    print("=" * 70)
    print(f"\nSource: {stats.source_sheet}")
    print(f"Target: {stats.target_sheet}")

    # 1. 컬럼 비교
    print("\n" + "-" * 70)
    print("[1] COLUMN STRUCTURE")
    print("-" * 70)
    print(f"  Common columns: {len(stats.column_diff.common)}")
    print(f"  Only in {stats.source_sheet}: {stats.column_diff.only_in_source or 'None'}")
    print(f"  Only in {stats.target_sheet}: {stats.column_diff.only_in_target or 'None'}")

    # 2. 행 비교
    print("\n" + "-" * 70)
    print("[2] ROW COMPARISON")
    print("-" * 70)
    print(f"  {stats.source_sheet} rows: {stats.total_source_rows:,}")
    print(f"  {stats.target_sheet} rows: {stats.total_target_rows:,}")
    print(f"  Matched by ID: {stats.matched_rows:,}")
    print(f"  Only in {stats.source_sheet}: {len(stats.source_only_ids)} rows")
    print(f"  Only in {stats.target_sheet}: {len(stats.target_only_ids)} rows")

    # 누락된 ID 샘플 출력
    if stats.source_only_ids:
        print(f"\n  Sample IDs only in {stats.source_sheet} (first 5):")
        for id_ in stats.source_only_ids[:5]:
            print(f"    - {id_}")

    if stats.target_only_ids:
        print(f"\n  Sample IDs only in {stats.target_sheet} (first 5):")
        for id_ in stats.target_only_ids[:5]:
            print(f"    - {id_}")

    # 3. 값 차이 요약
    print("\n" + "-" * 70)
    print("[3] VALUE DIFFERENCES SUMMARY")
    print("-" * 70)

    total_mismatches = sum(stats.value_mismatches_by_field.values())
    total_source_empty = sum(stats.source_empty_target_filled.values())
    total_target_empty = sum(stats.target_empty_source_filled.values())

    print(f"  Value mismatches: {total_mismatches:,}")
    print(f"  {stats.source_sheet} empty, {stats.target_sheet} filled: {total_source_empty:,}")
    print(f"  {stats.target_sheet} empty, {stats.source_sheet} filled: {total_target_empty:,}")

    # 4. 필드별 빈 값 분석 (Top 10)
    print("\n" + "-" * 70)
    print("[4] FIELD COVERAGE (Top 10)")
    print("-" * 70)

    print(f"\n  Fields where {stats.source_sheet} is empty but {stats.target_sheet} has data:")
    for field, count in sorted(
        stats.source_empty_target_filled.items(),
        key=lambda x: -x[1],
    )[:10]:
        print(f"    {field}: {count:,}")

    print(f"\n  Fields where {stats.target_sheet} is empty but {stats.source_sheet} has data:")
    for field, count in sorted(
        stats.target_empty_source_filled.items(),
        key=lambda x: -x[1],
    )[:10]:
        print(f"    {field}: {count:,}")

    if stats.value_mismatches_by_field:
        print("\n  Fields with value mismatches:")
        for field, count in sorted(
            stats.value_mismatches_by_field.items(),
            key=lambda x: -x[1],
        )[:10]:
            print(f"    {field}: {count:,}")

    # 5. 샘플 차이
    print("\n" + "-" * 70)
    print("[5] SAMPLE DIFFERENCES (First 10)")
    print("-" * 70)

    for diff in stats.value_diffs[:10]:
        print(f"\n  [{diff.diff_type}] Asset: {diff.asset_id}")
        print(f"    Field: {diff.field_name}")
        print(f"      {stats.source_sheet}: {diff.source_value or '(empty)'}")
        print(f"      {stats.target_sheet}: {diff.target_value or '(empty)'}")

    print("\n" + "=" * 70)
    print("COMPARISON COMPLETE")
    print("=" * 70)


def main() -> None:
    """메인 함수."""
    print("Google Sheets Comparison Tool")
    print("-" * 40)

    try:
        service = get_sheets_service()

        # 시트 읽기
        print(f"\nLoading {SOURCE_SHEET}...")
        source_headers, source_rows = read_sheet(service, SPREADSHEET_ID, SOURCE_SHEET)
        print(f"  Loaded {len(source_rows):,} rows, {len(source_headers)} columns")

        print(f"\nLoading {TARGET_SHEET}...")
        target_headers, target_rows = read_sheet(service, SPREADSHEET_ID, TARGET_SHEET)
        print(f"  Loaded {len(target_rows):,} rows, {len(target_headers)} columns")

        # 통계 초기화
        stats = CompareStats(
            source_sheet=SOURCE_SHEET,
            target_sheet=TARGET_SHEET,
            total_source_rows=len(source_rows),
            total_target_rows=len(target_rows),
        )

        # 비교 수행
        print("\nComparing columns...")
        stats.column_diff = compare_columns(source_headers, target_headers)

        print("Comparing rows...")
        compare_rows(source_rows, target_rows, stats)

        # 리포트 출력
        print("\n")
        print_report(stats)

    except Exception as e:
        print(f"\nError: {e}")
        raise


if __name__ == "__main__":
    main()
