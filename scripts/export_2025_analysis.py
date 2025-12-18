"""Export 2025 analysis to Google Sheets (Path + Filename based)."""
import sys
import re
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.database import get_db
from src.nams.api.database.models import NasFile
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


def extract_region(full_path: str) -> str:
    """Extract region from path."""
    if not full_path:
        return 'OTHER'
    path_upper = full_path.upper()
    if 'WSOP-LAS VEGAS' in path_upper:
        return 'LV'
    elif 'WSOP-EUROPE' in path_upper:
        return 'EU'
    elif 'MPP CYPRUS' in path_upper:
        return 'CYPRUS_MPP'
    elif 'CIRCUIT' in path_upper:
        return 'CYPRUS_CIRCUIT'
    return 'OTHER'


def extract_event_type(full_path: str) -> str:
    """Extract event type from path."""
    if not full_path:
        return ''
    path_upper = full_path.upper()
    if 'MAIN EVENT' in path_upper:
        return 'ME'
    elif 'BRACELET' in path_upper or 'SIDE EVENT' in path_upper:
        return 'BR'
    elif 'WSOPE' in path_upper:
        return 'BR'
    return ''


def extract_event_num(text: str) -> int:
    """Extract Event # from text."""
    match = re.search(r'Event #?(\d+)', text, re.I)
    return int(match.group(1)) if match else None


def extract_day_part(text: str) -> dict:
    """Extract Day and Part info."""
    day_match = re.search(r'Day (\d+[A-D]?)', text, re.I)
    part_match = re.search(r'Part (\d+)', text, re.I)
    final_match = re.search(r'Final Table', text, re.I)
    table_match = re.search(r'Table ([BC]) Only', text, re.I)

    return {
        'day': day_match.group(1) if day_match else ('FT' if final_match else None),
        'part': int(part_match.group(1)) if part_match else None,
        'table': table_match.group(1) if table_match else None
    }


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


def export_nas_path_based(db, sheets):
    """Export NAS files with path-based analysis."""
    print('\n[1/3] NAS_2025_PathBased')

    files = db.query(NasFile).filter(NasFile.year == 2025).order_by(NasFile.full_path).all()
    print(f'  Total files: {len(files)}')

    headers = [
        'No', 'Region', 'Event Type', 'Event #', 'Day', 'Part',
        'Full Path', 'Filename', 'Size (GB)', 'Excluded', 'Exclusion Reason'
    ]
    rows = [headers]

    for idx, f in enumerate(files, 1):
        region = extract_region(f.full_path)
        event_type = extract_event_type(f.full_path)
        event_num = extract_event_num(f.full_path or '' + ' ' + f.filename)
        day_part = extract_day_part(f.full_path or '' + ' ' + f.filename)

        rows.append([
            idx,
            region,
            event_type,
            event_num or '',
            day_part['day'] or '',
            day_part['part'] or '',
            f.full_path or '',
            f.filename,
            format_size(f.size_bytes),
            'Yes' if f.is_excluded else '',
            f.exclusion_reason or ''
        ])

    write_sheet(sheets, 'NAS_2025_PathBased', rows)
    return files


