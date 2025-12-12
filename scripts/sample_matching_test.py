"""
Sample Matching Test - 20개 샘플로 매칭 성공률 분석

PRD-0033 매칭 로직 테스트:
1. YouTube 20개 무작위 추출
2. NAS 전체 파일 대상 매칭
3. 성공률 분석
"""

import json
import random
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# Paths
DATA_DIR = Path("data")
YOUTUBE_VIDEOS = DATA_DIR / "sources/youtube/exports/videos/videos_001.json"
NAS_FILES = DATA_DIR / "sources/nas/nas_files.json"

# ==================== Dictionaries ====================

PLAYER_ALIASES = {
    "phil_hellmuth": ["hellmuth", "phil hellmuth", "poker brat"],
    "daniel_negreanu": ["negreanu", "daniel negreanu", "dnegs", "kidpoker"],
    "phil_ivey": ["ivey", "phil ivey"],
    "tom_dwan": ["dwan", "tom dwan", "durrrr"],
    "patrik_antonius": ["antonius", "patrik antonius"],
    "doug_polk": ["polk", "doug polk"],
    "doyle_brunson": ["brunson", "doyle brunson", "texas dolly"],
    "mike_matusow": ["matusow", "mike matusow", "the mouth"],
    "antonio_esfandiari": ["esfandiari", "antonio esfandiari", "the magician"],
    "shaun_deeb": ["deeb", "shaun deeb"],
    "justin_bonomo": ["bonomo", "justin bonomo"],
    "jeremy_ausmus": ["ausmus", "jeremy ausmus"],
    "landon_tice": ["tice", "landon tice"],
    "eric_persson": ["persson", "eric persson"],
    "garrett_adelstein": ["garrett", "adelstein", "garrett adelstein"],
    "alan_keating": ["keating", "alan keating"],
    "andrew_robl": ["robl", "andrew robl"],
    "matt_berkey": ["berkey", "matt berkey"],
    "brad_owen": ["brad owen", "owen"],
    "maria_ho": ["maria ho", "maria"],
    "jennifer_harman": ["harman", "jennifer harman"],
    "vanessa_selbst": ["selbst", "vanessa selbst"],
    "jason_koon": ["koon", "jason koon"],
    "bryn_kenney": ["bryn kenney", "bryn"],
    "fedor_holz": ["fedor", "holz", "fedor holz"],
    "david_peters": ["david peters", "peters"],
    "chris_moneymaker": ["moneymaker", "chris moneymaker"],
    "johnny_chan": ["johnny chan", "chan"],
    "stu_ungar": ["stu ungar", "ungar"],
    "scotty_nguyen": ["scotty nguyen", "scotty", "nguyen"],
}

EVENT_TYPES = {
    "wsop": ["wsop", "world series of poker", "world series", "bracelet"],
    "hsp": ["high stakes poker", "hsp", "high stakes"],
    "pad": ["poker after dark", "pad"],
    "shrb": ["super high roller bowl", "shrb", "shr bowl"],
    "hsd": ["high stakes duel", "hsd", "heads up duel"],
    "pgt": ["pokergo tour", "pgt"],
    "uspo": ["us poker open", "uspo", "u.s. poker open"],
    "pm": ["poker masters"],
    "ngnf": ["no gamble no future", "ngnf"],
    "wsope": ["wsop europe", "wsope"],
    "wsop_paradise": ["wsop paradise", "paradise"],
}

GAME_TYPES = {
    "nlh": ["nlh", "no limit hold'em", "no limit holdem", "nlhe", "no-limit", "hold'em", "holdem"],
    "plo": ["plo", "pot limit omaha", "omaha", "pot-limit omaha"],
    "27td": ["2-7 triple draw", "27td", "2-7 td", "triple draw", "27 triple", "2-7"],
    "stud": ["stud", "7 card stud", "razz"],
    "mixed": ["mixed", "horse", "8-game"],
}


@dataclass
class Features:
    """Extracted features from title/filename"""
    year: Optional[int] = None
    event: Optional[str] = None
    players: list = field(default_factory=list)
    game: Optional[str] = None
    keywords: list = field(default_factory=list)
    episode: Optional[int] = None
    day: Optional[str] = None
    normalized: str = ""


def normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_year(text: str) -> Optional[int]:
    """Extract year from text"""
    # 4-digit year
    match = re.search(r'20[0-2][0-9]', text)
    if match:
        return int(match.group())
    # 2-digit year (08 -> 2008)
    match = re.search(r'\b([0-2][0-9])\b', text)
    if match:
        year = int(match.group(1))
        if year >= 0 and year <= 25:
            return 2000 + year
    # 1973-1999
    match = re.search(r'19[7-9][0-9]', text)
    if match:
        return int(match.group())
    return None


