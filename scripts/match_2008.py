"""2008 NAS Matching Script.

2008 Structure:
- ESPN 2008 WSOP SEASON 6 SHOW 1 (single file)
- WSOP_2008_01.mp4 ~ WSOP_2008_31.mp4 (31 files)
- WSOP_2008_31.mxf (duplicate of #31)
- WSOPE08_Episode_1-8 (Europe, 8 files)

Grouping Rules:
- MP4 #31 + MXF #31: mp4 PRIMARY, mxf BACKUP
- WSOPE: Europe region, each PRIMARY
- ESPN: single PRIMARY
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
    content_type: str     # WSOP_LV, WSOP_EU, WSOP_ESPN, WSOP_MXF
    region: str           # LV, EU
    episode_num: int | None
    ext: str
    size_bytes: int
    role: str = 'PRIMARY'
    group_id: str = ''


def extract_episode_num(filename: str) -> int | None:
    """Extract episode/show number from filename."""
    # WSOP_2008_XX pattern
    match = re.search(r'WSOP_2008_(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    # WSOPE Episode pattern
    match = re.search(r'Episode_(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    # ESPN SHOW pattern
    match = re.search(r'SHOW\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def get_extension(filename: str) -> str:
    """Get file extension."""
    return filename.split('.')[-1].lower()


def classify_file(filename: str) -> tuple[str, str]:
    """Classify file into content type and region."""
    fn_lower = filename.lower()

    if 'wsope' in fn_lower:
        return ('WSOP_EU', 'EU')
    elif 'espn' in fn_lower:
        return ('WSOP_ESPN', 'LV')
    elif fn_lower.endswith('.mxf'):
        return ('WSOP_MXF', 'LV')
    else:
        return ('WSOP_LV', 'LV')


def generate_group_id(elem: NasElement) -> str:
    """Generate group ID for PRIMARY/BACKUP assignment."""
    if elem.content_type == 'WSOP_EU':
        return f'WSOP_2008_EU_EP{elem.episode_num}'
    elif elem.content_type == 'WSOP_ESPN':
        return f'WSOP_2008_ESPN_S{elem.episode_num}'
    elif elem.content_type in ('WSOP_LV', 'WSOP_MXF'):
        return f'WSOP_2008_LV_EP{elem.episode_num}'
    return f'WSOP_2008_OTHER_{elem.filename}'


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
        # Sort by extension priority
        group_elements.sort(key=lambda x: (EXT_PRIORITY.get(x.ext, 99), -x.size_bytes))

        # MXF-only groups: all BACKUP
        if len(group_elements) == 1 and group_elements[0].content_type == 'WSOP_MXF':
            group_elements[0].role = 'BACKUP'
            result.append(group_elements[0])
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
    if elem.content_type == 'WSOP_EU':
        return f'WSOP_2008_EU_EP{elem.episode_num:02d}'
    elif elem.content_type == 'WSOP_ESPN':
        return f'WSOP_2008_ESPN_S{elem.episode_num:02d}'
    elif elem.content_type == 'WSOP_MXF':
        return f'WSOP_2008_MXF_EP{elem.episode_num:02d}'
    return f'WSOP_2008_EP{elem.episode_num:02d}' if elem.episode_num else 'WSOP_2008_OTHER'


def generate_category(elem: NasElement) -> str:
    """Generate category name."""
    if elem.content_type == 'WSOP_EU':
        return 'WSOP 2008 Europe'
    elif elem.content_type == 'WSOP_ESPN':
        return 'WSOP 2008 ESPN Coverage'
    elif elem.content_type == 'WSOP_MXF':
        return 'WSOP 2008 MXF Masters'
    return 'WSOP 2008 Las Vegas'


def generate_title(elem: NasElement) -> str:
    """Generate display title."""
    if elem.content_type == 'WSOP_EU':
        title = f'2008 Europe Episode {elem.episode_num}'
    elif elem.content_type == 'WSOP_ESPN':
        title = f'2008 ESPN Season 6 Show {elem.episode_num}'
    elif elem.content_type == 'WSOP_MXF':
        title = f'2008 MXF Episode {elem.episode_num}'
    else:
        title = f'2008 Episode {elem.episode_num}'

    if elem.role == 'BACKUP':
        title += ' (Back up)'

    return title


def load_nas_files(db) -> list[NasElement]:
    """Load 2008 NAS files from database."""
    files = db.query(NasFile).filter(
        NasFile.year == 2008,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    elements = []
    for f in files:
        content_type, region = classify_file(f.filename)
        episode_num = extract_episode_num(f.filename)
        ext = get_extension(f.filename)

        elements.append(NasElement(
            file_id=f.id,
            full_path=f.full_path or '',
            filename=f.filename,
            content_type=content_type,
            region=region,
            episode_num=episode_num,
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
    sheet_name = '2008_Catalog'

    headers = [
        'No', 'Entry Key', 'Match Type', 'Role', 'Backup Type',
        'Category', 'Title', 'PokerGO Title',
        'Region', 'Event Type', 'Event #', 'Day', 'Part', 'RAW',
        'Size (GB)', 'Filename', 'Full Path'
    ]
    rows = [headers]

    def sort_key(x):
        type_order = {'WSOP_LV': 0, 'WSOP_ESPN': 1, 'WSOP_EU': 2, 'WSOP_MXF': 3}
        role_order = 0 if x.role == 'PRIMARY' else 1
        return (
            type_order.get(x.content_type, 9),
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
            elem.region, 'ME', '', '', '', '',
            f'{size_gb:.2f}', elem.filename, elem.full_path
        ])

    return write_sheet(sheets, sheet_name, rows)


def main():
    print('=' * 70)
    print('2008 NAS Matching')
    print('=' * 70)

    db = next(get_db())
    sheets = get_sheets_service()

    # Load files
    print('\n[Step 1] Loading 2008 files...')
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

    for ct in ['WSOP_LV', 'WSOP_ESPN', 'WSOP_EU', 'WSOP_MXF']:
        if ct in type_counts:
            c = type_counts[ct]
            print(f'  {ct}: P:{c["primary"]} B:{c["backup"]}')

    # Export
    print('\n[Step 3] Exporting to Google Sheets...')
    rows_written = export_to_sheet(sheets, elements)
    print(f'  2008_Catalog: {rows_written} rows')

    # Summary
    total_primary = sum(1 for e in elements if e.role == 'PRIMARY')
    total_backup = sum(1 for e in elements if e.role == 'BACKUP')
    total_size = sum(e.size_bytes for e in elements) / (1024**3)

    print('\n' + '=' * 70)
    print('[OK] 2008 Matching completed!')
    print(f'  Files: {len(elements)} (PRIMARY: {total_primary}, BACKUP: {total_backup})')
    print(f'  Size: {total_size:.1f} GB')
    print('=' * 70)


if __name__ == '__main__':
    main()
