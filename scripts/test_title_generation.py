#!/usr/bin/env python
"""Phase 3: AI 제목 생성 테스트.

NONE 항목에 대해 AI 기반 제목 생성을 테스트합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# .env 로드
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

import os
print(f"[ENV] GOOGLE_API_KEY 설정됨: {'Yes' if os.environ.get('GOOGLE_API_KEY') else 'No'}")

from src.nams.api.database import get_db_context
from src.nams.api.services.title_generation import (
    generate_titles_for_none_entries,
    improve_all_titles,
)


def main():
    """메인 실행."""
    print("=" * 60)
    print("Phase 3: AI 제목 생성 테스트")
    print("=" * 60)

    with get_db_context() as db:
        # 1. 먼저 dry_run으로 테스트
        print("\n[Step 1] Dry-run (패턴 기반)...")
        result = generate_titles_for_none_entries(db, use_ai=False, dry_run=True)

        print(f"  - 전체 NONE: {result['total']}개")
        print(f"  - 개선 예정: {result['improved']}개")
        print(f"  - 패턴 생성: {result['pattern_generated']}개")
        print(f"  - 유지: {result['unchanged']}개")

        if result['samples']:
            print("\n  [샘플 (최대 5개)]")
            for s in result['samples'][:5]:
                print(f"    - {s['entry_code']}")
                print(f"      OLD: {s['old']}")
                print(f"      NEW: {s['new']}")

        # 2. AI 사용 테스트 (dry_run)
        print("\n[Step 2] Dry-run (AI 기반)...")
        try:
            result_ai = generate_titles_for_none_entries(db, use_ai=True, dry_run=True)

            print(f"  - AI 생성: {result_ai['ai_generated']}개")
            print(f"  - 패턴 생성: {result_ai['pattern_generated']}개")

            if result_ai['samples']:
                print("\n  [AI 생성 샘플 (최대 5개)]")
                for s in result_ai['samples'][:5]:
                    print(f"    - {s['entry_code']}")
                    print(f"      OLD: {s['old']}")
                    print(f"      NEW: {s['new']}")
        except Exception as e:
            print(f"  [WARN] AI 생성 실패: {e}")

        # 3. 일관성 개선 테스트 (dry_run)
        print("\n[Step 3] 일관성 개선 (dry_run)...")
        consistency_result = improve_all_titles(db, dry_run=True)

        print(f"  - 전체: {consistency_result['total']}개")
        print(f"  - 개선 예정: {consistency_result['improved']}개")

        if consistency_result['samples']:
            print("\n  [일관성 개선 샘플 (최대 5개)]")
            for s in consistency_result['samples'][:5]:
                print(f"    - {s['entry_code']}")
                print(f"      OLD: {s['old']}")
                print(f"      NEW: {s['new']}")

    print("\n" + "=" * 60)
    print("[SUCCESS] Phase 3 테스트 완료!")
    print("=" * 60)
    print("\n실제 적용하려면: python scripts/run_title_generation.py --apply")

    return 0


if __name__ == "__main__":
    sys.exit(main())
