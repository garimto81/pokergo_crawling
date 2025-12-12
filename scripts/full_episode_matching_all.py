"""
Full Episode Matching - ALL NAS Full Episodes

1. 전체 NAS Full Episode (742개) 매칭
2. 미업로드 콘텐츠 목록 생성
3. 매칭 결과 DB 저장 (ContentMapping)
"""

import json
import re
import warnings
from pathlib import Path
from datetime import datetime
from typing import Optional
import sys

warnings.filterwarnings("ignore")

DATA_DIR = Path("data")
YOUTUBE_VIDEOS = DATA_DIR / "sources/youtube/exports/videos/videos_001.json"
NAS_FILES = DATA_DIR / "sources/nas/nas_files.json"

# YouTube 영상 최소 길이 필터 (초 단위)
# 2시간 = 7200초 - Full Episode만 매칭 대상으로
MIN_YOUTUBE_DURATION_SEC = 7200  # 2 hours


# ==================== Feature Extraction ====================

def extract_year(text: str) -> Optional[int]:
    match = re.search(r'20[0-2][0-9]', text)
    if match:
        return int(match.group())
    match = re.search(r'19[7-9][0-9]', text)
    if match:
        return int(match.group())
    match = re.search(r'WSOPE?(\d{2})[\s_]', text)
    if match:
        yr = int(match.group(1))
        return 2000 + yr if yr < 50 else 1900 + yr
    return None


def extract_event_type(text: str) -> Optional[str]:
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
    return None


def extract_day_episode(text: str) -> dict:
    result = {"day": None, "episode": None, "part": None, "event_num": None}
    text_lower = text.lower()

    day_match = re.search(r'day\s*(\d+[a-d]?)', text_lower)
    if day_match:
        result["day"] = day_match.group(1)

    ep_match = re.search(r'(?:episode|ep\.?)\s*(\d+)', text_lower)
    if ep_match:
        result["episode"] = int(ep_match.group(1))

    part_match = re.search(r'part\s*(\d+)', text_lower)
    if part_match:
        result["part"] = int(part_match.group(1))

    event_match = re.search(r'(?:event|ev|#)\s*#?(\d+)', text_lower)
    if event_match:
        result["event_num"] = int(event_match.group(1))

    if "final table" in text_lower or "final day" in text_lower:
        result["day"] = "final"

    return result


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def is_full_episode(filename: str, directory: str) -> bool:
    combined = (filename + " " + directory).lower()

    if any(kw in combined for kw in ["hand clip", "subclip", "_hand_", "clip"]):
        return False

    if any(kw in combined for kw in ["episode", "main event", "final table",
                                      "day 1", "day 2", "day 3", "day 4", "day 5",
                                      "bracelet", "stream"]):
        return True

    if filename.endswith('.mov') or filename.endswith('.mxf'):
        return True

    if "wsop" in combined and "archive" in combined:
        return True

    return False


# ==================== Matching ====================

def calculate_match_score(nas_info: dict, yt_video: dict) -> tuple[int, list]:
    nas_text = nas_info["filename"] + " " + nas_info["directory"]
    yt_title = yt_video.get("title", "")

    score = 0
    details = []

    nas_year = extract_year(nas_text)
    yt_year = extract_year(yt_title)

    if nas_year and yt_year:
        if nas_year == yt_year:
            score += 30
            details.append(f"year:{nas_year}")
        elif abs(nas_year - yt_year) == 1:
            score += 10

    nas_event = extract_event_type(nas_text)
    yt_event = extract_event_type(yt_title)

    if nas_event and yt_event and nas_event == yt_event:
        score += 25
        details.append(f"event:{nas_event}")

    nas_de = extract_day_episode(nas_text)
    yt_de = extract_day_episode(yt_title)

    if nas_de["day"] and yt_de["day"] and nas_de["day"] == yt_de["day"]:
        score += 15
        details.append(f"day:{nas_de['day']}")

    if nas_de["episode"] and yt_de["episode"] and nas_de["episode"] == yt_de["episode"]:
        score += 10

    if nas_de["event_num"] and yt_de["event_num"] and nas_de["event_num"] == yt_de["event_num"]:
        score += 10
        details.append(f"ev#{nas_de['event_num']}")

    nas_norm = normalize_text(nas_text)
    yt_norm = normalize_text(yt_title)
    nas_tokens = set(nas_norm.split())
    yt_tokens = set(yt_norm.split())

    if nas_tokens and yt_tokens:
        overlap = len(nas_tokens & yt_tokens)
        union = len(nas_tokens | yt_tokens)
        jaccard = overlap / union if union > 0 else 0
        semantic_score = int(jaccard * 20)
        score += semantic_score

    return score, details


