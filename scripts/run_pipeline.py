#!/usr/bin/env python
"""NAMS 자동화 파이프라인 실행 스크립트 (v2.0).

DB 기반 매칭 시스템으로 업데이트됨.

Usage:
    python scripts/run_pipeline.py --mode full         # 전체 재스캔 + 매칭 + 내보내기
    python scripts/run_pipeline.py --mode incremental  # 증분 스캔 + 매칭 + 내보내기
    python scripts/run_pipeline.py --skip-scan         # 스캔 건너뛰고 매칭 + 내보내기
    python scripts/run_pipeline.py --skip-export       # 내보내기 건너뛰기
    python scripts/run_pipeline.py --match-only        # 매칭만 실행
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

# UTF-8 출력 설정
sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def print_header(title: str):
    """헤더 출력."""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_status(status: str, message: str):
    """상태 메시지 출력."""
    symbols = {"OK": "[OK]", "ERROR": "[ERROR]", "INFO": "[INFO]", "SKIP": "[SKIP]", "WARN": "[WARN]"}
    print(f"{symbols.get(status, '[??]')} {message}")


def run_command(command: list, description: str, timeout: int = 600) -> bool:
    """명령어 실행."""
    print_status("INFO", f"{description}...")
    start_time = time.time()

    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=False,
            text=True,
            timeout=timeout
        )
        elapsed = time.time() - start_time

        if result.returncode == 0:
            print_status("OK", f"{description} 완료 ({elapsed:.1f}초)")
            return True
        else:
            print_status("ERROR", f"{description} 실패 (exit code: {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print_status("ERROR", f"{description} 타임아웃 ({timeout}초)")
        return False
    except Exception as e:
        print_status("ERROR", f"{description} 예외: {e}")
        return False


def phase1_scan(mode: str) -> bool:
    """Phase 1: NAS 스캔."""
    print_header("Phase 1: NAS 스캔")
    return run_command(
        [sys.executable, "scripts/scan_nas.py", "--mode", mode, "--folder", "all"],
        f"NAS 스캔 ({mode} 모드)",
        timeout=1800  # 30분
    )


def phase2_matching() -> bool:
    """Phase 2: PokerGO 매칭."""
    print_header("Phase 2: PokerGO 매칭")

    try:
        from src.nams.api.database.session import get_db_context
        from src.nams.api.database.models import AssetGroup
        from src.nams.api.services.matching import run_matching, update_match_categories, update_catalog_titles, enforce_one_to_one

        # 기존 매칭 초기화
        print_status("INFO", "기존 매칭 초기화...")
        with get_db_context() as db:
            updated = db.query(AssetGroup).update({
                AssetGroup.pokergo_episode_id: None,
                AssetGroup.pokergo_title: None,
                AssetGroup.pokergo_match_score: None,
                AssetGroup.match_category: None,
                AssetGroup.catalog_title: None,  # Reset catalog titles too
            })
            db.commit()
            print_status("OK", f"{updated} 그룹 초기화 완료")

        # 매칭 실행
        print_status("INFO", "PokerGO 매칭 실행...")
        result = run_matching(min_score=0.5)
        print_status("OK", f"매칭 결과: {result}")

        # 1:1 매칭 강제 (중복 제거)
        print_status("INFO", "1:1 매칭 강제 (중복 제거)...")
        with get_db_context() as db:
            one_to_one_result = enforce_one_to_one(db)
            print_status("OK", f"1:1 강제: {one_to_one_result}")

        # 카테고리 업데이트
        print_status("INFO", "매칭 카테고리 업데이트...")
        with get_db_context() as db:
            cat_result = update_match_categories(db)
            print_status("OK", f"카테고리: {cat_result}")

        # Catalog Title 생성 (CLASSIC Era Part 처리)
        print_status("INFO", "Catalog Title 생성...")
        with get_db_context() as db:
            title_result = update_catalog_titles(db)
            print_status("OK", f"Catalog Title: {title_result}")

        return True

    except Exception as e:
        print_status("ERROR", f"매칭 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def phase3_export() -> bool:
    """Phase 3: Google Sheets 내보내기."""
    print_header("Phase 3: Google Sheets 내보내기")
    return run_command(
        [sys.executable, "scripts/export_4sheets.py"],
        "Google Sheets 내보내기",
        timeout=600  # 10분
    )


def print_summary():
    """최종 요약 출력."""
    print_header("파이프라인 요약")

    try:
        from src.nams.api.database.session import get_db_context
        from src.nams.api.database.models import AssetGroup, NasFile

        with get_db_context() as db:
            total_files = db.query(NasFile).count()
            total_groups = db.query(AssetGroup).count()
            matched = db.query(AssetGroup).filter(AssetGroup.match_category == 'MATCHED').count()
            nas_only_historic = db.query(AssetGroup).filter(AssetGroup.match_category == 'NAS_ONLY_HISTORIC').count()
            nas_only_modern = db.query(AssetGroup).filter(AssetGroup.match_category == 'NAS_ONLY_MODERN').count()
            excluded = db.query(NasFile).filter(NasFile.is_excluded == True).count()

            print(f"""
  통합 데이터 요약
  ─────────────────────────────────────

  [NAS 데이터]
    총 파일:           {total_files:,}
    제외 파일:         {excluded:,}

  [그룹화 결과]
    총 그룹:           {total_groups:,}
    MATCHED:           {matched:,}
    NAS_ONLY_HISTORIC: {nas_only_historic:,}
    NAS_ONLY_MODERN:   {nas_only_modern:,}

  [매칭율]
    전체:              {matched / total_groups * 100:.1f}% ({matched}/{total_groups})

  ─────────────────────────────────────
