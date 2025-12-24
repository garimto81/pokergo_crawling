"""Archive_Metadata → Iconik 마이그레이션 테스트.

1개 행을 선택하여 Iconik 에셋의 메타데이터를 업데이트합니다.

Usage:
    python scripts/test_iconik_migration.py                  # Dry run
    python scripts/test_iconik_migration.py --execute        # 실행
    python scripts/test_iconik_migration.py --execute --row 5  # 5번째 행 사용
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Any

import httpx
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load iconik2sheet .env.local
ICONIK2SHEET_ROOT = Path(__file__).parent.parent / "src" / "migrations" / "iconik2sheet"
load_dotenv(ICONIK2SHEET_ROOT / ".env.local")

# Configuration
SERVICE_ACCOUNT_PATH = r"D:\AI\claude01\json\service_account_key.json"
SPREADSHEET_ID = "1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk"

ICONIK_APP_ID = os.getenv("ICONIK_APP_ID", "")
ICONIK_AUTH_TOKEN = os.getenv("ICONIK_AUTH_TOKEN", "")
ICONIK_BASE_URL = os.getenv("ICONIK_BASE_URL", "https://app.iconik.io")
ICONIK_METADATA_VIEW_ID = os.getenv("ICONIK_METADATA_VIEW_ID", "")

# Archive_Metadata 필드 → Iconik 메타데이터 필드 매핑
# NOTE: Iconik의 많은 필드가 dropdown 타입으로, 사전 정의된 값만 허용
# 자유 텍스트 필드만 마이그레이션 (dropdown 필드는 "no longer select in list" 오류 발생)

# 안전한 필드 (자유 텍스트)
FIELD_MAPPING = {
    "Description": "Description",
    "Year_": "Year_",
    "Location": "Location",       # text 필드
    "PlayersTags": "PlayersTags", # 다중 선택 가능
    "PokerPlayTags": "PokerPlayTags",  # 다중 선택 가능
}

# Dropdown 필드 (마이그레이션 제외 - 값 불일치)
# - HandGrade: Archive="1,2,3" vs Iconik="★,★★,★★★"
# - HANDTag: Archive="88 vs JJ" vs Iconik="AA vs KK" 등 정의된 패턴
# - Tournament: Archive="WSOP Circuit" vs Iconik="bracelet" 등
# - Source: Archive=NAS경로 vs Iconik="Clean,PGM" 등
# - Emotion: dropdown 타입
DROPDOWN_FIELDS_EXCLUDED = [
    "HandGrade", "HANDTag", "Tournament", "Source", "Emotion",
    "Venue", "GameType", "Scene", "Adjective", "EPICHAND",
    "AppearanceOutfit", "SceneryObject", "Badbeat", "Bluff",
    "Suckout", "Cooler", "PostFlop", "RUNOUTTag", "All-in",
]


def get_sheets_service() -> Any:
    """Google Sheets API 서비스 생성."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_PATH,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    return build("sheets", "v4", credentials=creds)


def read_sheet(service: Any, sheet_name: str, header_row: int = 1) -> list[dict]:
    """시트 데이터 읽기."""
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{sheet_name}'",
    ).execute()

    rows = result.get("values", [])
    if not rows or len(rows) < header_row:
        return []

    headers = rows[header_row - 1]
    data = []

    for row in rows[header_row:]:
        if not any(cell.strip() for cell in row if isinstance(cell, str)):
            continue
        padded_row = row + [""] * (len(headers) - len(row))
        row_dict = {}
        for i, header in enumerate(headers):
            if header and i < len(padded_row):
                row_dict[header] = padded_row[i]
        if row_dict:
            data.append(row_dict)

    return data


def build_metadata_payload(row: dict) -> dict:
    """Archive_Metadata 행을 Iconik 메타데이터 payload로 변환."""
    metadata_values = {}

    for sheet_col, api_field in FIELD_MAPPING.items():
        value = row.get(sheet_col, "").strip()
        if value:
            if "," in value:
                field_values = [{"value": v.strip()} for v in value.split(",") if v.strip()]
            else:
                field_values = [{"value": value}]
            metadata_values[api_field] = {"field_values": field_values}

    return metadata_values


