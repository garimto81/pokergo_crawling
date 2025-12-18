"""2019 NAS Matching Script.

Matches and exports 2019 NAS files:
- WSOP 2019 Main Event
- WSOP 2019 Bracelet Events
"""
import sys
import io
import re
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.database import get_db
from src.nams.api.database.models import NasFile
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

GOOGLE_SHEETS_ID = '1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4'
CREDENTIALS_PATH = Path('D:/AI/claude01/json/service_account_key.json')


@dataclass
class NasElement:
    file_id: int
    full_path: str
    filename: str
    content_type: str     # WSOP_ME, WSOP_BR
    region: str
    event_type: str       # ME, BR
    event_num: int | None
    event_name: str
    episode_num: int | None
    day: str
    day_display: str
    part: int | None
    size_bytes: int
    role: str = 'PRIMARY'


def extract_content_type(filename: str) -> str:
    fn_upper = filename.upper()
    # "Mini Main Event" is a Bracelet Event, not Main Event
    if 'MAIN EVENT' in fn_upper and 'MINI MAIN EVENT' not in fn_upper:
        return 'WSOP_ME'
    elif 'BRACELET' in fn_upper or 'EVENT #' in fn_upper:
        return 'WSOP_BR'
    return 'OTHER'


def extract_event_num(filename: str) -> int | None:
    match = re.search(r'Event #(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def extract_event_name(filename: str) -> str:
    # Pattern: Event #XX $XXK EventName (Part X)
    match = re.search(r'Event #\d+\s*((?:\$[\d,.]+[KM]?\s+)?.+?)(?:\s*\(Part|\s*\.mp4|$)', filename, re.I)
    if match:
        name = match.group(1).strip()
        name = re.sub(r'\s+Final Table.*$', '', name, flags=re.I)
        return name
    return ''


def extract_episode_num(filename: str) -> int | None:
    match = re.search(r'Episode\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def extract_day_info(filename: str) -> tuple[str, str]:
    # Final Table Day X
    match = re.search(r'Final Table Day\s*(\d+)', filename, re.I)
    if match:
        return (f'FT{match.group(1)}', f'Final Table Day {match.group(1)}')

    # Standalone Final Table
    if re.search(r'Final Table', filename, re.I):
        return ('FT', 'Final Table')

    # Day N
    match = re.search(r'Day\s*(\d+)([A-Z]*)', filename, re.I)
    if match:
        day_num = match.group(1)
        suffix = match.group(2).upper() if match.group(2) else ''
        return (f'{day_num}{suffix}', f'Day {day_num}{suffix}')

    return ('', '')


def extract_part(filename: str) -> int | None:
    match = re.search(r'\(Part\s*(\d+)\)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def generate_entry_key(elem: NasElement) -> str:
    parts = []
    if elem.content_type == 'WSOP_ME':
        parts.append('WSOP_2019_ME')
        if elem.episode_num:
            parts.append(f'EP{elem.episode_num}')
        elif elem.day:
            parts.append(f'D{elem.day}')
    elif elem.content_type == 'WSOP_BR':
        parts.append('WSOP_2019_BR')
        if elem.event_num:
            parts.append(f'E{elem.event_num}')
        if elem.part:
            parts.append(f'P{elem.part}')
    else:
        parts.append('WSOP_2019_OTHER')
    return '_'.join(parts)


def generate_category(elem: NasElement) -> str:
    if elem.content_type == 'WSOP_ME':
        return 'WSOP 2019 Main Event'
    elif elem.content_type == 'WSOP_BR':
        return 'WSOP 2019 Bracelet Events'
    return 'WSOP 2019 Other'


def generate_title(elem: NasElement) -> str:
    if elem.content_type == 'WSOP_ME':
        title = 'Main Event'
        if elem.episode_num:
            title += f' Episode {elem.episode_num}'
        elif elem.day_display:
            title += f' {elem.day_display}'
        if elem.part:
            title += f' Part {elem.part}'
        return title

    elif elem.content_type == 'WSOP_BR':
        if elem.event_num and elem.event_name:
            title = f'Event #{elem.event_num} {elem.event_name}'
        elif elem.event_num:
            title = f'Event #{elem.event_num}'
        else:
            title = elem.filename[:40]

        if elem.part:
            title += f' Part {elem.part}'
        if elem.day == 'FT':
            title += ' Final Table'
        return title

    return elem.filename[:50]


def load_nas_files(db) -> list[NasElement]:
    files = db.query(NasFile).filter(
        NasFile.year == 2019,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    elements = []
    for f in files:
        content_type = extract_content_type(f.filename)
        event_num = extract_event_num(f.filename)
        event_name = extract_event_name(f.filename)
        episode_num = extract_episode_num(f.filename)
        day_raw, day_display = extract_day_info(f.filename)
        part = extract_part(f.filename)

        if content_type == 'WSOP_ME':
            event_type = 'ME'
        elif content_type == 'WSOP_BR':
            event_type = 'BR'
        else:
            event_type = 'OTHER'

        elements.append(NasElement(
            file_id=f.id,
            full_path=f.full_path or '',
            filename=f.filename,
            content_type=content_type,
            region='LV',
            event_type=event_type,
            event_num=event_num,
            event_name=event_name,
            episode_num=episode_num,
            day=day_raw,
            day_display=day_display,
            part=part,
            size_bytes=f.size_bytes or 0,
            role='PRIMARY'
        ))

    return elements


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
    sheets.values().clear(spreadsheetId=GOOGLE_SHEETS_ID, range=f'{sheet_name}!A:Z').execute()
    result = sheets.values().update(
        spreadsheetId=GOOGLE_SHEETS_ID,
        range=f'{sheet_name}!A1',
        valueInputOption='RAW',
        body={'values': rows}
    ).execute()
    print(f'  Written: {result.get("updatedRows", 0)} rows')


def export_to_sheets(elements: list[NasElement]):
    sheets = get_sheets_service()
    print('\n[Export] 2019_Catalog')

    headers = [
        'No', 'Entry Key', 'Match Type', 'Role', 'Backup Type',
        'Category', 'Title', 'PokerGO Title',
        'Region', 'Event Type', 'Event #', 'Day', 'Part', 'RAW',
        'Size (GB)', 'Filename', 'Full Path'
    ]
    rows = [headers]

    # Sort: ME first, then BR by event number
    def sort_key(x):
        type_order = {'WSOP_ME': 0, 'WSOP_BR': 1, 'OTHER': 2}
        return (type_order.get(x.content_type, 9), x.episode_num or 0, x.event_num or 999, x.part or 0)

    for idx, elem in enumerate(sorted(elements, key=sort_key), 1):
        entry_key = generate_entry_key(elem)
        category = generate_category(elem)
        title = generate_title(elem)
        size_gb = elem.size_bytes / (1024**3)

        rows.append([
            idx, entry_key, 'NAS_ONLY', elem.role, '-',
            category, title, '',
            elem.region, elem.event_type, elem.event_num or '', elem.day_display or '', elem.part or '', '',
            f'{size_gb:.2f}', elem.filename, elem.full_path
        ])

    write_sheet(sheets, '2019_Catalog', rows)

    # Summary
    print('\n  Summary:')
    summary = defaultdict(lambda: {'count': 0, 'size': 0})
    for elem in elements:
        summary[elem.content_type]['count'] += 1
        summary[elem.content_type]['size'] += elem.size_bytes

    for ct in ['WSOP_ME', 'WSOP_BR', 'OTHER']:
        if ct in summary:
            s = summary[ct]
            print(f'    {ct}: {s["count"]} files ({s["size"]/(1024**3):.1f} GB)')

    total_size = sum(e.size_bytes for e in elements) / (1024**3)
    print(f'    Total: {len(elements)} files ({total_size:.1f} GB)')


def main():
    print('=' * 70)
    print('2019 NAS Matching')
    print('=' * 70)

    db = next(get_db())
    elements = load_nas_files(db)
    print(f'\n[Step 1] Loaded {len(elements)} files')

    # Analysis
    print('\n[Step 2] Analysis:')
    type_counts = defaultdict(int)
    for elem in elements:
        type_counts[elem.content_type] += 1
    for ct in ['WSOP_ME', 'WSOP_BR', 'OTHER']:
        if ct in type_counts:
            print(f'    {ct}: {type_counts[ct]}')

    print('\n[Step 3] Exporting...')
    export_to_sheets(elements)

    print('\n' + '=' * 70)
    print('[OK] 2019 Matching completed!')
    print('=' * 70)


if __name__ == '__main__':
    main()
