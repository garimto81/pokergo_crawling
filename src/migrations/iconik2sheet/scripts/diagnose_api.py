"""API 응답 구조 진단 스크립트.

iconik 메타데이터 추출 문제를 진단하기 위해:
1. 단일 Asset의 메타데이터 API 응답 구조 출력
2. Segment API 응답 구조 출력
3. 실제 필드명과 METADATA_FIELD_MAP 비교
"""

import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from config.settings import get_settings
from iconik import IconikClient


def main() -> None:
    """Diagnose API response structure."""
    print("=" * 60)
    print("Iconik API 응답 구조 진단")
    print("=" * 60)

    settings = get_settings()
    view_id = settings.iconik.metadata_view_id if settings.iconik else None

    print("\n[설정 확인]")
    print(f"  ICONIK_METADATA_VIEW_ID: {view_id or '(미설정)'}")

    if not view_id:
        print("\n⚠️ ICONIK_METADATA_VIEW_ID가 설정되지 않았습니다!")
        print("   .env 파일에 ICONIK_METADATA_VIEW_ID를 설정하세요.")

    iconik = IconikClient()

    try:
        # 1. 첫 번째 Asset 가져오기
        print("\n[1] Asset 조회...")
        first_asset = None
        for asset in iconik.get_all_assets():
            first_asset = asset
            break

        if not first_asset:
            print("   ⚠️ Asset이 없습니다!")
            return

        print(f"   Asset ID: {first_asset.id}")
        print(f"   Title: {first_asset.title}")

        # 2. Segment API 응답 확인
        print("\n[2] Segment API 응답 구조...")
        try:
            segments_raw = iconik.client.get(
                f"/assets/v1/assets/{first_asset.id}/segments/"
            )
            segments_data = segments_raw.json()
            print("\n   전체 응답 구조:")
            print(json.dumps(segments_data, indent=2, ensure_ascii=False)[:2000])

            if segments_data.get("objects"):
                first_seg = segments_data["objects"][0]
                print("\n   첫 번째 Segment의 키:")
                for key in sorted(first_seg.keys()):
                    print(f"     - {key}: {type(first_seg[key]).__name__} = {first_seg[key]}")
        except Exception as e:
            print(f"   ⚠️ Segment 조회 실패: {e}")

        # 3. Metadata API 응답 확인
        if view_id:
            print(f"\n[3] Metadata API 응답 구조 (view_id: {view_id})...")
            try:
                metadata_raw = iconik.client.get(
                    f"/metadata/v1/assets/{first_asset.id}/views/{view_id}/"
                )
                metadata_data = metadata_raw.json()
                print("\n   전체 응답 구조 (상위 키):")
                for key in sorted(metadata_data.keys()):
                    value = metadata_data[key]
                    if isinstance(value, dict):
                        print(f"     - {key}: dict ({len(value)} items)")
                    elif isinstance(value, list):
                        print(f"     - {key}: list ({len(value)} items)")
                    else:
                        print(f"     - {key}: {type(value).__name__} = {value}")

                # metadata_values 확인
                if "metadata_values" in metadata_data:
                    mv = metadata_data["metadata_values"]
                    print(f"\n   metadata_values 내부 키 ({len(mv)}개):")
                    for field_name in sorted(mv.keys()):
                        field_data = mv[field_name]
                        if isinstance(field_data, dict):
                            field_values = field_data.get("field_values", [])
                            if field_values:
                                # 첫 번째 값만 표시
                                first_val = field_values[0].get("value", field_values[0])
                                print(f"     - {field_name}: {first_val}")
                            else:
                                print(f"     - {field_name}: (empty)")
                        else:
                            print(f"     - {field_name}: {field_data}")
                else:
                    print("\n   ⚠️ 'metadata_values' 키가 없습니다!")
                    print("   전체 응답:")
                    print(json.dumps(metadata_data, indent=2, ensure_ascii=False)[:3000])

            except Exception as e:
                print(f"   ⚠️ Metadata 조회 실패: {e}")
        else:
            print("\n[3] Metadata API - view_id 없어서 건너뜀")

        # 4. 메타데이터 뷰 목록 확인
        print("\n[4] 사용 가능한 Metadata Views...")
        try:
            views = iconik.get_metadata_views()
            print(f"   총 {len(views)}개 뷰:")
            for v in views[:10]:  # 처음 10개만
                print(f"     - {v.get('id')}: {v.get('name')}")
        except Exception as e:
            print(f"   ⚠️ Views 조회 실패: {e}")

        # 5. 특정 뷰 상세 정보
        if view_id:
            print(f"\n[5] 지정된 View 상세 정보 (view_id: {view_id})...")
            try:
                view_detail = iconik.get_metadata_view(view_id)
                print(f"   Name: {view_detail.get('name')}")
                print(f"   Description: {view_detail.get('description')}")
                view_fields = view_detail.get("view_fields", [])
                print(f"   Fields ({len(view_fields)}개):")
                for field in view_fields[:20]:  # 처음 20개만
                    name = field.get("name") or field.get("label") or field.get("field_name")
                    print(f"     - {name}")
            except Exception as e:
                print(f"   ⚠️ View 상세 조회 실패: {e}")

    finally:
        iconik.close()

    print("\n" + "=" * 60)
    print("진단 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
