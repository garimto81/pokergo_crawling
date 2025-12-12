"""
Full Episode Matching - NAS to YouTube

NAS Full Episodes -> YouTube 매칭
- NAS가 원본 소스
- YouTube에 업로드되었으면 반드시 매칭되어야 함
- 매칭 안 되면 = 아직 미업로드 콘텐츠
"""

import json
import random
import re
import warnings
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

warnings.filterwarnings("ignore")

DATA_DIR = Path("data")
YOUTUBE_VIDEOS = DATA_DIR / "sources/youtube/exports/videos/videos_001.json"
NAS_FILES = DATA_DIR / "sources/nas/nas_files.json"

# ==================== Feature Extraction ====================

def extract_year(text: str) -> Optional[int]:
    """Extract year from text"""
    match = re.search(r'20[0-2][0-9]', text)
    if match:
        return int(match.group())
    match = re.search(r'19[7-9][0-9]', text)
    if match:
        return int(match.group())
    # 2-digit year (08 -> 2008)
    match = re.search(r'WSOPE?(\d{2})[\s_]', text)
    if match:
        yr = int(match.group(1))
        return 2000 + yr if yr < 50 else 1900 + yr
    return None


def extract_event_type(text: str) -> Optional[str]:
    """Extract event type"""
    text_lower = text.lower()
    if "wsop europe" in text_lower or "wsope" in text_lower:
        return "wsope"
    if "wsop paradise" in text_lower:
        return "wsop_paradise"
    if "wsop" in text_lower or "world series" in text_lower:
        return "wsop"
    if "high stakes poker" in text_lower or "hsp" in text_lower:
        return "hsp"
    if "poker after dark" in text_lower or "pad" in text_lower:
        return "pad"
    if "no gamble no future" in text_lower or "ngnf" in text_lower:
        return "ngnf"
    if "super high roller" in text_lower or "shrb" in text_lower:
        return "shrb"
    if "poker masters" in text_lower:
        return "pm"
    if "us poker open" in text_lower:
        return "uspo"
    return None


def extract_day_episode(text: str) -> dict:
    """Extract day/episode number"""
    result = {"day": None, "episode": None, "part": None, "event_num": None}

    text_lower = text.lower()

    # Day extraction
    day_match = re.search(r'day\s*(\d+[a-d]?)', text_lower)
    if day_match:
        result["day"] = day_match.group(1)

    # Episode extraction
    ep_match = re.search(r'(?:episode|ep\.?)\s*(\d+)', text_lower)
    if ep_match:
        result["episode"] = int(ep_match.group(1))

    # Part extraction
    part_match = re.search(r'part\s*(\d+)', text_lower)
    if part_match:
        result["part"] = int(part_match.group(1))

    # Event number (WSOP specific)
    event_match = re.search(r'(?:event|ev|#)\s*#?(\d+)', text_lower)
    if event_match:
        result["event_num"] = int(event_match.group(1))

    # Final table
    if "final table" in text_lower or "final day" in text_lower:
        result["day"] = "final"

    return result


def normalize_text(text: str) -> str:
    """Normalize for comparison"""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def is_full_episode(filename: str, directory: str) -> bool:
    """Check if NAS file is a full episode"""
    combined = (filename + " " + directory).lower()

    # Exclude clips
    if any(kw in combined for kw in ["hand clip", "subclip", "_hand_", "clip"]):
        return False

    # Include full episodes
    if any(kw in combined for kw in ["episode", "main event", "final table",
                                      "day 1", "day 2", "day 3", "day 4", "day 5",
                                      "bracelet", "stream"]):
        return True

    # Include by file extension (large master files)
    if filename.endswith('.mov') or filename.endswith('.mxf'):
        return True

    # WSOP archive files
    if "wsop" in combined and "archive" in combined:
        return True

    return False


# ==================== Matching ====================

