"""Export 4 sheets: NAS_Origin_Raw, NAS_Archive_Raw, PokerGO_Raw, Matching_Integrated."""
import sys
import re
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.database import get_db, NasFile, AssetGroup, PokergoEpisode, Region, EventType
from src.nams.api.services.matching_v2 import is_actual_episode
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

GOOGLE_SHEETS_ID = '1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4'
CREDENTIALS_PATH = Path('D:/AI/claude01/json/service_account_key.json')

# Extension priority for Primary/Backup
EXT_PRIORITY = {'.mp4': 1, '.mov': 2, '.mxf': 3, '.avi': 4, '.mkv': 5, '.wmv': 6, '.m4v': 7}

# Size threshold: 1GB in bytes
SIZE_1GB = 1024 * 1024 * 1024


def get_era(year: int) -> str:
    """Get WSOP era from year."""
    if not year:
        return ''
    if year <= 2002:
        return 'CLASSIC'
    elif year <= 2010:
        return 'BOOM'
    elif year <= 2025:
        return 'HD'
    else:
        return 'NEW'


def extract_year(path: str) -> int:
    """Extract year from path."""
    match = re.search(r'(19|20)\d{2}', path)
    return int(match.group()) if match else None


def extract_year_from_episode(ep) -> int:
    """Extract year from PokerGO episode."""
    for text in [ep.title, ep.collection_title, ep.season_title]:
        if text:
            match = re.search(r'\b(19|20)\d{2}\b', text)
            if match:
                return int(match.group())
    return None


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


def is_archive_path(path: str) -> bool:
    """Check if path is Archive (Z: drive)."""
    if not path:
        return False
    path_upper = path.upper()
    return path_upper.startswith('Z:') or 'ARCHIVE' in path_upper


def is_pokergo_source_path(path: str) -> bool:
    """Check if path is PokerGO source (X: drive)."""
    if not path:
        return False
    path_upper = path.upper()
    return path_upper.startswith('X:') or 'GGP FOOTAGE' in path_upper or 'POKERGO' in path_upper


def get_extension(filename: str) -> str:
    """Get file extension."""
    if '.' in filename:
        return '.' + filename.rsplit('.', 1)[1].lower()
    return ''


def is_hand_clip(filename: str) -> bool:
    """
    Detect hand/highlight clip files.

    Patterns:
    1. Starts with number + -wsop- (e.g., 43-wsop-2024-me-day1b-Koury-set-...)
    2. Contains 'hs-' (hand segment)
    3. Contains 'hand_' (e.g., 1213_Hand_09_...)
    4. Contains poker hand terms: vs, set, FH, quad, bluff, eliminated, wins, rivers, folds, cooler
    """
    fname_lower = filename.lower()

    # Pattern 1: Starts with number + -wsop- (clip files are numbered)
    if re.match(r'^\d+-wsop-', fname_lower):
        return True

    # Pattern 2: Contains 'hs-' (hand segment)
    if '-hs-' in fname_lower or '_hs_' in fname_lower:
        return True

    # Pattern 3: Contains 'hand_'
    if 'hand_' in fname_lower:
        return True

    return False


def check_exclude_conditions(filename: str, size_bytes: int, duration_sec: int = None) -> dict:
    """Check exclusion conditions for a file."""
    fname_lower = filename.lower()
    is_hand = is_hand_clip(filename)  # Hand clip 감지 (숫자+wsop, hs-, hand_)

    return {
        'less_1gb': size_bytes and size_bytes < SIZE_1GB,
        'less_30min': duration_sec is not None and duration_sec < 1800,  # 30분 = 1800초
        'clip': 'clip' in fname_lower,  # 'clip' 키워드만
        'hand': is_hand,  # Hand clip 패턴 (별도 표시)
        'circuit': 'circuit' in fname_lower,
        'highlight': 'highlight' in fname_lower,
    }


