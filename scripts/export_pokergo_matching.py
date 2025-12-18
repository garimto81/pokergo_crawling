"""Export PokerGO-based matching sheet: PokerGO titles with matched NAS files."""
import sys
import re
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.database import get_db, NasFile, AssetGroup, PokergoEpisode, Region, EventType
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

GOOGLE_SHEETS_ID = '1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4'
CREDENTIALS_PATH = Path('D:/AI/claude01/json/service_account_key.json')

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
    return 'NEW'


def extract_year_from_episode(ep) -> int:
    """Extract year from PokerGO episode."""
    for text in [ep.title, ep.collection_title, ep.season_title]:
        if text:
            match = re.search(r'\b(19|20)\d{2}\b', text)
            if match:
                return int(match.group())
    return None


def extract_episode_num_from_title(title: str) -> int:
    """Extract episode number from PokerGO title."""
    if not title:
        return None

    # "Episode N" or "Ep N" or "Ep. N"
    match = re.search(r'\b(?:Episode|Ep\.?)\s*(\d+)\b', title, re.I)
    if match:
        return int(match.group(1))

    # "Day N" -> treat as episode
    match = re.search(r'\bDay\s*(\d+)\b', title, re.I)
    if match:
        return int(match.group(1))

    # "Show N"
    match = re.search(r'\bShow\s*(\d+)\b', title, re.I)
    if match:
        return int(match.group(1))

    return None


def extract_event_type_from_title(title: str) -> str:
    """Extract event type from PokerGO title."""
    if not title:
        return None

    title_lower = title.lower()

    if 'main event' in title_lower:
        return 'ME'
    if 'bracelet' in title_lower or re.search(r'event\s*#?\d+', title_lower):
        return 'BR'
    if 'high roller' in title_lower:
        return 'HR'
    if 'heads up' in title_lower or 'heads-up' in title_lower:
        return 'HU'
    if 'tag team' in title_lower:
        return 'TT'
    if "player's championship" in title_lower or 'poc' in title_lower:
        return 'POC'

    return None


def extract_region_from_title(title: str, collection: str = None) -> str:
    """Extract region from PokerGO title or collection."""
    check_text = f"{title or ''} {collection or ''}".lower()

    if 'europe' in check_text:
        return 'EU'
    if 'apac' in check_text or 'asia' in check_text:
        return 'APAC'
    if 'paradise' in check_text:
        return 'PARADISE'
    if 'super circuit' in check_text:
        return 'SC'

    # Default is Las Vegas
    return 'LV'


def format_size(bytes_size: int) -> str:
    """Format bytes to GB."""
    if not bytes_size:
        return ""
    gb = bytes_size / (1024**3)
    return f"{gb:.1f}"


def get_source_drive(path: str) -> str:
    """Get source drive from path."""
    if not path:
        return ""
    if path.upper().startswith('Y:'):
        return 'Y:'
    elif path.upper().startswith('Z:'):
        return 'Z:'
    elif path.upper().startswith('X:'):
        return 'X:'
    return ""


def is_excluded_file(filename: str, size_bytes: int) -> bool:
    """Check if file should be excluded."""
    fname_lower = filename.lower()

    # Size < 1GB
    if size_bytes and size_bytes < SIZE_1GB:
        return True

    # Clip patterns
    if 'clip' in fname_lower or 'hand_' in fname_lower:
        return True
    if re.match(r'^\d+-wsop-', fname_lower):
        return True
    if 'circuit' in fname_lower:
        return True
    if 'highlight' in fname_lower:
        return True

    return False


def is_backup_filename(filename: str) -> bool:
    """파일명 패턴으로 Backup 여부 판단 (규칙 PB-2)."""
    # 복사본 패턴 감지: (1), (2), etc.
    if re.search(r'\(\d+\)', filename):
        return True

    fname_lower = filename.lower()
    if '_copy' in fname_lower or '복사본' in filename:
        return True

    return False


