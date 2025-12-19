"""PokerGO matching service for NAMS."""
import re
from difflib import SequenceMatcher
from typing import Optional

from sqlalchemy.orm import Session

from ..database import AssetGroup, EventType, NasFile, PokergoEpisode, Region, get_db_context


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    if not title:
        return ""
    # Lowercase
    title = title.lower()
    # Remove file extensions
    title = re.sub(r'\.(mp4|mov|mxf|mkv)$', '', title, flags=re.I)
    # Remove special characters
    title = re.sub(r'[^\w\s]', ' ', title)
    # Remove common suffixes
    title = re.sub(r'\b(h264|nobug|nb|nc|clean)\b', '', title, flags=re.I)
    # Normalize whitespace
    title = ' '.join(title.split())
    return title


# CLASSIC Era year-to-title mapping (1973-2002: 1 Main Event per year)
CLASSIC_ERA_TITLES = {
    1973: "Wsop 1973 Main Event",
    1974: "Wsop 1974 Main Event",
    1975: "Wsop 1975 Main Event",
    1976: "Wsop 1976 Main Event",
    1977: "Wsop 1977 Main Event",
    1978: "Wsop 1978 Main Event",
    1979: "Wsop 1979 Main Event",
    1980: "Wsop 1980 Main Event",
    1981: "Wsop 1981 Main Event",
    1982: "Wsop 1982 Main Event",
    1983: "Wsop 1983 Main Event",
    1984: "Wsop 1984 Main Event",
    1985: "Wsop 1985 Main Event",
    1986: "Wsop 1986 Main Event",
    1987: "Wsop 1987 Main Event",
    1988: "Wsop 1988 Main Event",
    1989: "Wsop 1989 Main Event",
    1990: "Wsop 1990 Main Event",
    1991: "Wsop 1991 Main Event",
    1992: "Wsop 1992 Main Event",
    1993: "Wsop 1993 Main Event",
    1994: "Wsop 1994 Main Event",
    1995: "Wsop 1995 Main Event",
    1996: "Wsop 1996 Main Event",
    1997: "Wsop 1997 Main Event",
    1998: "Wsop 1998 Main Event",
    1999: "Wsop 1999 Main Event",
    2000: "Wsop 2000 Main Event",
    2001: "Wsop 2001 Main Event",
    2002: "Wsop 2002 Main Event",
}

CLASSIC_ERA_END_YEAR = 2002


def generate_catalog_title(
    group: 'AssetGroup',
    pokergo_title: Optional[str] = None,
    region_code: Optional[str] = None,
    event_type_code: Optional[str] = None,
) -> str:
    """Generate a catalog title for display.

    For CLASSIC era (1973-2002) with Part numbers, appends Part N to the title.
    This handles the case where PokerGO has a generic title but NAS has multiple parts.

    Args:
        group: AssetGroup with year, part, episode etc.
        pokergo_title: Original PokerGO title if matched
        region_code: Region code (LV, EU, APAC, etc.)
        event_type_code: Event type code (ME, BR, GM, etc.)

    Returns:
        Generated catalog title

    Examples:
        - Matched: "Wsop 2002 Main Event" + Part 1 → "Wsop 2002 Main Event Part 1"
        - Matched: "WSOP 2011 Main Event Episode 25" → same (no Part)
        - Unmatched: 2002_ME_P1 → "WSOP 2002 Main Event Part 1"
        - Unmatched: 2011_ME_25 → "WSOP 2011 Main Event Episode 25"
    """
    if not group.year:
        return pokergo_title or ""

    # If matched to PokerGO and has Part, append Part to title
    if pokergo_title:
        if group.part:
            # Check if Part is already in title
            if not re.search(rf'part\s*{group.part}', pokergo_title, re.I):
                return f"{pokergo_title} Part {group.part}"
        return pokergo_title

    # Generate title from group metadata (unmatched case)
    parts = ["WSOP", str(group.year)]

    # Add region if not LV (default)
    if region_code and region_code != 'LV':
        if region_code == 'EU':
            parts.append("Europe")
        elif region_code == 'APAC':
            parts.append("APAC")
        elif region_code == 'PARADISE':
            parts.append("Paradise")
        else:
            parts.append(region_code)

    # Add event type
    if event_type_code:
        if event_type_code == 'ME':
            parts.append("Main Event")
        elif event_type_code == 'GM':
            parts.append("Grudge Match")
        elif event_type_code == 'HU':
            parts.append("Heads Up")
        elif event_type_code == 'HR':
            parts.append("High Roller")
        elif event_type_code == 'BR':
            parts.append("Bracelet")
        else:
            parts.append(event_type_code)

    # Add episode or part
    if group.episode:
        parts.append(f"Episode {group.episode}")
    elif group.part:
        parts.append(f"Part {group.part}")
    elif group.event_num:
        parts.append(f"Event #{group.event_num}")

    return " ".join(parts)


