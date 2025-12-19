"""Test semantic metadata matching between NAS and PokerGO."""
import json
import re
from pathlib import Path
from collections import defaultdict
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.nams.api.database import get_db, NasFile


def extract_pkg_metadata(title, year):
    """Extract structured metadata from PokerGO title."""
    title_lower = title.lower()
    meta = {
        'year': int(year) if year else None,
        'type': None,
        'episode': None,
        'day': None,
        'event_num': None,
        'part': None,
        'region': 'LV'
    }

    # Region
    if 'europe' in title_lower or 'wsope' in title_lower:
        meta['region'] = 'EU'
    elif 'apac' in title_lower:
        meta['region'] = 'APAC'

    # Type
    if 'main event' in title_lower:
        meta['type'] = 'ME'
    elif 'bracelet' in title_lower:
        meta['type'] = 'BR'
    elif 'high roller' in title_lower:
        meta['type'] = 'HR'
    elif 'heads' in title_lower:
        meta['type'] = 'HU'
    elif 'grudge' in title_lower:
        meta['type'] = 'GM'
    elif 'poker players championship' in title_lower:
        meta['type'] = 'PPC'
    elif 'national championship' in title_lower:
        meta['type'] = 'NC'
    elif 'big one' in title_lower:
        meta['type'] = 'BO'

    # Episode
    m = re.search(r'episode\s*(\d+)', title_lower)
    if m:
        meta['episode'] = int(m.group(1))

    # Day
    m = re.search(r'day\s*(\d+[a-d]?)', title_lower)
    if m:
        meta['day'] = m.group(1).upper()

    # Event number
    m = re.search(r'event\s*#(\d+)', title_lower)
    if m:
        meta['event_num'] = int(m.group(1))

    # Part
    m = re.search(r'part\s*(\d+)', title_lower)
    if m:
        meta['part'] = int(m.group(1))

    return meta


def extract_nas_metadata(filename):
    """Extract structured metadata from NAS filename."""
    fname_lower = filename.lower()
    meta = {
        'year': None,
        'type': None,
        'episode': None,
        'day': None,
        'event_num': None,
        'part': None,
        'region': 'LV'
    }

    # Region
    if 'wsope' in fname_lower or 'europe' in fname_lower:
        meta['region'] = 'EU'
    elif 'apac' in fname_lower:
        meta['region'] = 'APAC'

    # Year - Pattern 1: WS11, WS09
    m = re.search(r'\bws(\d{2})[-_]', fname_lower)
    if m:
        yy = int(m.group(1))
        meta['year'] = 2000 + yy if yy < 50 else 1900 + yy

    # Year - Pattern 2: WSOP_2011, WSOP 2024
    if not meta['year']:
        m = re.search(r'wsop[e]?\s*[-_]?\s*(19|20)(\d{2})', fname_lower)
        if m:
            meta['year'] = int(m.group(1) + m.group(2))

    # Year - Pattern 3: Just year
    if not meta['year']:
        m = re.search(r'\b(19[7-9]\d|20[0-2]\d)\b', fname_lower)
        if m:
            meta['year'] = int(m.group(1))

    # Type & Episode - Short Code: WS11_ME01, WS11_GM02
    m = re.search(r'ws\d{2}[-_](me|gm|hu|ppc|nc)(\d+)', fname_lower)
    if m:
        type_map = {'me': 'ME', 'gm': 'GM', 'hu': 'HU', 'ppc': 'PPC', 'nc': 'NC'}
        meta['type'] = type_map.get(m.group(1), m.group(1).upper())
        meta['episode'] = int(m.group(2))

    # Show Code: WS12_Show_10_ME06
    if not meta['episode']:
        m = re.search(r'show[-_](\d+)[-_]me(\d+)', fname_lower)
        if m:
            meta['type'] = 'ME'
            meta['episode'] = int(m.group(2))

    # ME pattern: WSOP15_ME11, WS11_ME25
    if not meta['episode']:
        m = re.search(r'[-_]me(\d+)', fname_lower)
        if m:
            meta['type'] = 'ME'
            meta['episode'] = int(m.group(1))

    # Day
    m = re.search(r'day\s*[-_]?(\d+[a-d]?)', fname_lower)
    if m:
        meta['day'] = m.group(1).upper()
        if not meta['type']:
            meta['type'] = 'ME'

    # Event number
    m = re.search(r'event\s*#?(\d+)', fname_lower)
    if m:
        meta['event_num'] = int(m.group(1))
        if not meta['type']:
            meta['type'] = 'BR'

    # Part
    m = re.search(r'part\s*[-_]?(\d+)', fname_lower)
    if m:
        meta['part'] = int(m.group(1))

    # Fallback type
    if not meta['type']:
        if 'main event' in fname_lower or '_me_' in fname_lower:
            meta['type'] = 'ME'
        elif 'bracelet' in fname_lower:
            meta['type'] = 'BR'

    return meta


