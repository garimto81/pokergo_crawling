"""Analyze PokerGO Only episodes to classify collection needs.

This script:
1. Analyzes 957 PokerGO episodes without NAS matches
2. Classifies them by year, collection, and type
3. Identifies which ones need collection

Usage:
    python scripts/analyze_pokergo_only.py
"""
import sys
import re
from pathlib import Path
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.database import get_db_context, PokergoEpisode
from src.nams.api.services.matching import get_pokergo_only_episodes


def extract_year(text: str) -> int:
    """Extract year from text."""
    if not text:
        return None
    match = re.search(r'\b(19|20)\d{2}\b', text)
    if match:
        return int(match.group())
    return None


def classify_episode(ep: dict) -> str:
    """Classify episode type based on title."""
    title = (ep.get('title') or '').lower()
    collection = (ep.get('collection_title') or '').lower()

    # Check for Main Event
    if 'main event' in title or 'main event' in collection:
        return 'ME'
    # Check for specific events
    if 'high roller' in title:
        return 'HR'
    if 'bracelet' in title or 'event #' in title:
        return 'BR'
    if 'heads up' in title:
        return 'HU'
    if 'final table' in title:
        return 'FT'
    if 'one drop' in title:
        return 'ONEDR'

    return 'OTHER'


def main():
    print("=" * 70)
    print("NAMS PokerGO Only 분석")
    print("=" * 70)

    with get_db_context() as db:
        episodes = get_pokergo_only_episodes(db)

    print(f"\n총 PokerGO Only 에피소드: {len(episodes)}개")
    print("-" * 70)

    # Analyze by year
    by_year = defaultdict(list)
    for ep in episodes:
        year = ep.get('year') or extract_year(ep.get('title') or '') or 'Unknown'
        by_year[year].append(ep)

    print("\n[연도별 분포]")
    for year in sorted(by_year.keys(), key=lambda x: (0 if x == 'Unknown' else x)):
        count = len(by_year[year])
        pct = count / len(episodes) * 100
        bar = '#' * int(pct / 2)
        print(f"  {str(year):>7}: {count:>4} ({pct:>5.1f}%) {bar}")

    # Analyze by collection
    by_collection = defaultdict(list)
    for ep in episodes:
        collection = ep.get('collection_title') or 'Unknown'
        by_collection[collection].append(ep)

    print(f"\n[컬렉션별 분포] (상위 15개)")
    sorted_collections = sorted(by_collection.items(), key=lambda x: -len(x[1]))[:15]
    for collection, eps in sorted_collections:
        count = len(eps)
        pct = count / len(episodes) * 100
        print(f"  {collection[:50]:50}: {count:>4} ({pct:>5.1f}%)")

    # Analyze by type
    by_type = defaultdict(list)
    for ep in episodes:
        ep_type = classify_episode(ep)
        by_type[ep_type].append(ep)

    print(f"\n[이벤트 타입별 분포]")
    for ep_type in ['ME', 'BR', 'HR', 'HU', 'FT', 'ONEDR', 'OTHER']:
        if ep_type in by_type:
            count = len(by_type[ep_type])
            pct = count / len(episodes) * 100
            type_name = {
                'ME': 'Main Event',
                'BR': 'Bracelet Event',
                'HR': 'High Roller',
                'HU': 'Heads Up',
                'FT': 'Final Table',
                'ONEDR': 'One Drop',
                'OTHER': 'Other',
            }.get(ep_type, ep_type)
            print(f"  {type_name:20}: {count:>4} ({pct:>5.1f}%)")

    # Analysis summary
    print("\n" + "=" * 70)
    print("분석 결론")
    print("=" * 70)

    # Check years
    years = [y for y in by_year.keys() if isinstance(y, int)]
    if years:
        min_year = min(years)
        max_year = max(years)
        recent_count = sum(len(by_year[y]) for y in years if y >= 2019)
        older_count = sum(len(by_year[y]) for y in years if y < 2019)

        print(f"\n연도 범위: {min_year} ~ {max_year}")
        print(f"  - 2019년 이후 (수집 대상): {recent_count}개")
        print(f"  - 2019년 이전 (PokerGO 이전): {older_count}개")

    # Check Main Event coverage
    me_by_year = defaultdict(int)
    for ep in by_type.get('ME', []):
        year = ep.get('year')
        if year:
            me_by_year[year] += 1

    print(f"\nMain Event 연도별 에피소드 (NAS에 없는 것):")
    for year in sorted(me_by_year.keys()):
        print(f"  {year}: {me_by_year[year]}개")

    # Recommendations
    print(f"\n[권장 조치]")
    print("  1. 2019년 이후 Main Event: 우선 수집 대상")
    print("  2. Bracelet Event: 선별적 수집 (중요 이벤트만)")
    print("  3. 2019년 이전: PokerGO 서비스 이전 콘텐츠 - 수집 불가")


if __name__ == "__main__":
    main()