def update_catalog_titles(db: Session) -> dict:
    """Update catalog_title for all groups.

    Generates display titles, especially for CLASSIC era groups with Parts.

    Returns:
        Statistics about title generation
    """
    stats = {
        'updated': 0,
        'with_part': 0,
        'skipped_manual': 0,
    }

    groups = db.query(AssetGroup).all()
    regions = {r.id: r.code for r in db.query(Region).all()}
    event_types = {e.id: e.code for e in db.query(EventType).all()}

    for group in groups:
        # Skip manually edited titles
        if group.catalog_title_manual:
            stats['skipped_manual'] += 1
            continue

        region_code = regions.get(group.region_id)
        event_type_code = event_types.get(group.event_type_id)

        new_title = generate_catalog_title(
            group,
            pokergo_title=group.pokergo_title,
            region_code=region_code,
            event_type_code=event_type_code,
        )

        if new_title and new_title != group.catalog_title:
            group.catalog_title = new_title
            stats['updated'] += 1

            if group.part:
                stats['with_part'] += 1

    db.commit()
    return stats


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


def extract_year_from_season(season_title: str) -> Optional[int]:
    """Extract year from season_title field (most reliable source)."""
    if not season_title:
        return None
    match = re.search(r'\b(19|20)\d{2}\b', season_title)
    if match:
        return int(match.group())
    return None


