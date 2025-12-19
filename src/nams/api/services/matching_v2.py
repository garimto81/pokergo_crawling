"""PokerGO matching service v2 for NAMS.

규칙 문서 기반 재설계:
- PokerGO Title에서 정확한 매칭 키 추출
- Main Event: Year + Episode
- Bracelet: Year + Event#
- Key 기반 매칭
- 컬렉션/시즌 헤더 제외
"""
import re
from typing import NamedTuple

from sqlalchemy.orm import Session

from ..database import AssetGroup, EventType, PokergoEpisode, Region, get_db_context


def is_actual_episode(title: str) -> bool:
    """실제 에피소드인지 확인 (컬렉션/시즌 헤더 제외).

    제외 대상:
    - "WSOP 2011 Main Event" (단독 시즌명)
    - "WSOP 2012 Bracelet Events" (단독 시즌명)
    - "... | Episodes" (시즌 헤더)
    - "... | Livestreams" (시즌 헤더)
    - "WSOP YYYY Bracelet Events | Event #N ..." (Day/Part/Final 없는 상위 헤더)
    """
    if not title:
        return False

    title = title.strip()

    # 시즌 헤더 제외 (| Episodes, | Livestreams로 끝나는 것)
    if title.endswith('| Episodes') or title.endswith('| Livestreams'):
        return False

    # 단독 시즌명 제외 (예: "WSOP 2011 Main Event", "WSOP 2012 Bracelet Events")
    if re.match(r'^WSOP[E]?\s*\d{4}\s*(Main Event|Bracelet Events)$', title, re.I):
        return False

    # Bracelet Event 상위 헤더 제외
    # "WSOP YYYY Bracelet Events | Event #N ..." 형태이지만 Day/Part/Final이 없는 경우
    if 'bracelet' in title.lower() and 'event #' in title.lower():
        has_detail = any(kw in title.lower() for kw in ['day ', 'part ', 'final'])
        if not has_detail:
            return False

    # 실제 에피소드 키워드 확인
    episode_keywords = [
        r'episode\s*\d+',      # Episode 1, Episode 25
        r'event\s*#?\s*\d+',   # Event #1, Event 85
        r'day\s*\d+',          # Day 1A, Day 2
        r'\(part\s*\d+\)',     # (Part 1), (Part 2)
        r'final\s*table',      # Final Table
        r'heads[\-\s]?up',     # Heads-Up, Heads Up
        r'\bvs\.?\b',          # vs, vs.
        r'grudge\s*match',     # Grudge Match
        r'stand\s*up\s*for',   # Stand Up for Me, Please
    ]

    for pattern in episode_keywords:
        if re.search(pattern, title, re.I):
            return True

    return False


class PokergoMatchKey(NamedTuple):
    """PokerGO 매칭 키."""
    year: int
    event_type: str  # ME, BR, GM, HU, EU, APAC, etc.
    episode: int | None  # Episode number or Event number
    day: str | None  # Day 1A, 1B, etc.
    region: str | None  # EU, APAC, PARADISE