def find_youtube_match(nas_file: dict, youtube_videos: list, sbert_model=None, yt_embeddings=None) -> tuple:
    nas_text = nas_file["filename"] + " " + nas_file["directory"]
    nas_year = extract_year(nas_text)
    nas_event = extract_event_type(nas_text)

    # Blocking
    candidate_indices = []
    for i, yt in enumerate(youtube_videos):
        yt_title = yt.get("title", "")
        yt_year = extract_year(yt_title)
        yt_event = extract_event_type(yt_title)

        if nas_year and yt_year and abs(nas_year - yt_year) > 1:
            continue
        if nas_event and yt_event and nas_event != yt_event:
            continue

        candidate_indices.append(i)

    if not candidate_indices:
        candidate_indices = list(range(len(youtube_videos)))

    best_match = None
    best_score = 0
    best_details = []
    best_idx = -1

    # SBERT matching
    if sbert_model and yt_embeddings is not None:
        try:
            from sentence_transformers import util

            nas_norm = normalize_text(nas_text)
            nas_emb = sbert_model.encode(nas_norm, convert_to_tensor=True)

            # Get candidate embeddings
            candidate_embs = yt_embeddings[candidate_indices]
            similarities = util.cos_sim(nas_emb, candidate_embs)[0].cpu().numpy()

            for j, i in enumerate(candidate_indices):
                yt = youtube_videos[i]
                feature_score, feature_details = calculate_match_score(nas_file, yt)

                sim = float(similarities[j])
                semantic_boost = int(max(0, (sim - 0.3)) / 0.7 * 30) if sim > 0.3 else 0

                total_score = feature_score + semantic_boost

                if total_score > best_score:
                    best_score = total_score
                    best_match = yt
                    best_details = feature_details
                    best_idx = i

        except Exception:
            pass

    # Fallback
    if best_match is None:
        for i in candidate_indices:
            yt = youtube_videos[i]
            score, details = calculate_match_score(nas_file, yt)
            if score > best_score:
                best_score = score
                best_match = yt
                best_details = details
                best_idx = i

    return best_match, best_score, best_details, best_idx


# ==================== DB Save ====================

def save_to_database(results: list, db_path: Path):
    """Save matching results to ContentMapping table"""
    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create ContentMapping table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS content_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nas_filename TEXT NOT NULL,
            nas_directory TEXT,
            nas_size_bytes INTEGER,
            youtube_video_id TEXT,
            youtube_title TEXT,
            match_score INTEGER,
            match_status TEXT,
            match_details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(nas_filename, nas_directory)
        )
    """)

    # Insert or update
    for r in results:
        nas = r["nas_file"]
        yt = r["youtube_match"]

        cursor.execute("""
            INSERT OR REPLACE INTO content_mapping
            (nas_filename, nas_directory, nas_size_bytes, youtube_video_id, youtube_title,
             match_score, match_status, match_details, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nas.get("filename"),
            nas.get("directory"),
            nas.get("size_bytes"),
            yt.get("video_id") if yt else None,
            yt.get("title") if yt else None,
            r["score"],
            r["status"],
            json.dumps(r["details"]),
            datetime.now().isoformat()
        ))

    conn.commit()
    conn.close()


# ==================== Main ====================