def extract_base_name(filename: str) -> str:
    """Extract base name from filename (remove version/channel/extension)."""
    name = filename.rsplit('.', 1)[0]  # Remove extension

    # Remove version (_v1, _v2, _FINAL, _Revised)
    name = re.sub(r'_v\d+$', '', name, flags=re.I)
    name = re.sub(r'_FINAL.*$', '', name, flags=re.I)
    name = re.sub(r'_Revised$', '', name, flags=re.I)

    # Remove channel (_4CH, _NB, _4CHAN)
    name = re.sub(r'_4CH(AN)?.*$', '', name, flags=re.I)
    name = re.sub(r'_NB$', '', name, flags=re.I)

    return name


def normalize_for_matching(text: str) -> str:
    """Normalize text for matching (NAS filename <-> PokerGO title).

    Handles:
    - Source prefix removal ((YouTube), (PokerGO), etc.)
    - Extension removal (.mp4, .mov, etc.)
    - Resolution removal (1080p, 720p, 4K, HD)
    - Pipe to space (| -> space)
    - Currency symbols ($, €) removal
    - Multiple spaces to single space
    - Lowercase
    """
    if not text:
        return ''

    # Remove source prefix (YouTube), (PokerGO), etc.
    text = re.sub(r'^\s*\(?(YouTube|PokerGO|PokerGo)\)?\s*', '', text, flags=re.I)

    # Remove extension
    text = re.sub(r'\.(mp4|mov|mxf|avi|mkv|wmv|m4v)$', '', text, flags=re.I)

    # Remove resolution info
    text = re.sub(r'\s*\(?(1080p|720p|480p|4K|HD|UHD)\)?', '', text, flags=re.I)

    # Remove trailing markers like _NB, _FINAL, etc.
    text = re.sub(r'[_-](NB|FINAL|4CH|CLEAN|MASTER(ED)?)$', '', text, flags=re.I)

    # Pipe, underscore, and slash to space
    text = text.replace('|', ' ')
    text = text.replace('_', ' ')
    text = text.replace('/', ' ')  # 슬래시도 공백으로 (Day 2A/B/C -> Day 2A B C)

    # Remove currency symbols ($, €, £)
    text = re.sub(r'[$€£]', '', text)

    # Multiple spaces to single
    text = re.sub(r'\s+', ' ', text)

    # Strip and lowercase
    return text.strip().lower()


def detect_duplicates(pokergo_to_files: dict, file_to_group: dict) -> dict:
    """Detect duplicate mappings (different GROUPS mapped to same PokerGO).

    Same group files are NOT duplicates (they're Primary/Backup copies).
    Different group files mapped to same PokerGO ARE duplicates.

    EXCEPTION: If different groups have different catalog_titles, they're NOT duplicates.
    This handles CLASSIC Era Part separation (Part 1 vs Part 2 -> same PokerGO title but different content).

    Returns dict of {title: {'files': [...], 'groups': [...], 'action': 'PATTERN_NEEDED'}}
    """
    duplicates = {}

    for title, files in pokergo_to_files.items():
        if len(files) <= 1:
            continue

        # Get unique groups and their catalog_titles for these files
        unique_groups = set()
        unique_catalog_titles = set()
        for f in files:
            group = file_to_group.get(f)
            if group:
                unique_groups.add(group.group_id)
                if group.catalog_title:
                    unique_catalog_titles.add(group.catalog_title)
            else:
                unique_groups.add(f'NO_GROUP:{f}')

        # If different groups are mapped to same PokerGO, check if they have different catalog_titles
        if len(unique_groups) > 1:
            # CLASSIC Era Part handling: different catalog_titles = NOT duplicate
            # Example: "Wsop 2002 Main Event Part 1" vs "Wsop 2002 Main Event Part 2"
            # Both share same PokerGO title but have different catalog_titles
            if len(unique_catalog_titles) == len(unique_groups):
                # Each group has unique catalog_title, so this is legitimate separation
                continue

            duplicates[title] = {
                'files': files,
                'groups': list(unique_groups),
                'catalog_titles': list(unique_catalog_titles),
                'action': 'PATTERN_NEEDED'
            }

    return duplicates


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