def extract_pokergo_match_key(episode: PokergoEpisode) -> PokergoMatchKey | None:
    """PokerGO 에피소드에서 매칭 키 추출.

    Title 패턴:
    - "WSOP 2024 Main Event | Episode 1" → LV, ME, Episode=1
    - "WSOP 2025 Main Event | Day 1A" → LV, ME, Day=1A
    - "WSOP 2024 Bracelet Events | Event #1 ..." → LV, BR, Event=1
    - "WSOPE 2011 Episode 1" → EU, ME, Episode=1  (별도 대회!)
    - "WSOP Europe 2021 ..." → EU

    중요: WSOP와 WSOPE는 별도 대회
    - WSOP = Las Vegas (기본)
    - WSOPE = WSOP Europe → Region=EU
    """
    title = episode.title or ""
    season = episode.season_title or ""
    collection = episode.collection_title or ""

    # Extract year
    year = None
    for text in [title, season, collection]:
        if text:
            match = re.search(r'\b(19|20)\d{2}\b', text)
            if match:
                year = int(match.group())
                break

    if not year:
        return None

    title_lower = title.lower()
    season_lower = season.lower()
    collection_lower = collection.lower()
    all_text = f"{title_lower} {season_lower} {collection_lower}"

    # Determine region (우선순위: WSOPE > APAC > PARADISE > LV)
    region = None  # None = Las Vegas (기본)

    # WSOPE 감지 (WSOP Europe는 별도 대회!)
    if 'wsope' in all_text or 'wsop europe' in all_text or 'wsop-europe' in all_text:
        region = 'EU'
    elif 'apac' in all_text or 'asia pacific' in all_text:
        region = 'APAC'
    elif 'paradise' in all_text:
        region = 'PARADISE'
    # WSOP만 있으면 Las Vegas (기본, region=None)

    # Determine event type and extract episode/event number
    event_type = None
    episode_num = None
    day = None

    # Main Event
    if 'main event' in season_lower:
        event_type = 'ME'

        # Episode pattern: "Episode 1", "Episode 25"
        ep_match = re.search(r'episode\s*(\d+)', title_lower)
        if ep_match:
            episode_num = int(ep_match.group(1))

        # Day pattern: "Day 1A", "Day 2", "Day 1A/B/C"
        day_match = re.search(r'day\s*(\d+[a-d]?)', title_lower)
        if day_match:
            day = day_match.group(1).upper()

    # Bracelet Events
    elif 'bracelet' in season_lower:
        # Check for special event types within Bracelet
        if 'grudge match' in title_lower:
            event_type = 'GM'
            # Grudge Match는 자동 매칭 불가 (수작업 필요)
            episode_num = None
        elif 'heads-up' in title_lower or 'heads up' in title_lower:
            event_type = 'HU'
            # Heads-Up Championship: Semifinals=1, Final=2
            if 'semifinals' in title_lower:
                episode_num = 1
            elif 'final' in title_lower:
                episode_num = 2
            else:
                # Event # pattern fallback
                ev_match = re.search(r'event\s*#?\s*(\d+)', title_lower)
                if ev_match:
                    episode_num = int(ev_match.group(1))
        else:
            event_type = 'BR'
            # Event # pattern: "Event #1", "Event #85"
            ev_match = re.search(r'event\s*#?\s*(\d+)', title_lower)
            if ev_match:
                episode_num = int(ev_match.group(1))

    # Other patterns
    elif 'grudge match' in title_lower:
        event_type = 'GM'
    elif 'heads-up' in title_lower or 'heads up' in title_lower:
        event_type = 'HU'
    elif 'high roller' in title_lower:
        event_type = 'HR'
    elif 'final table' in title_lower:
        event_type = 'FT'
    elif 'best of' in title_lower:
        event_type = 'BEST'
    elif region == 'EU':
        event_type = 'EU'
        # Europe episode pattern
        ep_match = re.search(r'episode\s*(\d+)', title_lower)
        if ep_match:
            episode_num = int(ep_match.group(1))
    else:
        # Unknown type
        event_type = 'UNK'

    return PokergoMatchKey(
        year=year,
        event_type=event_type,
        episode=episode_num,
        day=day,
        region=region,
    )


def extract_nas_match_key(
    group: AssetGroup, event_types: dict, regions: dict
) -> PokergoMatchKey | None:
    """NAS 그룹에서 매칭 키 추출."""
    if not group.year:
        return None

    # Get event type code
    event_type_code = 'UNK'
    if group.event_type_id and group.event_type_id in event_types:
        event_type_code = event_types[group.event_type_id]

    # Get region code
    region_code = None
    if group.region_id and group.region_id in regions:
        region_code = regions[group.region_id]
        if region_code == 'LV':
            region_code = None  # Las Vegas is default

    return PokergoMatchKey(
        year=group.year,
        event_type=event_type_code,
        episode=group.episode,
        day=None,
        region=region_code,
    )


