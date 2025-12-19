"""NAMS DB 데이터 현황 분석 스크립트"""
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
print("NAMS DB 데이터 현황 분석")
print("=" * 80)
print()

# 1. nas_files 테이블 현황
print("1. NAS Files 현황")
print("-" * 80)

# 전체 파일 수
cursor.execute("SELECT COUNT(*) FROM nas_files")
total_files = cursor.fetchone()[0]
print(f"전체 파일 수: {total_files:,}")

# 제외된 파일 수
cursor.execute("SELECT COUNT(*) FROM nas_files WHERE is_excluded = 1")
excluded_files = cursor.fetchone()[0]
print(f"제외된 파일 수: {excluded_files:,}")

# 활성 파일 수
active_files = total_files - excluded_files
print(f"활성 파일 수: {active_files:,}")

# 역할별 파일 수
cursor.execute("""
    SELECT
        role,
        COUNT(*) as count
    FROM nas_files
    WHERE is_excluded = 0
    GROUP BY role
""")
roles = cursor.fetchall()
print()
print("역할별 분포 (활성 파일만):")
for row in roles:
    role = row["role"] or "NULL"
    print(f"  {role}: {row['count']:,}")

# 그룹 할당 현황
cursor.execute("""
    SELECT
        CASE
            WHEN asset_group_id IS NOT NULL THEN 'Grouped'
            ELSE 'Ungrouped'
        END as group_status,
        COUNT(*) as count
    FROM nas_files
    WHERE is_excluded = 0
    GROUP BY group_status
""")
group_status = cursor.fetchall()
print()
print("그룹 할당 현황:")
for row in group_status:
    print(f"  {row['group_status']}: {row['count']:,}")

# 패턴 매칭 현황
cursor.execute("""
    SELECT
        CASE
            WHEN matched_pattern_id IS NOT NULL THEN 'Matched Pattern'
            ELSE 'No Pattern Match'
        END as pattern_status,
        COUNT(*) as count
    FROM nas_files
    WHERE is_excluded = 0
    GROUP BY pattern_status
""")
pattern_status = cursor.fetchall()
print()
print("패턴 매칭 현황:")
for row in pattern_status:
    print(f"  {row['pattern_status']}: {row['count']:,}")

# 확장자별 분포
cursor.execute("""
    SELECT
        extension,
        COUNT(*) as count
    FROM nas_files
    WHERE is_excluded = 0
    GROUP BY extension
    ORDER BY count DESC
    LIMIT 10
""")
extensions = cursor.fetchall()
print()
print("확장자별 분포 (Top 10):")
for row in extensions:
    ext = row["extension"] or "(없음)"
    print(f"  {ext}: {row['count']:,}")

print()
print("=" * 80)
print("2. PokerGO Episodes 현황")
print("-" * 80)

cursor.execute("SELECT COUNT(*) FROM pokergo_episodes")
total_episodes = cursor.fetchone()[0]
print(f"전체 에피소드 수: {total_episodes:,}")

# 컬렉션별 분포
cursor.execute("""
    SELECT
        collection_title,
        COUNT(*) as count
    FROM pokergo_episodes
    GROUP BY collection_title
    ORDER BY count DESC
    LIMIT 10
""")
collections = cursor.fetchall()
print()
print("컬렉션별 분포 (Top 10):")
for row in collections:
    title = row["collection_title"] or "(없음)"
    print(f"  {title}: {row['count']:,}")

print()
print("=" * 80)
print("3. Asset Groups 현황")
print("-" * 80)

cursor.execute("SELECT COUNT(*) FROM asset_groups")
total_groups = cursor.fetchone()[0]
print(f"전체 그룹 수: {total_groups:,}")

# PokerGO 매칭 현황
cursor.execute("""
    SELECT
        CASE
            WHEN pokergo_episode_id IS NOT NULL THEN 'Matched'
            ELSE 'Unmatched'
        END as match_status,
        COUNT(*) as count
    FROM asset_groups
    GROUP BY match_status
""")
match_status = cursor.fetchall()
print()
print("PokerGO 매칭 현황:")
for row in match_status:
    print(f"  {row['match_status']}: {row['count']:,}")

# 백업 존재 현황
cursor.execute("""
    SELECT
        CASE
            WHEN has_backup = 1 THEN 'Has Backup'
            ELSE 'No Backup'
        END as backup_status,
        COUNT(*) as count
    FROM asset_groups
    GROUP BY backup_status
""")
backup_status = cursor.fetchall()
print()
print("백업 존재 현황:")
for row in backup_status:
    print(f"  {row['backup_status']}: {row['count']:,}")

# 매치 카테고리별 분포
cursor.execute("""
    SELECT
        match_category,
        COUNT(*) as count
    FROM asset_groups
    WHERE match_category IS NOT NULL
    GROUP BY match_category
    ORDER BY count DESC
""")
categories = cursor.fetchall()
print()
print("매치 카테고리별 분포:")
for row in categories:
    print(f"  {row['match_category']}: {row['count']:,}")

