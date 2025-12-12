"""
Improved Matching Test - PolyFuzz + SBERT + Duration Blocking

Strategy:
1. Duration Blocking - Filter by video length
2. Content Type Classification - Compilation vs Episode
3. PolyFuzz + Sentence Transformers for semantic matching
4. Combined scoring (Feature + Semantic)
"""

import json
import random
import re
import warnings
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

warnings.filterwarnings("ignore")

# Paths
DATA_DIR = Path("data")
YOUTUBE_VIDEOS = DATA_DIR / "sources/youtube/exports/videos/videos_001.json"
NAS_FILES = DATA_DIR / "sources/nas/nas_files.json"

# ==================== Constants ====================

CLIP_DURATION_THRESHOLD = 1800  # 30 minutes in seconds

COMPILATION_KEYWORDS = [
    "top 5", "top 10", "best of", "worst", "every", "all time",
    "compilation", "recap", "highlights", "moments", "craziest",
    "sickest", "biggest", "wildest", "insane"
]

EPISODE_KEYWORDS = [
    "episode", "ep.", "day 1", "day 2", "day 3", "day 4", "day 5",
    "final table", "part 1", "part 2", "season", "main event"
]

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
    "garrett_adelstein": ["garrett", "adelstein", "garrett adelstein"],
    "alan_keating": ["keating", "alan keating"],
    "andrew_robl": ["robl", "andrew robl"],
    "matt_berkey": ["berkey", "matt berkey"],
    "jason_koon": ["koon", "jason koon"],
    "chris_moneymaker": ["moneymaker", "chris moneymaker"],
}

EVENT_TYPES = {
    "wsop": ["wsop", "world series of poker", "world series", "bracelet"],
    "hsp": ["high stakes poker", "hsp", "high stakes"],
    "pad": ["poker after dark", "pad"],
    "shrb": ["super high roller bowl", "shrb"],
    "hsd": ["high stakes duel", "hsd"],
    "ngnf": ["no gamble no future", "ngnf"],
}


# ==================== Helper Functions ====================

def normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_year(text: str) -> Optional[int]:
    """Extract year from text"""
    match = re.search(r'20[0-2][0-9]', text)
    if match:
        return int(match.group())
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


def classify_content_type(title: str) -> str:
    """Classify content as compilation, episode, or unknown"""
    title_lower = title.lower()

    for kw in COMPILATION_KEYWORDS:
        if kw in title_lower:
            return "compilation"

    for kw in EPISODE_KEYWORDS:
        if kw in title_lower:
            return "episode"

    return "unknown"


def get_duration_category(duration_seconds: Optional[int]) -> str:
    """Categorize by duration"""
    if duration_seconds is None:
        return "unknown"
    if duration_seconds < 300:  # < 5 min
        return "short_clip"
    if duration_seconds < CLIP_DURATION_THRESHOLD:  # 5-30 min
        return "clip"
    if duration_seconds < 7200:  # 30 min - 2 hours
        return "episode"
    return "long_episode"


# ==================== Feature Extraction ====================

@dataclass
class VideoFeatures:
    title: str
    normalized_title: str
    year: Optional[int] = None
    event: Optional[str] = None
    players: list = field(default_factory=list)
    content_type: str = "unknown"
    duration_category: str = "unknown"
    duration: Optional[int] = None


def extract_youtube_features(video: dict) -> VideoFeatures:
    """Extract features from YouTube video"""
    title = video.get("title", "")
    duration = video.get("duration")

    return VideoFeatures(
        title=title,
        normalized_title=normalize_text(title),
        year=extract_year(title),
        event=extract_event(title),
        players=extract_players(title),
        content_type=classify_content_type(title),
        duration_category=get_duration_category(duration),
        duration=duration
    )


def extract_nas_features(file_info: dict) -> VideoFeatures:
    """Extract features from NAS file"""
    filename = file_info.get("filename", "")
    directory = file_info.get("directory", "")
    combined = f"{filename} {directory}"

    year = extract_year(filename) or extract_year(directory)

    # Determine content type from path
    path_lower = (directory + filename).lower()
    if "clip" in path_lower or "subclip" in path_lower or "hand clip" in path_lower:
        content_type = "clip"
    elif "stream" in path_lower or "episode" in path_lower:
        content_type = "episode"
    else:
        content_type = classify_content_type(filename)

    return VideoFeatures(
        title=filename,
        normalized_title=normalize_text(filename),
        year=year,
        event=extract_event(combined),
        players=extract_players(combined),
        content_type=content_type,
        duration_category="unknown"
    )


# ==================== Blocking ====================

