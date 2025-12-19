#!/usr/bin/env python
"""Phase 3: AI 제목 생성 실행.

NONE 항목에 대해 제목 생성을 실행하고 DB에 저장합니다.
"""
import sys
import argparse
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
    parser = argparse.ArgumentParser(description='AI 제목 생성')
    parser.add_argument('--apply', action='store_true', help='실제 DB에 적용')
    parser.add_argument('--use-ai', action='store_true', default=True, help='AI 생성 사용')
    parser.add_argument('--pattern-only', action='store_true', help='패턴 기반만 사용')
    args = parser.parse_args()

    use_ai = not args.pattern_only
    dry_run = not args.apply

    print("=" * 60)
    print("Phase 3: 제목 생성")
    print("=" * 60)
    print(f"  Mode: {'실제 적용' if args.apply else 'Dry-run (테스트)'}")
    print(f"  AI 사용: {'Yes' if use_ai else 'No (패턴만)'}")

    with get_db_context() as db:
        # 1. 일관성 개선 (모든 항목)
        print("\n[Step 1] 일관성 개선 (대소문자, 약어 표준화)...")
        consistency_result = improve_all_titles(db, dry_run=dry_run)

        print(f"  - 전체: {consistency_result['total']}개")
        print(f"  - 개선{'됨' if args.apply else ' 예정'}: {consistency_result['improved']}개")

        # 2. NONE 항목 제목 생성
        print("\n[Step 2] NONE 항목 제목 생성...")
        result = generate_titles_for_none_entries(db, use_ai=use_ai, dry_run=dry_run)

        print(f"  - 전체 NONE: {result['total']}개")
        print(f"  - AI 생성: {result['ai_generated']}개")
        print(f"  - 패턴 생성: {result['pattern_generated']}개")
        print(f"  - 개선{'됨' if args.apply else ' 예정'}: {result['improved']}개")
        print(f"  - 유지: {result['unchanged']}개")

        if result['samples']:
            print("\n  [샘플 (최대 10개)]")
            for s in result['samples'][:10]:
                print(f"    - {s['entry_code']}")
                print(f"      OLD: {s['old']}")
                print(f"      NEW: {s['new']}")

    print("\n" + "=" * 60)
    if args.apply:
        print("[SUCCESS] Phase 3 제목 생성 완료!")
    else:
        print("[DRY-RUN] 테스트 완료. 실제 적용: --apply 옵션 추가")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