# 매치 스코어 분포
cursor.execute("""
    SELECT
        CASE
            WHEN pokergo_match_score >= 90 THEN 'Excellent (90-100)'
            WHEN pokergo_match_score >= 80 THEN 'Good (80-89)'
            WHEN pokergo_match_score >= 70 THEN 'Fair (70-79)'
            WHEN pokergo_match_score >= 60 THEN 'Poor (60-69)'
            ELSE 'Bad (<60)'
        END as score_range,
        COUNT(*) as count,
        AVG(pokergo_match_score) as avg_score
    FROM asset_groups
    WHERE pokergo_episode_id IS NOT NULL AND pokergo_match_score IS NOT NULL
    GROUP BY score_range
    ORDER BY avg_score DESC
""")
score_dist = cursor.fetchall()
print()
print("매치 스코어 분포 (매칭된 그룹만):")
for row in score_dist:
    print(f"  {row['score_range']}: {row['count']:,} (평균: {row['avg_score']:.1f})")

print()
print("=" * 80)
print("4. 미그룹화 파일 패턴 분석")
print("-" * 80)

# 미그룹화 파일 가져오기
cursor.execute("""
    SELECT full_path
    FROM nas_files
    WHERE is_excluded = 0
      AND asset_group_id IS NULL
""")
ungrouped_files = cursor.fetchall()

print(f"미그룹화 파일 수: {len(ungrouped_files):,}")
print()

# 파일명 패턴 분석
pattern_counter = Counter()
path_patterns = defaultdict(list)

for row in ungrouped_files:
    file_path = row["full_path"]
    filename = Path(file_path).name

    # 확장자 추출
    ext = Path(filename).suffix.lower()

    # 패턴 분류
    filename_lower = filename.lower()
    if "wsop" in filename_lower:
        if "main event" in filename_lower or " me " in filename_lower:
            pattern = f"WSOP ME - {ext}"
        elif "europe" in filename_lower:
            pattern = f"WSOP EU - {ext}"
        elif "apac" in filename_lower or "asia" in filename_lower:
            pattern = f"WSOP APAC - {ext}"
        else:
            pattern = f"WSOP Other - {ext}"
    elif "wpt" in filename_lower:
        pattern = f"WPT - {ext}"
    elif "hpl" in filename_lower or "high stakes" in filename_lower:
        pattern = f"High Stakes - {ext}"
    elif "poker after dark" in filename_lower:
        pattern = f"Poker After Dark - {ext}"
    elif ext in [".mp4", ".mkv", ".avi", ".mov", ".ts"]:
        pattern = f"Video (Unknown) - {ext}"
    elif ext in [".srt", ".sub", ".ass", ".vtt"]:
        pattern = f"Subtitle - {ext}"
    elif ext in [".jpg", ".png", ".jpeg"]:
        pattern = f"Image - {ext}"
    else:
        pattern = f"Other - {ext}"

    pattern_counter[pattern] += 1
    if len(path_patterns[pattern]) < 3:
        path_patterns[pattern].append(filename)

print("미그룹화 파일 패턴별 분포:")
for pattern, count in pattern_counter.most_common(20):
    print(f"  {pattern}: {count:,}")
    # 샘플 파일명 출력
    for sample in path_patterns[pattern][:2]:
        # 파일명이 너무 길면 잘라서 표시
        if len(sample) > 70:
            print(f"    예시: {sample[:70]}...")
        else:
            print(f"    예시: {sample}")

print()
print("=" * 80)
print("5. PokerGO 미매칭 그룹 분석")
print("-" * 80)

# 미매칭 그룹 가져오기
cursor.execute("""
    SELECT
        ag.id,
        ag.catalog_title,
        ag.year,
        r.code as region,
        et.code as event_type,
        ag.episode,
        ag.file_count
    FROM asset_groups ag
    LEFT JOIN regions r ON ag.region_id = r.id
    LEFT JOIN event_types et ON ag.event_type_id = et.id
    WHERE ag.pokergo_episode_id IS NULL
    ORDER BY ag.year DESC, ag.episode
    LIMIT 20
""")
unmatched_groups = cursor.fetchall()

print(f"미매칭 그룹 수: (샘플 20개)")
print()
for row in unmatched_groups:
    year = row["year"] or "N/A"
    region = row["region"] or "N/A"
    event_type = row["event_type"] or "N/A"
    episode = row["episode"] or "N/A"
    title = row["catalog_title"] or "(제목 없음)"
    file_count = row["file_count"] or 0

    print(f"  [{year} {region} {event_type} EP{episode}] {title[:50]} ({file_count}개 파일)")

print()
print("=" * 80)
print("분석 완료!")
print("=" * 80)

conn.close()