class IconikAPI:
    """Simple Iconik API client."""

    def __init__(self) -> None:
        self.base_url = f"{ICONIK_BASE_URL}/API"
        self.headers = {
            "App-ID": ICONIK_APP_ID,
            "Auth-Token": ICONIK_AUTH_TOKEN,
            "Content-Type": "application/json",
        }
        self.client = httpx.Client(base_url=self.base_url, headers=self.headers, timeout=30)

    def health_check(self) -> bool:
        try:
            resp = self.client.get("/files/v1/storages/")
            return resp.status_code == 200
        except Exception:
            return False

    def get_metadata(self, asset_id: str, view_id: str) -> dict | None:
        try:
            resp = self.client.get(f"/metadata/v1/assets/{asset_id}/views/{view_id}/")
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception:
            return None

    def update_metadata(self, asset_id: str, view_id: str, metadata_values: dict) -> dict:
        data = {"metadata_values": metadata_values}
        resp = self.client.put(f"/metadata/v1/assets/{asset_id}/views/{view_id}/", json=data)
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self.client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive_Metadata → Iconik 마이그레이션 테스트")
    parser.add_argument("--execute", action="store_true", help="실제 업데이트 실행")
    parser.add_argument("--row", type=int, default=1, help="테스트할 행 번호 (1부터 시작)")
    parser.add_argument("--asset-id", type=str, help="대상 Iconik 에셋 ID")
    args = parser.parse_args()

    print("=" * 60)
    print("Archive_Metadata -> Iconik Migration Test")
    print("=" * 60)

    # 1. 설정 확인
    if not ICONIK_METADATA_VIEW_ID:
        print("[ERROR] ICONIK_METADATA_VIEW_ID가 설정되지 않았습니다.")
        sys.exit(1)

    view_id = ICONIK_METADATA_VIEW_ID
    print(f"\nMetadata View ID: {view_id[:8]}...{view_id[-4:]}")

    # 2. Google Sheets 읽기
    service = get_sheets_service()

    archive_data = read_sheet(service, "Archive_Metadata", header_row=1)
    print(f"\nArchive_Metadata: {len(archive_data)} rows")

    if args.row > len(archive_data):
        print(f"[ERROR] Row {args.row}이 범위를 벗어났습니다. (max: {len(archive_data)})")
        sys.exit(1)

    source_row = archive_data[args.row - 1]
    print(f"\n[Source] Archive_Metadata Row {args.row}:")
    for k, v in source_row.items():
        if v:
            display_v = str(v)[:60] + "..." if len(str(v)) > 60 else v
            print(f"  {k}: {display_v}")

    # 3. 대상 Iconik 에셋 선택
    if args.asset_id:
        asset_id = args.asset_id
    else:
        iconik_data = read_sheet(service, "Iconik_Full_Metadata", header_row=1)
        if not iconik_data:
            print("[ERROR] Iconik_Full_Metadata가 비어 있습니다.")
            sys.exit(1)

        asset_id = iconik_data[0].get("id", "")
        if not asset_id:
            print("[ERROR] Iconik 에셋 ID를 찾을 수 없습니다.")
            sys.exit(1)

    print(f"\n[Target] Iconik Asset ID: {asset_id}")

    # 4. 메타데이터 payload 생성
    metadata_payload = build_metadata_payload(source_row)

    print(f"\n[Payload] Metadata to update ({len(metadata_payload)} fields):")
    for field, data in metadata_payload.items():
        values = [fv.get("value", "") for fv in data.get("field_values", [])]
        display = ", ".join(str(v) for v in values)[:50]
        print(f"  {field}: {display}")

    # 5. Iconik API
    print("\n" + "-" * 60)
    api = IconikAPI()

    try:
        if not api.health_check():
            print("[ERROR] Iconik API 연결 실패")
            sys.exit(1)
        print("[OK] Iconik API 연결 성공")

        # 6. 현재 메타데이터 조회
        print(f"\n[Before] Current metadata:")
        current = api.get_metadata(asset_id, view_id)
        if current:
            current_values = current.get("metadata_values", {})
            for field in FIELD_MAPPING.values():
                if field in current_values:
                    fv = current_values[field].get("field_values", [])
                    values = [str(v.get("value", "")) for v in fv]
                    print(f"  {field}: {', '.join(values)[:50]}")
        else:
            print("  (메타데이터 없음 또는 조회 실패)")

        # 7. Dry run 또는 실행
        if not args.execute:
            print("\n[DRY RUN] 업데이트를 실행하지 않습니다.")
            print("\n실제 업데이트를 실행하려면:")
            print(f"  python scripts/test_iconik_migration.py --execute --row {args.row}")
            return

        # 8. 메타데이터 업데이트
        print("\n[Executing] Updating metadata...")
        result = api.update_metadata(asset_id, view_id, metadata_payload)
        print("[OK] 메타데이터 업데이트 성공!")

        # 9. 업데이트 후 확인
        print(f"\n[After] Updated metadata:")
        updated = api.get_metadata(asset_id, view_id)
        if updated:
            updated_values = updated.get("metadata_values", {})
            for field in FIELD_MAPPING.values():
                if field in updated_values:
                    fv = updated_values[field].get("field_values", [])
                    values = [str(v.get("value", "")) for v in fv]
                    print(f"  {field}: {', '.join(values)[:50]}")

    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    finally:
        api.close()

    print("\n" + "=" * 60)
    print("Migration test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
