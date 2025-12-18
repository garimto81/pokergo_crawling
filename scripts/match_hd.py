"""HD Era NAS Matching Script (2011-2016).

Matches and exports HD era NAS files.
Main Event + WSOP Europe + APAC + High Roller.

Filename patterns:
- 2011: "WSOPE11_Episode_1_H264.mov"
- 2012: "WSOPE12_Episode_1_H264.mov"
- 2013: "WSOP13_APAC_ME01_NB.mp4", "WSOP13_ME01_NB.mp4"
- 2014: "WSOP14_APAC_HIGH_ROLLER-SHOW 1.mp4", "WSOP14_APAC_MAIN_EVENT-SHOW 1.mp4"
- 2015: "WSOP15_ME01_FINAL_4CH.mov"
- 2016: "WSOP16_GCC_P01.mxf", "2016 World Series of Poker - Main Event Show 01"
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

HD_YEARS = list(range(2011, 2017))  # 2011-2016


@dataclass
class NasElement:
    file_id: int
    full_path: str
    filename: str
    year: int
    content_type: str     # WSOP_ME, WSOPE, WSOP_APAC, WSOP_HR, WSOP_GCC, WSOP_OTHER
    region: str           # LV, EU, APAC
    event_type: str
    episode_num: int | None
    show_num: int | None
    part_num: int | None
    size_bytes: int
    role: str = 'PRIMARY'


def extract_content_type(filename: str, year: int) -> tuple[str, str]:
    """Determine content type and region from filename."""
    fn_upper = filename.upper()

    # WSOP Europe
    if 'WSOPE' in fn_upper:
        return 'WSOPE', 'EU'

    # APAC
    if 'APAC' in fn_upper:
        if 'HIGH_ROLLER' in fn_upper or 'HIGH ROLLER' in fn_upper:
            return 'WSOP_APAC_HR', 'APAC'
        return 'WSOP_APAC_ME', 'APAC'

    # GCC (Global Casino Championship)
    if 'GCC' in fn_upper:
        return 'WSOP_GCC', 'LV'

    # Main Event
    if 'ME' in fn_upper or 'MAIN EVENT' in fn_upper:
        return 'WSOP_ME', 'LV'

    return 'WSOP_OTHER', 'LV'


def extract_episode_num(filename: str) -> int | None:
    """Extract episode number (Episode_1, ME01, etc)."""
    # WSOPE pattern: Episode_X
    match = re.search(r'Episode[_\s]*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))

    # ME pattern: ME01, ME02
    match = re.search(r'ME(\d+)', filename, re.I)
    if match:
        return int(match.group(1))

    return None


def extract_show_num(filename: str) -> int | None:
    """Extract show number (SHOW 1, Show 01, etc)."""
    match = re.search(r'SHOW\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def extract_part_num(filename: str) -> int | None:
    """Extract part number (P01, P2, Part 1, etc)."""
    match = re.search(r'[_\s]P(\d+)', filename, re.I)
    if match:
        return int(match.group(1))

    match = re.search(r'Part\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))

    return None


def generate_entry_key(elem: NasElement) -> str:
    parts = [f'WSOP_{elem.year}']

    if elem.content_type == 'WSOP_ME':
        parts.append('ME')
        if elem.episode_num:
            parts.append(f'EP{elem.episode_num}')
    elif elem.content_type == 'WSOPE':
        parts.append('EU')
        if elem.episode_num:
            parts.append(f'EP{elem.episode_num}')
    elif elem.content_type == 'WSOP_APAC_ME':
        parts.append('APAC_ME')
        if elem.episode_num:
            parts.append(f'EP{elem.episode_num}')
        elif elem.show_num:
            parts.append(f'S{elem.show_num}')
    elif elem.content_type == 'WSOP_APAC_HR':
        parts.append('APAC_HR')
        if elem.show_num:
            parts.append(f'S{elem.show_num}')
    elif elem.content_type == 'WSOP_GCC':
        parts.append('GCC')
        if elem.part_num:
            parts.append(f'P{elem.part_num}')

    return '_'.join(parts)


def generate_category(elem: NasElement) -> str:
    if elem.content_type == 'WSOP_ME':
        return f'WSOP {elem.year} Main Event'
    elif elem.content_type == 'WSOPE':
        return f'WSOP Europe {elem.year}'
    elif elem.content_type == 'WSOP_APAC_ME':
        return f'WSOP APAC {elem.year} Main Event'
    elif elem.content_type == 'WSOP_APAC_HR':
        return f'WSOP APAC {elem.year} High Roller'
    elif elem.content_type == 'WSOP_GCC':
        return f'WSOP {elem.year} Global Casino Championship'
    return f'WSOP {elem.year} Other'


def generate_title(elem: NasElement) -> str:
    if elem.content_type == 'WSOP_ME':
        if elem.episode_num:
            return f'Main Event Episode {elem.episode_num}'
        return 'Main Event'

    if elem.content_type == 'WSOPE':
        if elem.episode_num:
            return f'Europe Episode {elem.episode_num}'
        return 'Europe'

    if elem.content_type == 'WSOP_APAC_ME':
        if elem.episode_num:
            return f'APAC Main Event Episode {elem.episode_num}'
        if elem.show_num:
            return f'APAC Main Event Show {elem.show_num}'
        return 'APAC Main Event'

    if elem.content_type == 'WSOP_APAC_HR':
        if elem.show_num:
            return f'APAC High Roller Show {elem.show_num}'
        return 'APAC High Roller'

    if elem.content_type == 'WSOP_GCC':
        if elem.part_num:
            return f'GCC Part {elem.part_num}'
        return 'Global Casino Championship'

    return elem.filename[:50]


def load_nas_files(db, year: int) -> list[NasElement]:
    files = db.query(NasFile).filter(
        NasFile.year == year,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    elements = []
    for f in files:
        content_type, region = extract_content_type(f.filename, year)
        episode_num = extract_episode_num(f.filename)
        show_num = extract_show_num(f.filename)
        part_num = extract_part_num(f.filename)

        # Determine event type
        if content_type == 'WSOP_ME':
            event_type = 'ME'
        elif content_type == 'WSOPE':
            event_type = 'EU'
        elif content_type in ['WSOP_APAC_ME', 'WSOP_APAC_HR']:
            event_type = 'APAC'
        elif content_type == 'WSOP_GCC':
            event_type = 'GCC'
        else:
            event_type = 'OTHER'

        elements.append(NasElement(
            file_id=f.id,
            full_path=f.full_path or '',
            filename=f.filename,
            year=year,
            content_type=content_type,
            region=region,
            event_type=event_type,
            episode_num=episode_num,
            show_num=show_num,
            part_num=part_num,
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
        print(f'    Created new sheet: {sheet_name}')


def write_sheet(sheets, sheet_name: str, rows: list):
    ensure_sheet_exists(sheets, sheet_name)
    sheets.values().clear(spreadsheetId=GOOGLE_SHEETS_ID, range=f'{sheet_name}!A:Z').execute()
    result = sheets.values().update(
        spreadsheetId=GOOGLE_SHEETS_ID,
        range=f'{sheet_name}!A1',
        valueInputOption='RAW',
        body={'values': rows}
    ).execute()
    return result.get('updatedRows', 0)


def export_year_to_sheet(sheets, year: int, elements: list[NasElement]) -> int:
    sheet_name = f'{year}_Catalog'

    headers = [
        'No', 'Entry Key', 'Match Type', 'Role', 'Backup Type',
        'Category', 'Title', 'PokerGO Title',
        'Region', 'Event Type', 'Event #', 'Day', 'Part', 'RAW',
        'Size (GB)', 'Filename', 'Full Path'
    ]
    rows = [headers]

    # Sort: ME first, then EU, then APAC, then by episode/show
    def sort_key(x):
        type_order = {
            'WSOP_ME': 0,
            'WSOPE': 1,
            'WSOP_APAC_ME': 2,
            'WSOP_APAC_HR': 3,
            'WSOP_GCC': 4,
            'WSOP_OTHER': 5
        }
        return (
            type_order.get(x.content_type, 9),
            x.episode_num or 0,
            x.show_num or 0,
            x.part_num or 0
        )

    for idx, elem in enumerate(sorted(elements, key=sort_key), 1):
        entry_key = generate_entry_key(elem)
        category = generate_category(elem)
        title = generate_title(elem)
        size_gb = elem.size_bytes / (1024**3)

        rows.append([
            idx, entry_key, 'NAS_ONLY', elem.role, '-',
            category, title, '',
            elem.region, elem.event_type, '', '', elem.part_num or '', '',
            f'{size_gb:.2f}', elem.filename, elem.full_path
        ])

    return write_sheet(sheets, sheet_name, rows)


def main():
    print('=' * 70)
    print('HD Era NAS Matching (2011-2016)')
    print('=' * 70)

    db = next(get_db())
    sheets = get_sheets_service()

    total_files = 0
    total_size = 0
    year_stats = []

    for year in HD_YEARS:
        elements = load_nas_files(db, year)
        if not elements:
            continue

        file_count = len(elements)
        year_size = sum(e.size_bytes for e in elements)
        total_files += file_count
        total_size += year_size

        # Count by type
        type_counts = defaultdict(int)
        for e in elements:
            type_counts[e.content_type] += 1

        rows_written = export_year_to_sheet(sheets, year, elements)

        type_summary = ', '.join(f'{t.replace("WSOP_", "")}: {c}' for t, c in sorted(type_counts.items()))
        print(f'  {year}_Catalog: {file_count} files ({year_size/(1024**3):.1f} GB) [{type_summary}]')

        year_stats.append((year, file_count, year_size, dict(type_counts)))

    print('\n' + '=' * 70)
    print(f'[OK] HD Era completed!')
    print(f'  Years processed: {len(year_stats)}')
    print(f'  Total files: {total_files}')
    print(f'  Total size: {total_size/(1024**3):.1f} GB')
    print('=' * 70)


if __name__ == '__main__':
    main()