def extract_players(text: str) -> list:
    """Extract player names from text"""
    text_lower = text.lower()
    found = []
    for canonical, aliases in PLAYER_ALIASES.items():
        for alias in aliases:
            if alias in text_lower:
                found.append(canonical)
                break
    return list(set(found))


def extract_event(text: str) -> Optional[str]:
    """Extract event type from text"""
    text_lower = text.lower()
    for event_type, keywords in EVENT_TYPES.items():
        for kw in keywords:
            if kw in text_lower:
                return event_type
    return None


def extract_game(text: str) -> Optional[str]:
    """Extract game type from text"""
    text_lower = text.lower()
    for game_type, keywords in GAME_TYPES.items():
        for kw in keywords:
            if kw in text_lower:
                return game_type
    return None


def extract_youtube_features(video: dict) -> Features:
    """Extract features from YouTube video"""
    title = video.get("title", "")
    desc = video.get("description", "") or ""
    combined = f"{title} {desc}"

    return Features(
        year=extract_year(title),
        event=extract_event(combined),
        players=extract_players(combined),
        game=extract_game(combined),
        normalized=normalize_text(title)
    )


def extract_nas_features(file_info: dict) -> Features:
    """Extract features from NAS file"""
    filename = file_info.get("filename", "")
    directory = file_info.get("directory", "")
    combined = f"{filename} {directory}"

    # Extract year from directory if not in filename
    year = extract_year(filename)
    if not year:
        year = extract_year(directory)

    return Features(
        year=year,
        event=extract_event(combined),
        players=extract_players(combined),
        game=extract_game(combined),
        normalized=normalize_text(filename)
    )


def calculate_similarity(s1: str, s2: str) -> float:
    """Simple token-based similarity (0-100)"""
    tokens1 = set(s1.split())
    tokens2 = set(s2.split())
    if not tokens1 or not tokens2:
        return 0
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    return len(intersection) / len(union) * 100


def calculate_match_score(yt_features: Features, nas_features: Features) -> tuple[int, list]:
    """Calculate match score between YouTube and NAS features"""
    score = 0
    details = []

    # 1. Year Match (max 30)
    if yt_features.year and nas_features.year:
        if yt_features.year == nas_features.year:
            score += 30
            details.append(f"year_match: +30 ({yt_features.year})")
        elif abs(yt_features.year - nas_features.year) == 1:
            score += 10
            details.append(f"year_close: +10 ({yt_features.year} vs {nas_features.year})")
    elif yt_features.year is None and nas_features.year is None:
        score += 5
        details.append("year_unknown: +5")

    # 2. Player Name Match (max 30)
    common_players = set(yt_features.players) & set(nas_features.players)
    if common_players:
        player_score = min(30, len(common_players) * 15)
        score += player_score
        details.append(f"player_match: +{player_score} ({', '.join(common_players)})")

    # 3. Event Type Match (max 20)
    if yt_features.event and nas_features.event:
        if yt_features.event == nas_features.event:
            score += 20
            details.append(f"event_match: +20 ({yt_features.event})")

    # 4. Game Type Match (max 10)
    if yt_features.game and nas_features.game:
        if yt_features.game == nas_features.game:
            score += 10
            details.append(f"game_match: +10 ({yt_features.game})")

    # 5. Fuzzy Title Similarity (max 10)
    similarity = calculate_similarity(yt_features.normalized, nas_features.normalized)
    fuzzy_score = int(similarity * 0.1)
    if fuzzy_score > 0:
        score += fuzzy_score
        details.append(f"fuzzy_match: +{fuzzy_score} ({similarity:.1f}%)")

    return score, details


def find_best_match(yt_video: dict, nas_files: list) -> tuple[Optional[dict], int, list]:
    """Find best matching NAS file for a YouTube video"""
    yt_features = extract_youtube_features(yt_video)

    best_match = None
    best_score = 0
    best_details = []

    # Pre-filter by event type if available
    candidates = nas_files
    if yt_features.event:
        # Blocking: only consider files with same event type
        filtered = [f for f in nas_files if extract_nas_features(f).event == yt_features.event]
        if filtered:
            candidates = filtered

    for nas_file in candidates:
        nas_features = extract_nas_features(nas_file)
        score, details = calculate_match_score(yt_features, nas_features)

        if score > best_score:
            best_score = score
            best_match = nas_file
            best_details = details

    return best_match, best_score, best_details


