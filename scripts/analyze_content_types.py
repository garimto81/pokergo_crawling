"""
Analyze YouTube and NAS content types for matching strategy
"""

import json
import re
from pathlib import Path
from collections import Counter, defaultdict

DATA_DIR = Path("data")
YOUTUBE_VIDEOS = DATA_DIR / "sources/youtube/exports/videos/videos_001.json"
NAS_FILES = DATA_DIR / "sources/nas/nas_files.json"


def classify_youtube_content(title: str, duration: int = None) -> dict:
    """Classify YouTube content type"""
    title_lower = title.lower()

    # Duration-based classification
    duration_type = "unknown"
    if duration:
        if duration < 300:  # < 5 min
            duration_type = "short_clip"
        elif duration < 1200:  # 5-20 min
            duration_type = "clip"
        elif duration < 3600:  # 20-60 min
            duration_type = "episode"
        else:  # 60+ min
            duration_type = "full_episode"

    # Content type keywords
    content_type = "other"

    # Full episode patterns
    if any(kw in title_lower for kw in ["episode", "| day", "day 1", "day 2", "day 3",
                                         "final table", "part 1", "part 2", "season"]):
        content_type = "full_episode"

    # Compilation patterns
    elif any(kw in title_lower for kw in ["top 5", "top 10", "best of", "worst",
                                           "every", "all time", "compilation",
                                           "highlights", "craziest", "sickest"]):
        content_type = "compilation"

    # Interview/podcast
    elif any(kw in title_lower for kw in ["interview", "podcast", "recap",
                                           "conversation", "talks"]):
        content_type = "interview"

    # Single hand clip
    elif any(kw in title_lower for kw in ["vs", "hand", "bluff", "fold", "call",
                                           "all-in", "cooler", "bad beat"]):
        content_type = "hand_clip"

    return {
        "content_type": content_type,
        "duration_type": duration_type,
        "duration": duration
    }


def classify_nas_content(filename: str, directory: str) -> dict:
    """Classify NAS content type"""
    combined = (filename + " " + directory).lower()

    content_type = "other"

    # Hand clips
    if "hand clip" in combined or "subclip" in combined or "_hand_" in combined:
        content_type = "hand_clip"

    # Stream/VOD
    elif "stream" in combined:
        content_type = "stream"

    # Full episode
    elif any(kw in combined for kw in ["episode", "day 1", "day 2", "day 3",
                                        "final table", "main event", "bracelet"]):
        content_type = "full_episode"

    # Clean/mastered clips
    elif "clean" in combined or "mastered" in combined:
        content_type = "mastered_clip"

    return {
        "content_type": content_type,
        "directory": directory
    }


