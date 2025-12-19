#!/usr/bin/env python
"""Phase 2: CategoryEntry PokerGO 매칭 실행.

CategoryEntry를 PokerGO 에피소드와 매칭하고 결과를 업데이트합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.nams.api.services.category_matching import (
    run_full_matching_pipeline,
    get_matching_summary,
    MATCH_TYPE_EXACT,
    MATCH_TYPE_PARTIAL,
    MATCH_TYPE_NONE,
)
from src.nams.api.database import get_db_context


def main():
    """메인 실행."""
    print("=" * 60)
    print("Phase 2: CategoryEntry PokerGO 매칭")
    print("=" * 60)

    # 전체 파이프라인 실행
    print("\n[Step 1] 매칭 파이프라인 실행...")
    results = run_full_matching_pipeline(clear_existing=True)

    # 매칭 결과
    matching = results['matching']
    print(f"\n[매칭 결과]")
    print(f"  - 전체 Entry: {matching['total_entries']}개")
    print(f"  - 처리됨: {matching['processed']}개")
    print(f"  - EXACT: {matching['exact']}개")
    print(f"  - PARTIAL: {matching['partial']}개")
    print(f"  - NONE: {matching['none']}개")
    print(f"  - 스킵: {matching['skipped']}개")

    # 제목 업데이트 결과
    titles = results['titles']
    print(f"\n[제목 업데이트]")
    print(f"  - 업데이트: {titles['updated']}개")
    print(f"  - 유지: {titles['kept']}개")

    # Summary
    summary = results['summary']
    print(f"\n[매칭 현황 요약]")
    print(f"  - 전체 Entry: {summary['total_entries']}개")

    print(f"\n  [매칭 유형별]")
    for mt, cnt in summary['by_match_type'].items():
        pct = cnt / summary['total_entries'] * 100 if summary['total_entries'] > 0 else 0
        print(f"    - {mt}: {cnt}개 ({pct:.1f}%)")

    print(f"\n  [Source별]")
    for src, cnt in summary['by_source'].items():
        pct = cnt / summary['total_entries'] * 100 if summary['total_entries'] > 0 else 0
        print(f"    - {src}: {cnt}개 ({pct:.1f}%)")

    print(f"\n  검증 필요 (PARTIAL, unverified): {summary['verification_needed']}개")

    # 상세 검증
    print("\n" + "=" * 60)
    print("상세 검증")
    print("=" * 60)

    with get_db_context() as db:
        from src.nams.api.database.models import CategoryEntry, Category

        # EXACT 샘플
        print(f"\n[EXACT 매칭 샘플 (5개)]")
        exact_samples = db.query(CategoryEntry).filter(
            CategoryEntry.match_type == MATCH_TYPE_EXACT
        ).limit(5).all()
        for e in exact_samples:
            print(f"  - {e.entry_code}")
            print(f"    NAS: {e.display_title}")
            print(f"    PokerGO: {e.pokergo_title}")
            print(f"    Score: {e.match_score:.2f}")

        # PARTIAL 샘플
        print(f"\n[PARTIAL 매칭 샘플 (5개)]")
        partial_samples = db.query(CategoryEntry).filter(
            CategoryEntry.match_type == MATCH_TYPE_PARTIAL
        ).limit(5).all()
        for e in partial_samples:
            print(f"  - {e.entry_code}")
            print(f"    NAS: {e.display_title}")
            print(f"    PokerGO: {e.pokergo_title}")
            print(f"    Score: {e.match_score:.2f}")

        # NONE 샘플
        print(f"\n[NONE (자체 생성) 샘플 (5개)]")
        none_samples = db.query(CategoryEntry).filter(
            CategoryEntry.match_type == MATCH_TYPE_NONE
        ).limit(5).all()
        for e in none_samples:
            cat = db.query(Category).filter(Category.id == e.category_id).first()
            print(f"  - {e.entry_code}")
            print(f"    Category: {cat.name if cat else 'N/A'}")
            print(f"    Title: {e.display_title}")

    print("\n" + "=" * 60)
    print("[SUCCESS] Phase 2 매칭 완료!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
