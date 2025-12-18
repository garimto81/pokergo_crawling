"""Export all WSOP NAS files to Google Sheets with PokerGO matching status."""
import sys
import re
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.database import get_db, NasFile, AssetGroup, PokergoEpisode
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

GOOGLE_SHEETS_ID = '1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4'
CREDENTIALS_PATH = Path('D:/AI/claude01/json/service_account_key.json')


def extract_year(path: str) -> int:
    """Extract year from path."""
    match = re.search(r'(19|20)\d{2}', path)
    return int(match.group()) if match else None


def extract_from_group_id(group_id: str) -> tuple:
    """Extract year, region, event_type, episode from group_id.

    Examples:
        2011_ME_25 -> (2011, 'LV', 'ME', '25')
        2011_EU_01 -> (2011, 'EU', 'ME', '01')
        2013_APAC-ME_01 -> (2013, 'APAC', 'ME', '01')
        2024_PARADISE-ME_01 -> (2024, 'PARADISE', 'ME', '01')
        2003_BEST -> (2003, 'LV', 'BEST', '')
    """
    if not group_id:
        return None, '', '', ''

    parts = group_id.split('_')
    year = int(parts[0]) if parts[0].isdigit() else None

    region = 'LV'
    event_type = ''
    episode = ''

    if len(parts) >= 2:
        second = parts[1]
        # Check for region prefix
        if 'EU' in second:
            region = 'EU'
            event_type = 'ME'  # EU is Main Event by default
        elif 'APAC' in second:
            region = 'APAC'
            if '-' in second:
                event_type = second.split('-')[1]
        elif 'PARADISE' in second:
            region = 'PARADISE'
            if '-' in second:
                event_type = second.split('-')[1]
        else:
            event_type = second

    if len(parts) >= 3:
        episode = parts[2]

    return year, region, event_type, episode


def extract_region_fallback(path: str) -> str:
    """Extract region from path (fallback)."""
    path_lower = path.lower()
    if 'wsope' in path_lower or 'wsop-europe' in path_lower or 'wsop europe' in path_lower:
        return 'EU'
    if 'apac' in path_lower:
        return 'APAC'
    if 'paradise' in path_lower:
        return 'PARADISE'
    return 'LV'


def extract_event_type_fallback(filename: str) -> str:
    """Extract event type from filename (fallback)."""
    fname_lower = filename.lower()

    if '_me' in fname_lower or '-me' in fname_lower or 'main event' in fname_lower:
        return 'ME'
    if '_gm' in fname_lower or 'grudge' in fname_lower:
        return 'GM'
    if '_hu' in fname_lower or 'heads' in fname_lower:
        return 'HU'
    if '_ppc' in fname_lower or 'ppc' in fname_lower:
        return 'PPC'
    if 'high roller' in fname_lower or 'highroller' in fname_lower or '_hr' in fname_lower:
        return 'HR'
    if 'bracelet' in fname_lower or '_br' in fname_lower:
        return 'BR'
    if 'best of' in fname_lower or 'best_of' in fname_lower:
        return 'BEST'
    if 'final table' in fname_lower or '_ft' in fname_lower:
        return 'FT'
    return ''


def extract_episode_fallback(filename: str) -> str:
    """Extract episode number from filename (fallback)."""
    # WS11_ME01 -> 01
    match = re.search(r'[_-]ME(\d+)', filename, re.I)
    if match:
        return match.group(1)

    # Episode_1 -> 1
    match = re.search(r'Episode[_\s]*(\d+)', filename, re.I)
    if match:
        return match.group(1)

    # Show 01 -> 01
    match = re.search(r'Show\s*(\d+)', filename, re.I)
    if match:
        return match.group(1)

    return ''


def format_size(bytes_size: int) -> str:
    """Format bytes to GB."""
    if not bytes_size:
        return ""
    gb = bytes_size / (1024**3)
    return f"{gb:.1f}"


def is_origin_path(path: str) -> bool:
    """Check if path is Origin (Y: drive)."""
    if not path:
        return False
    path_upper = path.upper()
    if 'ARCHIVE' in path_upper:
        return False
    return path_upper.startswith('Y:') or 'ORIGIN' in path_upper


