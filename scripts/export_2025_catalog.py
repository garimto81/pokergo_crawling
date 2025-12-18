"""Export 2025 catalog (categories and titles) to Google Sheets."""
import sys
import re
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.database import get_db
from src.nams.api.database.models import NasFile
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

GOOGLE_SHEETS_ID = '1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4'
CREDENTIALS_PATH = Path('D:/AI/claude01/json/service_account_key.json')


def format_size(bytes_size: int) -> str:
    """Format bytes to GB."""
    if not bytes_size:
        return ""
    gb = bytes_size / (1024**3)
    return f"{gb:.2f}"


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
    match = re.search(r'Event\s*#\d+\s+(.+?)(?:\s*[_|]\s*Day|\s*\(|\s*\.mp4|$)', filename, re.I)
    if match:
        name = match.group(1).strip()
        name = re.sub(r'[_|]+$', '', name).strip()
        return name
    match = re.search(r'WSOPE\s*#\d+\s+(.+?)(?:\s+Part|\s+Final|\s*_|\s*\.mp4|$)', filename, re.I)
    if match:
        name = match.group(1).strip()
        name = re.sub(r'[_|]+$', '', name).strip()
        return name
    return ''


def extract_day(filename):
    match = re.search(r'Final Table.*Day\s*(\d+)', filename, re.I)
    if match:
        return f'Final Table Day {match.group(1)}'
    if 'Final Table' in filename:
        return 'Final Table'
    if 'Final Day' in filename:
        return 'Final Day'
    if 'Final Four' in filename:
        return 'Final Four'
    match = re.search(r'Day\s*(\d+)([A-D])(?:[_/])([A-D])(?:[_/])?([A-D])?', filename, re.I)
    if match:
        day = match.group(1)
        parts = [match.group(2), match.group(3)]
        if match.group(4):
            parts.append(match.group(4))
        return f'Day {day}' + '/'.join(parts)
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
    if region == 'LV':
        if event_type == 'ME':
            title = 'Main Event'
            if day:
                title += f' {day}'
            if part:
                title += f' Part {part}'
            return title
        else:
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
            title = 'Main Event'
            if day:
                title += f' {day}'
            if is_raw and part:
                title += f' (Part {part:02d}) [RAW]'
            elif part:
                title += f' Part {part}'
            elif is_raw:
                title += ' [RAW]'
            return title
        else:
            if event_num and event_name:
                title = f'Event #{event_num} {event_name}'
            elif event_num:
                title = f'Event #{event_num}'
            else:
                title = 'Bracelet Event'
            if day:
                title += f' | {day}'
            if is_raw and part:
                title += f' (Part {part:02d}) [RAW]'
            elif part:
                title += f' Part {part}'
            elif is_raw:
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


def generate_entry_key(region, event_type, event_num, day, part, cyprus_event='', is_raw=False):
    """Generate normalized entry key."""
    parts = [region]

    if region == 'LV':
        parts.append('WSOP')
    elif region == 'EU':
        parts.append('WSOPE')
    elif region == 'CYPRUS':
        parts.append('MPP')
    elif region == 'CIRCUIT':
        parts.append('WSOP_CIRCUIT')

    if region == 'CYPRUS' and cyprus_event:
        if 'PokerOK' in cyprus_event:
            parts.append('POKEROK')
        elif 'Luxon' in cyprus_event:
            parts.append('LUXON')
        elif 'MPP Main' in cyprus_event:
            parts.append('MPP_ME')
    else:
        parts.append(event_type)
        if event_num:
            parts.append(f'E{event_num}')

    if day:
        day_norm = day.replace(' ', '').replace('/', '')
        parts.append(f'D{day_norm}')

    if part:
        parts.append(f'P{part}')

    if is_raw:
        parts.append('RAW')

    return '_'.join(parts)


EU_EVENT_NAMES = {
    2: "€350 NLH King's Million",
    4: '€2K Monsterstack',
    6: '€2K PLO',
    7: '€2.5K NLH 8-Max',
    10: '€10K PLO Mystery Bounty',
    13: '€1K GGMillion€',
    14: '€10.35K Main Event NLH'
}


def extract_hyperdeck_sequence(filename):
    """Extract sequence number from HyperDeck filename for sorting."""
    match = re.match(r'HyperDeck_(\d+)(?:-(\d+))?', filename)
    if match:
        main_num = int(match.group(1))
        sub_num = int(match.group(2)) if match.group(2) else 0
        return (main_num, sub_num)
    return (0, 0)


def get_hyperdeck_folder_key(full_path):
    """Get folder key for grouping HyperDeck files."""
    # Extract: Region + Event # + Day
    parts = []

    # Event #
    match = re.search(r'WSOP-EUROPE\s*#(\d+)', full_path or '', re.I)
    if match:
        parts.append(f'E{match.group(1)}')

    # Event type
    if 'MAIN EVENT' in (full_path or '').upper():
        parts.append('ME')
    else:
        parts.append('BR')

    # Day
    match = re.search(r'Day\s*(\d+)\s*([A-D])?', full_path or '', re.I)
    if match:
        parts.append(f'D{match.group(1)}{match.group(2) or ""}')
    elif 'FINAL' in (full_path or '').upper():
        parts.append('DFinal')

    return '_'.join(parts)


def get_sheets_service():
    creds = Credentials.from_service_account_file(
        str(CREDENTIALS_PATH),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)
    return service.spreadsheets()