def get_primary_score(filename: str, size_bytes: int = 0) -> int:
    """Primary 우선순위 점수 (높을수록 Primary) - 규칙 PB-2."""
    score = 0
    fname_lower = filename.lower()

    # 정제 키워드 = 높은 점수
    if 'nobug' in fname_lower:
        score += 100
    if 'clean' in fname_lower or 'final' in fname_lower:
        score += 80

    # 복사 표시 = 낮은 점수
    if re.search(r'\(\d+\)', filename):
        score -= 50
    if '_copy' in fname_lower or '복사본' in filename:
        score -= 50

    # 확장자 우선순위
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    ext_priority = {'mp4': 10, 'mov': 8, 'mxf': 6, 'avi': 4, 'mkv': 2, 'wmv': 1, 'm4v': 0}
    score += ext_priority.get(ext, 0)

    # 파일 크기 (큰 파일 선호)
    if size_bytes:
        score += min(size_bytes // (1024**3), 20)  # 최대 20점

    return score


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

    # Clear wider range for new columns
    sheets.values().clear(
        spreadsheetId=GOOGLE_SHEETS_ID,
        range=f'{sheet_name}!A:AZ'
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
        return

    requests = []
    for col_index in checkbox_columns:
        requests.append({
            'setDataValidation': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 1,
                    'endRowIndex': row_count,
                    'startColumnIndex': col_index,
                    'endColumnIndex': col_index + 1
                },
                'rule': {
                    'condition': {'type': 'BOOLEAN'},
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


def apply_conditional_formatting(sheets, sheet_name: str, row_count: int, col_count: int):
    """Apply conditional formatting for match status and backup patterns."""
    sheet_id = get_sheet_id(sheets, sheet_name)
    if sheet_id is None:
        return

    # 먼저 기존 조건부 서식 삭제
    clear_requests = [{
        'deleteConditionalFormatRule': {
            'sheetId': sheet_id,
            'index': 0
        }
    }]
    # 여러 번 삭제 시도 (기존 규칙 수만큼)
    for _ in range(10):
        try:
            sheets.batchUpdate(
                spreadsheetId=GOOGLE_SHEETS_ID,
                body={'requests': clear_requests}
            ).execute()
        except Exception:
            break

    requests = [
        # RED for DUPLICATE_ZX (치명적 오류 - 최상위 우선순위)
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
                            'type': 'TEXT_CONTAINS',
                            'values': [{'userEnteredValue': 'DUPLICATE_ZX'}]
                        },
                        'format': {
                            'backgroundColor': {'red': 1.0, 'green': 0.8, 'blue': 0.8}
                        }
                    }
                },
                'index': 0
            }
        },
        # Green for MATCHED
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
                            'type': 'TEXT_CONTAINS',
                            'values': [{'userEnteredValue': 'MATCHED'}]
                        },
                        'format': {
                            'backgroundColor': {'red': 0.85, 'green': 0.92, 'blue': 0.83}
                        }
                    }
                },
                'index': 1
            }
        },
        # Orange/Yellow for NO_NAS
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
                            'type': 'TEXT_CONTAINS',
                            'values': [{'userEnteredValue': 'NO_NAS'}]
                        },
                        'format': {
                            'backgroundColor': {'red': 1.0, 'green': 0.95, 'blue': 0.8}
                        }
                    }
                },
                'index': 2
            }
        },
        # Gray for CLIP_ONLY
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
                            'type': 'TEXT_CONTAINS',
                            'values': [{'userEnteredValue': 'CLIP_ONLY'}]
                        },
                        'format': {
                            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
                        }
                    }
                },
                'index': 3
            }
        },
        # Light blue for NAS_ONLY (needs rule)
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
                            'type': 'TEXT_CONTAINS',
                            'values': [{'userEnteredValue': 'NAS_ONLY'}]
                        },
                        'format': {
                            'backgroundColor': {'red': 0.85, 'green': 0.92, 'blue': 1.0}
                        }
                    }
                },
                'index': 4
            }
        },
        # Light gray for NAS_EXCLUDED
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
                            'type': 'TEXT_CONTAINS',
                            'values': [{'userEnteredValue': 'NAS_EXCLUDED'}]
                        },
                        'format': {
                            'backgroundColor': {'red': 0.95, 'green': 0.95, 'blue': 0.95}
                        }
                    }
                },
                'index': 5
            }
        },
        # Light purple for Is_Backup_Pattern (Rule 2: Primary에 백업 패턴 파일)
        # Is_Backup_Pattern 컬럼 (col 15)이 TRUE일 때 Primary 영역에 배경색
        {
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': sheet_id,
                        'startRowIndex': 1,
                        'endRowIndex': row_count,
                        'startColumnIndex': 11,  # Primary_Filename
                        'endColumnIndex': 16     # Is_Backup_Pattern 포함
                    }],
                    'booleanRule': {
                        'condition': {
                            'type': 'CUSTOM_FORMULA',
                            'values': [{'userEnteredValue': '=$P2=TRUE'}]  # P열 = Is_Backup_Pattern
                        },
                        'format': {
                            'backgroundColor': {'red': 0.95, 'green': 0.85, 'blue': 1.0}
                        }
                    }
                },
                'index': 6
            }
        }
    ]

    sheets.batchUpdate(
        spreadsheetId=GOOGLE_SHEETS_ID,
        body={'requests': requests}
    ).execute()
    print(f'  Applied conditional formatting (6 rules)')


