"""Category-based PokerGO matching service for NAMS.

Phase 2: 하이브리드 매칭 엔진
- CategoryEntry를 PokerGO 에피소드와 매칭
- match_type: EXACT, PARTIAL, MANUAL, NONE
- source: POKERGO, NAS_ONLY
"""
import re
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db_context
from ..database.models import Category, CategoryEntry, PokergoEpisode

# =============================================================================
# Match Type Constants
# =============================================================================

MATCH_TYPE_EXACT = "EXACT"      # PokerGO 1:1 완전 매칭
MATCH_TYPE_PARTIAL = "PARTIAL"  # 부분 매칭 (검증 필요)
MATCH_TYPE_MANUAL = "MANUAL"    # 수동 지정
MATCH_TYPE_NONE = "NONE"        # 매칭 없음 (자체 생성)

SOURCE_POKERGO = "POKERGO"
SOURCE_NAS_ONLY = "NAS_ONLY"

# CLASSIC Era: 1973-2002 (1 Main Event per year)
CLASSIC_ERA_END = 2002


# =============================================================================
# Match Key
# =============================================================================

@dataclass
class MatchKey:
    """매칭 키 - 연도, 이벤트, 에피소드 기반."""
    year: int
    region: str | None = None  # LV, EU, APAC, PARADISE, CYPRUS
    event_type: str | None = None  # ME, BR, HU, GM, HR
    episode: int | None = None  # Episode/Day/Part number
    event_num: int | None = None  # Bracelet Event #N


@dataclass
class MatchResult:
    """매칭 결과."""
    match_type: str
    score: float
    pokergo_ep_id: str | None = None
    pokergo_title: str | None = None
    reason: str = ""


# =============================================================================
# PokerGO Key Extraction
# =============================================================================

def extract_year_from_text(text: str) -> int | None:
    """텍스트에서 연도 추출."""
    if not text:
        return None
    match = re.search(r'\b(19[7-9]\d|20[0-2]\d)\b', text)
    return int(match.group()) if match else None