def main():
    print("=" * 70)
    print("YouTube vs NAS Content Type Analysis")
    print("=" * 70)

    # Load YouTube data
    with open(YOUTUBE_VIDEOS, 'r', encoding='utf-8') as f:
        yt_data = json.load(f)
    youtube_videos = yt_data.get("videos", [])

    # Load NAS data
    with open(NAS_FILES, 'r', encoding='utf-8') as f:
        nas_data = json.load(f)
    nas_files = nas_data.get("files", [])

    print(f"\nTotal YouTube: {len(youtube_videos)}")
    print(f"Total NAS: {len(nas_files)}")

    # Analyze YouTube content types
    print("\n" + "=" * 70)
    print("YOUTUBE CONTENT ANALYSIS")
    print("=" * 70)

    yt_content_types = Counter()
    yt_duration_types = Counter()
    yt_full_episodes = []

    for video in youtube_videos:
        info = classify_youtube_content(video.get("title", ""), video.get("duration"))
        yt_content_types[info["content_type"]] += 1
        yt_duration_types[info["duration_type"]] += 1

        if info["content_type"] == "full_episode" or info["duration_type"] == "full_episode":
            yt_full_episodes.append(video)

    print("\n[Content Types]")
    for ct, count in yt_content_types.most_common():
        print(f"  {ct:20s}: {count:4d} ({count/len(youtube_videos)*100:.1f}%)")

    print("\n[Duration Types]")
    for dt, count in yt_duration_types.most_common():
        print(f"  {dt:20s}: {count:4d} ({count/len(youtube_videos)*100:.1f}%)")

    print(f"\n[Full Episodes (matchable)]: {len(yt_full_episodes)}")
    print("\nSample full episodes:")
    for v in yt_full_episodes[:10]:
        dur = v.get("duration", 0)
        dur_str = f"{dur//3600}h{(dur%3600)//60}m" if dur else "?"
        print(f"  - [{dur_str}] {v['title'][:60]}...")

    # Analyze NAS content types
    print("\n" + "=" * 70)
    print("NAS CONTENT ANALYSIS")
    print("=" * 70)

    nas_content_types = Counter()
    nas_by_type = defaultdict(list)

    for f in nas_files:
        info = classify_nas_content(f.get("filename", ""), f.get("directory", ""))
        nas_content_types[info["content_type"]] += 1
        nas_by_type[info["content_type"]].append(f)

    print("\n[Content Types]")
    for ct, count in nas_content_types.most_common():
        print(f"  {ct:20s}: {count:4d} ({count/len(nas_files)*100:.1f}%)")

    # Sample each NAS type
    for ct in ["full_episode", "hand_clip", "mastered_clip", "stream"]:
        if nas_by_type[ct]:
            print(f"\n[Sample NAS {ct}]:")
            for f in nas_by_type[ct][:5]:
                print(f"  - {f['filename'][:55]}...")

    # Matching potential analysis
    print("\n" + "=" * 70)
    print("MATCHING POTENTIAL")
    print("=" * 70)

    print(f"""
    +-------------------------+----------+----------+
    | Content Type            | YouTube  |   NAS    |
    +-------------------------+----------+----------+
    | Full Episodes           | {len(yt_full_episodes):>8} | {nas_content_types['full_episode']:>8} |
    | Hand Clips              | {yt_content_types['hand_clip']:>8} | {nas_content_types['hand_clip']:>8} |
    | Compilations            | {yt_content_types['compilation']:>8} | {nas_content_types.get('compilation', 0):>8} |
    | Stream/VOD              | {0:>8} | {nas_content_types['stream']:>8} |
    +-------------------------+----------+----------+
    """)

    # Year distribution
    print("\n[Year Distribution - YouTube Full Episodes]")
    year_pattern = re.compile(r'20[0-2][0-9]|19[7-9][0-9]')
    yt_years = Counter()
    for v in yt_full_episodes:
        match = year_pattern.search(v.get("title", ""))
        if match:
            yt_years[match.group()] += 1
        else:
            yt_years["unknown"] += 1

    for year, count in sorted(yt_years.items()):
        print(f"  {year}: {count}")

    print("\n[Year Distribution - NAS Full Episodes]")
    nas_years = Counter()
    for f in nas_by_type["full_episode"]:
        match = year_pattern.search(f.get("directory", "") + f.get("filename", ""))
        if match:
            nas_years[match.group()] += 1
        else:
            nas_years["unknown"] += 1

    for year, count in sorted(nas_years.items())[:15]:
        print(f"  {year}: {count}")

    # Recommendation
    print("\n" + "=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)
    print("""
    1. FULL EPISODE MATCHING (High confidence)
       - YouTube full episodes -> NAS full episodes
       - Match by: Year + Event + Day/Episode number

    2. HAND CLIP MATCHING (Medium confidence)
       - YouTube hand clips -> NAS hand clips
       - Match by: Player names + Hand description

    3. EXCLUDE FROM MATCHING
       - YouTube compilations (edited from multiple sources)
       - YouTube interviews/podcasts (no NAS equivalent)
    """)


if __name__ == "__main__":
    main()