def export_pokergo_title_based(sheets):
    """Export PokerGO data with title-based analysis."""
    print('\n[2/3] PokerGO_2025_TitleBased')

    with open('data/pokergo/wsop_final.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    entries_2025 = [v for v in data if '2025' in str(v.get('title', ''))]
    print(f'  Total entries: {len(entries_2025)}')

    headers = [
        'No', 'Event Type', 'Event #', 'Day', 'Part', 'Table',
        'Title', 'Collection', 'Season'
    ]
    rows = [headers]

    for idx, entry in enumerate(entries_2025, 1):
        title = entry.get('title', '')
        collection = entry.get('collection_title', '') or ''
        season = entry.get('season_title', '') or ''

        # Determine event type
        if 'Bracelet' in title:
            event_type = 'BR'
        elif 'Main Event' in title:
            event_type = 'ME'
        else:
            event_type = ''

        event_num = extract_event_num(title)
        day_part = extract_day_part(title)

        rows.append([
            idx,
            event_type,
            event_num or '',
            day_part['day'] or '',
            day_part['part'] or '',
            day_part['table'] or '',
            title,
            collection,
            season
        ])

    write_sheet(sheets, 'PokerGO_2025_TitleBased', rows)
    return entries_2025


def export_matching_analysis(db, sheets, nas_files, pokergo_entries):
    """Export matching analysis."""
    print('\n[3/3] Matching_2025_Analysis')

    # Classify NAS files
    nas_by_region = defaultdict(list)
    for f in nas_files:
        if not f.is_excluded:
            region = extract_region(f.full_path)
            nas_by_region[region].append(f)

    # Classify PokerGO
    pkg_bracelet = [e for e in pokergo_entries if 'Bracelet' in e.get('title', '')]
    pkg_main = [e for e in pokergo_entries if 'Main Event' in e.get('title', '')]

    # Extract Event numbers
    nas_lv_events = set()
    for f in nas_by_region['LV']:
        event_type = extract_event_type(f.full_path)
        if event_type == 'BR':
            event_num = extract_event_num(f.full_path or '' + ' ' + f.filename)
            if event_num:
                nas_lv_events.add(event_num)

    pkg_events = set()
    for e in pkg_bracelet:
        event_num = extract_event_num(e.get('title', ''))
        if event_num:
            pkg_events.add(event_num)

    matched_events = nas_lv_events & pkg_events
    nas_only_events = nas_lv_events - pkg_events
    pkg_only_events = pkg_events - nas_lv_events

    # Build analysis rows
    rows = [
        ['2025 MATCHING ANALYSIS', ''],
        ['Generated', '2025-12-18'],
        ['', ''],
        ['=== NAS FILES BY REGION ===', ''],
        ['Region', 'Files', 'Valid', 'Excluded'],
    ]

    for region in ['LV', 'EU', 'CYPRUS_MPP', 'CYPRUS_CIRCUIT', 'OTHER']:
        total = len([f for f in nas_files if extract_region(f.full_path) == region])
        valid = len([f for f in nas_files if extract_region(f.full_path) == region and not f.is_excluded])
        excluded = total - valid
        rows.append([region, total, valid, excluded])

    rows.extend([
        ['', ''],
        ['=== POKERGO DATA ===', ''],
        ['Type', 'Count'],
        ['Bracelet Events', len(pkg_bracelet)],
        ['Main Event', len(pkg_main)],
        ['', ''],
        ['=== BRACELET EVENT MATCHING ===', ''],
        ['', ''],
        ['NAS Events', str(sorted(nas_lv_events))],
        ['PokerGO Events', str(sorted(pkg_events))],
        ['Matched', len(matched_events)],
        ['NAS Only', len(nas_only_events), str(sorted(nas_only_events)) if nas_only_events else ''],
        ['PokerGO Only', len(pkg_only_events), str(sorted(pkg_only_events)) if pkg_only_events else ''],
        ['', ''],
        ['=== MAIN EVENT MATCHING ===', ''],
        ['NAS Files', len([f for f in nas_by_region['LV'] if extract_event_type(f.full_path) == 'ME'])],
        ['PokerGO Entries', len(pkg_main)],
        ['Table B/C Only (PKG)', len([e for e in pkg_main if 'Table' in e.get('title', '')])],
        ['', ''],
        ['=== NON-MATCHABLE (NAS ONLY) ===', ''],
        ['EU', len(nas_by_region['EU']), 'No PokerGO coverage'],
        ['CYPRUS_MPP', len(nas_by_region['CYPRUS_MPP']), 'No PokerGO coverage'],
        ['', ''],
        ['=== SUMMARY ===', ''],
        ['EXACT (LV)', f"{len(matched_events)} BR + {len([f for f in nas_by_region['LV'] if extract_event_type(f.full_path) == 'ME'])} ME"],
        ['POKERGO_ONLY', f"{len([e for e in pkg_main if 'Table' in e.get('title', '')])} (Table B/C Only)"],
        ['NAS_ONLY', f"{len(nas_by_region['EU'])} EU + {len(nas_by_region['CYPRUS_MPP'])} Cyprus"],
    ])

    write_sheet(sheets, 'Matching_2025_Analysis', rows)


def main():
    print('=' * 60)
    print('2025 Analysis Export (Path + Filename Based)')
    print('=' * 60)

    db = next(get_db())
    sheets = get_sheets_service()

    nas_files = export_nas_path_based(db, sheets)
    pokergo_entries = export_pokergo_title_based(sheets)
    export_matching_analysis(db, sheets, nas_files, pokergo_entries)

    print('\n' + '=' * 60)
    print('[OK] Export completed')
    print(f'URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit')
    print('=' * 60)


if __name__ == '__main__':
    main()
