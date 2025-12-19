"""Extract categories and titles for 2025 NAS files."""
import sys
import re
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding='utf-8')

from src.nams.api.database import get_db
from src.nams.api.database.models import NasFile


def extract_region(full_path):
    if not full_path:
        return 'UNKNOWN'
    p = full_path.upper()
    if 'WSOP-LAS VEGAS' in p:
        return 'LV'
    elif 'WSOP-EUROPE' in p:
        return 'EU'
    elif 'MPP' in p and 'CYPRUS' in p:
        return 'CYPRUS'
    elif 'CIRCUIT' in p:
        return 'CIRCUIT'
    return 'UNKNOWN'


def extract_event_type(full_path, filename):
    p = (full_path or '').upper()
    f = filename.upper()
    if 'MAIN EVENT' in p or 'MAIN EVENT' in f:
        return 'ME'
    elif 'BRACELET' in p or 'SIDE EVENT' in p or 'EVENT #' in f or 'WSOPE #' in f:
        return 'BR'
    return 'OTHER'


def extract_event_num(text):
    match = re.search(r'Event\s*#(\d+)', text, re.I)
    if match:
        return int(match.group(1))
    match = re.search(r'WSOPE\s*#(\d+)', text, re.I)
    if match:
        return int(match.group(1))
    match = re.search(r'WSOP-EUROPE\s*#(\d+)', text, re.I)
    if match:
        return int(match.group(1))
    match = re.search(r'\[BRACELET(?:\s+EVENT)?\s*#(\d+)\]', text, re.I)
    if match:
        return int(match.group(1))
    return None


def extract_event_name(filename):
    """Extract event name from filename."""
    # Pattern: Event #N $XXK Event Name
    match = re.search(r'Event\s*#\d+\s+(.+?)(?:\s*[_|]\s*Day|\s*\(|\s*\.mp4|$)', filename, re.I)
    if match:
        name = match.group(1).strip()
        name = re.sub(r'[_|]+$', '', name).strip()
        return name

    # Pattern: WSOPE #N €XXK Event Name
    match = re.search(r'WSOPE\s*#\d+\s+(.+?)(?:\s+Part|\s+Final|\s*_|\s*\.mp4|$)', filename, re.I)
    if match:
        name = match.group(1).strip()
        name = re.sub(r'[_|]+$', '', name).strip()
        return name

    return ''


def extract_day(filename):
    # Final Table Day N
    match = re.search(r'Final Table.*Day\s*(\d+)', filename, re.I)
    if match:
        return f'Final Table Day {match.group(1)}'
    if 'Final Table' in filename:
        return 'Final Table'
    if 'Final Day' in filename:
        return 'Final Day'
    if 'Final Four' in filename:
        return 'Final Four'
    # Day NA_B_C
    match = re.search(r'Day\s*(\d+)([A-D])(?:[_/])([A-D])(?:[_/])?([A-D])?', filename, re.I)
    if match:
        day = match.group(1)
        parts = [match.group(2), match.group(3)]
        if match.group(4):
            parts.append(match.group(4))
        return f'Day {day}' + '/'.join(parts)
    # Day N[A-D]
    match = re.search(r'Day\s*(\d+)\s*([A-D])?', filename, re.I)
    if match:
        day = match.group(1)
        suffix = match.group(2) or ''
        return f'Day {day}{suffix}'
    return ''