def match_classic_era(
    db: Session,
    group: AssetGroup,
    episodes: list[PokergoEpisode]
) -> tuple[Optional[PokergoEpisode], float]:
    """Match CLASSIC Era (1973-2002) files by year only.

    In CLASSIC Era, there's only 1 Main Event video per year.
    PokerGO titles vary: "Wsop 1973", "Wsop 1978 Main Event", "Wsop 2000 Me"

    CRITICAL FIX: Use season_title for year extraction to avoid
    matching buy-in amounts (e.g., "$2000 NLHE") as years.

    Returns:
        Tuple of (best_match, score)
    """
    if not group.year or group.year > CLASSIC_ERA_END_YEAR:
        return None, 0.0

    year_str = str(group.year)

    # Search for match by year (CLASSIC Era has 1 video per year)
    for episode in episodes:
        if not episode.title:
            continue

        # CRITICAL: Use season_title for year extraction (most reliable)
        # Season format: "WSOP 2000", "WSOP 1973", etc.
        ep_year = extract_year_from_season(episode.season_title)

        # Fallback: If no season, check title starts with "Wsop YYYY"
        if not ep_year:
            title_match = re.match(r'wsop\s+(19|20)\d{2}\b', episode.title.lower())
            if title_match:
                ep_year = int(title_match.group().split()[-1])

        # Year must match exactly
        if ep_year != group.year:
            continue

        title_lower = episode.title.lower()

        # Verify it's WSOP related
        if 'wsop' not in title_lower:
            continue

        # Score based on match quality
        if 'main event' in title_lower:
            return episode, 1.0
        elif title_lower.strip() == f'wsop {year_str}' or ' me' in title_lower:
            return episode, 0.98  # Year-only or ME abbreviation
        else:
            return episode, 0.95

    return None, 0.0


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

    # CLASSIC Era (1973-2002): Year-only matching (M01 fix)
    if group.year and group.year <= CLASSIC_ERA_END_YEAR:
        classic_match, classic_score = match_classic_era(db, group, episodes)
        if classic_match:
            return classic_match, classic_score

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
        title_normalized = normalize_title(episode.title)

        # Year match (important) - Use season_title first (most reliable)
        ep_year = extract_year_from_season(episode.season_title)
        if not ep_year:
            ep_year = extract_year_from_title(episode.title)

        if ep_year and group.year:
            if ep_year == group.year:
                score += 0.3
            else:
                continue  # Year mismatch - skip

        # Region match (M01 fix: more patterns)
        # Determine episode region from title
        ep_is_europe = 'europe' in title_lower or 'wsope' in title_lower
        ep_is_apac = 'asia' in title_lower or 'apac' in title_lower
        ep_is_paradise = 'paradise' in title_lower
        ep_is_cyprus = 'cyprus' in title_lower
        ep_is_regional = ep_is_europe or ep_is_apac or ep_is_paradise or ep_is_cyprus

        if region_code:
            # CRITICAL: Region matching must be explicit, not substring-based
            # 'eu' in "reunion" would cause false positives

            # First: Check region MISMATCH (must skip before scoring)
            if region_code in ('EU', 'APAC', 'PARADISE', 'CYPRUS', 'LA', 'LONDON'):
                # Non-LV groups can ONLY match regional episodes
                if region_code == 'EU' and not ep_is_europe:
                    continue  # EU group must match Europe episode
                elif region_code == 'APAC' and not ep_is_apac:
                    continue  # APAC group must match APAC episode
                elif region_code == 'PARADISE' and not ep_is_paradise:
                    continue  # PARADISE group must match Paradise episode
                elif region_code == 'CYPRUS' and not ep_is_cyprus:
                    continue  # CYPRUS group must match Cyprus episode
                elif region_code in ('LA', 'LONDON') and not ep_is_regional:
                    # LA/LONDON have no PokerGO data anyway
                    continue
            elif region_code == 'LV' and ep_is_regional:
                # LV group should NOT match regional episodes
                continue

            # Then: Add score for matching region
            if region_code == 'APAC' and ep_is_apac:
                score += 0.2
            elif region_code == 'EU' and ep_is_europe:
                score += 0.2
            elif region_code == 'PARADISE' and ep_is_paradise:
                score += 0.2
            elif region_code == 'CYPRUS' and ep_is_cyprus:
                score += 0.2
            elif region_code == 'LV' and not ep_is_regional:
                score += 0.15  # Default LV matches non-regional episodes

        # Event type match (M01 fix: more patterns + strict constraints)
        is_main_event_title = 'main event' in title_lower
        is_grudge_match_title = 'grudge match' in title_lower
        is_heads_up_title = 'heads up' in title_lower or 'heads-up' in title_lower
        is_high_roller_title = 'high roller' in title_lower or 'highroller' in title_lower
        is_bracelet_title = 'bracelet' in title_lower

        if event_type_code:
            # CRITICAL: Prevent wrong event type matches
            # GM/HU/HR/BR groups should NEVER match Main Event titles (unless title also has their type)
            if event_type_code == 'GM':
                if is_grudge_match_title:
                    score += 0.3
                elif is_main_event_title and not is_grudge_match_title:
                    continue  # Skip - GM should not match Main Event
            elif event_type_code == 'HU':
                if is_heads_up_title:
                    score += 0.3
                elif is_main_event_title and not is_heads_up_title:
                    continue  # Skip - HU should not match Main Event
            elif event_type_code == 'HR':
                if is_high_roller_title:
                    score += 0.2
                elif is_main_event_title:
                    continue  # Skip - HR should not match Main Event
            elif event_type_code == 'BR':
                if is_bracelet_title:
                    score += 0.2
                elif is_main_event_title:
                    continue  # Skip - BR should not match Main Event
            elif event_type_code == 'ME':
                if is_main_event_title:
                    score += 0.2
                # ME can match Bracelet titles (some MEs are bracelet events)
            elif event_type_code.lower() in title_lower:
                score += 0.2
        else:
            # No event_type - be very strict about what this can match
            # Groups without event_type should only match Main Event coverage
            # to prevent random bracelet event matches (BOOM era issue)
            is_bracelet_event = re.search(r'wsop\s+\d{4}\s+\d{2}\s+', title_lower, re.I)  # "Wsop 2004 05 1500 Nlh"
            if is_bracelet_event and not is_main_event_title:
                # This looks like a bracelet event by number, but group has no event_type
                # Skip to prevent wrong matches
                continue

        # Event number match (for Bracelet Events: Event #37 etc.)
        # Get event_num from group's files or group itself
        group_event_num = group.event_num
        if not group_event_num:
            first_file = db.query(NasFile).filter(NasFile.asset_group_id == group.id).first()
            if first_file:
                group_event_num = first_file.event_num

        if group_event_num:
            event_num_matched = False
            event_num_patterns = [
                rf'event\s*#?\s*{group_event_num}\b',
                rf'#\s*{group_event_num}\b',
                rf'\bevt?\s*{group_event_num}\b',  # Ev11, Evt11
            ]
            for pattern in event_num_patterns:
                if re.search(pattern, title_lower, re.I):
                    score += 0.35  # Strong bonus for matching event number
                    event_num_matched = True
                    break

            # CRITICAL: If group has event_num but episode doesn't match, SKIP
            # This prevents "Event #11 Heads Up" from matching "Main Event Episode 1"
            if not event_num_matched:
                continue

        # Episode match (M01 fix: strict episode matching)
        ep_episode = extract_episode_from_title(episode.title)
        if ep_episode and group.episode:
            if ep_episode == group.episode:
                score += 0.3
            else:
                # CRITICAL: Episode mismatch - SKIP
                # This prevents Episode 25 from matching "Episode 2"
                continue
        elif group.episode and not ep_episode:
            # Group has episode but PokerGO title doesn't have episode number
            # Allow matching only if this is the only episode for this year/type
            pass  # Continue with scoring
        elif not group.episode and ep_episode and group.year and group.year >= 2003:
            # CRITICAL: Episode-less group should NOT match episode-specific title
            # in modern era (2003+) where multiple episodes exist per year
            # Exception: CLASSIC era (1973-2002) has only 1 ME per year
            continue  # Skip - prevent 2016_ME from matching "Episode 1"

        # Collection/Season match
        if episode.collection_title:
            collection_lower = episode.collection_title.lower()
            if group.year and str(group.year) in collection_lower:
                score += 0.1
            if region_code and region_code.lower() in collection_lower:
                score += 0.1

        # Title similarity bonus (M01 fix: better normalization)
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

        # Skip groups already categorized as NAS_ONLY (no PokerGO data exists)
        if group.match_category in (MATCH_CATEGORY_NAS_ONLY_HISTORIC, MATCH_CATEGORY_NAS_ONLY_MODERN):
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