def get_sheet_id(sheets, sheet_name: str) -> int:
    """Get sheet ID by name."""
    spreadsheet = sheets.get(spreadsheetId=GOOGLE_SHEETS_ID).execute()
    for sheet in spreadsheet['sheets']:
        if sheet['properties']['title'] == sheet_name:
            return sheet['properties']['sheetId']
    return None


def apply_checkboxes(sheets, sheet_name: str, checkbox_columns: list, row_count: int):
    """Apply actual Google Sheets checkboxes to specified columns."""
    sheet_id = get_sheet_id(sheets, sheet_name)
    if sheet_id is None:
        print(f'  Warning: Sheet {sheet_name} not found for checkbox')
        return

    requests = []
    for col_index in checkbox_columns:
        requests.append({
            'setDataValidation': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 1,  # Skip header
                    'endRowIndex': row_count,
                    'startColumnIndex': col_index,
                    'endColumnIndex': col_index + 1
                },
                'rule': {
                    'condition': {
                        'type': 'BOOLEAN'
                    },
                    'showCustomUi': True
                }
            }
        })

    if requests:
        sheets.batchUpdate(
            spreadsheetId=GOOGLE_SHEETS_ID,
            body={'requests': requests}
        ).execute()
        print(f'  Applied checkboxes to {len(checkbox_columns)} columns')


def apply_row_formatting(sheets, sheet_name: str, row_count: int, col_count: int):
    """Apply row formatting to distinguish Primary/Backup/Excluded rows.

    Colors:
    - Primary rows: White background (default, explicit)
    - Backup rows: Light blue-gray background
    - Excluded rows: Light gray background (highest priority)
    """
    sheet_id = get_sheet_id(sheets, sheet_name)
    if sheet_id is None:
        print(f'  Warning: Sheet {sheet_name} not found for formatting')
        return

    # First, clear existing conditional formatting
    clear_request = {
        'deleteConditionalFormatRule': {
            'sheetId': sheet_id,
            'index': 0
        }
    }

    # Column indices (0-based):
    # <1GB=11(L), <30min=12(M), Clip=13(N), Hand=14(O), Circuit=15(P), Backup=16(Q)
    requests = [
        # Rule 1: Excluded rows - light gray (index 0, highest priority)
        {
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': sheet_id,
                        'startRowIndex': 1,
                        'endRowIndex': row_count,
                        'startColumnIndex': 0,
                        'endColumnIndex': col_count
                    }],
                    'booleanRule': {
                        'condition': {
                            'type': 'CUSTOM_FORMULA',
                            'values': [{
                                'userEnteredValue': '=OR($L2=TRUE, $M2=TRUE, $N2=TRUE, $O2=TRUE, $P2=TRUE)'
                            }]
                        },
                        'format': {
                            'backgroundColor': {
                                'red': 0.85,
                                'green': 0.85,
                                'blue': 0.85
                            }
                        }
                    }
                },
                'index': 0
            }
        },
        # Rule 2: Backup rows - light blue-gray (index 1)
        {
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': sheet_id,
                        'startRowIndex': 1,
                        'endRowIndex': row_count,
                        'startColumnIndex': 0,
                        'endColumnIndex': col_count
                    }],
                    'booleanRule': {
                        'condition': {
                            'type': 'CUSTOM_FORMULA',
                            'values': [{
                                'userEnteredValue': '=$Q2=TRUE'  # Backup column
                            }]
                        },
                        'format': {
                            'backgroundColor': {
                                'red': 0.92,
                                'green': 0.95,
                                'blue': 0.98
                            }
                        }
                    }
                },
                'index': 1
            }
        },
        # Rule 3: Primary rows (not backup, not excluded) - white background
        {
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': sheet_id,
                        'startRowIndex': 1,
                        'endRowIndex': row_count,
                        'startColumnIndex': 0,
                        'endColumnIndex': col_count
                    }],
                    'booleanRule': {
                        'condition': {
                            'type': 'CUSTOM_FORMULA',
                            'values': [{
                                'userEnteredValue': '=AND($Q2=FALSE, NOT(OR($L2=TRUE, $M2=TRUE, $N2=TRUE, $O2=TRUE, $P2=TRUE)))'
                            }]
                        },
                        'format': {
                            'backgroundColor': {
                                'red': 1.0,
                                'green': 1.0,
                                'blue': 1.0
                            }
                        }
                    }
                },
                'index': 2
            }
        }
    ]

    sheets.batchUpdate(
        spreadsheetId=GOOGLE_SHEETS_ID,
        body={'requests': requests}
    ).execute()
    print(f'  Applied row formatting (Primary=white, Backup=light blue, Excluded=gray)')