def ensure_sheet_exists(sheets, sheet_name: str):
    spreadsheet = sheets.get(spreadsheetId=GOOGLE_SHEETS_ID).execute()
    existing_sheets = [s['properties']['title'] for s in spreadsheet['sheets']]
    if sheet_name not in existing_sheets:
        sheets.batchUpdate(
            spreadsheetId=GOOGLE_SHEETS_ID,
            body={'requests': [{'addSheet': {'properties': {'title': sheet_name}}}]}
        ).execute()
        print(f'  Created new sheet: {sheet_name}')


def write_sheet(sheets, sheet_name: str, rows: list):
    ensure_sheet_exists(sheets, sheet_name)
    sheets.values().clear(
        spreadsheetId=GOOGLE_SHEETS_ID,
        range=f'{sheet_name}!A:Z'
    ).execute()
    result = sheets.values().update(
        spreadsheetId=GOOGLE_SHEETS_ID,
        range=f'{sheet_name}!A1',
        valueInputOption='RAW',
        body={'values': rows}
    ).execute()
    print(f'  Written: {result.get("updatedRows", 0)} rows')


def main():
    print('=' * 60)
    print('2025 Catalog Export to Google Sheets')
    print('=' * 60)

    db = next(get_db())
    sheets = get_sheets_service()

    # Get all 2025 files
    files = db.query(NasFile).filter(
        NasFile.year == 2025,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    print(f'\nTotal files: {len(files)}')

    # Pre-process: Assign HyperDeck part numbers
    hyperdeck_parts = {}  # file_id -> part_number
    hyperdeck_groups = defaultdict(list)

    for f in files:
        if is_hyperdeck(f.filename):
            folder_key = get_hyperdeck_folder_key(f.full_path)
            seq = extract_hyperdeck_sequence(f.filename)
            hyperdeck_groups[folder_key].append((f.id, f.filename, seq))

    for folder_key, items in hyperdeck_groups.items():
        # Sort by sequence number
        items.sort(key=lambda x: x[2])
        # Assign part numbers
        for idx, (file_id, filename, seq) in enumerate(items, 1):
            hyperdeck_parts[file_id] = idx

    # Process files
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

        # HyperDeck path extraction
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
            # Assign part number from pre-processed data
            if f.id in hyperdeck_parts:
                part = hyperdeck_parts[f.id]

        if region == 'EU' and not event_name and event_num in EU_EVENT_NAMES:
            event_name = EU_EVENT_NAMES[event_num]

        if region == 'CIRCUIT':
            day = extract_day(f.filename)
            suffix_match = re.search(r'-(\d+)\.mp4$', f.filename)
            if suffix_match:
                part = int(suffix_match.group(1))

        category = generate_category(region, event_type, cyprus_event)
        title = generate_title(region, event_type, event_num, event_name, day, part, cyprus_event, raw)
        entry_key = generate_entry_key(region, event_type, event_num, day, part, cyprus_event, raw)

        results.append({
            'id': f.id,
            'filename': f.filename,
            'full_path': f.full_path,
            'size_gb': format_size(f.size_bytes),
            'region': region,
            'event_type': event_type,
            'event_num': event_num,
            'event_name': event_name,
            'day': day,
            'part': part,
            'category': category,
            'title': title,
            'entry_key': entry_key,
            'is_raw': raw
        })

    # Sheet 1: Full Catalog
    print('\n[1/3] 2025_Catalog')
    headers = [
        'No', 'Entry Key', 'Category', 'Title', 'Region', 'Event Type',
        'Event #', 'Day', 'Part', 'RAW', 'Size (GB)', 'Filename', 'Full Path'
    ]
    rows = [headers]
    for idx, r in enumerate(results, 1):
        rows.append([
            idx,
            r['entry_key'],
            r['category'],
            r['title'],
            r['region'],
            r['event_type'],
            r['event_num'] or '',
            r['day'],
            r['part'] or '',
            'Yes' if r['is_raw'] else '',
            r['size_gb'],
            r['filename'],
            r['full_path'] or ''
        ])
    write_sheet(sheets, '2025_Catalog', rows)

    # Sheet 2: By Category Summary
    print('\n[2/3] 2025_Categories')
    by_category = defaultdict(list)
    for r in results:
        by_category[r['category']].append(r)

    rows = [['Category', 'Files', 'Titles', 'Size (GB)']]
    for category in sorted(by_category.keys()):
        items = by_category[category]
        titles = len(set(r['title'] for r in items))
        total_size = sum(float(r['size_gb'] or 0) for r in items)
        rows.append([category, len(items), titles, f'{total_size:.2f}'])
    rows.append([''])
    rows.append(['Total', len(results), '', ''])
    write_sheet(sheets, '2025_Categories', rows)

    # Sheet 3: Title List
    print('\n[3/3] 2025_Titles')
    by_title = defaultdict(list)
    for r in results:
        key = (r['category'], r['title'])
        by_title[key].append(r)

    rows = [['No', 'Category', 'Title', 'Files', 'Entry Key']]
    idx = 1
    for (category, title) in sorted(by_title.keys()):
        items = by_title[(category, title)]
        entry_key = items[0]['entry_key']
        rows.append([idx, category, title, len(items), entry_key])
        idx += 1
    write_sheet(sheets, '2025_Titles', rows)

    print('\n' + '=' * 60)
    print('[OK] Export completed')
    print(f'URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit')
    print('=' * 60)


if __name__ == '__main__':
    main()
