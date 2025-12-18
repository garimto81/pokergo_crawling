"""Export 2025 WSOP data to Google Sheets."""
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.database import get_db
from src.nams.api.database.models import CategoryEntry, NasFile
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

GOOGLE_SHEETS_ID = '1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4'
CREDENTIALS_PATH = Path('D:/AI/claude01/json/service_account_key.json')


def format_size(bytes_size: int) -> str:
    """Format bytes to GB."""
    if not bytes_size:
        return ""
    gb = bytes_size / (1024**3)
    return f"{gb:.1f}"


def get_sheets_service():
    """Get Google Sheets service."""
    creds = Credentials.from_service_account_file(
        str(CREDENTIALS_PATH),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)
    return service.spreadsheets()


def ensure_sheet_exists(sheets, sheet_name: str):
    """Ensure sheet exists, create if not."""
    spreadsheet = sheets.get(spreadsheetId=GOOGLE_SHEETS_ID).execute()
    existing_sheets = [s['properties']['title'] for s in spreadsheet['sheets']]

    if sheet_name not in existing_sheets:
        sheets.batchUpdate(
            spreadsheetId=GOOGLE_SHEETS_ID,
            body={'requests': [{'addSheet': {'properties': {'title': sheet_name}}}]}
        ).execute()
        print(f'  Created new sheet: {sheet_name}')


def write_sheet(sheets, sheet_name: str, rows: list):
    """Clear and write data to sheet."""
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


def export_entries(db, sheets):
    """Export Sheet 1: WSOP_2025_Entries."""
    print('\n[1/3] WSOP_2025_Entries')

    entries = db.query(CategoryEntry).filter(
        CategoryEntry.year == 2025
    ).order_by(CategoryEntry.entry_code).all()

    print(f'  Total entries: {len(entries)}')

    # Count files per entry
    file_counts = {}
    for entry in entries:
        count = db.query(NasFile).filter(
            NasFile.entry_id == entry.id,
            NasFile.is_excluded == False
        ).count()
        file_counts[entry.id] = count

    headers = [
        'No', 'Entry Code', 'Match Type', 'Event Type',
        'PokerGO Title', 'File Count', 'Display Title', 'Notes'
    ]
    rows = [headers]

    for idx, entry in enumerate(entries, 1):
        rows.append([
            idx,
            entry.entry_code,
            entry.match_type or '',
            entry.event_type or '',
            entry.pokergo_title or '',
            file_counts.get(entry.id, 0),
            entry.display_title or '',
            entry.notes or ''
        ])

    write_sheet(sheets, 'WSOP_2025_Entries', rows)
    return entries


def export_files(db, sheets):
    """Export Sheet 2: WSOP_2025_Files."""
    print('\n[2/3] WSOP_2025_Files')

    files = db.query(NasFile).filter(
        NasFile.year == 2025
    ).order_by(NasFile.folder, NasFile.filename).all()

    print(f'  Total files: {len(files)}')

    # Get entry codes
    entry_map = {}
    entries = db.query(CategoryEntry).filter(CategoryEntry.year == 2025).all()
    for entry in entries:
        entry_map[entry.id] = entry.entry_code

    headers = [
        'No', 'Filename', 'Folder', 'Drive', 'Size (GB)',
        'Entry Code', 'Match Type', 'Excluded', 'Exclusion Reason'
    ]
    rows = [headers]

    for idx, f in enumerate(files, 1):
        entry_code = entry_map.get(f.entry_id, '') if f.entry_id else ''

        # Get match type from entry
        match_type = ''
        if f.entry_id:
            entry = db.query(CategoryEntry).filter(CategoryEntry.id == f.entry_id).first()
            if entry:
                match_type = entry.match_type or ''

        rows.append([
            idx,
            f.filename,
            f.folder or '',
            f.drive or '',
            format_size(f.size_bytes),
            entry_code,
            match_type,
            'Yes' if f.is_excluded else '',
            f.exclusion_reason or ''
        ])

    write_sheet(sheets, 'WSOP_2025_Files', rows)
    return files


def export_summary(db, sheets, entries, files):
    """Export Sheet 3: WSOP_2025_Summary."""
    print('\n[3/3] WSOP_2025_Summary')

    # Calculate statistics
    match_type_counts = defaultdict(int)
    event_type_counts = defaultdict(int)
    for entry in entries:
        match_type_counts[entry.match_type or 'UNKNOWN'] += 1
        event_type_counts[entry.event_type or 'OTHER'] += 1

    file_stats = {
        'total': len(files),
        'connected': len([f for f in files if f.entry_id and not f.is_excluded]),
        'excluded': len([f for f in files if f.is_excluded]),
        'unmatched': len([f for f in files if not f.entry_id and not f.is_excluded]),
    }

    folder_counts = defaultdict(int)
    folder_sizes = defaultdict(int)
    for f in files:
        if not f.is_excluded:
            folder_counts[f.folder or 'unknown'] += 1
            folder_sizes[f.folder or 'unknown'] += f.size_bytes or 0

    rows = [
        ['WSOP 2025 Data Summary', ''],
        ['Generated', '2025-12-18'],
        ['', ''],
        ['=== ENTRY STATISTICS ===', ''],
        ['Total Entries', len(entries)],
        ['', ''],
        ['Match Type', 'Count'],
    ]

    for mt, count in sorted(match_type_counts.items()):
        rows.append([mt, count])

    rows.extend([
        ['', ''],
        ['Event Type', 'Count'],
    ])

    for et, count in sorted(event_type_counts.items()):
        rows.append([et, count])

    rows.extend([
        ['', ''],
        ['=== FILE STATISTICS ===', ''],
        ['Total Files', file_stats['total']],
        ['Connected', file_stats['connected']],
        ['Excluded', file_stats['excluded']],
        ['Unmatched', file_stats['unmatched']],
        ['', ''],
        ['Folder', 'Files', 'Size (GB)'],
    ])

    for folder in sorted(folder_counts.keys()):
        rows.append([folder, folder_counts[folder], format_size(folder_sizes[folder])])

    rows.extend([
        ['', ''],
        ['=== NOTES ===', ''],
        ['EXACT', 'NAS + PokerGO matched'],
        ['NONE', 'NAS Only (no PokerGO)'],
        ['POKERGO_ONLY', 'PokerGO Only (need NAS)'],
    ])

    write_sheet(sheets, 'WSOP_2025_Summary', rows)


def main():
    print('=' * 60)
    print('WSOP 2025 Data Export to Google Sheets')
    print('=' * 60)

    db = next(get_db())
    sheets = get_sheets_service()

    entries = export_entries(db, sheets)
    files = export_files(db, sheets)
    export_summary(db, sheets, entries, files)

    print('\n' + '=' * 60)
    print('[OK] Export completed successfully')
    print(f'URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit')
    print('=' * 60)


if __name__ == '__main__':
    main()