def apply_blocking(yt_features: VideoFeatures, nas_files: list) -> list:
    """Apply blocking rules to reduce candidate set"""
    candidates = []

    for nas_file in nas_files:
        nas_features = extract_nas_features(nas_file)

        # Rule 1: Year blocking (if both have year, must match or be close)
        if yt_features.year and nas_features.year:
            if abs(yt_features.year - nas_features.year) > 1:
                continue

        # Rule 2: Content type blocking
        # Compilations don't match with full episodes
        if yt_features.content_type == "compilation":
            if nas_features.content_type == "episode":
                continue

        # Rule 3: Duration blocking
        # Short clips (< 30min) should match with clips, not full episodes
        if yt_features.duration_category in ["short_clip", "clip"]:
            if nas_features.content_type == "episode" and "clip" not in nas_file.get("directory", "").lower():
                continue

        candidates.append(nas_file)

    return candidates if candidates else nas_files[:100]  # Fallback to first 100


# ==================== Scoring ====================

def calculate_feature_score(yt: VideoFeatures, nas: VideoFeatures) -> tuple[int, list]:
    """Calculate feature-based match score (max 50)"""
    score = 0
    details = []

    # Year match (max 20)
    if yt.year and nas.year:
        if yt.year == nas.year:
            score += 20
            details.append(f"year: +20 ({yt.year})")
        elif abs(yt.year - nas.year) == 1:
            score += 8
            details.append(f"year_close: +8")

    # Player match (max 15)
    common_players = set(yt.players) & set(nas.players)
    if common_players:
        player_score = min(15, len(common_players) * 8)
        score += player_score
        details.append(f"players: +{player_score}")

    # Event match (max 10)
    if yt.event and nas.event and yt.event == nas.event:
        score += 10
        details.append(f"event: +10 ({yt.event})")

    # Content type match (max 5)
    if yt.content_type != "unknown" and nas.content_type != "unknown":
        if yt.content_type == nas.content_type:
            score += 5
            details.append(f"type: +5")

    return score, details


def calculate_semantic_score(yt_title: str, nas_title: str, polyfuzz_model) -> float:
    """Calculate semantic similarity score using PolyFuzz"""
    try:
        result = polyfuzz_model.match([yt_title], [nas_title])
        matches = result.get_matches()
        if not matches.empty:
            similarity = matches.iloc[0]["Similarity"]
            return similarity * 100  # Convert to 0-100 scale
    except Exception:
        pass
    return 0.0


# ==================== Main Matching ====================

def find_best_match_improved(
    yt_video: dict,
    nas_files: list,
    sbert_model,
    use_semantic: bool = True
) -> tuple[Optional[dict], int, list, dict]:
    """Find best match using improved strategy with direct SBERT"""

    yt_features = extract_youtube_features(yt_video)

    # Apply blocking
    candidates = apply_blocking(yt_features, nas_files)

    best_match = None
    best_score = 0
    best_details = []
    debug_info = {
        "candidates_count": len(candidates),
        "blocking_applied": len(candidates) < len(nas_files),
        "yt_content_type": yt_features.content_type,
        "yt_duration_cat": yt_features.duration_category
    }

    # Pre-compute embeddings for semantic matching
    if use_semantic and sbert_model and candidates:
        try:
            from sentence_transformers import util

            # Get YouTube embedding
            yt_embedding = sbert_model.encode(yt_features.normalized_title, convert_to_tensor=True)

            # Get NAS embeddings
            nas_titles = [extract_nas_features(f).normalized_title for f in candidates]
            nas_embeddings = sbert_model.encode(nas_titles, convert_to_tensor=True)

            # Calculate cosine similarities
            similarities = util.cos_sim(yt_embedding, nas_embeddings)[0]
            semantic_scores = similarities.cpu().numpy()
        except Exception as e:
            semantic_scores = None
    else:
        semantic_scores = None

    for i, nas_file in enumerate(candidates):
        nas_features = extract_nas_features(nas_file)

        # Feature score (max 50)
        feature_score, feature_details = calculate_feature_score(yt_features, nas_features)

        # Semantic score (max 50) - increased weight
        semantic_score = 0
        if semantic_scores is not None:
            try:
                raw_similarity = float(semantic_scores[i])
                # Scale: 0.3+ similarity = meaningful match
                if raw_similarity > 0.3:
                    semantic_score = int((raw_similarity - 0.3) / 0.7 * 50)
                else:
                    semantic_score = int(raw_similarity * 20)
            except Exception:
                pass

        total_score = int(feature_score + semantic_score)

        if total_score > best_score:
            best_score = total_score
            best_match = nas_file
            best_details = feature_details.copy()
            if semantic_score > 0:
                best_details.append(f"semantic: +{semantic_score}")

    return best_match, best_score, best_details, debug_info


# ==================== Main ====================