def export_nas_origin_raw(db, sheets):
    """Export Sheet 1: NAS_Origin_Raw."""
    print('\n[1/5] NAS_Origin_Raw')

    # Get all WSOP files from Origin
    all_files = db.query(NasFile).filter(
        (NasFile.full_path.ilike('%wsop%') |
         NasFile.full_path.ilike('%ws0%') |
         NasFile.full_path.ilike('%ws1%') |
         NasFile.full_path.ilike('%ws2%'))
    ).order_by(NasFile.full_path).all()

    origin_files = [f for f in all_files if is_origin_path(f.full_path)]
    print(f'  Origin files: {len(origin_files)}')

    headers = ['Year', 'Filename', 'Size_GB', 'Full_Path', 'Extension']
    rows = [headers]

    for f in origin_files:
        year = extract_year(f.full_path)
        ext = get_extension(f.filename)
        rows.append([
            year or '',
            f.filename,
            format_size(f.size_bytes),
            f.full_path or '',
            ext
        ])

    write_sheet(sheets, 'NAS_Origin_Raw', rows)
    return origin_files


def export_nas_archive_raw(db, sheets):
    """Export Sheet 2: NAS_Archive_Raw."""
    print('\n[2/5] NAS_Archive_Raw')

    # Get all WSOP files from Archive
    all_files = db.query(NasFile).filter(
        (NasFile.full_path.ilike('%wsop%') |
         NasFile.full_path.ilike('%ws0%') |
         NasFile.full_path.ilike('%ws1%') |
         NasFile.full_path.ilike('%ws2%'))
    ).order_by(NasFile.full_path).all()

    archive_files = [f for f in all_files if is_archive_path(f.full_path)]
    print(f'  Archive files: {len(archive_files)}')

    headers = ['Year', 'Filename', 'Size_GB', 'Full_Path', 'Extension']
    rows = [headers]

    for f in archive_files:
        year = extract_year(f.full_path)
        ext = get_extension(f.filename)
        rows.append([
            year or '',
            f.filename,
            format_size(f.size_bytes),
            f.full_path or '',
            ext
        ])

    write_sheet(sheets, 'NAS_Archive_Raw', rows)
    return archive_files


def export_nas_pokergo_raw(db, sheets):
    """Export Sheet 3: NAS_PokerGO_Raw (X: drive PokerGO source files)."""
    print('\n[3/5] NAS_PokerGO_Raw')

    # Get all files from PokerGO source (X: drive) - filter by path, not role
    all_files = db.query(NasFile).order_by(NasFile.full_path).all()

    pokergo_src_files = [f for f in all_files if is_pokergo_source_path(f.full_path)]
    print(f'  PokerGO source files: {len(pokergo_src_files)}')

    headers = ['Year', 'Filename', 'Size_GB', 'Full_Path', 'Extension']
    rows = [headers]

    for f in pokergo_src_files:
        year = extract_year(f.full_path)
        ext = get_extension(f.filename)
        rows.append([
            year or '',
            f.filename,
            format_size(f.size_bytes),
            f.full_path or '',
            ext
        ])

    write_sheet(sheets, 'NAS_PokerGO_Raw', rows)
    return pokergo_src_files


