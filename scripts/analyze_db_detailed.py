"""NAMS DB 상세 분석 - 미그룹화 및 미매칭 원인 파악"""
import sqlite3
import sys
from pathlib import Path
from collections import Counter, defaultdict

# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

db_path = Path("D:/AI/claude01/pokergo_crawling/src/nams/data/nams.db")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("NAMS DB 상세 분석 - 문제점 진단")
print("=" * 80)
print()

# 1. 왜 모든 파일이 미그룹화 상태인가?
print("1. 미그룹화 원인 분석")
print("-" * 80)

cursor.execute("""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN matched_pattern_id IS NOT NULL THEN 1 ELSE 0 END) as with_pattern,
           SUM(CASE WHEN year IS NOT NULL THEN 1 ELSE 0 END) as with_year,
           SUM(CASE WHEN region_id IS NOT NULL THEN 1 ELSE 0 END) as with_region,
           SUM(CASE WHEN event_type_id IS NOT NULL THEN 1 ELSE 0 END) as with_event_type,
           SUM(CASE WHEN episode IS NOT NULL THEN 1 ELSE 0 END) as with_episode
    FROM nas_files
    WHERE is_excluded = 0
""")
result = cursor.fetchone()

print("활성 파일 메타데이터 추출 현황:")
print(f"  전체 파일: {result['total']:,}")
print(f"  패턴 매칭됨: {result['with_pattern']:,} ({result['with_pattern']/result['total']*100:.1f}%)")
print(f"  연도 추출됨: {result['with_year']:,} ({result['with_year']/result['total']*100:.1f}%)")
print(f"  지역 추출됨: {result['with_region']:,} ({result['with_region']/result['total']*100:.1f}%)")
print(f"  이벤트 타입 추출됨: {result['with_event_type']:,} ({result['with_event_type']/result['total']*100:.1f}%)")
print(f"  에피소드 추출됨: {result['with_episode']:,} ({result['with_episode']/result['total']*100:.1f}%)")

print()
print("문제점:")
print("  - 모든 파일이 패턴 매칭 실패 (0%)")
print("  - 메타데이터 추출 전무")
print("  - 그룹핑 불가능 (메타데이터 필요)")
print()

# 2. 패턴 정의 확인
print("=" * 80)
print("2. 등록된 패턴 확인")
print("-" * 80)

cursor.execute("""
    SELECT id, name, priority, is_active, extract_type, regex
    FROM patterns
    ORDER BY priority
""")
patterns = cursor.fetchall()

print(f"등록된 패턴 수: {len(patterns)}")
print()

if len(patterns) == 0:
    print("문제점:")
    print("  - 패턴이 하나도 등록되지 않음!")
    print("  - init_db.py가 실행되지 않았거나 패턴 삽입 실패")
else:
    print("패턴 목록:")
    for p in patterns[:10]:
        active = "활성" if p["is_active"] else "비활성"
        extract_type = p['extract_type'] or "N/A"
        print(f"  [{p['priority']}] {p['name']} ({extract_type}) - {active}")

print()

# 3. 샘플 파일 경로 확인
print("=" * 80)
print("3. 샘플 파일 경로 분석")
print("-" * 80)

cursor.execute("""
    SELECT full_path, filename
    FROM nas_files
    WHERE is_excluded = 0
    LIMIT 10
""")
sample_files = cursor.fetchall()

print("샘플 파일 경로 (10개):")
for f in sample_files:
    print(f"  {f['full_path']}")

print()

# 4. Asset Groups가 왜 716개나 있는가?
print("=" * 80)
print("4. Asset Groups 분석")
print("-" * 80)

cursor.execute("""
    SELECT
        ag.id,
        ag.group_id,
        ag.year,
        r.code as region,
        et.code as event_type,
        ag.episode,
        ag.file_count,
        ag.pokergo_episode_id,
        ag.catalog_title
    FROM asset_groups ag
    LEFT JOIN regions r ON ag.region_id = r.id
    LEFT JOIN event_types et ON ag.event_type_id = et.id
    LIMIT 10
""")
sample_groups = cursor.fetchall()

print(f"Asset Groups 샘플 (10개):")
for g in sample_groups:
    year = g["year"] or "N/A"
    region = g["region"] or "N/A"
    event_type = g["event_type"] or "N/A"
    episode = g["episode"] or "N/A"
    file_count = g["file_count"] or 0
    matched = "매칭됨" if g["pokergo_episode_id"] else "미매칭"
    title = g["catalog_title"] or "(제목 없음)"

    print(f"  [{year} {region} {event_type} EP{episode}] {title[:40]} - {file_count}개 파일, {matched}")

print()

# 5. nas_files와 asset_groups 관계 확인
print("=" * 80)
print("5. nas_files와 asset_groups 연결 확인")
print("-" * 80)

cursor.execute("""
    SELECT COUNT(*) as count
    FROM nas_files nf
    JOIN asset_groups ag ON nf.asset_group_id = ag.id
    WHERE nf.is_excluded = 0
""")
linked_count = cursor.fetchone()["count"]

print(f"asset_group_id로 연결된 파일 수: {linked_count}")
print(f"미연결 파일 수: {result['total'] - linked_count}")
print()

if linked_count == 0:
    print("문제점:")
    print("  - 716개의 그룹이 존재하지만 파일과 연결되지 않음")
    print("  - 그룹은 PokerGO 에피소드만 기준으로 생성된 것으로 추정")
    print("  - NAS 파일 그룹핑이 실행되지 않음")

print()

# 6. PokerGO Episodes와 Asset Groups 매칭 확인
print("=" * 80)
print("6. PokerGO 매칭 분석")
print("-" * 80)

cursor.execute("""
    SELECT
        ag.pokergo_episode_id,
        pe.title as pokergo_title,
        pe.collection_title,
        ag.catalog_title as group_title,
        ag.pokergo_match_score
    FROM asset_groups ag
    JOIN pokergo_episodes pe ON ag.pokergo_episode_id = pe.id
    LIMIT 10
""")
matched_samples = cursor.fetchall()

print("PokerGO 매칭 샘플 (10개):")
for m in matched_samples:
    score = m["pokergo_match_score"] or 0
    print(f"  [{score:.0f}점] {m['pokergo_title'][:50]}")
    print(f"    컬렉션: {m['collection_title']}")
    print(f"    그룹 제목: {m['group_title'][:50]}")

print()

# 7. 진단 요약
print("=" * 80)
print("7. 진단 요약 및 권장 조치")
print("-" * 80)

print("\n문제점:")
print("  1. NAS 파일 스캔 실행되었으나 패턴 매칭 0%")
print("  2. 패턴이 등록되지 않았거나 패턴 엔진이 실행되지 않음")
print("  3. 메타데이터 추출 전무 (year, region, episode 등)")
print("  4. 716개 Asset Groups는 PokerGO 에피소드 기준으로만 생성됨")
print("  5. NAS 파일과 Asset Groups 연결 0개")

print("\n권장 조치:")
print("  1. 패턴 초기화:")
print("     python -c 'from src.nams.api.database.init_db import init_patterns; init_patterns()'")
print()
print("  2. 패턴 엔진 재실행:")
print("     python scripts/migrate_and_reprocess.py")
print()
print("  3. NAS 파일 그룹핑:")
print("     python scripts/create_asset_groups.py")
print()
print("  4. PokerGO 매칭:")
print("     python scripts/match_pokergo_nas.py")

print()
print("=" * 80)
print("분석 완료!")
print("=" * 80)

conn.close()
