"""Export WSOP Europe files from NAS to Google Sheets."""
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


def extract_episode(filename: str) -> str:
    """Extract episode number from filename."""
    # WSOPE08_Episode_1 -> 1
    match = re.search(r'Episode[_\s]*(\d+)', filename, re.I)
    if match:
        return match.group(1)

    # WE24-ME-01 -> 01
    match = re.search(r'ME[_-](\d+)', filename, re.I)
    if match:
        return match.group(1)

    # wsope-2021-10k-me-ft-004 -> 004
    match = re.search(r'-(\d{3,})\.', filename)
    if match:
        return match.group(1)

    # Part1, Part2 etc
    match = re.search(r'Part\s*(\d+)', filename, re.I)
    if match:
        return f"P{match.group(1)}"

    # Day 1A, Day 2
    match = re.search(r'Day\s*(\d+[A-D]?)', filename, re.I)
    if match:
        return f"D{match.group(1)}"

    return ""


def extract_event_type(filename: str) -> str:
    """Extract event type from filename."""
    fname_lower = filename.lower()

    if 'main event' in fname_lower or '_me' in fname_lower or '-me-' in fname_lower:
        return 'ME'
    if 'high roller' in fname_lower or 'highroller' in fname_lower:
        return 'HR'
    if 'colossus' in fname_lower:
        return 'COL'
    if 'mystery bounty' in fname_lower:
        return 'MB'
    if 'plo' in fname_lower or 'omaha' in fname_lower:
        return 'PLO'
    if 'monsterstack' in fname_lower:
        return 'MS'
    if 'ggmillion' in fname_lower:
        return 'GGM'
    if 'king' in fname_lower and 'million' in fname_lower:
        return 'KM'
    if 'mini main' in fname_lower:
        return 'MME'
    if 'nlh' in fname_lower or '6max' in fname_lower or '6-max' in fname_lower:
        return 'NLH'
    if 'hyperdeck' in fname_lower:
        return 'RAW'

    return 'EU'  # Default Europe


def format_size(bytes_size: int) -> str:
    """Format bytes to human readable."""
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


def is_archive_path(path: str) -> bool:
    """Check if path is Archive (Z: drive)."""
    if not path:
        return False
    path_upper = path.upper()
    return path_upper.startswith('Z:') or 'ARCHIVE' in path_upper


def main():
    db = next(get_db())

    # Get WSOP Europe files
    eu_files = db.query(NasFile).filter(
        NasFile.full_path.ilike('%wsope%') |
        NasFile.full_path.ilike('%wsop-europe%') |
        NasFile.full_path.ilike('%wsop europe%')
    ).order_by(NasFile.full_path).all()

    print(f'WSOP Europe files: {len(eu_files)}')

    # Check PokerGO WSOP Europe episodes
    pokergo_eu = db.query(PokergoEpisode).filter(
        PokergoEpisode.title.ilike('%wsope%') |
        PokergoEpisode.title.ilike('%wsop europe%') |
        PokergoEpisode.collection_title.ilike('%europe%') |
        PokergoEpisode.season_title.ilike('%europe%')
    ).all()

    print(f'PokerGO Europe episodes: {len(pokergo_eu)}')

    # Build file -> group -> pokergo mapping
    file_to_pokergo = {}
    for f in eu_files:
        if f.asset_group_id:
            group = db.query(AssetGroup).filter(AssetGroup.id == f.asset_group_id).first()
            if group and group.pokergo_episode_id:
                ep = db.query(PokergoEpisode).filter(PokergoEpisode.id == group.pokergo_episode_id).first()
                if ep:
                    file_to_pokergo[f.id] = ep.title

    # Prepare sheet data
    headers = [
        'Year', 'Event Type', 'Episode', 'Filename', 'Size (GB)',
        'Location', 'Full Path', 'PokerGO Match', 'Notes'
    ]
    rows = [headers]

    # Group by year for stats
    by_year = defaultdict(list)
    matched_count = 0

    for f in eu_files:
        year = extract_year(f.full_path)
        episode = extract_episode(f.filename)
        event_type = extract_event_type(f.filename)
        size_gb = format_size(f.size_bytes)

        # Determine location
        if is_origin_path(f.full_path):
            location = 'Origin'
        elif is_archive_path(f.full_path):
            location = 'Archive'
        else:
            location = 'Unknown'

        # PokerGO match status
        pokergo_match = file_to_pokergo.get(f.id, '')
        if pokergo_match:
            matched_count += 1

        # Notes
        notes = ""
        if 'hyperdeck' in f.filename.lower():
            notes = "Raw recording"
        elif f.size_bytes and f.size_bytes < 1024**3:
            notes = "< 1GB (clip?)"

        by_year[year].append(f)

        rows.append([
            year or '',
            event_type,
            episode,
            f.filename[:80],
            size_gb,
            location,
            f.full_path[:100] if f.full_path else '',
            pokergo_match[:60] if pokergo_match else 'NO POKERGO',
            notes
        ])

    print(f'Matched to PokerGO: {matched_count}')

    print(f'Rows prepared: {len(rows)}')

    # Print year stats
    print('\n=== Year Stats ===')
    for year in sorted(by_year.keys()):
        files = by_year[year]
        total_gb = sum(f.size_bytes or 0 for f in files) / (1024**3)
        print(f'{year}: {len(files)} files, {total_gb:.1f}GB')

    # Google Sheets Export
    creds = Credentials.from_service_account_file(
        str(CREDENTIALS_PATH),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)
    sheets = service.spreadsheets()

    sheet_name = 'NAS_WSOP_Europe'

    # Check if sheet exists
    spreadsheet = sheets.get(spreadsheetId=GOOGLE_SHEETS_ID).execute()
    existing_sheets = [s['properties']['title'] for s in spreadsheet['sheets']]

    if sheet_name not in existing_sheets:
        sheets.batchUpdate(
            spreadsheetId=GOOGLE_SHEETS_ID,
            body={'requests': [{'addSheet': {'properties': {'title': sheet_name}}}]}
        ).execute()
        print(f'Created new sheet: {sheet_name}')

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