def main():
    print("=" * 70)
    print("IMPROVED Matching Test - PolyFuzz + SBERT + Blocking")
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

    # Initialize Sentence Transformers directly
    print("\n[2] Initializing Sentence Transformers...")
    try:
        from sentence_transformers import SentenceTransformer

        sbert_model = SentenceTransformer("all-MiniLM-L6-v2")
        print("    Model loaded: all-MiniLM-L6-v2")
        use_semantic = True
    except Exception as e:
        print(f"    Warning: Could not load SBERT model: {e}")
        print("    Falling back to feature-only matching")
        sbert_model = None
        use_semantic = False

    # Same 20 samples as before (seed=42)
    print("\n[3] Sampling same 20 YouTube videos (seed=42)...")
    random.seed(42)
    samples = random.sample(youtube_videos, min(20, len(youtube_videos)))

    # Run matching
    print("\n[4] Running IMPROVED matching algorithm...")
    print("-" * 70)

    results = []
    for i, video in enumerate(samples, 1):
        title = video.get("title", "")[:55]

        match, score, details, debug = find_best_match_improved(
            video, nas_files, sbert_model, use_semantic
        )

        match_filename = match.get("filename", "")[:45] if match else "No match"
        # Remove non-ASCII characters for console output
        match_filename = match_filename.encode('ascii', 'ignore').decode('ascii')

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
            "category": category,
            "debug": debug
        })

        print(f"\n[{i:02d}] {title}...")
        print(f"     -> {match_filename}...")
        print(f"     Score: {score} ({category}) | Candidates: {debug['candidates_count']}")
        if details:
            print(f"     {', '.join(details[:4])}")

    # Analysis
    print("\n" + "=" * 70)
    print("IMPROVED MATCHING RESULTS")
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
    print(f"| CONFIDENT (>=80)|{confident:>6} |{confident/total*100:>7.1f}% |")
    print(f"| LIKELY (60-79)  |{likely:>6} |{likely/total*100:>7.1f}% |")
    print(f"| POSSIBLE (40-59)|{possible:>6} |{possible/total*100:>7.1f}% |")
    print(f"| NO_MATCH (<40)  |{no_match:>6} |{no_match/total*100:>7.1f}% |")
    print(f"+-----------------+-------+---------+")

    print(f"\n[*] SUCCESS RATE (CONFIDENT + LIKELY): {success_rate:.1f}%")

    # Score stats
    scores = [r["score"] for r in results]
    avg_score = sum(scores) / len(scores) if scores else 0

    print(f"\n+-----------------+-------+")
    print(f"| Score Stats     | Value |")
    print(f"+-----------------+-------+")
    print(f"| Average         |{avg_score:>6.1f} |")
    print(f"| Max             |{max(scores):>6} |")
    print(f"| Min             |{min(scores):>6} |")
    print(f"+-----------------+-------+")

    # Blocking effectiveness
    avg_candidates = sum(r["debug"]["candidates_count"] for r in results) / total
    blocking_rate = (1 - avg_candidates / len(nas_files)) * 100

    print(f"\n[Blocking Effectiveness]")
    print(f"  Average candidates per video: {avg_candidates:.0f} / {len(nas_files)}")
    print(f"  Blocking reduction: {blocking_rate:.1f}%")

    # Comparison with baseline
    print("\n" + "=" * 70)
    print("COMPARISON: Baseline vs Improved")
    print("=" * 70)
    print(f"\n+-------------------+-----------+-----------+")
    print(f"| Metric            | Baseline  | Improved  |")
    print(f"+-------------------+-----------+-----------+")
    print(f"| Success Rate      |      5.0% |   {success_rate:>6.1f}% |")
    print(f"| Avg Score         |      29.3 |    {avg_score:>5.1f} |")
    print(f"| CONFIDENT matches |         0 |        {confident} |")
    print(f"| LIKELY matches    |         1 |        {likely} |")
    print(f"+-------------------+-----------+-----------+")

    improvement = success_rate - 5.0
    print(f"\n[*] IMPROVEMENT: +{improvement:.1f}% points")

    # Save results
    output_file = DATA_DIR / "analysis" / "improved_matching_results.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "strategy": "PolyFuzz + SBERT + Duration/Content Blocking",
        "total_samples": total,
        "success_rate": success_rate,
        "baseline_success_rate": 5.0,
        "improvement": improvement,
        "categories": {
            "confident": confident,
            "likely": likely,
            "possible": possible,
            "no_match": no_match
        },
        "score_stats": {
            "average": avg_score,
            "max": max(scores),
            "min": min(scores)
        },
        "blocking_stats": {
            "avg_candidates": avg_candidates,
            "total_nas_files": len(nas_files),
            "reduction_percent": blocking_rate
        },
        "results": [
            {
                "youtube_title": r["video"].get("title"),
                "youtube_id": r["video"].get("video_id"),
                "nas_filename": r["match"].get("filename") if r["match"] else None,
                "score": r["score"],
                "category": r["category"],
                "details": r["details"],
                "candidates_count": r["debug"]["candidates_count"]
            }
            for r in results
        ]
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n[*] Results saved to: {output_file}")


if __name__ == "__main__":
    main()