def main():
    print('=' * 60)
    print('PokerGO-NAS 1:1 Matching Export')
    print('=' * 60)

    db = next(get_db())

    # Load all data
    episodes = db.query(PokergoEpisode).order_by(PokergoEpisode.id).all()
    groups = db.query(AssetGroup).all()
    files = db.query(NasFile).all()
    regions = {r.id: r for r in db.query(Region).all()}
    event_types = {e.id: e for e in db.query(EventType).all()}

    print(f'  PokerGO episodes: {len(episodes)}')
    print(f'  Asset groups: {len(groups)}')
    print(f'  NAS files: {len(files)}')

    # Create lookup maps
    # group_id -> group
    group_map = {g.id: g for g in groups}

    # pokergo_episode_id -> groups (matched)
    episode_to_groups = defaultdict(list)
    for g in groups:
        if g.pokergo_episode_id:
            episode_to_groups[g.pokergo_episode_id].append(g)

    # group_id -> files
    group_to_files = defaultdict(list)
    for f in files:
        if f.asset_group_id:
            group_to_files[f.asset_group_id].append(f)

    # All NAS files by year/episode for additional matching
    files_by_year_episode = defaultdict(list)
    for f in files:
        if f.year and f.episode:
            key = (f.year, f.episode)
            files_by_year_episode[key].append(f)

    # Headers - 새 구조: Primary (Z:+X:) / Backup (Y:)
    # Rule 1: Z:/X: 중복 = 치명적 오류 (DUPLICATE_ERROR)
    # Rule 2: Z:/X: 백업패턴 파일 = Primary에 표시 + Is_Backup 체크박스 + 배경색
    headers = [
        # PokerGO columns (original)
        'Era', 'Year', 'Region', 'EventType', 'Episode',
        'PokerGO_Title', 'Collection', 'Season', 'Duration_sec',
        # Matching status
        'Match_Status', 'Match_Score',
        # Primary (Z: Archive + X: PokerGO source)
        'Primary_Filename', 'Primary_Path', 'Primary_Size_GB', 'Primary_Drive', 'Is_Backup_Pattern',
        # Backup (Y: WSOP backup)
        'Backup_Filename', 'Backup_Path', 'Backup_Size_GB',
        # Matching info
        'Match_Strategy',       # 매칭 전략 (사용자 서술)
        # Group info
        'Group_ID',
        # Checkboxes
        'No_NAS', 'Clip_Only', 'Need_Rule', 'Manual_Check', 'Duplicate_ZX'
    ]

    rows = [headers]
    stats = {'MATCHED': 0, 'NO_NAS': 0, 'CLIP_ONLY': 0, 'DUPLICATE_ZX': 0}

    def sort_files_by_priority(file_list):
        """Sort files by primary score (nobug first, copies last)."""
        def file_sort_key(f):
            primary_score = -get_primary_score(f.filename, f.size_bytes)
            backup_priority = 1 if is_backup_filename(f.filename) else 0
            return (backup_priority, primary_score)
        return sorted(file_list, key=file_sort_key)

    for ep in episodes:
        year = extract_year_from_episode(ep)
        era = get_era(year)
        region = extract_region_from_title(ep.title, ep.collection_title)
        event_type = extract_event_type_from_title(ep.title)
        episode_num = extract_episode_num_from_title(ep.title)

        # Get matched groups for this episode
        matched_groups = episode_to_groups.get(ep.id, [])

        # Get files for matched groups
        all_matched_files = []
        for g in matched_groups:
            all_matched_files.extend(group_to_files.get(g.id, []))

        # 드라이브별로 파일 분리 (새 로직)
        # Primary sources: Z: (Archive) + X: (PokerGO source)
        # Backup source: Y: (WSOP backup)
        z_files = [f for f in all_matched_files if f.full_path and f.full_path.upper().startswith('Z:')]
        y_files = [f for f in all_matched_files if f.full_path and f.full_path.upper().startswith('Y:')]
        x_files = [f for f in all_matched_files if f.full_path and f.full_path.upper().startswith('X:')]

        # Rule 1: Z:/X: 중복 검출 (치명적 오류)
        has_duplicate_zx = len(z_files) > 0 and len(x_files) > 0

        # Primary = Z: + X: 합쳐서 정렬 (best score 선택)
        primary_files = z_files + x_files
        primary_files = sort_files_by_priority(primary_files)

        # Backup = Y: 정렬
        backup_files = sort_files_by_priority(y_files)

        # Determine match status
        if has_duplicate_zx:
            match_status = 'DUPLICATE_ZX'
            stats['DUPLICATE_ZX'] += 1
        elif all_matched_files:
            non_excluded = [f for f in all_matched_files if not is_excluded_file(f.filename, f.size_bytes)]
            if non_excluded:
                match_status = 'MATCHED'
                stats['MATCHED'] += 1
            else:
                match_status = 'CLIP_ONLY'
                stats['CLIP_ONLY'] += 1
        else:
            match_status = 'NO_NAS'
            stats['NO_NAS'] += 1

        # Get group info
        group = matched_groups[0] if matched_groups else None
        match_score = group.pokergo_match_score if group else ''
        group_id = group.group_id if group else ''

        # Primary file (best from Z: or X:)
        primary = primary_files[0] if primary_files else None
        primary_drive = get_source_drive(primary.full_path) if primary else ''
        # Rule 2: Primary가 백업 패턴인지 확인
        is_backup_pattern = is_backup_filename(primary.filename) if primary else False

        # Backup file (best from Y:)
        backup = backup_files[0] if backup_files else None

        row = [
            era,
            year or '',
            region or '',
            event_type or '',
            episode_num or '',
            ep.title or '',
            ep.collection_title or '',
            ep.season_title or '',
            ep.duration_sec or '',
            match_status,
            f'{match_score:.2f}' if match_score else '',
            # Primary (Z: + X:)
            primary.filename if primary else '',
            primary.full_path if primary else '',
            format_size(primary.size_bytes) if primary else '',
            primary_drive,
            'TRUE' if is_backup_pattern else '',  # Is_Backup_Pattern 체크박스
            # Backup (Y:)
            backup.filename if backup else '',
            backup.full_path if backup else '',
            format_size(backup.size_bytes) if backup else '',
            # Match Strategy
            '',  # Match_Strategy (사용자 서술)
            # Group
            group_id,
            # Checkboxes (TRUE for issues)
            'TRUE' if match_status == 'NO_NAS' else '',
            'TRUE' if match_status == 'CLIP_ONLY' else '',
            '',  # Need_Rule (manual)
            '',  # Manual_Check (manual)
            'TRUE' if has_duplicate_zx else '',  # Duplicate_ZX
        ]
        rows.append(row)

    # === Part 2: Add unmatched NAS files (NAS_ONLY) ===
    # Find all NAS files that are NOT in any matched group
    matched_file_ids = set()
    for g in groups:
        if g.pokergo_episode_id:
            for f in group_to_files.get(g.id, []):
                matched_file_ids.add(f.id)

    # Get unmatched files (not excluded, has year)
    unmatched_files = [f for f in files if f.id not in matched_file_ids and f.year]

    # Sort by year, then filename
    unmatched_files.sort(key=lambda f: (f.year or 9999, f.filename or ''))

    print(f'\n  Unmatched NAS files: {len(unmatched_files)}')

    for f in unmatched_files:
        is_excluded = is_excluded_file(f.filename, f.size_bytes)
        if is_excluded:
            match_status = 'NAS_EXCLUDED'
        else:
            match_status = 'NAS_ONLY'
            stats['NAS_ONLY'] = stats.get('NAS_ONLY', 0) + 1

        # Get region/event_type names
        region_code = regions.get(f.region_id).code if f.region_id and regions.get(f.region_id) else ''
        event_type_code = event_types.get(f.event_type_id).code if f.event_type_id and event_types.get(f.event_type_id) else ''

        # 드라이브 판별 (새 로직: Z:+X: = Primary, Y: = Backup)
        drive = get_source_drive(f.full_path)
        is_primary_drive = drive in ('Z:', 'X:')
        is_backup_drive = drive == 'Y:'

        # Primary (Z: or X:) vs Backup (Y:)
        primary_filename = f.filename if is_primary_drive else ''
        primary_path = f.full_path if is_primary_drive else ''
        primary_size = format_size(f.size_bytes) if is_primary_drive else ''
        primary_drive_val = drive if is_primary_drive else ''
        is_backup_pattern = is_backup_filename(f.filename) if is_primary_drive else False

        backup_filename = f.filename if is_backup_drive else ''
        backup_path = f.full_path if is_backup_drive else ''
        backup_size = format_size(f.size_bytes) if is_backup_drive else ''

        row = [
            get_era(f.year),
            f.year or '',
            region_code,
            event_type_code,
            f.episode or '',
            '',  # PokerGO_Title (empty for NAS_ONLY)
            '',  # Collection
            '',  # Season
            '',  # Duration_sec
            match_status,
            '',  # Match_Score
            # Primary (Z: + X:)
            primary_filename,
            primary_path,
            primary_size,
            primary_drive_val,
            'TRUE' if is_backup_pattern else '',  # Is_Backup_Pattern
            # Backup (Y:)
            backup_filename,
            backup_path,
            backup_size,
            # Match Strategy
            '',  # Match_Strategy
            # Group
            '',
            # Checkboxes
            '',  # No_NAS
            '',  # Clip_Only
            'TRUE' if match_status == 'NAS_ONLY' else '',  # Need_Rule
            '',  # Manual_Check
            '',  # Duplicate_ZX
        ]
        rows.append(row)

    print(f'\n  Match Statistics:')
    print(f'    MATCHED: {stats["MATCHED"]}')
    print(f'    NO_NAS: {stats["NO_NAS"]}')
    print(f'    CLIP_ONLY: {stats["CLIP_ONLY"]}')
    print(f'    NAS_ONLY: {stats.get("NAS_ONLY", 0)}')
    print(f'    DUPLICATE_ZX: {stats["DUPLICATE_ZX"]} (치명적 오류!)')

    # Write to Google Sheets
    print(f'\nWriting to Google Sheets...')
    sheets = get_sheets_service()
    sheet_name = 'PokerGO_NAS_Matching'

    write_sheet(sheets, sheet_name, rows)

    # Apply checkboxes to checkbox columns
    # 새 헤더 구조 (24개 컬럼):
    # 0-10: Era~Match_Score (11개)
    # 11-15: Primary_Filename~Is_Backup_Pattern (5개) - Is_Backup_Pattern = col 15
    # 16-18: Backup_Filename~Backup_Size_GB (3개)
    # 19: Match_Strategy
    # 20: Group_ID
    # 21-25: No_NAS, Clip_Only, Need_Rule, Manual_Check, Duplicate_ZX
    checkbox_cols = [15, 21, 22, 23, 24, 25]  # Is_Backup_Pattern, No_NAS~Duplicate_ZX
    apply_checkboxes(sheets, sheet_name, checkbox_cols, len(rows))

    # Apply conditional formatting
    apply_conditional_formatting(sheets, sheet_name, len(rows), len(headers))

    print(f'\n{"=" * 60}')
    print(f'[OK] Export complete: {sheet_name}')
    print(f'URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit')
    print('=' * 60)

    db.close()


if __name__ == '__main__':
    main()