def calculate_match_score(nas_info: dict, yt_video: dict) -> tuple[int, list]:
    """Calculate match score (NAS -> YouTube)"""
    nas_text = nas_info["filename"] + " " + nas_info["directory"]
    yt_title = yt_video.get("title", "")

    score = 0
    details = []

    # 1. Year match (30 points)
    nas_year = extract_year(nas_text)
    yt_year = extract_year(yt_title)

    if nas_year and yt_year:
        if nas_year == yt_year:
            score += 30
            details.append(f"year: +30 ({nas_year})")
        elif abs(nas_year - yt_year) == 1:
            score += 10
            details.append(f"year_close: +10")
    elif nas_year is None and yt_year is None:
        score += 5

    # 2. Event type match (25 points)
    nas_event = extract_event_type(nas_text)
    yt_event = extract_event_type(yt_title)

    if nas_event and yt_event and nas_event == yt_event:
        score += 25
        details.append(f"event: +25 ({nas_event})")

    # 3. Day/Episode match (25 points)
    nas_de = extract_day_episode(nas_text)
    yt_de = extract_day_episode(yt_title)

    day_match = False
    if nas_de["day"] and yt_de["day"]:
        if nas_de["day"] == yt_de["day"]:
            score += 15
            details.append(f"day: +15 ({nas_de['day']})")
            day_match = True

    if nas_de["episode"] and yt_de["episode"]:
        if nas_de["episode"] == yt_de["episode"]:
            score += 10
            details.append(f"episode: +10 ({nas_de['episode']})")

    if nas_de["event_num"] and yt_de["event_num"]:
        if nas_de["event_num"] == yt_de["event_num"]:
            score += 10
            details.append(f"event#: +10 ({nas_de['event_num']})")

    # 4. Semantic similarity (20 points)
    nas_norm = normalize_text(nas_text)
    yt_norm = normalize_text(yt_title)

    # Token overlap
    nas_tokens = set(nas_norm.split())
    yt_tokens = set(yt_norm.split())

    if nas_tokens and yt_tokens:
        overlap = len(nas_tokens & yt_tokens)
        union = len(nas_tokens | yt_tokens)
        jaccard = overlap / union if union > 0 else 0
        semantic_score = int(jaccard * 20)
        if semantic_score > 0:
            score += semantic_score
            details.append(f"semantic: +{semantic_score}")

    return score, details


def find_youtube_match(nas_file: dict, youtube_videos: list, sbert_model=None) -> tuple:
    """Find best YouTube match for NAS file"""
    nas_text = nas_file["filename"] + " " + nas_file["directory"]
    nas_year = extract_year(nas_text)
    nas_event = extract_event_type(nas_text)

    # Blocking: filter by year and event
    candidates = []
    for yt in youtube_videos:
        yt_title = yt.get("title", "")
        yt_year = extract_year(yt_title)
        yt_event = extract_event_type(yt_title)

        # Year filter
        if nas_year and yt_year:
            if abs(nas_year - yt_year) > 1:
                continue

        # Event filter (if both have event)
        if nas_event and yt_event:
            if nas_event != yt_event:
                continue

        candidates.append(yt)

    # If no candidates, use all
    if not candidates:
        candidates = youtube_videos

    # Find best match
    best_match = None
    best_score = 0
    best_details = []

    # Use SBERT if available
    if sbert_model and candidates:
        try:
            from sentence_transformers import util

            nas_norm = normalize_text(nas_text)
            yt_titles = [normalize_text(yt.get("title", "")) for yt in candidates]

            nas_emb = sbert_model.encode(nas_norm, convert_to_tensor=True)
            yt_embs = sbert_model.encode(yt_titles, convert_to_tensor=True)
            similarities = util.cos_sim(nas_emb, yt_embs)[0].cpu().numpy()

            for i, yt in enumerate(candidates):
                feature_score, feature_details = calculate_match_score(nas_file, yt)

                # Semantic score from SBERT (max 30)
                sim = float(similarities[i])
                semantic_boost = int(max(0, (sim - 0.3)) / 0.7 * 30) if sim > 0.3 else 0

                total_score = feature_score + semantic_boost
                details = feature_details.copy()
                if semantic_boost > 0:
                    details.append(f"sbert: +{semantic_boost}")

                if total_score > best_score:
                    best_score = total_score
                    best_match = yt
                    best_details = details

        except Exception as e:
            pass

    # Fallback to feature-only matching
    if best_match is None:
        for yt in candidates:
            score, details = calculate_match_score(nas_file, yt)
            if score > best_score:
                best_score = score
                best_match = yt
                best_details = details

    return best_match, best_score, best_details, len(candidates)


# ==================== Main ====================