def load_pokergo_from_json():
    """Load PokerGO data from wsop_final.json (includes WSOP Classic)."""
    import json
    json_path = Path(__file__).parent.parent / 'data' / 'pokergo' / 'wsop_final.json'

    if not json_path.exists():
        print(f'  [WARNING] {json_path} not found, falling back to DB')
        return None

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle both list format and dict format
    if isinstance(data, list):
        return data
    return data.get('videos', [])


def export_pokergo_raw(db, sheets):
    """Export Sheet 4: PokerGO_Raw (from DB with Collection/Season)."""
    print('\n[4/5] PokerGO_Raw')

    # Get all PokerGO episodes from DB (includes collection_title, season_title)
    all_episodes = db.query(PokergoEpisode).all()
    print(f'  PokerGO episodes (from DB): {len(all_episodes)}')

    # Count by era
    era_counts = {'CLASSIC': 0, 'BOOM': 0, 'HD': 0}
    for ep in all_episodes:
        year = extract_year_from_episode(ep)
        if year and year <= 2002:
            era_counts['CLASSIC'] += 1
        elif year and year <= 2010:
            era_counts['BOOM'] += 1
        else:
            era_counts['HD'] += 1
    print(f'    CLASSIC: {era_counts["CLASSIC"]}, BOOM: {era_counts["BOOM"]}, HD: {era_counts["HD"]}')

    # Headers with Collection and Season
    headers = ['ID', 'Year', 'Era', 'Collection', 'Season', 'Title', 'Region', 'Event_Type', 'Duration']
    rows = [headers]

    # Sort by year, then title
    sorted_episodes = sorted(all_episodes, key=lambda x: (extract_year_from_episode(x) or 9999, x.title or ''))

    for idx, ep in enumerate(sorted_episodes):
        year = extract_year_from_episode(ep)
        era = get_era(year)
        title = ep.title or ''
        title_lower = title.lower()
        collection = ep.collection_title or ''
        season = ep.season_title or ''

        # Extract region from title/collection
        if 'europe' in title_lower or 'wsope' in title_lower or 'europe' in collection.lower():
            region = 'EU'
        elif 'apac' in title_lower or 'apac' in collection.lower():
            region = 'APAC'
        elif 'paradise' in title_lower or 'paradise' in collection.lower():
            region = 'PAR'
        else:
            region = 'LV'

        # Extract event type
        if 'main event' in title_lower or 'main event' in collection.lower():
            event_type = 'ME'
        elif 'bracelet' in title_lower or 'bracelet' in collection.lower() or 'event #' in title_lower:
            event_type = 'BR'
        elif 'high roller' in title_lower:
            event_type = 'HR'
        elif 'heads-up' in title_lower or 'heads up' in title_lower:
            event_type = 'HU'
        else:
            event_type = ''

        # Format duration
        duration_str = ''
        if ep.duration_sec:
            mins = ep.duration_sec // 60
            duration_str = f'{mins}m'

        rows.append([
            idx + 1,  # ID
            year or '',
            era,
            collection,
            season,
            title,
            region,
            event_type,
            duration_str
        ])

    write_sheet(sheets, 'PokerGO_Raw', rows)
    return all_episodes


