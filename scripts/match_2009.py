"""2009 NAS Matching Script.

2009 Structure:
- 2009 WSOP ME01-ME24 (Main Event Episodes)
- 2009 WSOP ME25 Final Table Part 1/2
- 2009 WSOP Show 1-6 (Bracelet Events)
- WSOP_2009_31-1.mxf, 31-2.mxf (Final Table backup)
- WSOPE09_Episode_X (Europe mov, EP 1,3,5,7-10)
- WSOP Europe 2009 mp4 (ME EP 2,4,6, Caesars Cup)

Grouping Rules:
- ME episodes: each PRIMARY
- Final Table Part 1/2: each PRIMARY
- Shows: each PRIMARY
- MXF: BACKUP
- Europe mov/mp4: different episodes, all PRIMARY
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
    content_type: str     # WSOP_ME, WSOP_ME_FT, WSOP_BR, WSOP_EU, WSOP_MXF
    region: str           # LV, EU
    episode_num: int | None
    part_num: int | None
    event_name: str
    ext: str
    size_bytes: int
    role: str = 'PRIMARY'
    group_id: str = ''


def extract_info(filename: str) -> tuple:
    """Extract episode, part, and event info from filename."""
    fn = filename
    fn_lower = fn.lower()

    episode_num = None
    part_num = None
    event_name = ''

    # ME episode
    match = re.search(r'ME(\d+)', fn, re.I)
    if match:
        episode_num = int(match.group(1))

    # Part number
    match = re.search(r'Part\s*(\d+)', fn, re.I)
    if match:
        part_num = int(match.group(1))

    # WSOPE Episode
    match = re.search(r'Episode[_\s]*(\d+)', fn, re.I)
    if match and not episode_num:
        episode_num = int(match.group(1))

    # Show number for BR
    match = re.search(r'Show\s*(\d+)\s*(.+?)(?:\.mov|$)', fn, re.I)
    if match:
        episode_num = int(match.group(1))
        event_name = match.group(2).strip()
        # Clean up event name
        event_name = re.sub(r'\.mov$', '', event_name)

    # Caesars Cup
    if 'caesars cup' in fn_lower:
        match = re.search(r'Part\s*(\d+)', fn, re.I)
        if match:
            part_num = int(match.group(1))
        event_name = 'Caesars Cup'

    return episode_num, part_num, event_name


def get_extension(filename: str) -> str:
    """Get file extension."""
    # Handle double extensions like .mov.mov
    if filename.endswith('.mov.mov'):
        return 'mov'
    return filename.split('.')[-1].lower()


def classify_file(filename: str) -> tuple[str, str]:
    """Classify file into content type and region."""
    fn = filename
    fn_lower = fn.lower()

    # MXF
    if fn_lower.endswith('.mxf'):
        return ('WSOP_MXF', 'LV')

    # Europe
    if 'wsope' in fn_lower or 'europe' in fn_lower:
        return ('WSOP_EU', 'EU')

    # Final Table
    if 'final table' in fn_lower:
        return ('WSOP_ME_FT', 'LV')

    # Main Event
    if re.search(r'2009 WSOP ME\d+', fn):
        return ('WSOP_ME', 'LV')

    # Shows = Bracelet Events
    if re.search(r'2009 WSOP Show', fn):
        return ('WSOP_BR', 'LV')

    return ('WSOP_OTHER', 'LV')


def generate_group_id(elem: NasElement) -> str:
    """Generate group ID for PRIMARY/BACKUP assignment."""
    if elem.content_type == 'WSOP_MXF':
        return 'WSOP_2009_MXF'  # Group all MXF together as BACKUP

    if elem.content_type == 'WSOP_ME':
        return f'WSOP_2009_ME_EP{elem.episode_num}'

    if elem.content_type == 'WSOP_ME_FT':
        return f'WSOP_2009_ME_FT_PT{elem.part_num}'

    if elem.content_type == 'WSOP_BR':
        return f'WSOP_2009_BR_S{elem.episode_num}'

    if elem.content_type == 'WSOP_EU':
        if 'caesars' in elem.event_name.lower():
            return f'WSOP_2009_EU_CC_PT{elem.part_num}'
        return f'WSOP_2009_EU_EP{elem.episode_num}'

    return f'WSOP_2009_OTHER_{elem.filename}'


def assign_roles(elements: list[NasElement]) -> list[NasElement]:
    """Assign PRIMARY/BACKUP roles within groups."""
    groups = defaultdict(list)
    for elem in elements:
        elem.group_id = generate_group_id(elem)
        groups[elem.group_id].append(elem)

    result = []
    for group_id, group_elements in groups.items():
        # MXF group: all BACKUP
        if 'MXF' in group_id:
            for elem in group_elements:
                elem.role = 'BACKUP'
            result.extend(group_elements)
            continue

        # Single file = PRIMARY
        if len(group_elements) == 1:
            group_elements[0].role = 'PRIMARY'
            result.append(group_elements[0])
            continue

        # Multiple files: first = PRIMARY, rest = BACKUP
        group_elements[0].role = 'PRIMARY'
        for elem in group_elements[1:]:
            elem.role = 'BACKUP'
        result.extend(group_elements)

    return result


def generate_entry_key(elem: NasElement) -> str:
    """Generate entry key for catalog."""
    if elem.content_type == 'WSOP_ME':
        return f'WSOP_2009_ME_EP{elem.episode_num:02d}'
    elif elem.content_type == 'WSOP_ME_FT':
        return f'WSOP_2009_ME_FT_PT{elem.part_num}'
    elif elem.content_type == 'WSOP_BR':
        return f'WSOP_2009_BR_S{elem.episode_num:02d}'
    elif elem.content_type == 'WSOP_EU':
        if 'caesars' in elem.event_name.lower():
            return f'WSOP_2009_EU_CC_PT{elem.part_num}'
        return f'WSOP_2009_EU_EP{elem.episode_num:02d}'
    elif elem.content_type == 'WSOP_MXF':
        return 'WSOP_2009_MXF'
    return 'WSOP_2009_OTHER'


def generate_category(elem: NasElement) -> str:
    """Generate category name."""
    if elem.content_type == 'WSOP_ME':
        return 'WSOP 2009 Main Event'
    elif elem.content_type == 'WSOP_ME_FT':
        return 'WSOP 2009 Main Event Final Table'
    elif elem.content_type == 'WSOP_BR':
        return 'WSOP 2009 Bracelet Events'
    elif elem.content_type == 'WSOP_EU':
        return 'WSOP 2009 Europe'
    elif elem.content_type == 'WSOP_MXF':
        return 'WSOP 2009 MXF Masters'
    return 'WSOP 2009 Other'


def generate_title(elem: NasElement) -> str:
    """Generate display title."""
    if elem.content_type == 'WSOP_ME':
        title = f'2009 Main Event Episode {elem.episode_num}'
    elif elem.content_type == 'WSOP_ME_FT':
        title = f'2009 Main Event Final Table Part {elem.part_num}'
    elif elem.content_type == 'WSOP_BR':
        title = f'2009 Show {elem.episode_num}: {elem.event_name}' if elem.event_name else f'2009 Bracelet Event Show {elem.episode_num}'
    elif elem.content_type == 'WSOP_EU':
        if 'caesars' in elem.event_name.lower():
            title = f'2009 Europe Caesars Cup Part {elem.part_num}'
        else:
            title = f'2009 Europe Episode {elem.episode_num}'
    elif elem.content_type == 'WSOP_MXF':
        title = '2009 MXF'
    else:
        title = '2009 Other'

    if elem.role == 'BACKUP':
        title += ' (Back up)'

    return title


def load_nas_files(db) -> list[NasElement]:
    """Load 2009 NAS files from database."""
    files = db.query(NasFile).filter(
        NasFile.year == 2009,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    elements = []
    for f in files:
        content_type, region = classify_file(f.filename)
        episode_num, part_num, event_name = extract_info(f.filename)
        ext = get_extension(f.filename)

        elements.append(NasElement(
            file_id=f.id,
            full_path=f.full_path or '',
            filename=f.filename,
            content_type=content_type,
            region=region,
            episode_num=episode_num,
            part_num=part_num,
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
    return result.get('updatedRows', 0)


def export_to_sheet(sheets, elements: list[NasElement]) -> int:
    sheet_name = '2009_Catalog'

    headers = [
        'No', 'Entry Key', 'Match Type', 'Role', 'Backup Type',
        'Category', 'Title', 'PokerGO Title',
        'Region', 'Event Type', 'Event #', 'Day', 'Part', 'RAW',
        'Size (GB)', 'Filename', 'Full Path'
    ]
    rows = [headers]

    def sort_key(x):
        type_order = {'WSOP_ME': 0, 'WSOP_ME_FT': 1, 'WSOP_BR': 2, 'WSOP_EU': 3, 'WSOP_MXF': 4, 'WSOP_OTHER': 5}
        role_order = 0 if x.role == 'PRIMARY' else 1
        return (
            type_order.get(x.content_type, 9),
            x.episode_num or 0,
            x.part_num or 0,
            role_order
        )

    for idx, elem in enumerate(sorted(elements, key=sort_key), 1):
        entry_key = generate_entry_key(elem)
        category = generate_category(elem)
        title = generate_title(elem)
        size_gb = elem.size_bytes / (1024**3)

        event_type = 'ME' if elem.content_type in ('WSOP_ME', 'WSOP_ME_FT') else 'BR' if elem.content_type == 'WSOP_BR' else 'OTHER'

        rows.append([
            idx, entry_key, 'NAS_ONLY', elem.role, '-',
            category, title, '',
            elem.region, event_type, '', '', elem.part_num or '', '',
            f'{size_gb:.2f}', elem.filename, elem.full_path
        ])

    return write_sheet(sheets, sheet_name, rows)


def main():
    print('=' * 70)
    print('2009 NAS Matching')
    print('=' * 70)

    db = next(get_db())
    sheets = get_sheets_service()

    # Load files
    print('\n[Step 1] Loading 2009 files...')
    elements = load_nas_files(db)
    print(f'  Total: {len(elements)} files')

    # Analysis
    print('\n[Step 2] Analysis by type:')
    type_counts = defaultdict(lambda: {'primary': 0, 'backup': 0})
    for e in elements:
        if e.role == 'PRIMARY':
            type_counts[e.content_type]['primary'] += 1
        else:
            type_counts[e.content_type]['backup'] += 1

    for ct in ['WSOP_ME', 'WSOP_ME_FT', 'WSOP_BR', 'WSOP_EU', 'WSOP_MXF', 'WSOP_OTHER']:
        if ct in type_counts:
            c = type_counts[ct]
            print(f'  {ct}: P:{c["primary"]} B:{c["backup"]}')

    # Export
    print('\n[Step 3] Exporting to Google Sheets...')
    rows_written = export_to_sheet(sheets, elements)
    print(f'  2009_Catalog: {rows_written} rows')

    # Summary
    total_primary = sum(1 for e in elements if e.role == 'PRIMARY')
    total_backup = sum(1 for e in elements if e.role == 'BACKUP')
    total_size = sum(e.size_bytes for e in elements) / (1024**3)

    print('\n' + '=' * 70)
    print('[OK] 2009 Matching completed!')
    print(f'  Files: {len(elements)} (PRIMARY: {total_primary}, BACKUP: {total_backup})')
    print(f'  Size: {total_size:.1f} GB')
    print('=' * 70)


if __name__ == '__main__':
    main()