def main():
    print("=" * 70)
    print("NAS Full Episode -> YouTube Matching")
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

    # Filter NAS full episodes
    print("\n[2] Filtering NAS Full Episodes...")
    nas_full_episodes = [
        f for f in nas_files
        if is_full_episode(f.get("filename", ""), f.get("directory", ""))
    ]
    print(f"    NAS Full Episodes: {len(nas_full_episodes)}")

    # Load SBERT
    print("\n[3] Loading Sentence Transformers...")
    try:
        from sentence_transformers import SentenceTransformer
        sbert_model = SentenceTransformer("all-MiniLM-L6-v2")
        print("    Model loaded: all-MiniLM-L6-v2")
    except Exception as e:
        print(f"    Warning: {e}")
        sbert_model = None

    # Sample 20 NAS full episodes
    print("\n[4] Sampling 20 NAS Full Episodes...")
    random.seed(42)
    samples = random.sample(nas_full_episodes, min(20, len(nas_full_episodes)))

    # Run matching
    print("\n[5] Running NAS -> YouTube matching...")
    print("-" * 70)

    results = []
    for i, nas_file in enumerate(samples, 1):
        filename = nas_file.get("filename", "")[:50]
        filename_safe = filename.encode('ascii', 'ignore').decode('ascii')

        match, score, details, candidates = find_youtube_match(
            nas_file, youtube_videos, sbert_model
        )

        yt_title = match.get("title", "")[:45] if match else "No match"
        yt_title_safe = yt_title.encode('ascii', 'ignore').decode('ascii')

        # Categorize
        if score >= 80:
            category = "MATCHED"
        elif score >= 60:
            category = "LIKELY"
        elif score >= 40:
            category = "POSSIBLE"
        else:
            category = "NOT_UPLOADED"

        results.append({
            "nas_file": nas_file,
            "youtube_match": match,
            "score": score,
            "details": details,
            "category": category
        })

        print(f"\n[{i:02d}] NAS: {filename_safe}...")
        print(f"     YT:  {yt_title_safe}...")
        print(f"     Score: {score} ({category}) | Candidates: {candidates}")
        if details:
            print(f"     {', '.join(details[:4])}")

    # Analysis
    print("\n" + "=" * 70)
    print("MATCHING RESULTS (NAS -> YouTube)")
    print("=" * 70)

    matched = sum(1 for r in results if r["category"] == "MATCHED")
    likely = sum(1 for r in results if r["category"] == "LIKELY")
    possible = sum(1 for r in results if r["category"] == "POSSIBLE")
    not_uploaded = sum(1 for r in results if r["category"] == "NOT_UPLOADED")

    total = len(results)
    match_rate = (matched + likely) / total * 100 if total > 0 else 0

    print(f"\nTotal NAS Samples: {total}")
    print(f"\n+-------------------+-------+---------+")
    print(f"| Status            | Count | Percent |")
    print(f"+-------------------+-------+---------+")
    print(f"| MATCHED (>=80)    |{matched:>6} |{matched/total*100:>7.1f}% |")
    print(f"| LIKELY (60-79)    |{likely:>6} |{likely/total*100:>7.1f}% |")
    print(f"| POSSIBLE (40-59)  |{possible:>6} |{possible/total*100:>7.1f}% |")
    print(f"| NOT_UPLOADED (<40)|{not_uploaded:>6} |{not_uploaded/total*100:>7.1f}% |")
    print(f"+-------------------+-------+---------+")

    print(f"\n[*] MATCH RATE (MATCHED + LIKELY): {match_rate:.1f}%")
    print(f"[*] Potential NOT UPLOADED: {not_uploaded} files ({not_uploaded/total*100:.1f}%)")

    # Score stats
    scores = [r["score"] for r in results]
    print(f"\n+-------------------+-------+")
    print(f"| Score Stats       | Value |")
    print(f"+-------------------+-------+")
    print(f"| Average           |{sum(scores)/len(scores):>6.1f} |")
    print(f"| Max               |{max(scores):>6} |")
    print(f"| Min               |{min(scores):>6} |")
    print(f"+-------------------+-------+")

    # Show NOT_UPLOADED files
    print("\n" + "=" * 70)
    print("POTENTIAL NOT UPLOADED (Score < 40)")
    print("=" * 70)
    for r in results:
        if r["category"] == "NOT_UPLOADED":
            nas = r["nas_file"]
            fname = nas.get("filename", "").encode('ascii', 'ignore').decode('ascii')
            directory = nas.get("directory", "")[:40].encode('ascii', 'ignore').decode('ascii')
            print(f"\n  File: {fname}")
            print(f"  Path: {directory}")
            print(f"  Score: {r['score']}")

    # Save results
    output_file = DATA_DIR / "analysis" / "full_episode_matching.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "total_nas_full_episodes": len(nas_full_episodes),
        "sampled": total,
        "match_rate": match_rate,
        "categories": {
            "matched": matched,
            "likely": likely,
            "possible": possible,
            "not_uploaded": not_uploaded
        },
        "results": [
            {
                "nas_filename": r["nas_file"].get("filename"),
                "nas_directory": r["nas_file"].get("directory"),
                "youtube_title": r["youtube_match"].get("title") if r["youtube_match"] else None,
                "youtube_id": r["youtube_match"].get("video_id") if r["youtube_match"] else None,
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