def main():
    # Load PokerGO
    json_path = Path(__file__).parent.parent / 'data' / 'pokergo' / 'wsop_final.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        videos = json.load(f).get('videos', [])

    # Build PokerGO index
    pkg_index = {}
    for v in videos:
        title = v.get('title', '')
        year = v.get('year', '')
        meta = extract_pkg_metadata(title, year)

        if meta['year'] and meta['type']:
            if meta['episode']:
                key = (meta['year'], meta['region'], meta['type'], 'ep', meta['episode'])
                pkg_index[key] = title
            if meta['day']:
                key = (meta['year'], meta['region'], meta['type'], 'day', meta['day'])
                pkg_index[key] = title
            if meta['event_num']:
                key = (meta['year'], meta['region'], 'BR', 'event', meta['event_num'])
                pkg_index[key] = title

    print(f'PokerGO Index Keys: {len(pkg_index)}')

    # Load NAS
    db = next(get_db())
    all_files = db.query(NasFile).filter(
        (NasFile.full_path.ilike('%wsop%') |
         NasFile.full_path.ilike('%ws0%') |
         NasFile.full_path.ilike('%ws1%') |
         NasFile.full_path.ilike('%ws2%'))
    ).all()

    # Match
    matched = 0
    match_details = []
    unmatched = []

    for f in all_files:
        meta = extract_nas_metadata(f.filename)
        matched_title = None

        if meta['year'] and meta['type']:
            # Try episode
            if meta['episode']:
                key = (meta['year'], meta['region'], meta['type'], 'ep', meta['episode'])
                if key in pkg_index:
                    matched_title = pkg_index[key]

            # Try day
            if not matched_title and meta['day']:
                key = (meta['year'], meta['region'], meta['type'], 'day', meta['day'])
                if key in pkg_index:
                    matched_title = pkg_index[key]

            # Try event
            if not matched_title and meta['event_num']:
                key = (meta['year'], meta['region'], 'BR', 'event', meta['event_num'])
                if key in pkg_index:
                    matched_title = pkg_index[key]

        if matched_title:
            matched += 1
            match_details.append((f.filename, matched_title))
        else:
            unmatched.append((f.filename, meta))

    print(f'Total NAS files: {len(all_files)}')
    print(f'Matched: {matched}')
    print(f'Unmatched: {len(unmatched)}')
    print(f'Match rate: {matched/len(all_files)*100:.1f}%')

    print('\n=== Sample Matches ===')
    for nas, pkg in match_details[:10]:
        clean = nas.encode('ascii', 'ignore').decode()[:50]
        print(f'{clean}')
        print(f'  -> {pkg[:60]}')

    print('\n=== Unmatched Samples ===')
    for nas, meta in unmatched[:15]:
        clean = nas.encode('ascii', 'ignore').decode()[:50]
        print(f'{clean}')
        print(f'  meta: {meta}')


if __name__ == '__main__':
    main()
