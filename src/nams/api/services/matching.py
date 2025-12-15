"""PokerGO matching service for NAMS."""
import re
from difflib import SequenceMatcher
from typing import Optional
from sqlalchemy.orm import Session

from ..database import AssetGroup, PokergoEpisode, Region, EventType, get_db_context


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    if not title:
        return ""
    # Lowercase
    title = title.lower()
    # Remove special characters
    title = re.sub(r'[^\w\s]', ' ', title)
    # Normalize whitespace
    title = ' '.join(title.split())
    return title


def extract_year_from_title(title: str) -> Optional[int]:
    """Extract year from title."""
    # Look for 4-digit year
    match = re.search(r'\b(19|20)\d{2}\b', title)
    if match:
        return int(match.group())
    return None


def extract_episode_from_title(title: str) -> Optional[int]:
    """Extract episode number from title."""
    # Look for Episode N, Ep N, #N patterns
    patterns = [
        r'episode\s*(\d+)',
        r'ep\.?\s*(\d+)',
        r'#(\d+)',
        r'\bpart\s*(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, title, re.I)
        if match:
            return int(match.group(1))
    return None


def calculate_similarity(s1: str, s2: str) -> float:
    """Calculate similarity between two strings."""
    return SequenceMatcher(None, normalize_title(s1), normalize_title(s2)).ratio()


def match_group_to_pokergo(
    db: Session,
    group: AssetGroup,
    episodes: list[PokergoEpisode]
) -> tuple[Optional[PokergoEpisode], float]:
    """Find best matching PokerGO episode for a group.

    Returns:
        Tuple of (best_match, score)
    """
    if not episodes:
        return None, 0.0

    # Build search terms from group
    search_terms = []

    # Get region and event type names
    region = db.query(Region).get(group.region_id) if group.region_id else None
    event_type = db.query(EventType).get(group.event_type_id) if group.event_type_id else None

    region_name = region.name if region else ""
    region_code = region.code if region else ""
    event_type_name = event_type.name if event_type else ""
    event_type_code = event_type.code if event_type else ""

    # Build expected title patterns
    if group.year:
        search_terms.append(str(group.year))
    if region_code:
        search_terms.append(region_code)
        if region_code == 'APAC':
            search_terms.append('asia')
        elif region_code == 'EU':
            search_terms.append('europe')
    if event_type_code:
        search_terms.append(event_type_code)
        if event_type_code == 'ME':
            search_terms.append('main event')
    if group.episode:
        search_terms.append(f'episode {group.episode}')

    best_match = None
    best_score = 0.0

    for episode in episodes:
        if not episode.title:
            continue

        score = 0.0
        title_lower = episode.title.lower()

        # Year match (important)
        ep_year = extract_year_from_title(episode.title)
        if ep_year and group.year:
            if ep_year == group.year:
                score += 0.3
            else:
                continue  # Year mismatch - skip

        # Region match
        if region_code:
            if region_code.lower() in title_lower:
                score += 0.2
            elif region_code == 'APAC' and 'asia' in title_lower:
                score += 0.2
            elif region_code == 'EU' and 'europe' in title_lower:
                score += 0.2
            elif region_code == 'PARADISE' and 'paradise' in title_lower:
                score += 0.2

        # Event type match
        if event_type_code:
            if event_type_code.lower() in title_lower:
                score += 0.2
            elif event_type_code == 'ME' and 'main event' in title_lower:
                score += 0.2

        # Episode match
        ep_episode = extract_episode_from_title(episode.title)
        if ep_episode and group.episode:
            if ep_episode == group.episode:
                score += 0.3

        # Collection/Season match
        if episode.collection_title:
            collection_lower = episode.collection_title.lower()
            if group.year and str(group.year) in collection_lower:
                score += 0.1
            if region_code and region_code.lower() in collection_lower:
                score += 0.1

        # Title similarity bonus
        group_title = f"WSOP {group.year} {region_code} {event_type_code} Episode {group.episode}"
        similarity = calculate_similarity(group_title, episode.title)
        score += similarity * 0.2

        if score > best_score:
            best_score = score
            best_match = episode

    # Normalize score to 0-1
    best_score = min(best_score, 1.0)

    return best_match, best_score


def run_pokergo_matching(db: Session, min_score: float = 0.5) -> dict:
    """Match unmatched groups to PokerGO episodes.

    Args:
        db: Database session
        min_score: Minimum score to accept match

    Returns:
        Statistics about matching
    """
    stats = {
        'processed': 0,
        'matched': 0,
        'skipped': 0,
    }

    # Get groups without PokerGO match
    groups = db.query(AssetGroup).filter(
        AssetGroup.pokergo_episode_id == None
    ).all()

    stats['processed'] = len(groups)

    # Get all PokerGO episodes
    episodes = db.query(PokergoEpisode).all()

    if not episodes:
        return stats

    for group in groups:
        # Skip groups without year
        if not group.year:
            stats['skipped'] += 1
            continue

        # Find best match
        best_match, score = match_group_to_pokergo(db, group, episodes)

        if best_match and score >= min_score:
            group.pokergo_episode_id = best_match.id
            group.pokergo_title = best_match.title
            group.pokergo_match_score = score
            stats['matched'] += 1

    db.commit()
    return stats


def run_matching(min_score: float = 0.5) -> dict:
    """Run PokerGO matching on all unmatched groups."""
    with get_db_context() as db:
        return run_pokergo_matching(db, min_score)