def main():
    db = next(get_db())

    # Get all WSOP NAS files
    all_files = db.query(NasFile).filter(
        NasFile.full_path.ilike('%wsop%') |
        NasFile.full_path.ilike('%ws0%') |
        NasFile.full_path.ilike('%ws1%') |
        NasFile.full_path.ilike('%ws2%')
    ).order_by(NasFile.full_path).all()

    print(f'Total WSOP NAS files: {len(all_files)}')

    # Build file -> pokergo mapping
    file_to_pokergo = {}
    file_to_group = {}
    for f in all_files:
        if f.asset_group_id:
            group = db.query(AssetGroup).filter(AssetGroup.id == f.asset_group_id).first()
            if group:
                file_to_group[f.id] = group.group_id
                if group.pokergo_episode_id:
                    ep = db.query(PokergoEpisode).filter(PokergoEpisode.id == group.pokergo_episode_id).first()
                    if ep:
                        file_to_pokergo[f.id] = ep.title

    # Build filename -> locations mapping for Origin/Archive check
    filename_locations = defaultdict(lambda: {'origin': False, 'archive': False, 'origin_path': '', 'archive_path': ''})
    for f in all_files:
        fname = f.filename
        if is_origin_path(f.full_path):
            filename_locations[fname]['origin'] = True
            filename_locations[fname]['origin_path'] = f.full_path
        else:
            filename_locations[fname]['archive'] = True
            filename_locations[fname]['archive_path'] = f.full_path

    # Prepare sheet data
    headers = [
        'Year', 'Region', 'Event Type', 'Episode', 'Filename', 'Size (GB)',
        'Location', 'Origin Path', 'Archive Path', 'Storage Status',
        'Group ID', 'PokerGO Match', 'Match Status'
    ]
    rows = [headers]

    # Stats
    by_year = defaultdict(list)
    by_region = defaultdict(int)
    by_storage = defaultdict(int)
    matched_count = 0
    unmatched_count = 0
    grouped_count = 0

    for f in all_files:
        group_id = file_to_group.get(f.id, '')
        pokergo_match = file_to_pokergo.get(f.id, '')

        # Use AssetGroup info if available (document rules applied)
        if group_id:
            grouped_count += 1
            year, region, event_type, episode = extract_from_group_id(group_id)
            # Fallback for year if not in group_id
            if not year:
                year = extract_year(f.full_path)
        else:
            # Fallback: extract from filename/path
            year = extract_year(f.full_path)
            region = extract_region_fallback(f.full_path)
            event_type = extract_event_type_fallback(f.filename)
            episode = extract_episode_fallback(f.filename)

        size_gb = format_size(f.size_bytes)
        location = 'Origin' if is_origin_path(f.full_path) else 'Archive'

        if pokergo_match:
            match_status = 'MATCHED'
            matched_count += 1
        elif group_id:
            match_status = 'GROUPED'  # 패턴 매칭됨, PokerGO 없음
        else:
            match_status = 'UNCLASSIFIED'  # 패턴 매칭 안됨
            unmatched_count += 1

        by_year[year].append(f)
        by_region[region] += 1

        # Get Origin/Archive status for this filename (for stats)
        loc_info_stat = filename_locations[f.filename]
        if loc_info_stat['origin'] and loc_info_stat['archive']:
            by_storage['BOTH'] += 1
        elif loc_info_stat['origin']:
            by_storage['ORIGIN_ONLY'] += 1
        elif loc_info_stat['archive']:
            by_storage['ARCHIVE_ONLY'] += 1

        # Clean filename for display
        fname = f.filename.replace('\U0001f3c6', '[T]')  # Replace trophy emoji

        # Get Origin/Archive status for this filename
        loc_info = filename_locations[f.filename]
        origin_path = loc_info['origin_path'][:80] if loc_info['origin_path'] else ''
        archive_path = loc_info['archive_path'][:80] if loc_info['archive_path'] else ''

        # Storage status
        if loc_info['origin'] and loc_info['archive']:
            storage_status = 'BOTH'
        elif loc_info['origin']:
            storage_status = 'ORIGIN_ONLY'
        elif loc_info['archive']:
            storage_status = 'ARCHIVE_ONLY'  # Warning: Origin missing!
        else:
            storage_status = 'UNKNOWN'

        rows.append([
            year or '',
            region,
            event_type,
            episode,
            fname[:70],
            size_gb,
            location,
            origin_path,
            archive_path,
            storage_status,
            group_id,
            pokergo_match[:50] if pokergo_match else '',
            match_status
        ])

    print(f'Grouped (pattern matched): {grouped_count}')

    print(f'Matched: {matched_count}')
    print(f'Unmatched: {unmatched_count}')
    print(f'Rows prepared: {len(rows)}')

    # Year stats
    print('\n=== Year Stats ===')
    for year in sorted(by_year.keys(), key=lambda x: x or 0):
        files = by_year[year]
        total_gb = sum(f.size_bytes or 0 for f in files) / (1024**3)
        print(f'{year}: {len(files)} files, {total_gb:.1f}GB')

    # Region stats
    print('\n=== Region Stats ===')
    for region, count in sorted(by_region.items()):
        print(f'{region}: {count} files')

    # Storage stats
    print('\n=== Storage Stats ===')
    for status, count in sorted(by_storage.items()):
        warning = ' [WARNING: Origin missing!]' if status == 'ARCHIVE_ONLY' else ''
        print(f'{status}: {count} files{warning}')

    # Google Sheets Export
    creds = Credentials.from_service_account_file(
        str(CREDENTIALS_PATH),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)
    sheets = service.spreadsheets()

    sheet_name = 'NAS_WSOP_All'

    # Check if sheet exists
    spreadsheet = sheets.get(spreadsheetId=GOOGLE_SHEETS_ID).execute()
    existing_sheets = [s['properties']['title'] for s in spreadsheet['sheets']]

    if sheet_name not in existing_sheets:
        sheets.batchUpdate(
            spreadsheetId=GOOGLE_SHEETS_ID,
            body={'requests': [{'addSheet': {'properties': {'title': sheet_name}}}]}
        ).execute()
        print(f'\nCreated new sheet: {sheet_name}')

    # Clear and write
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

    print(f'\n[OK] Export complete: {result.get("updatedRows", 0)} rows')
    print(f'URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit')


if __name__ == '__main__':
    main()
