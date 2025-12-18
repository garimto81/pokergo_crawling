"""Master Catalog Integration Script.

Combines all year catalogs into:
1. Master_Catalog - All files from 1973-2025
2. Summary - Statistics by year/era/type
"""
import sys
import io
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

GOOGLE_SHEETS_ID = '1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4'
CREDENTIALS_PATH = Path('D:/AI/claude01/json/service_account_key.json')

# Era definitions
ERAS = {
    'CLASSIC': list(range(1973, 2003)),  # 1973-2002
    'BOOM': list(range(2003, 2011)),      # 2003-2010
    'HD': list(range(2011, 2026)),        # 2011-2025
}

# Sheet name patterns
YEAR_SHEETS = {
    'classic': '1973-2002_Catalog',
    'years': [f'{y}_Catalog' for y in range(2003, 2026)]
}


def get_sheets_service():
    creds = Credentials.from_service_account_file(
        str(CREDENTIALS_PATH),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)
    return service.spreadsheets()


def get_era(year: int) -> str:
    """Get era name for a year."""
    if year <= 2002:
        return 'CLASSIC'
    elif year <= 2010:
        return 'BOOM'
    return 'HD'


def read_sheet(sheets, sheet_name: str) -> list:
    """Read all data from a sheet."""
    try:
        result = sheets.values().get(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=f'{sheet_name}!A:Z'
        ).execute()
        return result.get('values', [])
    except Exception as e:
        print(f'  Warning: Could not read {sheet_name}: {e}')
        return []


def ensure_sheet_exists(sheets, sheet_name: str):
    """Create sheet if it doesn't exist."""
    spreadsheet = sheets.get(spreadsheetId=GOOGLE_SHEETS_ID).execute()
    existing_sheets = [s['properties']['title'] for s in spreadsheet['sheets']]
    if sheet_name not in existing_sheets:
        sheets.batchUpdate(
            spreadsheetId=GOOGLE_SHEETS_ID,
            body={'requests': [{'addSheet': {'properties': {'title': sheet_name}}}]}
        ).execute()
        print(f'  Created new sheet: {sheet_name}')


def write_sheet(sheets, sheet_name: str, rows: list):
    """Write data to a sheet."""
    ensure_sheet_exists(sheets, sheet_name)
    sheets.values().clear(spreadsheetId=GOOGLE_SHEETS_ID, range=f'{sheet_name}!A:Z').execute()
    result = sheets.values().update(
        spreadsheetId=GOOGLE_SHEETS_ID,
        range=f'{sheet_name}!A1',
        valueInputOption='RAW',
        body={'values': rows}
    ).execute()
    return result.get('updatedRows', 0)


def extract_year_from_entry_key(entry_key: str) -> int:
    """Extract year from entry key like WSOP_2015_ME_EP01."""
    import re
    match = re.search(r'(\d{4})', entry_key)
    if match:
        return int(match.group(1))
    return 0


def load_all_catalogs(sheets) -> tuple[list, dict]:
    """Load all catalog data from all sheets."""
    all_rows = []
    stats = defaultdict(lambda: {
        'files': 0, 'primary': 0, 'backup': 0, 'size_gb': 0.0,
        'types': defaultdict(int)
    })

    print('\n[Step 1] Loading all catalog sheets...')

    # Load Classic Era (combined sheet)
    classic_data = read_sheet(sheets, YEAR_SHEETS['classic'])
    if classic_data and len(classic_data) > 1:
        headers = classic_data[0]
        for row in classic_data[1:]:
            if len(row) >= 15:
                all_rows.append(row)
                # Extract year from entry key
                entry_key = row[1] if len(row) > 1 else ''
                year = extract_year_from_entry_key(entry_key)
                if year:
                    role = row[3] if len(row) > 3 else ''
                    size_str = row[14] if len(row) > 14 else '0'
                    try:
                        size = float(size_str)
                    except:
                        size = 0.0

                    stats[year]['files'] += 1
                    stats[year]['size_gb'] += size
                    if role == 'PRIMARY':
                        stats[year]['primary'] += 1
                    else:
                        stats[year]['backup'] += 1

        print(f'  1973-2002_Catalog: {len(classic_data)-1} rows')

    # Load individual year sheets (2003-2025)
    for sheet_name in YEAR_SHEETS['years']:
        data = read_sheet(sheets, sheet_name)
        if data and len(data) > 1:
            year = int(sheet_name.split('_')[0])
            for row in data[1:]:
                if len(row) >= 15:
                    all_rows.append(row)

                    role = row[3] if len(row) > 3 else ''
                    category = row[5] if len(row) > 5 else ''
                    size_str = row[14] if len(row) > 14 else '0'
                    try:
                        size = float(size_str)
                    except:
                        size = 0.0

                    stats[year]['files'] += 1
                    stats[year]['size_gb'] += size
                    if role == 'PRIMARY':
                        stats[year]['primary'] += 1
                    else:
                        stats[year]['backup'] += 1

                    # Extract type from category
                    if 'Main Event' in category:
                        stats[year]['types']['ME'] += 1
                    elif 'Europe' in category:
                        stats[year]['types']['EU'] += 1
                    elif 'APAC' in category:
                        stats[year]['types']['APAC'] += 1
                    elif 'Bracelet' in category:
                        stats[year]['types']['BR'] += 1
                    elif 'MXF' in category:
                        stats[year]['types']['MXF'] += 1
                    else:
                        stats[year]['types']['OTHER'] += 1

            print(f'  {sheet_name}: {len(data)-1} rows')

    return all_rows, stats