def extract_part(filename):
    match = re.search(r'Part\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def extract_cyprus_event(filename):
    f = filename.upper()
    if 'POKEROK' in f or 'MYSTERY BOUNTY' in f:
        return 'PokerOK Mystery Bounty'
    elif 'LUXON' in f:
        return 'Luxon Pay Grand Final'
    elif 'MPP MAIN EVENT' in f:
        return 'MPP Main Event'
    return ''


def is_hyperdeck(filename):
    return filename.startswith('HyperDeck_')


def generate_category(region, event_type, cyprus_event=''):
    if region == 'LV':
        if event_type == 'ME':
            return 'WSOP 2025 Main Event'
        else:
            return 'WSOP 2025 Bracelet Events'
    elif region == 'EU':
        if event_type == 'ME':
            return 'WSOP Europe 2025 Main Event'
        else:
            return 'WSOP Europe 2025 Bracelet Events'
    elif region == 'CYPRUS':
        if cyprus_event:
            return f'MPP Cyprus 2025 - {cyprus_event}'
        return 'MPP Cyprus 2025'
    elif region == 'CIRCUIT':
        return 'WSOP Circuit Cyprus 2025'
    return 'Other 2025'


def generate_title(region, event_type, event_num, event_name, day, part, cyprus_event='', is_raw=False):
    """Generate title in requested format."""

    if region == 'LV':
        if event_type == 'ME':
            # Main Event Day XX
            title = 'Main Event'
            if day:
                title += f' {day}'
            if part:
                title += f' Part {part}'
            return title
        else:
            # Event #N Event Name | Day
            if event_num and event_name:
                title = f'Event #{event_num} {event_name}'
            elif event_num:
                title = f'Event #{event_num}'
            else:
                title = 'Bracelet Event'
            if day:
                title += f' | {day}'
            if part:
                title += f' Part {part}'
            return title

    elif region == 'EU':
        if event_type == 'ME':
            # Main Event Day XX
            title = 'Main Event'
            if day:
                title += f' {day}'
            if part:
                title += f' Part {part}'
            if is_raw:
                title += ' [RAW]'
            return title
        else:
            # Event #N Event Name | Day
            if event_num and event_name:
                title = f'Event #{event_num} {event_name}'
            elif event_num:
                title = f'Event #{event_num}'
            else:
                title = 'Bracelet Event'
            if day:
                title += f' | {day}'
            if part:
                title += f' Part {part}'
            if is_raw:
                title += ' [RAW]'
            return title

    elif region == 'CYPRUS':
        title = cyprus_event or 'MPP Cyprus'
        if day:
            title += f' | {day}'
        if part:
            title += f' Part {part}'
        return title

    elif region == 'CIRCUIT':
        title = 'Main Event'
        if day:
            title += f' {day}'
        if part:
            title += f' Part {part}'
        return title

    return 'Unknown'


# EU 이벤트 이름 매핑 (경로에서 추출)
EU_EVENT_NAMES = {
    2: '€350 NLH King\'s Million',
    4: '€2K Monsterstack',
    6: '€2K PLO',
    7: '€2.5K NLH 8-Max',
    10: '€10K PLO Mystery Bounty',
    13: '€1K GGMillion€',
    14: '€10.35K Main Event NLH'
}


def main():
    db = next(get_db())

    files = db.query(NasFile).filter(
        NasFile.year == 2025,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    results = []
    for f in files:
        region = extract_region(f.full_path)
        event_type = extract_event_type(f.full_path, f.filename)
        event_num = extract_event_num((f.full_path or '') + ' ' + f.filename)
        event_name = extract_event_name(f.filename)
        day = extract_day(f.filename)
        part = extract_part(f.filename)
        cyprus_event = extract_cyprus_event(f.filename)
        raw = is_hyperdeck(f.filename)

        # HyperDeck 경로에서 추출
        if raw:
            match = re.search(r'WSOP-EUROPE\s*#(\d+)', f.full_path or '', re.I)
            if match:
                event_num = int(match.group(1))
            if 'MAIN EVENT' in (f.full_path or '').upper():
                event_type = 'ME'
            else:
                event_type = 'BR'
            match = re.search(r'Day\s*(\d+)\s*([A-D])?', f.full_path or '', re.I)
            if match:
                day = f'Day {match.group(1)}{match.group(2) or ""}'
            elif 'FINAL' in (f.full_path or '').upper():
                day = 'Final'
            if event_num in EU_EVENT_NAMES and event_type == 'BR':
                event_name = EU_EVENT_NAMES[event_num]

        # EU event name from mapping
        if region == 'EU' and not event_name and event_num in EU_EVENT_NAMES:
            event_name = EU_EVENT_NAMES[event_num]

        # Circuit
        if region == 'CIRCUIT':
            day = extract_day(f.filename)
            suffix_match = re.search(r'-(\d+)\.mp4$', f.filename)
            if suffix_match:
                part = int(suffix_match.group(1))

        category = generate_category(region, event_type, cyprus_event)
        title = generate_title(region, event_type, event_num, event_name, day, part, cyprus_event, raw)

        results.append({
            'id': f.id,
            'filename': f.filename,
            'region': region,
            'category': category,
            'title': title
        })

    # 카테고리별 그룹화
    by_category = defaultdict(list)
    for r in results:
        by_category[r['category']].append(r)

    print('=' * 80)
    print('2025 NAS 파일 카테고리 및 제목 추출 결과')
    print('=' * 80)
    print(f'총 파일: {len(results)}개')
    print(f'카테고리: {len(by_category)}개')

    for category in sorted(by_category.keys()):
        items = by_category[category]
        print(f'\n### {category} ({len(items)}개)')
        print('-' * 70)

        by_title = defaultdict(list)
        for item in items:
            by_title[item['title']].append(item['filename'])

        for title in sorted(by_title.keys()):
            fnames = by_title[title]
            if len(fnames) == 1:
                print(f'  {title}')
            else:
                print(f'  {title} [{len(fnames)} files]')

    print()
    print('=' * 80)


if __name__ == '__main__':
    main()