def main():
    print("=" * 70)
    print("NAS Full Episode -> YouTube Matching (ALL)")
    print("=" * 70)

    # Load data
    print("\n[1] Loading data...")

    with open(YOUTUBE_VIDEOS, 'r', encoding='utf-8') as f:
        yt_data = json.load(f)
    youtube_videos_all = yt_data.get("videos", [])
    print(f"    YouTube videos (total): {len(youtube_videos_all)}")

    # Filter: 2시간 이상 영상만 (Full Episode)
    youtube_videos = [
        v for v in youtube_videos_all
        if v.get("duration", 0) >= MIN_YOUTUBE_DURATION_SEC
    ]
    print(f"    YouTube videos (>= 2h): {len(youtube_videos)}")

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

    # Load SBERT and pre-compute YouTube embeddings
    print("\n[3] Loading SBERT & computing YouTube embeddings...")
    try:
        from sentence_transformers import SentenceTransformer
        import torch

        sbert_model = SentenceTransformer("all-MiniLM-L6-v2")
        print("    Model loaded: all-MiniLM-L6-v2")

        yt_titles = [normalize_text(yt.get("title", "")) for yt in youtube_videos]
        print(f"    Computing embeddings for {len(yt_titles)} YouTube titles...")
        yt_embeddings = sbert_model.encode(yt_titles, convert_to_tensor=True, show_progress_bar=True)
        print("    YouTube embeddings ready")

    except Exception as e:
        print(f"    Warning: {e}")
        sbert_model = None
        yt_embeddings = None

    # Run matching for ALL
    print(f"\n[4] Running matching for {len(nas_full_episodes)} NAS files...")
    print("-" * 70)

    results = []
    matched_count = 0
    likely_count = 0
    possible_count = 0
    not_uploaded_count = 0

    for i, nas_file in enumerate(nas_full_episodes, 1):
        match, score, details, _ = find_youtube_match(
            nas_file, youtube_videos, sbert_model, yt_embeddings
        )

        if score >= 80:
            status = "MATCHED"
            matched_count += 1
        elif score >= 60:
            status = "LIKELY"
            likely_count += 1
        elif score >= 40:
            status = "POSSIBLE"
            possible_count += 1
        else:
            status = "NOT_UPLOADED"
            not_uploaded_count += 1

        results.append({
            "nas_file": nas_file,
            "youtube_match": match,
            "score": score,
            "details": details,
            "status": status
        })

        # Progress
        if i % 50 == 0 or i == len(nas_full_episodes):
            pct = i / len(nas_full_episodes) * 100
            print(f"    Progress: {i}/{len(nas_full_episodes)} ({pct:.1f}%) | "
                  f"Matched: {matched_count}, Likely: {likely_count}, Not Uploaded: {not_uploaded_count}")

    # Results summary
    total = len(results)
    match_rate = (matched_count + likely_count) / total * 100 if total > 0 else 0

    print("\n" + "=" * 70)
    print("MATCHING RESULTS SUMMARY")
    print("=" * 70)

    print(f"\nTotal NAS Full Episodes: {total}")
    print(f"\n+-------------------+-------+---------+")
    print(f"| Status            | Count | Percent |")
    print(f"+-------------------+-------+---------+")
    print(f"| MATCHED (>=80)    |{matched_count:>6} |{matched_count/total*100:>7.1f}% |")
    print(f"| LIKELY (60-79)    |{likely_count:>6} |{likely_count/total*100:>7.1f}% |")
    print(f"| POSSIBLE (40-59)  |{possible_count:>6} |{possible_count/total*100:>7.1f}% |")
    print(f"| NOT_UPLOADED (<40)|{not_uploaded_count:>6} |{not_uploaded_count/total*100:>7.1f}% |")
    print(f"+-------------------+-------+---------+")

    print(f"\n[*] MATCH RATE: {match_rate:.1f}%")

    # Score stats
    scores = [r["score"] for r in results]
    print(f"\n+-------------------+-------+")
    print(f"| Score Stats       | Value |")
    print(f"+-------------------+-------+")
    print(f"| Average           |{sum(scores)/len(scores):>6.1f} |")
    print(f"| Max               |{max(scores):>6} |")
    print(f"| Min               |{min(scores):>6} |")
    print(f"+-------------------+-------+")

    # Not uploaded list
    not_uploaded = [r for r in results if r["status"] == "NOT_UPLOADED"]

    print("\n" + "=" * 70)
    print(f"NOT UPLOADED CONTENT ({len(not_uploaded)} files)")
    print("=" * 70)

    # Group by directory
    from collections import defaultdict
    by_dir = defaultdict(list)
    for r in not_uploaded:
        directory = r["nas_file"].get("directory", "Unknown")
        by_dir[directory].append(r)

    for directory, files in sorted(by_dir.items()):
        dir_safe = directory[:60].encode('ascii', 'ignore').decode('ascii')
        print(f"\n[{dir_safe}] ({len(files)} files)")
        for r in files[:5]:  # Show max 5 per directory
            fname = r["nas_file"].get("filename", "")[:50]
            fname_safe = fname.encode('ascii', 'ignore').decode('ascii')
            print(f"  - {fname_safe}... (score: {r['score']})")
        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more files")

    # Save to DB
    print("\n" + "=" * 70)
    print("SAVING TO DATABASE")
    print("=" * 70)

    db_path = DATA_DIR / "db" / "pokergo.db"
    print(f"\n[5] Saving to {db_path}...")
    save_to_database(results, db_path)
    print(f"    Saved {len(results)} records to content_mapping table")

    # Save JSON reports
    output_dir = DATA_DIR / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Full results
    full_results_path = output_dir / "full_episode_matching_all.json"
    with open(full_results_path, 'w', encoding='utf-8') as f:
        json.dump({
            "summary": {
                "total": total,
                "matched": matched_count,
                "likely": likely_count,
                "possible": possible_count,
                "not_uploaded": not_uploaded_count,
                "match_rate": match_rate
            },
            "results": [
                {
                    "nas_filename": r["nas_file"].get("filename"),
                    "nas_directory": r["nas_file"].get("directory"),
                    "youtube_id": r["youtube_match"].get("video_id") if r["youtube_match"] else None,
                    "youtube_title": r["youtube_match"].get("title") if r["youtube_match"] else None,
                    "score": r["score"],
                    "status": r["status"]
                }
                for r in results
            ]
        }, f, ensure_ascii=False, indent=2)
    print(f"    Full results: {full_results_path}")

    # Not uploaded report
    not_uploaded_path = output_dir / "not_uploaded_content.json"
    with open(not_uploaded_path, 'w', encoding='utf-8') as f:
        json.dump({
            "total_not_uploaded": len(not_uploaded),
            "by_directory": {
                directory: [
                    {
                        "filename": r["nas_file"].get("filename"),
                        "size_bytes": r["nas_file"].get("size_bytes"),
                        "score": r["score"]
                    }
                    for r in files
                ]
                for directory, files in by_dir.items()
            }
        }, f, ensure_ascii=False, indent=2)
    print(f"    Not uploaded: {not_uploaded_path}")

    print("\n[*] COMPLETE!")


if __name__ == "__main__":
    main()
