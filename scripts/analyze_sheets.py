"""Google Sheets 구조 분석 스크립트.

Spreadsheet ID: 1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk
"""

import sys
import io

# UTF-8 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import Any

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SERVICE_ACCOUNT_FILE = r"D:\AI\claude01\json\service_account_key.json"
SPREADSHEET_ID = "1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk"


def get_sheets_service() -> Any:
    """Google Sheets API 서비스 객체 생성."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


def analyze_spreadsheet(service: Any, spreadsheet_id: str) -> None:
    """스프레드시트 구조 분석.

    Args:
        service: Google Sheets API 서비스
        spreadsheet_id: 스프레드시트 ID
    """
    # 1. 스프레드시트 메타데이터 조회
    print("=" * 80)
    print("📊 Google Sheets 구조 분석")
    print("=" * 80)

    spreadsheet = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id
    ).execute()

    print(f"\n📌 Spreadsheet ID: {spreadsheet_id}")
    print(f"📌 Title: {spreadsheet.get('properties', {}).get('title', 'N/A')}")

    # 2. 시트 목록 조회
    sheets = spreadsheet.get("sheets", [])
    print(f"\n📋 총 {len(sheets)}개 시트 발견\n")

    # 3. 각 시트별 상세 분석
    for idx, sheet in enumerate(sheets, 1):
        sheet_title = sheet["properties"]["title"]
        sheet_id = sheet["properties"]["sheetId"]

        print(f"\n{'─' * 80}")
        print(f"시트 {idx}: {sheet_title} (ID: {sheet_id})")
        print(f"{'─' * 80}")

        # 4. 헤더 및 데이터 샘플 조회 (A1:Z6 범위)
        range_name = f"{sheet_title}!A1:Z6"

        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()

            values = result.get("values", [])

            if not values:
                print("  ⚠️  데이터 없음")
                continue

            # 헤더 출력
            if values:
                print(f"\n  📌 헤더 ({len(values[0])}개 컬럼):")
                for col_idx, header in enumerate(values[0], 1):
                    print(f"    {col_idx:2d}. {header}")

            # 데이터 샘플 출력 (최대 5행)
            if len(values) > 1:
                print(f"\n  📊 데이터 샘플 ({len(values) - 1}행):")
                for row_idx, row in enumerate(values[1:6], 2):
                    # 각 행을 컬럼별로 출력
                    print(f"\n    Row {row_idx}:")
                    for col_idx, cell in enumerate(row):
                        if cell:  # 비어있지 않은 셀만 출력
                            col_name = values[0][col_idx] if col_idx < len(values[0]) else f"Col{col_idx + 1}"
                            print(f"      {col_name}: {cell}")
            else:
                print("\n  ⚠️  데이터 행 없음 (헤더만 존재)")

        except Exception as e:
            print(f"  ❌ 오류: {e}")

    print(f"\n{'=' * 80}")
    print("✅ 분석 완료")
    print(f"{'=' * 80}\n")


def main() -> None:
    """메인 함수."""
    try:
        service = get_sheets_service()
        analyze_spreadsheet(service, SPREADSHEET_ID)
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