def main():
    print("=" * 70)
    print("YouTube-NAS Matching Test (20 Samples)")
    print("=" * 70)

    # Load data
    print("\n[1] Loading data...")

    with open(YOUTUBE_VIDEOS, 'r', encoding='utf-8') as f:
        yt_data = json.load(f)
    youtube_videos = yt_data.get("videos", [])
    print(f"    YouTube videos: {len(youtube_videos)}")

    with open(NAS_FILES, 'r', encoding='utf-8') as f:
        nas_data = json.load(f)
    nas_files = nas_data.get("files", [])
    print(f"    NAS files: {len(nas_files)}")

    # Random sample of 20 YouTube videos
    print("\n[2] Sampling 20 random YouTube videos...")
    random.seed(42)  # Reproducible
    samples = random.sample(youtube_videos, min(20, len(youtube_videos)))

    # Matching
    print("\n[3] Running matching algorithm...")
    print("-" * 70)

    results = []
    for i, video in enumerate(samples, 1):
        title = video.get("title", "")[:60]
        match, score, details = find_best_match(video, nas_files)

        match_filename = match.get("filename", "")[:50] if match else "No match"

        # Categorize
        if score >= 80:
            category = "CONFIDENT"
        elif score >= 60:
            category = "LIKELY"
        elif score >= 40:
            category = "POSSIBLE"
        else:
            category = "NO_MATCH"

        results.append({
            "video": video,
            "match": match,
            "score": score,
            "details": details,
            "category": category
        })

        print(f"\n[{i:02d}] {title}...")
        print(f"     -> {match_filename}...")
        print(f"     Score: {score} ({category})")
        if details:
            print(f"     Details: {', '.join(details[:3])}")

    # Analysis
    print("\n" + "=" * 70)
    print("MATCHING RESULTS ANALYSIS")
    print("=" * 70)

    confident = sum(1 for r in results if r["category"] == "CONFIDENT")
    likely = sum(1 for r in results if r["category"] == "LIKELY")
    possible = sum(1 for r in results if r["category"] == "POSSIBLE")
    no_match = sum(1 for r in results if r["category"] == "NO_MATCH")

    total = len(results)
    success_rate = (confident + likely) / total * 100 if total > 0 else 0

    print(f"\nTotal Samples: {total}")
    print(f"\n+-----------------+-------+---------+")
    print(f"| Category        | Count | Percent |")
    print(f"+-----------------+-------+---------+")
    print(f"| CONFIDENT (>=80)| {confident:>5} | {confident/total*100:>6.1f}% |")
    print(f"| LIKELY (60-79)  | {likely:>5} | {likely/total*100:>6.1f}% |")
    print(f"| POSSIBLE (40-59)| {possible:>5} | {possible/total*100:>6.1f}% |")
    print(f"| NO_MATCH (<40)  | {no_match:>5} | {no_match/total*100:>6.1f}% |")
    print(f"+-----------------+-------+---------+")

    print(f"\n[*] Success Rate (CONFIDENT + LIKELY): {success_rate:.1f}%")

    # Score distribution
    scores = [r["score"] for r in results]
    avg_score = sum(scores) / len(scores) if scores else 0
    max_score = max(scores) if scores else 0
    min_score = min(scores) if scores else 0

    print(f"\n+-----------------+-------+")
    print(f"| Score Stats     | Value |")
    print(f"+-----------------+-------+")
    print(f"| Average         | {avg_score:>5.1f} |")
    print(f"| Max             | {max_score:>5} |")
    print(f"| Min             | {min_score:>5} |")
    print(f"+-----------------+-------+")

    # Feature analysis
    print("\n[Feature Extraction Stats]")
    yt_with_year = sum(1 for r in results if extract_youtube_features(r["video"]).year)
    yt_with_event = sum(1 for r in results if extract_youtube_features(r["video"]).event)
    yt_with_players = sum(1 for r in results if extract_youtube_features(r["video"]).players)

    print(f"  YouTube videos with year:    {yt_with_year}/{total} ({yt_with_year/total*100:.1f}%)")
    print(f"  YouTube videos with event:   {yt_with_event}/{total} ({yt_with_event/total*100:.1f}%)")
    print(f"  YouTube videos with players: {yt_with_players}/{total} ({yt_with_players/total*100:.1f}%)")

    # Save results
    output_file = DATA_DIR / "analysis" / "matching_test_results.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "total_samples": total,
        "success_rate": success_rate,
        "categories": {
            "confident": confident,
            "likely": likely,
            "possible": possible,
            "no_match": no_match
        },
        "score_stats": {
            "average": avg_score,
            "max": max_score,
            "min": min_score
        },
        "results": [
            {
                "youtube_title": r["video"].get("title"),
                "youtube_id": r["video"].get("video_id"),
                "nas_filename": r["match"].get("filename") if r["match"] else None,
                "score": r["score"],
                "category": r["category"],
                "details": r["details"]
            }
            for r in results
        ]
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n[*] Results saved to: {output_file}")


if __name__ == "__main__":
    main()
