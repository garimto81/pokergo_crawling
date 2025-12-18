"""Export WSOP episodes with NAS Origin/Archive matching to Google Sheets."""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.database import get_db, PokergoEpisode, AssetGroup, NasFile, Region, EventType
from src.nams.api.services.matching_v2 import is_actual_episode
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

GOOGLE_SHEETS_ID = '1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4'
CREDENTIALS_PATH = Path('D:/AI/claude01/json/service_account_key.json')


def extract_year(ep):
    """Extract year from episode."""
    for text in [ep.title, ep.collection_title, ep.season_title]:
        if text:
            match = re.search(r'\b(19|20)\d{2}\b', text)
            if match:
                return int(match.group())
    return None


def format_size(bytes_size: int) -> str:
    """Format bytes to human readable."""
    if not bytes_size:
        return ""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} PB"


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

    # Get lookup tables
    regions = {r.id: r.code for r in db.query(Region).all()}
    event_types = {e.id: e.code for e in db.query(EventType).all()}

    # Get all WSOP episodes (실제 에피소드만, 시즌 헤더 제외)
    all_wsop = db.query(PokergoEpisode).filter(
        PokergoEpisode.title.ilike('%WSOP%') |
        PokergoEpisode.collection_title.ilike('%WSOP%') |
        PokergoEpisode.season_title.ilike('%WSOP%')
    ).all()

    # Filter out collection/season headers
    wsop_episodes = [ep for ep in all_wsop if is_actual_episode(ep.title)]

    print(f'WSOP episodes (total): {len(all_wsop)}')
    print(f'WSOP episodes (actual): {len(wsop_episodes)}')
    print(f'Filtered headers: {len(all_wsop) - len(wsop_episodes)}')

    # Get all matched groups with PokerGO episode ID
    matched_groups = {
        g.pokergo_episode_id: g
        for g in db.query(AssetGroup).filter(AssetGroup.pokergo_episode_id.isnot(None)).all()
    }

    # Prepare sheet data
    headers = [
        'Year', 'Collection', 'Season', 'Title', 'Duration (min)',
        'Match Status', 'NAS Group ID', 'Region', 'Event Type', 'Episode',
        'Origin Path', 'Origin Filename', 'Origin Size',
        'Archive Path', 'Archive Filename', 'Archive Size',
        'Match Score', 'PokerGO ID'
    ]
    rows = [headers]

    matched_count = 0
    for ep in sorted(wsop_episodes, key=lambda x: (extract_year(x) or 9999, x.collection_title or '', x.title or '')):
        year = extract_year(ep)
        duration = f'{int(ep.duration_sec // 60)}' if ep.duration_sec else ''

        # Check if matched to NAS
        group = matched_groups.get(ep.id)

        if group:
            matched_count += 1
            # Get files for this group
            files = db.query(NasFile).filter(NasFile.asset_group_id == group.id).all()

            # Separate Origin and Archive files
            origin_files = [f for f in files if is_origin_path(f.full_path)]
            archive_files = [f for f in files if is_archive_path(f.full_path)]

            # Get primary/first file for each location
            origin_primary = next((f for f in origin_files if f.role == 'primary'), None)
            if not origin_primary and origin_files:
                origin_primary = origin_files[0]

            archive_primary = archive_files[0] if archive_files else None

            rows.append([
                year or '',
                (ep.collection_title or '').strip(),
                (ep.season_title or '').strip(),
                (ep.title or '').strip(),
                duration,
                'MATCHED',
                group.group_id,
                regions.get(group.region_id, ''),
                event_types.get(group.event_type_id, ''),
                group.episode or '',
                origin_primary.full_path if origin_primary else '',
                origin_primary.filename if origin_primary else '',
                format_size(origin_primary.size_bytes) if origin_primary else '',
                archive_primary.full_path if archive_primary else '',
                archive_primary.filename if archive_primary else '',
                format_size(archive_primary.size_bytes) if archive_primary else '',
                f'{group.pokergo_match_score:.2f}' if group.pokergo_match_score else '',
                ep.id
            ])
        else:
            # Not matched
            rows.append([
                year or '',
                (ep.collection_title or '').strip(),
                (ep.season_title or '').strip(),
                (ep.title or '').strip(),
                duration,
                'NO NAS',
                '', '', '', '',
                '', '', '',
                '', '', '',
                '',
                ep.id
            ])

    print(f'Matched: {matched_count}')
    print(f'Unmatched: {len(wsop_episodes) - matched_count}')
    print(f'Rows prepared: {len(rows)}')

    # Google Sheets Export
    creds = Credentials.from_service_account_file(
        str(CREDENTIALS_PATH),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)
    sheets = service.spreadsheets()

    sheet_name = 'PokerGO_WSOP_All'

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

    print(f'[OK] Export complete: {result.get("updatedRows", 0)} rows')
    print(f'URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit')


if __name__ == '__main__':
    main()