def enforce_one_to_one(db: Session) -> dict:
    """Enforce 1:1 matching rule: One PokerGO episode = One NAS group.

    ABSOLUTE PRINCIPLE: One PokerGO Title = One NAS Group (NO EXCEPTIONS)

    When multiple groups are matched to the same PokerGO episode:
    - Only the group with the highest score is kept
    - Other groups are unmatched (become NAS_ONLY)
    - Part separation is handled via Catalog Title, not by allowing N:1 matching

    Returns:
        Statistics about enforcement
    """
    from collections import defaultdict

    stats = {
        'checked_episodes': 0,
        'conflicts_found': 0,
        'groups_unmatched': 0,
    }

    # Find all PokerGO episodes with multiple group matches
    episode_to_groups = defaultdict(list)

    groups_with_match = db.query(AssetGroup).filter(
        AssetGroup.pokergo_episode_id != None
    ).all()

    for group in groups_with_match:
        episode_to_groups[group.pokergo_episode_id].append(group)

    stats['checked_episodes'] = len(episode_to_groups)

    # Process episodes with multiple matches
    for episode_id, groups in episode_to_groups.items():
        if len(groups) <= 1:
            continue

        stats['conflicts_found'] += 1

        # ABSOLUTE PRINCIPLE: Keep only the best match (highest score)
        # Sort by score descending, then by group_id for consistency
        sorted_groups = sorted(
            groups,
            key=lambda g: (g.pokergo_match_score or 0, g.group_id),
            reverse=True
        )

        # Unmatch all but the best group
        for group in sorted_groups[1:]:
            group.pokergo_episode_id = None
            group.pokergo_title = None
            group.pokergo_match_score = None
            # catalog_title will be regenerated by update_catalog_titles()
            stats['groups_unmatched'] += 1

    db.commit()
    return stats


