"""2007 NAS Matching Script.

2007 Structure:
- ESPN 2007 WSOP SEASON 5 SHOW 1-32
- MXF files: WSOP_2007_25.mxf, _26.mxf (match Show 25-26)
- No ME/BR distinction in filenames

Grouping Rules:
- Each ESPN Show = PRIMARY
- MXF matches Show number → BACKUP
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
    content_type: str     # WSOP_COVERAGE, WSOP_MXF
    show_num: int | None
    ext: str
    size_bytes: int
    role: str = 'PRIMARY'
    group_id: str = ''


def extract_show_num(filename: str) -> int | None:
    """Extract show number from filename."""
    # ESPN pattern
    match = re.search(r'SHOW\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    # mxf pattern
    match = re.search(r'WSOP_2007_(\d+)\.mxf', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def get_extension(filename: str) -> str:
    """Get file extension."""
    return filename.split('.')[-1].lower()


def classify_file(filename: str) -> str:
    """Classify file into content type."""
    if filename.lower().endswith('.mxf'):
        return 'WSOP_MXF'
    return 'WSOP_COVERAGE'


def generate_group_id(elem: NasElement) -> str:
    """Generate group ID for PRIMARY/BACKUP assignment."""
    if elem.show_num:
        return f'WSOP_2007_S{elem.show_num:02d}'
    return f'WSOP_2007_OTHER_{elem.filename}'


# Extension priority: mov > mxf
EXT_PRIORITY = {'mov': 1, 'mxf': 2}


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
    if elem.content_type == 'WSOP_MXF':
        return f'WSOP_2007_MXF_S{elem.show_num:02d}' if elem.show_num else 'WSOP_2007_MXF'
    return f'WSOP_2007_S{elem.show_num:02d}' if elem.show_num else 'WSOP_2007_OTHER'


def generate_category(elem: NasElement) -> str:
    """Generate category name."""
    if elem.content_type == 'WSOP_MXF':
        return 'WSOP 2007 MXF Masters'
    return 'WSOP 2007 Coverage'


def generate_title(elem: NasElement) -> str:
    """Generate display title."""
    if elem.content_type == 'WSOP_MXF':
        title = f'2007 MXF Show {elem.show_num}' if elem.show_num else '2007 MXF'
    else:
        title = f'2007 Season 5 Show {elem.show_num}' if elem.show_num else '2007 Coverage'

    if elem.role == 'BACKUP':
        title += ' (Back up)'

    return title


def load_nas_files(db) -> list[NasElement]:
    """Load 2007 NAS files from database."""
    files = db.query(NasFile).filter(
        NasFile.year == 2007,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    elements = []
    for f in files:
        content_type = classify_file(f.filename)
        show_num = extract_show_num(f.filename)
        ext = get_extension(f.filename)

        elements.append(NasElement(
            file_id=f.id,
            full_path=f.full_path or '',
            filename=f.filename,
            content_type=content_type,
            show_num=show_num,
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
    sheet_name = '2007_Catalog'

    headers = [
        'No', 'Entry Key', 'Match Type', 'Role', 'Backup Type',
        'Category', 'Title', 'PokerGO Title',
        'Region', 'Event Type', 'Event #', 'Day', 'Part', 'RAW',
        'Size (GB)', 'Filename', 'Full Path'
    ]
    rows = [headers]

    def sort_key(x):
        type_order = {'WSOP_COVERAGE': 0, 'WSOP_MXF': 1}
        role_order = 0 if x.role == 'PRIMARY' else 1
        return (
            type_order.get(x.content_type, 9),
            x.show_num or 0,
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
            'LV', 'COVERAGE', '', '', '', '',
            f'{size_gb:.2f}', elem.filename, elem.full_path
        ])

    return write_sheet(sheets, sheet_name, rows)


def main():
    print('=' * 70)
    print('2007 NAS Matching (ESPN Season 5)')
    print('=' * 70)

    db = next(get_db())
    sheets = get_sheets_service()

    # Load files
    print('\n[Step 1] Loading 2007 files...')
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

    for ct in ['WSOP_COVERAGE', 'WSOP_MXF']:
        if ct in type_counts:
            c = type_counts[ct]
            print(f'  {ct}: P:{c["primary"]} B:{c["backup"]}')

    # Export
    print('\n[Step 3] Exporting to Google Sheets...')
    rows_written = export_to_sheet(sheets, elements)
    print(f'  2007_Catalog: {rows_written} rows')

    # Summary
    total_primary = sum(1 for e in elements if e.role == 'PRIMARY')
    total_backup = sum(1 for e in elements if e.role == 'BACKUP')
    total_size = sum(e.size_bytes for e in elements) / (1024**3)

    print('\n' + '=' * 70)
    print('[OK] 2007 Matching completed!')
    print(f'  Files: {len(elements)} (PRIMARY: {total_primary}, BACKUP: {total_backup})')
    print(f'  Size: {total_size:.1f} GB')
    print('=' * 70)


if __name__ == '__main__':
    main()
