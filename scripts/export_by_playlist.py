"""Export YouTube videos organized by playlist."""
import subprocess
import json
import os
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

SNAPSHOT_DIR = Path("data/sources/youtube/snapshots/2025-12-12_142644")
EXPORT_DIR = Path("data/sources/youtube/exports")
PLAYLISTS_DIR = EXPORT_DIR / "playlists"

def slugify(text):
    """Convert text to URL-safe slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')[:50]

def load_video_metadata():
    """Load all video metadata from snapshot."""
    videos = {}
    videos_dir = SNAPSHOT_DIR / "videos"
    for fname in videos_dir.glob("*.json"):
        with open(fname, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for v in data.get('videos', []):
                videos[v['video_id']] = v
    return videos

def fetch_playlist_videos(playlist_id, playlist_title):
    """Fetch video IDs from a playlist using yt-dlp."""
    cmd = [
        'yt-dlp',
        '--flat-playlist',
        '--dump-json',
        f'https://www.youtube.com/playlist?list={playlist_id}'
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        video_ids = []
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    data = json.loads(line)
                    video_ids.append(data.get('id'))
                except:
                    pass
        return playlist_id, playlist_title, video_ids
    except Exception as e:
        print(f"  Error fetching {playlist_title}: {e}")
        return playlist_id, playlist_title, []

def main():
    # Load playlists
    with open(SNAPSHOT_DIR / "playlists/playlists.json", 'r', encoding='utf-8') as f:
        playlists = json.load(f)['playlists']

    print(f"Loading video metadata...")
    all_videos = load_video_metadata()
    print(f"Loaded {len(all_videos)} videos")

    # Create export directory
    PLAYLISTS_DIR.mkdir(parents=True, exist_ok=True)

    # Fetch playlist videos in parallel
    print(f"\nFetching {len(playlists)} playlists...")
    playlist_videos = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(fetch_playlist_videos, p['playlist_id'], p['title']): p
            for p in playlists
        }

        for i, future in enumerate(as_completed(futures), 1):
            playlist_id, title, video_ids = future.result()
            playlist_videos[playlist_id] = video_ids
            print(f"  [{i}/{len(playlists)}] {title[:40]}: {len(video_ids)} videos")

    # Create playlist JSON files and index
    index = {
        "version": "3.0",
        "structure": "by_playlist",
        "total_videos": len(all_videos),
        "total_playlists": len(playlists),
        "playlists": []
    }

    print(f"\nCreating playlist files...")
    for p in playlists:
        pid = p['playlist_id']
        video_ids = playlist_videos.get(pid, [])

        # Get full video data
        videos = []
        total_duration = 0
        for vid in video_ids:
            if vid in all_videos:
                v = all_videos[vid]
                videos.append(v)
                total_duration += v.get('duration', 0) or 0

        if not videos:
            continue

        slug = slugify(p['title'])
        filename = f"{slug}.json"
        filepath = PLAYLISTS_DIR / filename

        # Format duration
        hours, remainder = divmod(total_duration, 3600)
        minutes = remainder // 60
        duration_str = f"{hours}h {minutes}m"

        playlist_data = {
            "playlist_id": pid,
            "slug": slug,
            "name": p['title'],
            "count": len(videos),
            "videos": videos
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(playlist_data, f, ensure_ascii=False)

        file_size = filepath.stat().st_size

        index['playlists'].append({
            "playlist_id": pid,
            "slug": slug,
            "name": p['title'],
            "count": len(videos),
            "duration": duration_str,
            "file": f"playlists/{filename}",
            "size": file_size
        })

    # Sort by video count descending
    index['playlists'].sort(key=lambda x: x['count'], reverse=True)

    # Save index
    with open(EXPORT_DIR / "index_v3.json", 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Created {len(index['playlists'])} playlist files")
    print(f"Index: {EXPORT_DIR / 'index_v3.json'}")

if __name__ == "__main__":
    main()