def run_one_to_one_enforcement() -> dict:
    """Run 1:1 enforcement on all matched groups."""
    with get_db_context() as db:
        return enforce_one_to_one(db)


# Match Category Constants
MATCH_CATEGORY_MATCHED = "MATCHED"
MATCH_CATEGORY_NAS_ONLY_HISTORIC = "NAS_ONLY_HISTORIC"
MATCH_CATEGORY_NAS_ONLY_MODERN = "NAS_ONLY_MODERN"
MATCH_CATEGORY_POKERGO_ONLY = "POKERGO_ONLY"

HISTORIC_YEAR_THRESHOLD = 2011  # Years before this are considered "historic"


def calculate_match_category(group: AssetGroup) -> str:
    """Calculate match category for a group.

    Categories:
    - MATCHED: NAS exists + PokerGO matched
    - NAS_ONLY_HISTORIC: NAS exists + No PokerGO (year < 2011)
    - NAS_ONLY_MODERN: NAS exists + No PokerGO (year >= 2011)
    """
    if group.pokergo_episode_id:
        return MATCH_CATEGORY_MATCHED
    elif group.year and group.year < HISTORIC_YEAR_THRESHOLD:
        return MATCH_CATEGORY_NAS_ONLY_HISTORIC
    else:
        return MATCH_CATEGORY_NAS_ONLY_MODERN


def update_match_categories(db: Session) -> dict:
    """Update match_category for all groups.

    Returns:
        Statistics about categorization
    """
    stats = {
        MATCH_CATEGORY_MATCHED: 0,
        MATCH_CATEGORY_NAS_ONLY_HISTORIC: 0,
        MATCH_CATEGORY_NAS_ONLY_MODERN: 0,
        'total': 0,
    }

    groups = db.query(AssetGroup).all()
    stats['total'] = len(groups)

    for group in groups:
        category = calculate_match_category(group)
        group.match_category = category
        stats[category] += 1

    db.commit()
    return stats


def get_pokergo_only_episodes(db: Session) -> list[dict]:
    """Get PokerGO episodes that have no matching NAS group.

    Returns:
        List of episode info dicts
    """
    # Get all matched episode IDs
    matched_ids = set()
    groups_with_match = db.query(AssetGroup).filter(
        AssetGroup.pokergo_episode_id != None
    ).all()
    for g in groups_with_match:
        matched_ids.add(g.pokergo_episode_id)

    # Get unmatched episodes
    all_episodes = db.query(PokergoEpisode).all()
    unmatched = []

    for ep in all_episodes:
        if ep.id not in matched_ids:
            # Extract year from title or collection
            year = None
            for text in [ep.title, ep.collection_title]:
                if text:
                    match = re.search(r'\b(19|20)\d{2}\b', text)
                    if match:
                        year = int(match.group())
                        break

            unmatched.append({
                'id': ep.id,
                'title': ep.title,
                'collection_title': ep.collection_title,
                'season_title': ep.season_title,
                'year': year,
                'duration_sec': ep.duration_sec,
                'match_category': MATCH_CATEGORY_POKERGO_ONLY,
            })

    return unmatched


def get_matching_summary(db: Session) -> dict:
    """Get summary of matching categories.

    Returns:
        Dictionary with counts for each category
    """
    from sqlalchemy import func

    # NAS group categories
    category_counts = db.query(
        AssetGroup.match_category,
        func.count(AssetGroup.id)
    ).group_by(AssetGroup.match_category).all()

    summary = {
        MATCH_CATEGORY_MATCHED: 0,
        MATCH_CATEGORY_NAS_ONLY_HISTORIC: 0,
        MATCH_CATEGORY_NAS_ONLY_MODERN: 0,
        MATCH_CATEGORY_POKERGO_ONLY: 0,
        'total_nas_groups': 0,
        'total_pokergo_episodes': 0,
    }

    for category, count in category_counts:
        if category in summary:
            summary[category] = count
        summary['total_nas_groups'] += count

    # Count PokerGO only
    pokergo_only = get_pokergo_only_episodes(db)
    summary[MATCH_CATEGORY_POKERGO_ONLY] = len(pokergo_only)
    summary['total_pokergo_episodes'] = db.query(PokergoEpisode).count()

    return summary