def export_matching_integrated(db, sheets, origin_files, archive_files, pokergo_src_files, pokergo_episodes):
    """Export Sheet 5: Matching_Integrated with actual Google Sheets checkboxes."""
    print('\n[5/5] Matching_Integrated')

    # Build full_path -> file mapping (Full Path 기준 - 중복 방지)
    origin_by_path = {f.full_path: f for f in origin_files}
    archive_by_path = {f.full_path: f for f in archive_files}
    pokergo_src_by_path = {f.full_path: f for f in pokergo_src_files}

    # Also build filename -> paths mapping for cross-reference
    origin_names = {f.filename for f in origin_files}
    archive_names = {f.filename for f in archive_files}
    pokergo_src_names = {f.filename for f in pokergo_src_files}

    # All unique paths from NAS
    all_nas_paths = set(origin_by_path.keys()) | set(archive_by_path.keys()) | set(pokergo_src_by_path.keys())
    print(f'  Total NAS paths: {len(all_nas_paths)} (Origin: {len(origin_by_path)}, Archive: {len(archive_by_path)}, PokerGO_Src: {len(pokergo_src_by_path)})')

    # Build file -> group -> pokergo mapping from DB AssetGroup (NOT SemanticMatcher)
    # DB의 매칭 결과만 사용하여 일관성 유지
    file_to_group = {}
    file_to_pokergo = {}  # filename -> PokergoEpisode object (not just title)
    pokergo_to_files = defaultdict(list)  # For duplicate detection

    all_files = db.query(NasFile).filter(
        (NasFile.full_path.ilike('%wsop%') |
         NasFile.full_path.ilike('%ws0%') |
         NasFile.full_path.ilike('%ws1%') |
         NasFile.full_path.ilike('%ws2%'))
    ).all()

    for f in all_files:
        if f.asset_group_id:
            group = db.query(AssetGroup).filter(AssetGroup.id == f.asset_group_id).first()
            if group:
                file_to_group[f.filename] = group
                if group.pokergo_episode_id:
                    ep = db.query(PokergoEpisode).filter(PokergoEpisode.id == group.pokergo_episode_id).first()
                    if ep:
                        file_to_pokergo[f.filename] = ep  # Store full episode object
                        # CRITICAL: Only add NON-EXCLUDED files to duplicate detection
                        # Excluded files (clips, hand samples) should not trigger duplicates
                        if not f.is_excluded:
                            pokergo_to_files[ep.title].append(f.filename)

    # NOTE: SemanticMatcher 추가 매칭 제거
    # DB의 matching.py가 이미 Region mismatch, Event # 필수 매칭 등을 처리하므로
    # 여기서 추가 매칭 시 규칙 위반으로 DUPLICATE 발생 가능

    # Detect duplicate mappings (1:N violation)
    duplicates = detect_duplicates(pokergo_to_files, file_to_group)
    duplicate_files = set()
    for info in duplicates.values():
        duplicate_files.update(info['files'])

    # Headers with checkbox columns (Full Path 기준)
    # Checkbox columns: Origin(7), Archive(8), PokerGO_Src(9), PKG(10), <1GB(11), <30min(12), Clip(13), Hand(14), Circuit(15), Backup(16)
    headers = [
        'Year', 'NAS Filename', 'Full_Path', 'PokerGO Title', 'Catalog Title', 'Collection', 'Season',  # +1 column (Catalog Title)
        'Origin', 'Archive', 'PokerGO_Src', 'PKG',  # Storage Status (checkboxes)
        '<1GB', '<30min', 'Clip', 'Hand', 'Circuit',  # Exclude Conditions (checkboxes)
        'Backup', 'Group ID', 'Action'  # Duplicate & Action
    ]
    rows = [headers]

    # Stats
    action_counts = defaultdict(int)

    # Track displayed PokerGO titles to avoid duplicates (1:1 rule)
    displayed_pokergo_titles = set()

    # Process NAS files by Full Path (중복 방지)
    processed_paths = set()

    for full_path in sorted(all_nas_paths):
        if full_path in processed_paths:
            continue
        processed_paths.add(full_path)

        # Get file object
        file_obj = origin_by_path.get(full_path) or archive_by_path.get(full_path) or pokergo_src_by_path.get(full_path)
        if not file_obj:
            continue

        filename = file_obj.filename
        year = extract_year(full_path)

        # Determine Origin/Archive/PokerGO_Src status for this specific path
        is_origin_file = full_path in origin_by_path
        is_archive_file = full_path in archive_by_path
        is_pokergo_src_file = full_path in pokergo_src_by_path

        # Check if same filename exists in other storage
        has_origin_copy = filename in origin_names
        has_archive_copy = filename in archive_names
        has_pokergo_src_copy = filename in pokergo_src_names

        # Get group info
        group = file_to_group.get(filename)
        group_id_str = group.group_id if group else ''

        # Determine if file is Backup (from DB role field)
        is_backup = file_obj.role == 'backup'

        # Exclude conditions (check FIRST before PokerGO matching)
        exclude = check_exclude_conditions(filename, file_obj.size_bytes, None)
        is_excluded = exclude['less_1gb'] or exclude['clip'] or exclude['circuit'] or exclude['highlight'] or exclude['hand']

        is_less_1gb = True if exclude['less_1gb'] else False
        is_less_30min = False  # Duration not available for NAS files
        is_clip = True if exclude['clip'] else False
        is_hand = True if exclude['hand'] else False
        is_circuit = True if exclude['circuit'] else False

        # PokerGO match (SKIP if excluded or backup - backup files don't show PokerGO title)
        # Primary files only show PokerGO title to avoid duplicate display in sheet
        # Also skip if this PokerGO title was already displayed (1:1 rule)
        if is_excluded or is_backup:
            pokergo_title = ''
            catalog_title = ''
            pokergo_collection = ''
            pokergo_season = ''
            has_pokergo = False if is_excluded else bool(file_to_pokergo.get(filename))  # Backup still counts as having PKG
        else:
            pokergo_ep = file_to_pokergo.get(filename)
            if pokergo_ep:
                raw_title = pokergo_ep.title or ''
                # 1:1 rule: Only display each PokerGO title once
                # Exception: Different catalog_titles (e.g., Part 1 vs Part 2) can share same PokerGO title
                catalog_title_check = group.catalog_title if group else raw_title
                display_key = catalog_title_check or raw_title

                if display_key and display_key in displayed_pokergo_titles:
                    # Already displayed this title, skip to enforce 1:1
                    pokergo_title = ''
                    catalog_title = ''
                    pokergo_collection = ''
                    pokergo_season = ''
                    has_pokergo = True  # Still has PKG match, just not displayed
                else:
                    pokergo_title = raw_title
                    pokergo_collection = pokergo_ep.collection_title or ''
                    pokergo_season = pokergo_ep.season_title or ''
                    has_pokergo = True
                    if display_key:
                        displayed_pokergo_titles.add(display_key)

                    # Get Catalog Title from group (CLASSIC era Part handling)
                    catalog_title = group.catalog_title if group else ''
                    if not catalog_title:
                        catalog_title = pokergo_title  # Fallback to PokerGO title
            else:
                pokergo_title = ''
                pokergo_collection = ''
                pokergo_season = ''
                has_pokergo = False
                catalog_title = ''

        # Storage Status checkboxes - this specific path
        has_origin = is_origin_file
        has_archive = is_archive_file
        has_pokergo_src = is_pokergo_src_file

        # Action determination
        action = ''
        if is_excluded:
            action = 'Excluded'
        elif filename in duplicate_files and not is_backup:
            # 백업본에는 DUPLICATE 마킹하지 않음 (Primary만 표시)
            action = 'DUPLICATE'
        elif has_origin_copy and not has_archive_copy:
            action = '-> Archive'

        action_counts[action if action else 'OK'] += 1

        rows.append([
            year or '',
            filename,
            full_path,  # Full Path 추가
            pokergo_title,
            catalog_title,  # Catalog Title (CLASSIC era Part 처리)
            pokergo_collection,  # Collection 추가
            pokergo_season,  # Season 추가
            has_origin,
            has_archive,
            has_pokergo_src,  # PokerGO_Src (X: 드라이브)
            has_pokergo,  # PKG 매칭 (제외 시 FALSE)
            is_less_1gb,
            is_less_30min,
            is_clip,
            is_hand,
            is_circuit,
            is_backup,
            group_id_str,
            action
        ])

    # Add PokerGO-only entries (not yet matched - rules need improvement)
    # These entries help identify missing matching rules
    matched_titles = set(ep_obj.title for ep_obj in file_to_pokergo.values() if ep_obj)

    for ep in pokergo_episodes:
        # Handle both DB objects and JSON dicts
        if isinstance(ep, dict):
            title = ep.get('title', '')
            collection = ep.get('collection_title', '')
            season = ep.get('season_title', '')
            year = int(ep.get('year', 0)) if ep.get('year') else None
            is_less_30min = False
        else:
            title = ep.title or ''
            collection = ep.collection_title or ''
            season = ep.season_title or ''
            year = extract_year_from_episode(ep)
            is_less_30min = ep.duration_sec is not None and ep.duration_sec > 0 and ep.duration_sec < 1800

        # Skip if already matched to NAS file
        if title in matched_titles:
            continue

        # Action: Need to add matching rule
        action = 'RULE_NEEDED' if not is_less_30min else 'Excluded'

        rows.append([
            year or '',
            '',  # No NAS filename yet
            '',  # No Full_Path yet
            title,  # PokerGO Title
            title,  # Catalog Title
            collection,
            season,
            False,  # No Origin
            False,  # No Archive
            False,  # No PokerGO_Src
            True,   # Has PokerGO (PKG)
            False,  # <1GB
            is_less_30min,
            False,  # Clip
            False,  # Hand
            False,  # Circuit
            False,  # Not backup
            '',  # No group yet
            action
        ])
        action_counts[action] += 1

    write_sheet(sheets, 'Matching_Integrated', rows)

    # Apply actual Google Sheets checkboxes
    # Column indices (0-based): Origin=7, Archive=8, PokerGO_Src=9, PKG=10, <1GB=11, <30min=12, Clip=13, Hand=14, Circuit=15, Backup=16
    checkbox_columns = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
    apply_checkboxes(sheets, 'Matching_Integrated', checkbox_columns, len(rows))

    # Apply gray background to excluded rows (where any exclude condition is TRUE)
    apply_row_formatting(sheets, 'Matching_Integrated', len(rows), len(headers))

    # Stats
    print('\n=== Action Stats ===')
    for action, count in sorted(action_counts.items()):
        warning = ''
        if action == '-> Archive':
            warning = ' [WARNING: Archive missing!]'
        elif action == '-> Find NAS':
            warning = ' [INFO: NAS file needed]'
        elif action == 'DUPLICATE':
            warning = ' [WARNING: 1:N violation - pattern needed!]'
        print(f'  {action or "OK"}: {count}{warning}')

    # Duplicate details
    if duplicates:
        print(f'\n=== Duplicate Mappings ({len(duplicates)}) ===')
        print('  (다른 그룹이 동일 PokerGO에 매칭 - 패턴 규칙 추가 필요)')
        print('  (CLASSIC Era Part 분리는 catalog_title로 구분되어 제외됨)')
        for title, info in sorted(duplicates.items())[:10]:
            print(f'\n  [{title}]')
            print(f'    Groups: {sorted(info["groups"])[:5]}')
            if info.get('catalog_titles'):
                print(f'    Catalog Titles: {sorted(info["catalog_titles"])[:5]}')
            if len(info['groups']) > 5:
                print(f'    ... (+{len(info["groups"])-5} more)')
        if len(duplicates) > 10:
            print(f'\n  ... (+{len(duplicates)-10} more duplicates)')


def main():
    print('=' * 60)
    print('5 Sheets Export System (v3 - with PokerGO Source)')
    print('=' * 60)

    db = next(get_db())
    sheets = get_sheets_service()

    # Export all 5 sheets
    origin_files = export_nas_origin_raw(db, sheets)
    archive_files = export_nas_archive_raw(db, sheets)
    pokergo_src_files = export_nas_pokergo_raw(db, sheets)
    pokergo_episodes = export_pokergo_raw(db, sheets)
    export_matching_integrated(db, sheets, origin_files, archive_files, pokergo_src_files, pokergo_episodes)

    print('\n' + '=' * 60)
    print(f'[OK] All 5 sheets exported successfully')
    print(f'URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit')
    print('=' * 60)


if __name__ == '__main__':
    main()
