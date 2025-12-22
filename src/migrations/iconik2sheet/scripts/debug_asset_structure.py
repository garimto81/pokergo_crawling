"""Debug Asset structure - Subclip의 parent_id 필드 확인."""

import json
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_settings
import httpx


def debug_asset_structure(asset_id: str) -> None:
    """Debug asset structure to find parent_id field."""
    print("=" * 70)
    print(f"Asset 구조 분석: {asset_id}")
    print("=" * 70)

    settings = get_settings()

    headers = {
        "App-ID": settings.iconik.app_id,
        "Auth-Token": settings.iconik.auth_token,
        "Content-Type": "application/json",
    }

    base_url = settings.iconik.base_url

    # 1. Asset 전체 응답 조회
    print("\n[1] Asset 전체 응답 조회")
    with httpx.Client(base_url=base_url, headers=headers, timeout=30) as client:
        response = client.get(f"/API/assets/v1/assets/{asset_id}/")
        response.raise_for_status()
        asset_data = response.json()

    # 모든 필드 출력
    print("\n모든 필드:")
    for key, value in sorted(asset_data.items()):
        # 긴 값은 잘라서 출력
        str_value = str(value)
        if len(str_value) > 100:
            str_value = str_value[:100] + "..."
        print(f"  {key}: {str_value}")

    # 2. Parent 관련 필드 확인
    print("\n[2] Parent 관련 필드 확인")
    parent_fields = ["parent_id", "parent_asset_id", "parent", "source_asset_id", "original_asset_id"]
    for field in parent_fields:
        value = asset_data.get(field)
        if value:
            print(f"  ✓ {field}: {value}")
        else:
            print(f"  ✗ {field}: (없음)")

    # 3. Type 관련 필드 확인
    print("\n[3] Type 관련 필드 확인")
    type_fields = ["type", "asset_type", "object_type", "is_subclip"]
    for field in type_fields:
        value = asset_data.get(field)
        if value:
            print(f"  ✓ {field}: {value}")
        else:
            print(f"  ✗ {field}: (없음)")

    # 4. 시간 관련 필드 확인
    print("\n[4] 시간/타임코드 관련 필드 확인")
    time_fields = ["time_start", "time_end", "in_point", "out_point", "offset", "duration", "time_base"]
    for field in time_fields:
        value = asset_data.get(field)
        if value is not None:
            print(f"  ✓ {field}: {value}")
        else:
            print(f"  ✗ {field}: (없음)")

    # 5. 버전 관련 필드 확인
    print("\n[5] 버전 관련 필드 확인")
    if "versions" in asset_data:
        versions = asset_data["versions"]
        print(f"  versions: {len(versions)}개")
        for i, ver in enumerate(versions[:2]):  # 최대 2개만
            print(f"    [{i}] id={ver.get('id', 'N/A')}, source_asset_id={ver.get('source_asset_id', 'N/A')}")

    # 6. Relations 엔드포인트 시도
    print("\n[6] Relations/Relationships 엔드포인트 시도")
    with httpx.Client(base_url=base_url, headers=headers, timeout=30) as client:
        try:
            response = client.get(f"/API/assets/v1/assets/{asset_id}/relations/")
            if response.status_code == 200:
                relations = response.json()
                print(f"  Relations: {json.dumps(relations, indent=2, default=str)[:500]}")
            else:
                print(f"  Relations: HTTP {response.status_code}")
        except Exception as e:
            print(f"  Relations: Error - {e}")

        try:
            response = client.get(f"/API/assets/v1/assets/{asset_id}/relationships/")
            if response.status_code == 200:
                relationships = response.json()
                print(f"  Relationships: {json.dumps(relationships, indent=2, default=str)[:500]}")
            else:
                print(f"  Relationships: HTTP {response.status_code}")
        except Exception as e:
            print(f"  Relationships: Error - {e}")


if __name__ == "__main__":
    # WS11_ME03_NB_subclip_DN_interview
    asset_id = "623b5a30-63b9-11f0-b2c5-9e2846c90c6f"
    debug_asset_structure(asset_id)
