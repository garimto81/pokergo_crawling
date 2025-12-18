"""BOOM Era NAS Matching Script (2003-2010).

Matches and exports BOOM era NAS files.
Main Event + Bracelet Events + Best Of compilations.

Filename patterns:
- 2003: "2003 WSOP Best of ALL INS", "2003 2003 WSOP Best of..."
- 2004: "2004 WSOP Tournament of Champs"
- 2005: "WSOP 2005 Show 10 2k Limit Holdem"
- 2006: "WSOP_2006_21.mxf", "WSOP 2006 EOE Final Table"
- 2007: "ESPN 2007 WSOP SEASON 5 SHOW 1"
- 2008: "ESPN 2008 WSOP SEASON 6 SHOW 1", "WSOP_2008_01.mp4"
- 2009: "2009 WSOP ME01.mov"
- 2010: "2010 WSOP ME03.mov"
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

BOOM_YEARS = list(range(2003, 2011))  # 2003-2010


@dataclass
class NasElement:
    file_id: int
    full_path: str
    filename: str
    year: int
    content_type: str     # WSOP_ME, WSOP_BR, WSOP_BEST, WSOP_OTHER
    region: str
    event_type: str
    episode_num: int | None
    show_num: int | None
    event_name: str
    size_bytes: int
    role: str = 'PRIMARY'


def extract_content_type(filename: str, year: int) -> str:
    """Determine content type from filename."""
    fn_upper = filename.upper()

    # Main Event patterns
    if 'ME' in fn_upper or 'MAIN EVENT' in fn_upper:
        return 'WSOP_ME'

    # Best Of compilations (2003)
    if 'BEST OF' in fn_upper:
        return 'WSOP_BEST'

    # Tournament of Champions (2004)
    if 'TOURNAMENT OF CHAMP' in fn_upper:
        return 'WSOP_BR'

    # Show/Episode patterns (usually Bracelet Events coverage)
    if 'SHOW' in fn_upper:
        return 'WSOP_BR'

    # EOE = Event of Events
    if 'EOE' in fn_upper:
        return 'WSOP_BR'

    # Numbered episodes without ME marker
    if re.search(r'WSOP_?\d{4}_\d+', fn_upper):
        return 'WSOP_BR'

    return 'WSOP_OTHER'


def extract_episode_num(filename: str) -> int | None:
    """Extract episode number (ME01, ME02, etc)."""
    match = re.search(r'ME(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def extract_show_num(filename: str) -> int | None:
    """Extract show number (SHOW 1, Show 10, etc)."""
    match = re.search(r'SHOW\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))

    # WSOP_2006_21.mxf pattern
    match = re.search(r'WSOP_\d{4}_(\d+)', filename, re.I)
    if match:
        return int(match.group(1))

    return None


def extract_event_name(filename: str) -> str:
    """Extract event name from filename."""
    # Best Of patterns
    match = re.search(r'Best of\s+(.+?)(?:_ES|\.mov|\.mp4|\.mxf|$)', filename, re.I)
    if match:
        return match.group(1).strip()

    # Tournament of Champions
    if 'Tournament of Champ' in filename:
        return 'Tournament of Champions'

    # Show title (2005 pattern)
    match = re.search(r'Show\s*\d+\s+(.+?)(?:_ES|\.mov|\.mp4|\.mxf|$)', filename, re.I)
    if match:
        return match.group(1).strip()

    # EOE = Event of Events
    if 'EOE' in filename.upper():
        return 'Event of Events'

    return ''


def generate_entry_key(elem: NasElement) -> str:
    parts = [f'WSOP_{elem.year}']

    if elem.content_type == 'WSOP_ME':
        parts.append('ME')
        if elem.episode_num:
            parts.append(f'EP{elem.episode_num}')
    elif elem.content_type == 'WSOP_BEST':
        parts.append('BEST')
        if elem.show_num:
            parts.append(f'{elem.show_num}')
    elif elem.content_type == 'WSOP_BR':
        parts.append('BR')
        if elem.show_num:
            parts.append(f'S{elem.show_num}')

    return '_'.join(parts)


def generate_category(elem: NasElement) -> str:
    if elem.content_type == 'WSOP_ME':
        return f'WSOP {elem.year} Main Event'
    elif elem.content_type == 'WSOP_BEST':
        return f'WSOP {elem.year} Best Of'
    elif elem.content_type == 'WSOP_BR':
        return f'WSOP {elem.year} Coverage'
    return f'WSOP {elem.year} Other'


def generate_title(elem: NasElement) -> str:
    if elem.content_type == 'WSOP_ME':
        if elem.episode_num:
            return f'Main Event Episode {elem.episode_num}'
        return 'Main Event'

    if elem.content_type == 'WSOP_BEST':
        if elem.event_name:
            return f'Best Of: {elem.event_name}'
        return 'Best Of'

    if elem.content_type == 'WSOP_BR':
        title_parts = []
        if elem.event_name:
            title_parts.append(elem.event_name)
        if elem.show_num:
            if title_parts:
                title_parts.append(f'Show {elem.show_num}')
            else:
                title_parts.append(f'Show {elem.show_num}')
        return ' '.join(title_parts) if title_parts else 'Coverage'

    return elem.filename[:50]


def load_nas_files(db, year: int) -> list[NasElement]:
    files = db.query(NasFile).filter(
        NasFile.year == year,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    elements = []
    for f in files:
        content_type = extract_content_type(f.filename, year)
        episode_num = extract_episode_num(f.filename)
        show_num = extract_show_num(f.filename)
        event_name = extract_event_name(f.filename)

        if content_type == 'WSOP_ME':
            event_type = 'ME'
        elif content_type == 'WSOP_BR':
            event_type = 'BR'
        elif content_type == 'WSOP_BEST':
            event_type = 'BEST'
        else:
            event_type = 'OTHER'

        elements.append(NasElement(
            file_id=f.id,
            full_path=f.full_path or '',
            filename=f.filename,
            year=year,
            content_type=content_type,
            region='LV',
            event_type=event_type,
            episode_num=episode_num,
            show_num=show_num,
            event_name=event_name,
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

    # Sort: ME first, then by episode/show number
    def sort_key(x):
        type_order = {'WSOP_ME': 0, 'WSOP_BR': 1, 'WSOP_BEST': 2, 'WSOP_OTHER': 3}
        return (
            type_order.get(x.content_type, 9),
            x.episode_num or 0,
            x.show_num or 0
        )

    for idx, elem in enumerate(sorted(elements, key=sort_key), 1):
        entry_key = generate_entry_key(elem)
        category = generate_category(elem)
        title = generate_title(elem)
        size_gb = elem.size_bytes / (1024**3)

        rows.append([
            idx, entry_key, 'NAS_ONLY', elem.role, '-',
            category, title, '',
            elem.region, elem.event_type, '', '', '', '',
            f'{size_gb:.2f}', elem.filename, elem.full_path
        ])

    return write_sheet(sheets, sheet_name, rows)


def main():
    print('=' * 70)
    print('BOOM Era NAS Matching (2003-2010)')
    print('=' * 70)

    db = next(get_db())
    sheets = get_sheets_service()

    total_files = 0
    total_size = 0
    year_stats = []

    for year in BOOM_YEARS:
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
    print(f'[OK] BOOM Era completed!')
    print(f'  Years processed: {len(year_stats)}')
    print(f'  Total files: {total_files}')
    print(f'  Total size: {total_size/(1024**3):.1f} GB')
    print('=' * 70)


if __name__ == '__main__':
    main()
