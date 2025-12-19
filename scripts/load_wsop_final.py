"""Load wsop_final.json data into pokergo_episodes table.

This script imports 828 WSOP videos including:
- CLASSIC Era (1973-2002): 20 videos
- BOOM Era (2003-2010): 236 videos
- HD Era (2011-2025): 572 videos
- WSOP Europe: 36 videos
"""
import json
import sys
import io
import re
from pathlib import Path

# UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.database import get_db_context, PokergoEpisode


def extract_year_from_title(title: str) -> int | None:
    """Extract year from title."""
    match = re.search(r'\b(19[7-9]\d|20[0-2]\d)\b', title)
    if match:
        return int(match.group(1))
    return None


def extract_episode_from_title(title: str) -> int | None:
    """Extract episode number from title."""
    patterns = [
        r'Episode\s*(\d+)',
        r'Ep\.?\s*(\d+)',
        r'Part\s*(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, title, re.I)
        if match:
            return int(match.group(1))
    return None


def determine_collection(title: str) -> str:
    """Determine collection based on title."""
    title_lower = title.lower()
    if 'europe' in title_lower:
        return 'WSOP Europe'
    elif 'bracelet' in title_lower:
        return 'WSOP Bracelet Events'
    elif 'main event' in title_lower or ' me' in title_lower:
        return 'WSOP Main Event'
    else:
        return 'WSOP'


def load_wsop_final():
    """Load wsop_final.json into pokergo_episodes table."""
    json_path = Path(__file__).parent.parent / 'data' / 'pokergo' / 'wsop_final.json'

    if not json_path.exists():
        print(f"File not found: {json_path}")
        return

    with open(json_path, encoding='utf-8') as f:
        videos = json.load(f)

    print(f"Loading {len(videos)} videos from wsop_final.json")

    stats = {
        'total': len(videos),
        'inserted': 0,
        'skipped': 0,
        'errors': 0,
    }

    with get_db_context() as db:
        for video in videos:
            title = video.get('title', '')
            year = video.get('year')
            url = video.get('url', '')
            slug = video.get('slug', '')

            # Extract year from title if not provided
            if not year or not str(year).isdigit():
                year = extract_year_from_title(title)
            else:
                year = int(year)

            # Check if already exists
            existing = db.query(PokergoEpisode).filter(
                PokergoEpisode.title == title
            ).first()

            if existing:
                stats['skipped'] += 1
                continue

            try:
                # Use slug as id (required primary key)
                episode_id = slug or title.lower().replace(' ', '-').replace('|', '').replace('#', '')

                episode = PokergoEpisode(
                    id=episode_id,
                    title=title,
                    collection_title=determine_collection(title),
                    season_title=f"WSOP {year}" if year else None,
                    description=f"Source: {url}",
                    duration_sec=0,  # Not available in this data
                )
                db.add(episode)
                stats['inserted'] += 1
            except Exception as e:
                print(f"Error inserting {title}: {e}")
                stats['errors'] += 1

        db.commit()

    print()
    print("=== Load Complete ===")
    print(f"Total: {stats['total']}")
    print(f"Inserted: {stats['inserted']}")
    print(f"Skipped (duplicate): {stats['skipped']}")
    print(f"Errors: {stats['errors']}")

    # Verify
    with get_db_context() as db:
        count = db.query(PokergoEpisode).count()
        print(f"\nTotal pokergo_episodes in DB: {count}")


if __name__ == '__main__':
    load_wsop_final()
