"""
PokerGO-NAS WSOP Matching Script
================================
양쪽 데이터를 매칭하고 전체 로그 생성
"""

import json
import re
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

# 경로 설정
WSOP_DIR = Path("D:/AI/claude01/pokergo_crawling/data/pokergo/wsop_only")
OUTPUT_DIR = WSOP_DIR / "matching_results"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_data():
    """데이터 로드"""
    with open(WSOP_DIR / "episodes.json", "r", encoding="utf-8") as f:
        pokergo_data = json.load(f)

    with open(WSOP_DIR / "nas_wsop_2011_2025.json", "r", encoding="utf-8") as f:
        nas_data = json.load(f)

    return pokergo_data["episodes"], nas_data["files"]


def extract_year_from_pokergo(ep):
    """PokerGO 에피소드에서 연도 추출"""
    coll = ep.get("collection_title", "")
    match = re.search(r"20\d{2}", coll)
    if match:
        return int(match.group())
    return None


def extract_episode_info(title):
    """에피소드 번호 및 타입 추출"""
    title_upper = title.upper()

    # 에피소드 번호 추출
    ep_match = re.search(r"EPISODE\s*(\d+)", title_upper)
    if not ep_match:
        ep_match = re.search(r"EP\.?\s*(\d+)", title_upper)
    if not ep_match:
        ep_match = re.search(r"E(\d+)", title_upper)

    ep_num = int(ep_match.group(1)) if ep_match else None

    # 타입 추출
    if "MAIN EVENT" in title_upper or "_ME" in title_upper:
        event_type = "MAIN_EVENT"
    elif "BRACELET" in title_upper:
        event_type = "BRACELET"
    elif "HIGH ROLLER" in title_upper:
        event_type = "HIGH_ROLLER"
    elif "LIVESTREAM" in title_upper:
        event_type = "LIVESTREAM"
    else:
        event_type = "OTHER"

    # Day 추출
    day_match = re.search(r"DAY\s*(\d+[A-Z]?)", title_upper)
    day = day_match.group(1) if day_match else None

    return {
        "episode_num": ep_num,
        "event_type": event_type,
        "day": day
    }


def normalize_title(title):
    """제목 정규화 (비교용)"""
    # 소문자 변환
    t = title.lower()
    # 특수문자 제거
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    # 연속 공백 제거
    t = re.sub(r"\s+", " ", t).strip()
    return t


def similarity_score(str1, str2):
    """두 문자열 유사도 점수 (0-100)"""
    return int(SequenceMatcher(None, str1, str2).ratio() * 100)


def match_files(pokergo_eps, nas_files):
    """매칭 수행"""
    results = []
    matched_nas_ids = set()
    matched_pg_ids = set()

    # 연도별로 그룹화
    pg_by_year = {}
    for ep in pokergo_eps:
        year = extract_year_from_pokergo(ep)
        if year:
            if year not in pg_by_year:
                pg_by_year[year] = []
            pg_by_year[year].append(ep)

    nas_by_year = {}
    for f in nas_files:
        year = f.get("detected_year")
        if year:
            if year not in nas_by_year:
                nas_by_year[year] = []
            nas_by_year[year].append(f)

    # 연도별 매칭
    all_years = sorted(set(list(pg_by_year.keys()) + list(nas_by_year.keys())))

    for year in all_years:
        pg_items = pg_by_year.get(year, [])
        nas_items = nas_by_year.get(year, [])

        # 각 PokerGO 에피소드에 대해 최적 NAS 파일 찾기
        for pg in pg_items:
            pg_info = extract_episode_info(pg.get("title", ""))
            pg_normalized = normalize_title(pg.get("title", ""))

            best_match = None
            best_score = 0

            for nas in nas_items:
                if nas["id"] in matched_nas_ids:
                    continue

                nas_info = extract_episode_info(nas.get("filename", ""))
                nas_normalized = normalize_title(nas.get("filename", ""))

                # 점수 계산
                score = 0

                # 이벤트 타입 일치
                if pg_info["event_type"] == nas_info["event_type"]:
                    score += 40

                # 에피소드 번호 일치
                if pg_info["episode_num"] and nas_info["episode_num"]:
                    if pg_info["episode_num"] == nas_info["episode_num"]:
                        score += 35

                # Day 일치
                if pg_info["day"] and nas_info["day"]:
                    if pg_info["day"] == nas_info["day"]:
                        score += 15

                # 제목 유사도
                title_sim = similarity_score(pg_normalized, nas_normalized)
                score += title_sim * 0.1

                if score > best_score:
                    best_score = score
                    best_match = nas

            # 매칭 임계값 (50점 이상)
            if best_match and best_score >= 50:
                matched_nas_ids.add(best_match["id"])
                matched_pg_ids.add(pg["id"])
                results.append({
                    "year": year,
                    "match_score": round(best_score, 1),
                    "pokergo": {
                        "id": pg["id"],
                        "title": pg.get("title"),
                        "collection": pg.get("collection_title"),
                        "season": pg.get("season_title"),
                        "duration_min": pg.get("duration_min")
                    },
                    "nas": {
                        "id": best_match["id"],
                        "filename": best_match.get("filename"),
                        "directory": best_match.get("directory"),
                        "size_gb": best_match.get("size_gb")
                    }
                })
            else:
                # 매칭 안됨 - PokerGO만
                results.append({
                    "year": year,
                    "match_score": 0,
                    "pokergo": {
                        "id": pg["id"],
                        "title": pg.get("title"),
                        "collection": pg.get("collection_title"),
                        "season": pg.get("season_title"),
                        "duration_min": pg.get("duration_min")
                    },
                    "nas": None
                })

    # 매칭 안된 NAS 파일 추가
    for nas in nas_files:
        if nas["id"] not in matched_nas_ids:
            year = nas.get("detected_year")
            results.append({
                "year": year,
                "match_score": 0,
                "pokergo": None,
                "nas": {
                    "id": nas["id"],
                    "filename": nas.get("filename"),
                    "directory": nas.get("directory"),
                    "size_gb": nas.get("size_gb")
                }
            })

    # 연도, 매칭 여부로 정렬
    results.sort(key=lambda x: (
        x["year"] or 9999,
        0 if x["pokergo"] and x["nas"] else 1,
        x["pokergo"]["title"] if x["pokergo"] else (x["nas"]["filename"] if x["nas"] else "")
    ))

    return results