def extract_episode_from_text(text: str) -> int | None:
    """텍스트에서 에피소드 번호 추출."""
    if not text:
        return None
    patterns = [
        r'episode\s*(\d+)',
        r'ep\.?\s*(\d+)',
        r'day\s*(\d+)',
        r'part\s*(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return int(match.group(1))
    return None


def extract_event_num_from_text(text: str) -> int | None:
    """텍스트에서 이벤트 번호 추출 (Bracelet Event #N)."""
    if not text:
        return None
    match = re.search(r'event\s*#?\s*(\d+)', text, re.I)
    return int(match.group(1)) if match else None


def extract_pokergo_key(episode: PokergoEpisode) -> MatchKey | None:
    """PokerGO 에피소드에서 매칭 키 추출."""
    title = episode.title or ""
    season = episode.season_title or ""
    collection = episode.collection_title or ""
    all_text = f"{title} {season} {collection}".lower()

    # Year extraction (season_title이 가장 신뢰도 높음)
    year = extract_year_from_text(season) or extract_year_from_text(title)
    if not year:
        return None

    # Region detection
    region = None
    if 'wsope' in all_text or 'europe' in all_text:
        region = 'EU'
    elif 'apac' in all_text or 'asia' in all_text:
        region = 'APAC'
    elif 'paradise' in all_text:
        region = 'PARADISE'
    elif 'cyprus' in all_text:
        region = 'CYPRUS'
    # LV는 기본값 (region=None)

    # Event type detection
    # Bracelet Events는 최우선 - 개별 이벤트 타입보다 우선
    event_type = None
    if 'bracelet' in all_text:
        event_type = 'BR'
    elif 'main event' in all_text:
        event_type = 'ME'
    elif 'grudge match' in all_text:
        event_type = 'GM'
    elif 'heads' in all_text and 'up' in all_text:
        event_type = 'HU'
    elif 'high roller' in all_text:
        event_type = 'HR'
    elif 'mystery bounty' in all_text:
        event_type = 'MB'

    # Episode/Event number
    episode_num = extract_episode_from_text(title)
    # Bracelet Events인 경우 Event # 추출
    event_num = extract_event_num_from_text(title) if event_type == 'BR' else None

    return MatchKey(
        year=year,
        region=region,
        event_type=event_type,
        episode=episode_num,
        event_num=event_num,
    )


# =============================================================================
# CategoryEntry Key Extraction
# =============================================================================

def extract_event_num_from_entry_code(entry_code: str) -> int | None:
    """entry_code에서 Bracelet Event 번호 추출.

    예: WSOP_2025_BR_E09 -> 9
        WSOP_2025_BR_E76 -> 76
    """
    if not entry_code:
        return None
    match = re.search(r'_E(\d+)$', entry_code)
    return int(match.group(1)) if match else None


def extract_entry_key(entry: CategoryEntry, category: Category) -> MatchKey:
    """CategoryEntry에서 매칭 키 추출."""
    # Bracelet Event의 경우 entry_code에서 이벤트 번호 추출
    event_num = None
    if entry.event_type == 'BR':
        event_num = extract_event_num_from_entry_code(entry.entry_code)

    return MatchKey(
        year=entry.year,
        region=category.region if category else None,
        event_type=entry.event_type,
        episode=entry.sequence,
        event_num=event_num,
    )


# =============================================================================
# Matching Logic
# =============================================================================

def calculate_match_score(entry_key: MatchKey, pg_key: MatchKey) -> tuple[float, str]:
    """두 키 간의 매칭 점수 계산.

    Returns:
        (score, reason) - score는 0.0~1.0
    """
    reasons = []
    score = 0.0

    # Year match (필수)
    if entry_key.year != pg_key.year:
        return 0.0, "Year mismatch"
    score += 0.3
    reasons.append(f"Year={entry_key.year}")

    # Region match
    entry_region = entry_key.region or 'LV'
    pg_region = pg_key.region or 'LV'

    if entry_region != pg_region:
        return 0.0, f"Region mismatch: {entry_region} vs {pg_region}"
    score += 0.15
    reasons.append(f"Region={entry_region}")

    # Event type match
    if entry_key.event_type and pg_key.event_type:
        if entry_key.event_type == pg_key.event_type:
            score += 0.25
            reasons.append(f"Type={entry_key.event_type}")
        elif entry_key.event_type == 'ME' and pg_key.event_type in ('ME', 'FT'):
            # Main Event와 Final Table은 호환
            score += 0.2
            reasons.append(f"Type compatible: ME/{pg_key.event_type}")
        else:
            return score * 0.5, f"Type mismatch: {entry_key.event_type} vs {pg_key.event_type}"
    elif entry_key.event_type or pg_key.event_type:
        # 한쪽만 있으면 부분 매칭
        score += 0.1
        reasons.append("Type partial")

    # Event number match (Bracelet Events)
    if entry_key.event_num is not None or pg_key.event_num is not None:
        if entry_key.event_num == pg_key.event_num:
            score += 0.3
            reasons.append(f"Event#{entry_key.event_num}")
            return min(score, 1.0), " | ".join(reasons)
        else:
            # Event 번호 불일치는 치명적 (Bracelet Events)
            return 0.0, f"Event# mismatch: {entry_key.event_num} vs {pg_key.event_num}"

    # Episode match
    if entry_key.episode and pg_key.episode:
        if entry_key.episode == pg_key.episode:
            score += 0.3
            reasons.append(f"Episode={entry_key.episode}")
            return min(score, 1.0), " | ".join(reasons)
        else:
            # Episode 불일치는 치명적
            return score * 0.3, f"Episode mismatch: {entry_key.episode} vs {pg_key.episode}"

    # Episode 없는 경우 (CLASSIC Era 또는 단일 콘텐츠)
    if not entry_key.episode and not pg_key.episode:
        score += 0.2
        reasons.append("No episode (single content)")
    elif entry_key.year <= CLASSIC_ERA_END:
        # CLASSIC Era는 연도만으로 매칭
        score += 0.25
        reasons.append("CLASSIC era year-only match")

    return min(score, 1.0), " | ".join(reasons)


def find_best_match(
    entry: CategoryEntry,
    category: Category,
    episodes: list[PokergoEpisode],
    episode_keys: dict,
) -> MatchResult:
    """CategoryEntry에 가장 적합한 PokerGO 에피소드 찾기.

    보수적 매칭: 확실한 1:1 매칭만 EXACT, 나머지는 NONE
    """
    entry_key = extract_entry_key(entry, category)

    # 1단계: Year+Region+EventType 일치하는 후보 찾기
    candidates = []
    for ep in episodes:
        pg_key = episode_keys.get(ep.id)
        if not pg_key:
            continue

        # Year 일치 필수
        if entry_key.year != pg_key.year:
            continue

        # Region 일치 (None은 LV로 취급)
        entry_region = entry_key.region or 'LV'
        pg_region = pg_key.region or 'LV'
        if entry_region != pg_region:
            continue

        # EventType 일치
        if entry_key.event_type and pg_key.event_type:
            if entry_key.event_type != pg_key.event_type:
                continue

        candidates.append((ep, pg_key))

    # 후보가 없으면 NONE
    if not candidates:
        return MatchResult(
            match_type=MATCH_TYPE_NONE,
            score=0.0,
            reason="No candidates found",
        )

    # 2단계: Episode/Event# 번호로 정확히 매칭되는 후보 찾기
    exact_match = None
    exact_reason = ""

    for ep, pg_key in candidates:
        # Bracelet Event: Event# 번호로 매칭
        if entry_key.event_num is not None and pg_key.event_num is not None:
            if entry_key.event_num == pg_key.event_num:
                exact_match = ep
                exact_reason = (
                    f"Year={entry_key.year} | Type={entry_key.event_type} | "
                    f"Event#{entry_key.event_num}"
                )
                break

        # Episode 번호로 매칭
        if entry_key.episode is not None and pg_key.episode is not None:
            if entry_key.episode == pg_key.episode:
                exact_match = ep
                exact_reason = (
                    f"Year={entry_key.year} | Type={entry_key.event_type} | "
                    f"Episode={entry_key.episode}"
                )
                break

    # 번호로 정확히 매칭되면 EXACT
    if exact_match:
        return MatchResult(
            match_type=MATCH_TYPE_EXACT,
            score=1.0,
            pokergo_ep_id=exact_match.id,
            pokergo_title=exact_match.title,
            reason=exact_reason,
        )

    # 3단계: 후보가 1개뿐이고 CLASSIC Era이거나 Episode 번호가 없는 경우
    if len(candidates) == 1:
        ep, pg_key = candidates[0]
        # CLASSIC Era (1973-2002)는 연도당 1개 Main Event
        if entry_key.year <= CLASSIC_ERA_END:
            return MatchResult(
                match_type=MATCH_TYPE_EXACT,
                score=0.9,
                pokergo_ep_id=ep.id,
                pokergo_title=ep.title,
                reason=f"Year={entry_key.year} | CLASSIC era single match",
            )
        # Episode/Event# 모두 없는 단일 후보
        if entry_key.episode is None and entry_key.event_num is None:
            if pg_key.episode is None and pg_key.event_num is None:
                return MatchResult(
                    match_type=MATCH_TYPE_EXACT,
                    score=0.85,
                    pokergo_ep_id=ep.id,
                    pokergo_title=ep.title,
                    reason=(
                        f"Year={entry_key.year} | Type={entry_key.event_type} | "
                        "Single candidate"
                    ),
                )

    # 4단계: 여러 후보가 있는데 번호로 구분 불가 → NONE (보수적 처리)
    return MatchResult(
        match_type=MATCH_TYPE_NONE,
        score=0.0,
        reason=f"Ambiguous: {len(candidates)} candidates, no exact number match",
    )


# =============================================================================
# Main Matching Functions
# =============================================================================

def run_category_matching(
    db: Session,
    min_score: float = 0.5,
    clear_existing: bool = False,
) -> dict:
    """CategoryEntry를 PokerGO와 매칭.

    Args:
        db: Database session
        min_score: 최소 매칭 점수
        clear_existing: 기존 매칭 초기화 여부

    Returns:
        매칭 통계
    """
    stats = {
        'total_entries': 0,
        'processed': 0,
        'exact': 0,
        'partial': 0,
        'none': 0,
        'skipped': 0,
    }

    # Clear existing if requested
    if clear_existing:
        db.query(CategoryEntry).update({
            CategoryEntry.pokergo_ep_id: None,
            CategoryEntry.pokergo_title: None,
            CategoryEntry.match_type: None,
            CategoryEntry.match_score: None,
            CategoryEntry.source: SOURCE_NAS_ONLY,
        })
        db.commit()

    # Load all PokerGO episodes
    episodes = db.query(PokergoEpisode).all()
    if not episodes:
        return stats

    # Pre-compute episode keys
    episode_keys = {}
    for ep in episodes:
        key = extract_pokergo_key(ep)
        if key:
            episode_keys[ep.id] = key

    # Load categories for lookup
    categories = {c.id: c for c in db.query(Category).all()}

    # Process each entry
    entries = db.query(CategoryEntry).all()
    stats['total_entries'] = len(entries)

    for entry in entries:
        # Skip already matched entries (unless clearing)
        if entry.pokergo_ep_id and not clear_existing:
            stats['skipped'] += 1
            continue

        # Skip manually set entries
        if entry.match_type == MATCH_TYPE_MANUAL:
            stats['skipped'] += 1
            continue

        category = categories.get(entry.category_id)
        result = find_best_match(entry, category, episodes, episode_keys)

        # Apply result
        if result.score >= min_score:
            entry.pokergo_ep_id = result.pokergo_ep_id
            entry.pokergo_title = result.pokergo_title
            entry.match_type = result.match_type
            entry.match_score = result.score
            entry.source = SOURCE_POKERGO if result.pokergo_ep_id else SOURCE_NAS_ONLY

            if result.match_type == MATCH_TYPE_EXACT:
                stats['exact'] += 1
            elif result.match_type == MATCH_TYPE_PARTIAL:
                stats['partial'] += 1
        else:
            entry.match_type = MATCH_TYPE_NONE
            entry.source = SOURCE_NAS_ONLY
            stats['none'] += 1

        stats['processed'] += 1

    db.commit()
    return stats


def update_display_titles(db: Session) -> dict:
    """매칭 결과에 따라 display_title 업데이트.

    - EXACT/PARTIAL: PokerGO 제목 사용
    - NONE: 자체 생성 제목 유지
    """
    stats = {'updated': 0, 'kept': 0}

    entries = db.query(CategoryEntry).filter(
        CategoryEntry.pokergo_title.isnot(None),
        CategoryEntry.match_type.in_([MATCH_TYPE_EXACT, MATCH_TYPE_PARTIAL]),
    ).all()

    for entry in entries:
        if entry.pokergo_title and entry.display_title != entry.pokergo_title:
            entry.display_title = entry.pokergo_title
            stats['updated'] += 1
        else:
            stats['kept'] += 1

    db.commit()
    return stats


def get_matching_summary(db: Session) -> dict:
    """매칭 현황 요약."""
    summary = {
        'total_entries': db.query(CategoryEntry).count(),
        'by_match_type': {},
        'by_source': {},
        'by_year': {},
        'verification_needed': 0,
    }

    # By match_type
    match_type_counts = db.query(
        CategoryEntry.match_type, func.count(CategoryEntry.id)
    ).group_by(CategoryEntry.match_type).all()

    for mt, cnt in match_type_counts:
        summary['by_match_type'][mt or 'NULL'] = cnt

    # By source
    source_counts = db.query(
        CategoryEntry.source, func.count(CategoryEntry.id)
    ).group_by(CategoryEntry.source).all()

    for src, cnt in source_counts:
        summary['by_source'][src or 'NULL'] = cnt

    # By year (top 10)
    year_counts = db.query(
        CategoryEntry.year, func.count(CategoryEntry.id)
    ).group_by(CategoryEntry.year).order_by(CategoryEntry.year.desc()).limit(10).all()

    for yr, cnt in year_counts:
        summary['by_year'][yr] = cnt

    # Verification needed (PARTIAL)
    summary['verification_needed'] = db.query(CategoryEntry).filter(
        CategoryEntry.match_type == MATCH_TYPE_PARTIAL,
        not CategoryEntry.verified,
    ).count()

    return summary


# =============================================================================
# Standalone Functions
# =============================================================================

def run_matching_standalone(min_score: float = 0.5, clear_existing: bool = False) -> dict:
    """독립 실행 매칭."""
    with get_db_context() as db:
        return run_category_matching(db, min_score, clear_existing)


def run_full_matching_pipeline(clear_existing: bool = False) -> dict:
    """전체 매칭 파이프라인 실행."""
    with get_db_context() as db:
        results = {}

        # 1. Category 매칭
        results['matching'] = run_category_matching(
            db, min_score=0.5, clear_existing=clear_existing
        )

        # 2. Display title 업데이트
        results['titles'] = update_display_titles(db)

        # 3. Summary
        results['summary'] = get_matching_summary(db)

        return results
