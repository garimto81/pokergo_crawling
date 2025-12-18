"""HD Era Early Years NAS Matching Script (2011-2016).

HD Era patterns:
- 2011: WS11_{TYPE}{EP}_NB.mp4 (ME, GM, HU, PPC)
- 2012: WS12_Show_{N}_{TYPE}{EP}_NB.mp4
- 2013: WSOP13_{TYPE}{EP}_NB.mp4 (includes APAC)
- 2014: WSOP14_{TYPE}{EP}_FINAL_4CH.mp4 (includes BO)
- 2015: WSOP15_{TYPE}{EP}_FINAL_4CH.mov
- 2016: WSOP16_{TYPE}{EP}_NB.mp4

Rules:
- Each file is generally unique (PRIMARY)
- MXF files are BACKUP
- WSOPE/WSOPA = Europe region
- Version suffixes (_v1, _v2): latest version = PRIMARY
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

HD_EARLY_YEARS = list(range(2011, 2017))  # 2011-2016


@dataclass
class NasElement:
    file_id: int
    full_path: str
    filename: str
    year: int
    content_type: str     # ME, GM, HU, PPC, NC, BO, GCC, APAC, EU, MXF, OTHER
    region: str           # LV, EU, APAC
    episode_num: int | None
    show_num: int | None
    event_name: str
    ext: str
    size_bytes: int
    role: str = 'PRIMARY'
    group_id: str = ''


def extract_info(filename: str, year: int) -> tuple:
    """Extract content type, region, episode, show, and event name."""
    fn = filename
    fn_upper = fn.upper()

    content_type = 'OTHER'
    region = 'LV'
    episode_num = None
    show_num = None
    event_name = ''

    # Check region first
    if 'WSOPE' in fn_upper or 'WSOPA' in fn_upper:
        region = 'EU'
        content_type = 'EU'
        match = re.search(r'Episode[_\s]*(\d+)', fn, re.I)
        if match:
            episode_num = int(match.group(1))
        return content_type, region, episode_num, show_num, event_name

    if 'APAC' in fn_upper:
        region = 'APAC'
        content_type = 'APAC'
        match = re.search(r'ME(\d+)', fn, re.I)
        if match:
            episode_num = int(match.group(1))
        return content_type, region, episode_num, show_num, event_name

    # MXF files
    if fn.lower().endswith('.mxf'):
        content_type = 'MXF'
        match = re.search(r'ME(\d+)', fn, re.I)
        if match:
            episode_num = int(match.group(1))
        return content_type, region, episode_num, show_num, event_name

    # Extract content type and episode
    # Pattern: WS{YY}_{TYPE}{EP} or WSOP{YY}_{TYPE}{EP}
    type_patterns = [
        (r'_ME(\d+)', 'ME'),
        (r'_GM(\d+)', 'GM'),
        (r'_HU(\d+)', 'HU'),
        (r'_PPC(\d+)', 'PPC'),
        (r'_NC(\d+)', 'NC'),
        (r'_BO(\d+)', 'BO'),
        (r'_GCC_P(\d+)', 'GCC'),
        # 2012 specific patterns
        (r'_BIG_ONE_(\d+)', 'BO'),      # Big One for One Drop
        (r'_NAT_CHAMP_(\d+)', 'NC'),    # National Championship
    ]

    for pattern, ctype in type_patterns:
        match = re.search(pattern, fn, re.I)
        if match:
            content_type = ctype
            episode_num = int(match.group(1))
            break

    # Final Table detection (no episode number in pattern)
    if content_type == 'OTHER' and '_FINAL' in fn_upper:
        content_type = 'ME_FT'
        # Try to extract show number as reference
        show_match = re.search(r'Show[_\s]*(\d+)', fn, re.I)
        if show_match:
            episode_num = int(show_match.group(1))

    # Show number for 2012 format
    show_match = re.search(r'Show[_\s]*(\d+)', fn, re.I)
    if show_match:
        show_num = int(show_match.group(1))

    # Event name extraction for special events
    if 'BIG_ONE' in fn_upper:
        event_name = 'Big One for One Drop'
    elif 'NAT_CHAMP' in fn_upper:
        event_name = 'National Championship'

    return content_type, region, episode_num, show_num, event_name


def get_extension(filename: str) -> str:
    """Get file extension."""
    return filename.split('.')[-1].lower()


def generate_group_id(elem: NasElement) -> str:
    """Generate group ID for PRIMARY/BACKUP assignment."""
    base = f'WSOP_{elem.year}'

    if elem.content_type == 'MXF':
        if elem.episode_num:
            return f'{base}_MXF_ME{elem.episode_num}'
        return f'{base}_MXF'

    if elem.content_type == 'EU':
        if elem.episode_num:
            return f'{base}_EU_EP{elem.episode_num}'
        return f'{base}_EU_{elem.filename}'

    if elem.content_type == 'APAC':
        if elem.episode_num:
            return f'{base}_APAC_ME{elem.episode_num}'
        return f'{base}_APAC_{elem.filename}'

    if elem.content_type == 'ME':
        if elem.episode_num:
            return f'{base}_ME_EP{elem.episode_num}'
        return f'{base}_ME_{elem.filename}'

    if elem.content_type == 'ME_FT':
        if elem.episode_num:
            return f'{base}_ME_FT_S{elem.episode_num}'
        return f'{base}_ME_FT'

    if elem.episode_num:
        return f'{base}_{elem.content_type}_EP{elem.episode_num}'
    return f'{base}_{elem.content_type}_{elem.filename}'


# Extension priority: mp4 > mov > mxf
EXT_PRIORITY = {'mp4': 1, 'mov': 2, 'mxf': 3}


def assign_roles(elements: list[NasElement]) -> list[NasElement]:
    """Assign PRIMARY/BACKUP roles within groups."""
    groups = defaultdict(list)
    for elem in elements:
        elem.group_id = generate_group_id(elem)
        groups[elem.group_id].append(elem)

    result = []
    for group_id, group_elements in groups.items():
        # Sort by extension priority, then by size descending
        group_elements.sort(key=lambda x: (EXT_PRIORITY.get(x.ext, 99), -x.size_bytes))

        # MXF-only groups: all BACKUP
        if all(e.content_type == 'MXF' for e in group_elements):
            for elem in group_elements:
                elem.role = 'BACKUP'
            result.extend(group_elements)
            continue

        # Single file = PRIMARY
        if len(group_elements) == 1:
            group_elements[0].role = 'PRIMARY'
            result.append(group_elements[0])
            continue

        # First file = PRIMARY, rest = BACKUP
        group_elements[0].role = 'PRIMARY'
        for elem in group_elements[1:]:
            elem.role = 'BACKUP'
        result.extend(group_elements)

    return result


def generate_entry_key(elem: NasElement) -> str:
    """Generate entry key for catalog."""
    base = f'WSOP_{elem.year}'

    if elem.content_type == 'EU':
        return f'{base}_EU_EP{elem.episode_num:02d}' if elem.episode_num else f'{base}_EU'
    elif elem.content_type == 'APAC':
        return f'{base}_APAC_ME{elem.episode_num:02d}' if elem.episode_num else f'{base}_APAC'
    elif elem.content_type == 'MXF':
        return f'{base}_MXF_ME{elem.episode_num:02d}' if elem.episode_num else f'{base}_MXF'
    elif elem.content_type == 'ME_FT':
        return f'{base}_ME_FT'
    elif elem.content_type in ('ME', 'GM', 'HU', 'PPC', 'NC', 'BO', 'GCC'):
        if elem.episode_num:
            return f'{base}_{elem.content_type}_EP{elem.episode_num:02d}'
        return f'{base}_{elem.content_type}'
    return f'{base}_OTHER'


def generate_category(elem: NasElement) -> str:
    """Generate category name."""
    year = elem.year
    type_names = {
        'ME': f'WSOP {year} Main Event',
        'ME_FT': f'WSOP {year} Main Event Final Table',
        'GM': f'WSOP {year} Game',
        'HU': f'WSOP {year} Heads Up',
        'PPC': f'WSOP {year} Players Championship',
        'NC': f'WSOP {year} National Championship',
        'BO': f'WSOP {year} Big One',
        'GCC': f'WSOP {year} Global Casino Championship',
        'EU': f'WSOP {year} Europe',
        'APAC': f'WSOP {year} APAC',
        'MXF': f'WSOP {year} MXF Masters',
    }
    return type_names.get(elem.content_type, f'WSOP {year} Other')


def generate_title(elem: NasElement) -> str:
    """Generate display title."""
    year = elem.year
    type_titles = {
        'ME': f'{year} Main Event Episode {elem.episode_num}',
        'ME_FT': f'{year} Main Event Final Table',
        'GM': f'{year} Game Episode {elem.episode_num}',
        'HU': f'{year} Heads Up Episode {elem.episode_num}',
        'PPC': f'{year} Players Championship Episode {elem.episode_num}',
        'NC': f'{year} National Championship Episode {elem.episode_num}',
        'BO': f'{year} Big One Episode {elem.episode_num}',
        'GCC': f'{year} Global Casino Championship Part {elem.episode_num}',
        'EU': f'{year} Europe Episode {elem.episode_num}',
        'APAC': f'{year} APAC Main Event Episode {elem.episode_num}',
        'MXF': f'{year} MXF Episode {elem.episode_num}' if elem.episode_num else f'{year} MXF',
    }
    title = type_titles.get(elem.content_type, f'{year} Episode {elem.episode_num}')

    if elem.role == 'BACKUP':
        title += ' (Back up)'

    return title


def load_nas_files(db, year: int) -> list[NasElement]:
    """Load NAS files for a specific year."""
    files = db.query(NasFile).filter(
        NasFile.year == year,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    elements = []
    for f in files:
        content_type, region, episode_num, show_num, event_name = extract_info(f.filename, year)
        ext = get_extension(f.filename)

        elements.append(NasElement(
            file_id=f.id,
            full_path=f.full_path or '',
            filename=f.filename,
            year=year,
            content_type=content_type,
            region=region,
            episode_num=episode_num,
            show_num=show_num,
            event_name=event_name,
            ext=ext,
            size_bytes=f.size_bytes or 0,
            role='PRIMARY'
        ))

    # Assign PRIMARY/BACKUP roles
    elements = assign_roles(elements)
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

    def sort_key(x):
        type_order = {'ME': 0, 'ME_FT': 1, 'GM': 2, 'HU': 3, 'PPC': 4, 'NC': 5, 'BO': 6, 'GCC': 7, 'EU': 8, 'APAC': 9, 'MXF': 10, 'OTHER': 11}
        role_order = 0 if x.role == 'PRIMARY' else 1
        return (
            type_order.get(x.content_type, 99),
            x.episode_num or 0,
            role_order
        )

    for idx, elem in enumerate(sorted(elements, key=sort_key), 1):
        entry_key = generate_entry_key(elem)
        category = generate_category(elem)
        title = generate_title(elem)
        size_gb = elem.size_bytes / (1024**3)

        rows.append([
            idx, entry_key, 'NAS_ONLY', elem.role, '-',
            category, title, '',
            elem.region, elem.content_type, '', '', '', '',
            f'{size_gb:.2f}', elem.filename, elem.full_path
        ])

    return write_sheet(sheets, sheet_name, rows)


def main():
    print('=' * 70)
    print('HD Era Early Years NAS Matching (2011-2016)')
    print('=' * 70)

    db = next(get_db())
    sheets = get_sheets_service()

    total_files = 0
    total_primary = 0
    total_backup = 0
    total_size = 0

    for year in HD_EARLY_YEARS:
        elements = load_nas_files(db, year)
        if not elements:
            continue

        # Count by type
        type_counts = defaultdict(lambda: {'primary': 0, 'backup': 0})
        for e in elements:
            if e.role == 'PRIMARY':
                type_counts[e.content_type]['primary'] += 1
            else:
                type_counts[e.content_type]['backup'] += 1

        year_primary = sum(1 for e in elements if e.role == 'PRIMARY')
        year_backup = sum(1 for e in elements if e.role == 'BACKUP')
        year_size = sum(e.size_bytes for e in elements) / (1024**3)

        rows_written = export_year_to_sheet(sheets, year, elements)

        # Summary line
        type_summary = ', '.join(f'{t}:{c["primary"]}' for t, c in sorted(type_counts.items()) if c['primary'] > 0)
        print(f'  {year}_Catalog: {len(elements)} files (P:{year_primary} B:{year_backup}) [{type_summary}]')

        total_files += len(elements)
        total_primary += year_primary
        total_backup += year_backup
        total_size += year_size

    print('\n' + '=' * 70)
    print('[OK] HD Era Early Years completed!')
    print(f'  Years: {len(HD_EARLY_YEARS)} (2011-2016)')
    print(f'  Total files: {total_files} (PRIMARY: {total_primary}, BACKUP: {total_backup})')
    print(f'  Total size: {total_size:.1f} GB')
    print('=' * 70)


if __name__ == '__main__':
    main()