""")

    except Exception as e:
        print_status("WARN", f"요약 생성 실패: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='NAMS 자동화 파이프라인 (v2.0)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
예시:
  python scripts/run_pipeline.py --mode full         전체 재스캔
  python scripts/run_pipeline.py --mode incremental  증분 스캔 (기본)
  python scripts/run_pipeline.py --skip-scan         스캔 건너뛰기
  python scripts/run_pipeline.py --match-only        매칭만 실행
'''
    )
    parser.add_argument(
        '--mode',
        choices=['full', 'incremental'],
        default='incremental',
        help='스캔 모드 (full: 전체 재스캔, incremental: 증분)'
    )
    parser.add_argument(
        '--skip-scan',
        action='store_true',
        help='Phase 1 (NAS 스캔) 건너뛰기'
    )
    parser.add_argument(
        '--skip-match',
        action='store_true',
        help='Phase 2 (PokerGO 매칭) 건너뛰기'
    )
    parser.add_argument(
        '--skip-export',
        action='store_true',
        help='Phase 3 (Google Sheets 내보내기) 건너뛰기'
    )
    parser.add_argument(
        '--match-only',
        action='store_true',
        help='매칭만 실행 (스캔, 내보내기 건너뛰기)'
    )

    args = parser.parse_args()

    # --match-only 처리
    if args.match_only:
        args.skip_scan = True
        args.skip_export = True

    # 시작
    print_header("NAMS 자동화 파이프라인 v2.0")
    print(f"  시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  모드: {args.mode}")
    print(f"  스캔: {'건너뛰기' if args.skip_scan else '실행'}")
    print(f"  매칭: {'건너뛰기' if args.skip_match else '실행'}")
    print(f"  내보내기: {'건너뛰기' if args.skip_export else '실행'}")

    start_time = time.time()
    results = {}

    # Phase 1: NAS 스캔
    if args.skip_scan:
        print_header("Phase 1: NAS 스캔")
        print_status("SKIP", "스캔 건너뛰기")
        results['scan'] = 'SKIPPED'
    else:
        results['scan'] = 'OK' if phase1_scan(args.mode) else 'FAILED'
        if results['scan'] == 'FAILED':
            print_status("ERROR", "스캔 실패로 파이프라인 중단")
            return 1

    # Phase 2: PokerGO 매칭
    if args.skip_match:
        print_header("Phase 2: PokerGO 매칭")
        print_status("SKIP", "매칭 건너뛰기")
        results['match'] = 'SKIPPED'
    else:
        results['match'] = 'OK' if phase2_matching() else 'FAILED'
        if results['match'] == 'FAILED':
            print_status("ERROR", "매칭 실패로 파이프라인 중단")
            return 1

    # Phase 3: Google Sheets 내보내기
    if args.skip_export:
        print_header("Phase 3: Google Sheets 내보내기")
        print_status("SKIP", "내보내기 건너뛰기")
        results['export'] = 'SKIPPED'
    else:
        results['export'] = 'OK' if phase3_export() else 'FAILED'
        if results['export'] == 'FAILED':
            print_status("WARN", "내보내기 실패")
            # 내보내기 실패는 치명적이지 않음

    # 요약
    print_summary()

    # 완료
    elapsed = time.time() - start_time
    print_header("파이프라인 완료")
    print(f"  총 소요 시간: {elapsed:.1f}초")
    print(f"  완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("  결과:")
    for phase, status in results.items():
        status_symbol = "✓" if status == 'OK' else "○" if status == 'SKIPPED' else "✗"
        print(f"    [{status_symbol}] {phase}: {status}")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