def match_keys(nas_key: PokergoMatchKey, pokergo_key: PokergoMatchKey) -> tuple[bool, float, str]:
    """두 매칭 키 비교.

    Returns:
        (is_match, score, reason)
    """
    # Year must match
    if nas_key.year != pokergo_key.year:
        return False, 0.0, "Year mismatch"

    # Region must match
    if nas_key.region != pokergo_key.region:
        return False, 0.0, f"Region mismatch: NAS={nas_key.region}, PG={pokergo_key.region}"

    score = 0.3  # Year + Region match base score
    reasons = []

    # Event type match
    type_match = False

    # Direct match
    if nas_key.event_type == pokergo_key.event_type:
        type_match = True
        score += 0.3
        reasons.append(f"Type exact match: {nas_key.event_type}")

    # Main Event variations
    elif nas_key.event_type == 'ME' and pokergo_key.event_type in ('ME', 'HU', 'GM'):
        # HU and GM are often part of Main Event series in PokerGO
        if pokergo_key.event_type == 'ME':
            type_match = True
            score += 0.3
            reasons.append("Type match: Main Event")

    # Bracelet includes HU events
    elif nas_key.event_type == 'BR' and pokergo_key.event_type in ('BR', 'HU'):
        type_match = True
        score += 0.2
        reasons.append(f"Type match: Bracelet/{pokergo_key.event_type}")

    if not type_match:
        return False, score, f"Type mismatch: NAS={nas_key.event_type}, PG={pokergo_key.event_type}"

    # Episode/Event number match
    if nas_key.episode and pokergo_key.episode:
        if nas_key.episode == pokergo_key.episode:
            score += 0.4
            reasons.append(f"Episode exact match: {nas_key.episode}")
            return True, score, " | ".join(reasons)
        else:
            # Episode mismatch but type matches
            mismatch_msg = (
                f"Episode mismatch: NAS={nas_key.episode}, PG={pokergo_key.episode}"
            )
            return False, score * 0.5, mismatch_msg

    # Day match (for Main Event without episode)
    if nas_key.event_type == 'ME' and not nas_key.episode and pokergo_key.day:
        # Main Event without episode can match Day content
        score += 0.2
        reasons.append(f"Day content: {pokergo_key.day}")
        return True, score, " | ".join(reasons)

    # Episode not specified - partial match
    if not nas_key.episode and pokergo_key.episode:
        score += 0.1
        reasons.append(f"Partial: NAS no episode, PG has episode {pokergo_key.episode}")
        return True, score, " | ".join(reasons)

    return True, score, " | ".join(reasons) if reasons else "Year+Region+Type match"