def generate_log(results):
    """로그 파일 생성"""
    log_lines = []

    # 헤더
    log_lines.append("=" * 140)
    log_lines.append("WSOP MATCHING LOG: PokerGO ↔ NAS")
    log_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_lines.append("=" * 140)

    # 통계
    matched = [r for r in results if r["pokergo"] and r["nas"]]
    pg_only = [r for r in results if r["pokergo"] and not r["nas"]]
    nas_only = [r for r in results if not r["pokergo"] and r["nas"]]

    log_lines.append(f"\nSUMMARY:")
    log_lines.append(f"  Total entries: {len(results)}")
    log_lines.append(f"  Matched: {len(matched)}")
    log_lines.append(f"  PokerGO only (NAS 없음): {len(pg_only)}")
    log_lines.append(f"  NAS only (PokerGO 없음): {len(nas_only)}")
    log_lines.append("")

    # 연도별 테이블
    current_year = None

    for r in results:
        year = r["year"]

        # 연도 구분선
        if year != current_year:
            current_year = year
            log_lines.append("")
            log_lines.append("-" * 140)
            log_lines.append(f"[{year}]")
            log_lines.append("-" * 140)
            log_lines.append(f"{'Score':<6} | {'PokerGO Title':<60} | {'NAS Filename':<65}")
            log_lines.append("-" * 140)

        pg_title = r["pokergo"]["title"][:58] if r["pokergo"] else ""
        nas_file = r["nas"]["filename"][:63] if r["nas"] else ""
        score = f"{r['match_score']:.0f}" if r["match_score"] > 0 else "-"

        log_lines.append(f"{score:<6} | {pg_title:<60} | {nas_file:<65}")

    log_lines.append("")
    log_lines.append("=" * 140)
    log_lines.append("END OF LOG")
    log_lines.append("=" * 140)

    return "\n".join(log_lines)


def main():
    print("Loading data...")
    pokergo_eps, nas_files = load_data()
    print(f"  PokerGO: {len(pokergo_eps)} episodes")
    print(f"  NAS: {len(nas_files)} files")

    print("\nMatching...")
    results = match_files(pokergo_eps, nas_files)

    # 통계
    matched = [r for r in results if r["pokergo"] and r["nas"]]
    pg_only = [r for r in results if r["pokergo"] and not r["nas"]]
    nas_only = [r for r in results if not r["pokergo"] and r["nas"]]

    print(f"\nResults:")
    print(f"  Matched: {len(matched)}")
    print(f"  PokerGO only: {len(pg_only)}")
    print(f"  NAS only: {len(nas_only)}")

    # JSON 저장
    json_path = OUTPUT_DIR / "matching_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "stats": {
                "total": len(results),
                "matched": len(matched),
                "pokergo_only": len(pg_only),
                "nas_only": len(nas_only)
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)
    print(f"\nSaved JSON: {json_path}")

    # 로그 저장
    log_content = generate_log(results)
    log_path = OUTPUT_DIR / "matching_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(log_content)
    print(f"Saved Log: {log_path}")

    # CSV 저장 (스프레드시트용)
    csv_lines = ["Year,Match Score,PokerGO ID,PokerGO Title,NAS ID,NAS Filename,NAS Size GB"]
    for r in results:
        pg_id = r["pokergo"]["id"] if r["pokergo"] else ""
        pg_title = r["pokergo"]["title"].replace(",", ";") if r["pokergo"] else ""
        nas_id = r["nas"]["id"] if r["nas"] else ""
        nas_file = r["nas"]["filename"].replace(",", ";") if r["nas"] else ""
        nas_size = r["nas"]["size_gb"] if r["nas"] else ""
        csv_lines.append(f'{r["year"]},{r["match_score"]},{pg_id},"{pg_title}",{nas_id},"{nas_file}",{nas_size}')

    csv_path = OUTPUT_DIR / "matching_results.csv"
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(csv_lines))
    print(f"Saved CSV: {csv_path}")


if __name__ == "__main__":
    main()
