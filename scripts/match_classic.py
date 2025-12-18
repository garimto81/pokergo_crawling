"""CLASSIC Era NAS Matching Script (1973-2002).

Matches and exports CLASSIC era NAS files.
Simple Main Event only - no Bracelet Events in this era.

Primary/Backup Grouping Rules:
- 'nobug' in filename → BACKUP
- 'VHS DUB' in filename → BACKUP
- Same year without Part → Group by size (largest = PRIMARY)
- 'Part X' in filename → Separate episode
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

CLASSIC_YEARS = list(range(1973, 2003))  # 1973-2002


@dataclass
class NasElement:
    file_id: int
    full_path: str
    filename: str
    year: int
    content_type: str  # WSOP_ME
    region: str
    event_type: str
    part_num: int | None
    size_bytes: int
    role: str = 'PRIMARY'
    group_id: str = ''


def is_backup_file(filename: str) -> bool:
    """Check if file is a backup based on filename patterns."""
    fn_lower = filename.lower()
    # nobug files are backups
    if 'nobug' in fn_lower:
        return True
    # VHS DUB is a backup
    if 'vhs dub' in fn_lower:
        return True
    return False


def extract_part_num(filename: str) -> int | None:
    """Extract part number from filename (Part 1, Part 2, _1, _2)."""
    # "Part 1", "Part 2"
    match = re.search(r'Part\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    # "WSOP_2002_1.mxf", "WSOP_2002_2.mxf"
    match = re.search(r'WSOP_\d{4}_(\d+)\.', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def generate_entry_key(elem: NasElement) -> str:
    key = f'WSOP_{elem.year}_ME'
    if elem.part_num:
        key += f'_P{elem.part_num}'
    return key


def generate_category(elem: NasElement) -> str:
    return f'WSOP {elem.year} Main Event'


def generate_title(elem: NasElement) -> str:
    title = f'{elem.year} Main Event'
    if elem.part_num:
        title += f' Part {elem.part_num}'
    if elem.role == 'BACKUP':
        title += ' (Back up)'
    return title


def assign_roles(elements: list[NasElement]) -> list[NasElement]:
    """Assign PRIMARY/BACKUP roles within groups."""
    # Group by part_num (None = single episode year)
    groups = defaultdict(list)
    for elem in elements:
        group_key = elem.part_num if elem.part_num else 0
        groups[group_key].append(elem)

    result = []
    for group_key, group_elements in groups.items():
        # Sort by size descending
        group_elements.sort(key=lambda x: x.size_bytes, reverse=True)

        # If only one file in group, it's PRIMARY regardless of filename
        if len(group_elements) == 1:
            group_elements[0].role = 'PRIMARY'
            group_elements[0].group_id = f'WSOP_{group_elements[0].year}_ME' + (f'_P{group_key}' if group_key else '')
            result.append(group_elements[0])
            continue

        # Find primary (largest non-backup file)
        primary_found = False
        for elem in group_elements:
            if is_backup_file(elem.filename):
                elem.role = 'BACKUP'
            elif not primary_found:
                elem.role = 'PRIMARY'
                primary_found = True
            else:
                elem.role = 'BACKUP'

            elem.group_id = f'WSOP_{elem.year}_ME' + (f'_P{group_key}' if group_key else '')
            result.append(elem)

        # If no primary found (all files are backup-type), assign largest as PRIMARY
        if not primary_found:
            group_elements[0].role = 'PRIMARY'

    return result


def load_nas_files(db, year: int) -> list[NasElement]:
    files = db.query(NasFile).filter(
        NasFile.year == year,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    elements = []
    for f in files:
        part_num = extract_part_num(f.filename)
        elements.append(NasElement(
            file_id=f.id,
            full_path=f.full_path or '',
            filename=f.filename,
            year=year,
            content_type='WSOP_ME',
            region='LV',
            event_type='ME',
            part_num=part_num,
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


def delete_sheet_if_exists(sheets, sheet_name: str):
    """Delete a sheet if it exists."""
    try:
        spreadsheet = sheets.get(spreadsheetId=GOOGLE_SHEETS_ID).execute()
        for sheet in spreadsheet['sheets']:
            if sheet['properties']['title'] == sheet_name:
                sheet_id = sheet['properties']['sheetId']
                sheets.batchUpdate(
                    spreadsheetId=GOOGLE_SHEETS_ID,
                    body={'requests': [{'deleteSheet': {'sheetId': sheet_id}}]}
                ).execute()
                return True
    except Exception:
        pass
    return False


def export_consolidated_sheet(sheets, all_elements: list[NasElement]) -> int:
    """Export all CLASSIC era files to a single consolidated sheet."""
    sheet_name = '1973-2002_Catalog'

    headers = [
        'No', 'Entry Key', 'Match Type', 'Role', 'Backup Type',
        'Category', 'Title', 'PokerGO Title',
        'Region', 'Event Type', 'Event #', 'Day', 'Part', 'RAW',
        'Size (GB)', 'Filename', 'Full Path'
    ]
    rows = [headers]

    # Sort: by year, then PRIMARY first, then by part_num, then by size
    def sort_key(x):
        role_order = 0 if x.role == 'PRIMARY' else 1
        return (x.year, x.part_num or 0, role_order, -x.size_bytes)

    for idx, elem in enumerate(sorted(all_elements, key=sort_key), 1):
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
    print('CLASSIC Era NAS Matching (1973-2002)')
    print('=' * 70)

    db = next(get_db())
    sheets = get_sheets_service()

    # Step 1: Delete existing individual year sheets
    print('\n[Step 1] Deleting individual year sheets...')
    deleted_count = 0
    for year in CLASSIC_YEARS:
        sheet_name = f'{year}_Catalog'
        if delete_sheet_if_exists(sheets, sheet_name):
            print(f'  Deleted: {sheet_name}')
            deleted_count += 1
    print(f'  Deleted {deleted_count} sheets')

    # Step 2: Load all files
    print('\n[Step 2] Loading files...')
    all_elements = []
    total_primary = 0
    total_backup = 0
    years_with_data = []

    for year in CLASSIC_YEARS:
        elements = load_nas_files(db, year)
        if not elements:
            continue

        years_with_data.append(year)
        primary_count = sum(1 for e in elements if e.role == 'PRIMARY')
        backup_count = sum(1 for e in elements if e.role == 'BACKUP')
        total_primary += primary_count
        total_backup += backup_count
        all_elements.extend(elements)

        role_info = f'P:{primary_count} B:{backup_count}' if backup_count > 0 else f'P:{primary_count}'
        print(f'  {year}: {len(elements)} files [{role_info}]')

    # Step 3: Export consolidated sheet
    print('\n[Step 3] Exporting consolidated sheet...')
    rows_written = export_consolidated_sheet(sheets, all_elements)
    print(f'  1973-2002_Catalog: {rows_written} rows')

    total_size = sum(e.size_bytes for e in all_elements)
    print('\n' + '=' * 70)
    print(f'[OK] CLASSIC Era completed!')
    print(f'  Years: {len(years_with_data)} ({min(years_with_data)}-{max(years_with_data)})')
    print(f'  Total files: {len(all_elements)} (PRIMARY: {total_primary}, BACKUP: {total_backup})')
    print(f'  Total size: {total_size/(1024**3):.1f} GB')
    print(f'  Output: 1973-2002_Catalog (single sheet)')
    print('=' * 70)


if __name__ == '__main__':
    main()