def run_matching_v2(db: Session, min_score: float = 0.5, clear_existing: bool = False) -> dict:
    """키 기반 매칭 실행.

    Args:
        db: Database session
        min_score: Minimum score to accept match
        clear_existing: Clear existing matches before running

    Returns:
        Statistics about matching
    """
    stats = {
        'total_groups': 0,
        'total_episodes': 0,
        'matched': 0,
        'skipped_no_year': 0,
        'skipped_no_match': 0,
        'match_details': {},
    }

    # Clear existing matches if requested
    if clear_existing:
        db.query(AssetGroup).update({
            'pokergo_episode_id': None,
            'pokergo_title': None,
            'pokergo_match_score': None,
        })
        db.commit()

    # Get lookup tables
    event_types = {et.id: et.code for et in db.query(EventType).all()}
    regions = {r.id: r.code for r in db.query(Region).all()}

    # Get all groups
    groups = db.query(AssetGroup).all()
    stats['total_groups'] = len(groups)

    # Get all WSOP PokerGO episodes (실제 에피소드만, 시즌 헤더 제외)
    all_episodes = db.query(PokergoEpisode).filter(
        PokergoEpisode.title.ilike('%WSOP%') |
        PokergoEpisode.collection_title.ilike('%WSOP%')
    ).all()

    # Filter out collection/season headers
    episodes = [ep for ep in all_episodes if is_actual_episode(ep.title)]
    stats['total_episodes'] = len(episodes)
    stats['filtered_headers'] = len(all_episodes) - len(episodes)

    # Build episode index by key
    episode_index = {}
    for ep in episodes:
        key = extract_pokergo_match_key(ep)
        if key:
            # Index by (year, type, episode) if episode exists
            if key.episode:
                idx_key = (key.year, key.event_type, key.episode, key.region)
                if idx_key not in episode_index:
                    episode_index[idx_key] = []
                episode_index[idx_key].append((ep, key))

            # Also index by (year, type) for partial matches
            idx_key_partial = (key.year, key.event_type, None, key.region)
            if idx_key_partial not in episode_index:
                episode_index[idx_key_partial] = []
            episode_index[idx_key_partial].append((ep, key))

    # Match groups
    for group in groups:
        # Skip if already matched (unless clearing)
        if group.pokergo_episode_id and not clear_existing:
            continue

        nas_key = extract_nas_match_key(group, event_types, regions)
        if not nas_key:
            stats['skipped_no_year'] += 1
            continue

        best_match = None
        best_score = 0.0

        # Try exact match first
        if nas_key.episode:
            idx_key = (nas_key.year, nas_key.event_type, nas_key.episode, nas_key.region)
            candidates = episode_index.get(idx_key, [])

            for ep, pg_key in candidates:
                is_match, score, reason = match_keys(nas_key, pg_key)
                if is_match and score > best_score:
                    best_match = ep
                    best_score = score

        # Try partial match if no exact match
        if not best_match:
            idx_key_partial = (nas_key.year, nas_key.event_type, None, nas_key.region)
            candidates = episode_index.get(idx_key_partial, [])

            for ep, pg_key in candidates:
                is_match, score, reason = match_keys(nas_key, pg_key)
                if is_match and score > best_score:
                    best_match = ep
                    best_score = score

        # Apply match if score meets threshold
        if best_match and best_score >= min_score:
            group.pokergo_episode_id = best_match.id
            group.pokergo_title = best_match.title
            group.pokergo_match_score = best_score
            stats['matched'] += 1

            # Track match details
            match_type = f"{nas_key.event_type}_{nas_key.year}"
            if match_type not in stats['match_details']:
                stats['match_details'][match_type] = 0
            stats['match_details'][match_type] += 1
        else:
            stats['skipped_no_match'] += 1

    db.commit()
    return stats


def run_matching_v2_standalone(min_score: float = 0.5, clear_existing: bool = False) -> dict:
    """Standalone 매칭 실행."""
    with get_db_context() as db:
        return run_matching_v2(db, min_score, clear_existing)


def analyze_unmatched(db: Session) -> dict:
    """미매칭 분석."""
    # Get lookup tables
    event_types = {et.id: et.code for et in db.query(EventType).all()}
    {r.id: r.code for r in db.query(Region).all()}

    # Groups without match
    unmatched_groups = db.query(AssetGroup).filter(
        AssetGroup.pokergo_episode_id is None
    ).all()

    # Analyze by type and year
    analysis = {
        'total_unmatched': len(unmatched_groups),
        'by_type': {},
        'by_year': {},
        'samples': [],
    }

    for g in unmatched_groups:
        et_code = event_types.get(g.event_type_id, 'UNK')
        year = g.year or 0

        if et_code not in analysis['by_type']:
            analysis['by_type'][et_code] = 0
        analysis['by_type'][et_code] += 1

        if year not in analysis['by_year']:
            analysis['by_year'][year] = 0
        analysis['by_year'][year] += 1

        # Sample first 10
        if len(analysis['samples']) < 10:
            analysis['samples'].append({
                'group_id': g.group_id,
                'year': g.year,
                'type': et_code,
                'episode': g.episode,
            })

    return analysis