def create_master_catalog(sheets, all_rows: list) -> int:
    """Create the Master_Catalog sheet with all data."""
    print('\n[Step 2] Creating Master_Catalog...')

    headers = [
        'No', 'Entry Key', 'Match Type', 'Role', 'Backup Type',
        'Category', 'Title', 'PokerGO Title',
        'Region', 'Event Type', 'Event #', 'Day', 'Part', 'RAW',
        'Size (GB)', 'Filename', 'Full Path'
    ]

    # Re-number rows
    rows = [headers]
    for idx, row in enumerate(all_rows, 1):
        new_row = [idx] + list(row[1:]) if len(row) > 1 else [idx]
        # Ensure row has enough columns
        while len(new_row) < len(headers):
            new_row.append('')
        rows.append(new_row[:len(headers)])

    written = write_sheet(sheets, 'Master_Catalog', rows)
    print(f'  Master_Catalog: {written} rows written')
    return written


def create_summary_sheet(sheets, stats: dict) -> int:
    """Create the Summary sheet with statistics."""
    print('\n[Step 3] Creating Summary sheet...')

    rows = []

    # Header section
    rows.append(['WSOP NAS Catalog Summary'])
    rows.append(['Generated by NAMS (NAS Asset Management System)'])
    rows.append([])

    # Era summary
    rows.append(['Era Summary'])
    rows.append(['Era', 'Years', 'Files', 'PRIMARY', 'BACKUP', 'Size (GB)', 'Size (TB)'])

    for era_name, years in ERAS.items():
        era_files = sum(stats[y]['files'] for y in years if y in stats)
        era_primary = sum(stats[y]['primary'] for y in years if y in stats)
        era_backup = sum(stats[y]['backup'] for y in years if y in stats)
        era_size = sum(stats[y]['size_gb'] for y in years if y in stats)

        year_range = f'{years[0]}-{years[-1]}'
        rows.append([
            era_name, year_range, era_files, era_primary, era_backup,
            f'{era_size:.1f}', f'{era_size/1024:.2f}'
        ])

    # Total
    total_files = sum(s['files'] for s in stats.values())
    total_primary = sum(s['primary'] for s in stats.values())
    total_backup = sum(s['backup'] for s in stats.values())
    total_size = sum(s['size_gb'] for s in stats.values())
    rows.append([
        'TOTAL', '1973-2025', total_files, total_primary, total_backup,
        f'{total_size:.1f}', f'{total_size/1024:.2f}'
    ])

    rows.append([])
    rows.append([])

    # Year-by-year detail
    rows.append(['Year-by-Year Detail'])
    rows.append(['Year', 'Era', 'Files', 'PRIMARY', 'BACKUP', 'Size (GB)', 'P/B Ratio'])

    for year in sorted(stats.keys()):
        s = stats[year]
        era = get_era(year)
        ratio = f'{s["primary"]}/{s["backup"]}' if s['backup'] > 0 else f'{s["primary"]}/0'
        rows.append([
            year, era, s['files'], s['primary'], s['backup'],
            f'{s["size_gb"]:.1f}', ratio
        ])

    rows.append([])
    rows.append([])

    # Role breakdown
    rows.append(['Role Breakdown'])
    rows.append(['Role', 'Count', 'Percentage'])
    rows.append(['PRIMARY', total_primary, f'{total_primary/total_files*100:.1f}%'])
    rows.append(['BACKUP', total_backup, f'{total_backup/total_files*100:.1f}%'])

    written = write_sheet(sheets, 'Summary', rows)
    print(f'  Summary: {written} rows written')
    return written


def main():
    print('=' * 70)
    print('Master Catalog Integration')
    print('=' * 70)

    sheets = get_sheets_service()

    # Load all data
    all_rows, stats = load_all_catalogs(sheets)

    if not all_rows:
        print('\nNo data found in catalog sheets!')
        return

    # Create Master Catalog
    master_rows = create_master_catalog(sheets, all_rows)

    # Create Summary
    summary_rows = create_summary_sheet(sheets, stats)

    # Final summary
    total_files = sum(s['files'] for s in stats.values())
    total_primary = sum(s['primary'] for s in stats.values())
    total_backup = sum(s['backup'] for s in stats.values())
    total_size = sum(s['size_gb'] for s in stats.values())

    print('\n' + '=' * 70)
    print('[OK] Master Catalog Integration completed!')
    print(f'  Years: {len(stats)} (1973-2025)')
    print(f'  Total files: {total_files} (PRIMARY: {total_primary}, BACKUP: {total_backup})')
    print(f'  Total size: {total_size:.1f} GB ({total_size/1024:.2f} TB)')
    print('=' * 70)


if __name__ == '__main__':
    main()
