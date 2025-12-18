"""2023 NAS Matching Script.

Matches and exports 2023 NAS files:
- GOG (Game of Gold): 24 files
- WSOP 2023 Bracelet Events: 36 files
- WSOP 2023 Main Event: 15 files
"""
import sys
import re
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.database import get_db
from src.nams.api.database.models import NasFile
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

GOOGLE_SHEETS_ID = '1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4'
CREDENTIALS_PATH = Path('D:/AI/claude01/json/service_account_key.json')


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class NasElement:
    """Normalized NAS file element for 2023."""
    file_id: int
    full_path: str
    filename: str
    content_type: str     # GOG, WSOP_BR, WSOP_ME
    region: str           # LV (default for 2023)
    event_type: str       # BR, ME, GOG
    event_num: int | None
    event_name: str
    episode_num: int | None
    part: int | None
    size_bytes: int
    role: str = 'PRIMARY'        # PRIMARY or BACKUP
    version_type: str = ''       # 찐최종, 최종, 클린본, or empty


# =============================================================================
# Extractors (2023-specific)
# =============================================================================

def extract_content_type(filename: str, full_path: str) -> str:
    """Determine content type from filename."""
    if 'GOG' in filename.upper() or 'GOG' in full_path.upper():
        return 'GOG'
    elif 'Main Event' in filename:
        return 'WSOP_ME'
    elif 'Bracelet' in filename:
        return 'WSOP_BR'
    return 'OTHER'


def extract_event_num(filename: str) -> int | None:
    """Extract event number from filename."""
    # Pattern: Event #XX
    match = re.search(r'Event\s*#(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def extract_event_name(filename: str) -> str:
    """Extract event name from filename."""
    # Pattern 1: Event #XX $XXK EventName (Part X)
    match = re.search(r'Event\s*#\d+[-\s]+(\$[\d.]+K?\s+[^(]+?)(?:\s*\(Part|\s*\.mp4|$)', filename, re.I)
    if match:
        return match.group(1).strip()

    # Pattern 2: Event #XX EventName (Part X) - without $ (e.g., Tournament of Champions)
    match = re.search(r'Event\s*#\d+[-\s]+([A-Za-z][^(]+?)(?:\s*\(Part|\s*\.mp4|$)', filename, re.I)
    if match:
        name = match.group(1).strip()
        # Don't capture partial words
        if name and not name.endswith('-'):
            return name

    return ''


def extract_episode_num(filename: str) -> int | None:
    """Extract episode number."""
    # GOG: E01, E02, etc.
    match = re.search(r'^E(\d+)_GOG', filename, re.I)
    if match:
        return int(match.group(1))

    # WSOP Main Event: Episode X
    match = re.search(r'Episode\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))

    return None


def extract_part(filename: str) -> int | None:
    """Extract part number."""
    match = re.search(r'\(Part\s*(\d+)\)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def extract_gog_version_type(filename: str) -> tuple[str, int]:
    """Extract GOG version type and priority.

    Priority (higher = better):
    - 찐최종: 3 (highest)
    - 최종: 2
    - 클린본: 1
    - 기타: 0 (lowest)
    """
    if '찐최종' in filename:
        return ('찐최종', 3)
    elif '최종' in filename and '찐최종' not in filename:
        return ('최종', 2)
    elif '클린본' in filename:
        return ('클린본', 1)
    return ('', 0)


# =============================================================================
# Entry Key Generation
# =============================================================================

def generate_entry_key(elem: NasElement) -> str:
    """Generate entry key for 2023 NAS file."""
    parts = []

    if elem.content_type == 'GOG':
        parts.append('GOG_2023')
        if elem.episode_num:
            parts.append(f'EP{elem.episode_num:02d}')

    elif elem.content_type == 'WSOP_ME':
        parts.append('WSOP_2023_ME')
        if elem.episode_num:
            parts.append(f'EP{elem.episode_num}')

    elif elem.content_type == 'WSOP_BR':
        parts.append('WSOP_2023_BR')
        if elem.event_num:
            parts.append(f'E{elem.event_num}')
        if elem.part:
            parts.append(f'P{elem.part}')

    else:
        parts.append('WSOP_2023_OTHER')
        parts.append(elem.filename[:20])

    return '_'.join(parts)


# =============================================================================
# Category and Title Generation
# =============================================================================

def generate_category(elem: NasElement) -> str:
    """Generate category name."""
    if elem.content_type == 'GOG':
        return 'Game of Gold 2023'
    elif elem.content_type == 'WSOP_ME':
        return 'WSOP 2023 Main Event'
    elif elem.content_type == 'WSOP_BR':
        return 'WSOP 2023 Bracelet Events'
    return 'WSOP 2023 Other'


def generate_title(elem: NasElement) -> str:
    """Generate display title from NAS element."""
    if elem.content_type == 'GOG':
        if elem.episode_num:
            return f'Episode {elem.episode_num}'
        return elem.filename[:40]

    elif elem.content_type == 'WSOP_ME':
        if elem.episode_num:
            return f'Main Event Episode {elem.episode_num}'
        return 'Main Event'

    elif elem.content_type == 'WSOP_BR':
        if elem.event_num and elem.event_name:
            title = f'Event #{elem.event_num} {elem.event_name}'
        elif elem.event_num:
            title = f'Event #{elem.event_num}'
        else:
            title = elem.filename[:40]

        if elem.part:
            title += f' Part {elem.part}'
        return title

    return elem.filename[:50]


# =============================================================================
# Data Loading
# =============================================================================

def load_nas_files(db) -> list[NasElement]:
    """Load 2023 NAS files from database."""
    files = db.query(NasFile).filter(
        NasFile.year == 2023,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    elements = []
    for f in files:
        content_type = extract_content_type(f.filename, f.full_path)
        event_num = extract_event_num(f.filename)
        event_name = extract_event_name(f.filename)
        episode_num = extract_episode_num(f.filename)
        part = extract_part(f.filename)

        # Determine event_type
        if content_type == 'GOG':
            event_type = 'GOG'
        elif content_type == 'WSOP_ME':
            event_type = 'ME'
        elif content_type == 'WSOP_BR':
            event_type = 'BR'
        else:
            event_type = 'OTHER'

        # Extract GOG version type
        version_type, _ = extract_gog_version_type(f.filename) if content_type == 'GOG' else ('', 0)

        elements.append(NasElement(
            file_id=f.id,
            full_path=f.full_path or '',
            filename=f.filename,
            content_type=content_type,
            region='LV',  # All 2023 is Las Vegas
            event_type=event_type,
            event_num=event_num,
            event_name=event_name,
            episode_num=episode_num,
            part=part,
            size_bytes=f.size_bytes or 0,
            role='PRIMARY',  # Will be updated for GOG
            version_type=version_type
        ))

    # Assign GOG roles based on version priority
    # Group GOG files by episode
    gog_by_episode = defaultdict(list)
    for elem in elements:
        if elem.content_type == 'GOG' and elem.episode_num:
            gog_by_episode[elem.episode_num].append(elem)

    # For each episode, find highest priority and assign roles
    for episode_num, ep_files in gog_by_episode.items():
        # Get priority for each file
        priorities = [(elem, extract_gog_version_type(elem.filename)[1]) for elem in ep_files]
        # Sort by priority descending
        priorities.sort(key=lambda x: x[1], reverse=True)

        # Highest priority file is PRIMARY, rest are BACKUP
        for i, (elem, priority) in enumerate(priorities):
            if i == 0:
                elem.role = 'PRIMARY'
            else:
                elem.role = 'BACKUP'

    return elements


# =============================================================================
# Google Sheets Export
# =============================================================================

def get_sheets_service():
    """Get Google Sheets API service."""
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
    """Write data to sheet."""
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


def export_to_sheets(elements: list[NasElement]):
    """Export 2023 results to Google Sheets."""
    sheets = get_sheets_service()

    # 2023_Catalog - Same structure as 2024/2025
    print('\n[Export] 2023_Catalog')
    headers = [
        'No', 'Entry Key', 'Match Type', 'Role', 'Backup Type',
        'Category', 'Title', 'PokerGO Title',
        'Region', 'Event Type', 'Event #', 'Day', 'Part', 'RAW',
        'Size (GB)', 'Filename', 'Full Path'
    ]
    rows = [headers]

    # Sort: GOG first, then WSOP ME, then WSOP BR
    def sort_key(x):
        type_order = {'GOG': 0, 'WSOP_ME': 1, 'WSOP_BR': 2, 'OTHER': 3}
        return (type_order.get(x.content_type, 9), x.episode_num or 999, x.event_num or 999, x.part or 0)

    for idx, elem in enumerate(sorted(elements, key=sort_key), 1):
        entry_key = generate_entry_key(elem)
        category = generate_category(elem)
        title = generate_title(elem)
        size_gb = elem.size_bytes / (1024**3)

        # Day column: empty for 2023 (no day-based events)
        # Episode info is in title for GOG/ME
        rows.append([
            idx,
            entry_key,
            'NAS_ONLY',      # Match Type
            elem.role,       # Role (PRIMARY or BACKUP for GOG)
            elem.version_type or '-',  # Backup Type (version type for GOG)
            category,
            title,
            '',              # PokerGO Title
            elem.region,
            elem.event_type,
            elem.event_num or '',
            '',              # Day (empty for 2023)
            elem.part or '',
            '',              # RAW
            f'{size_gb:.2f}',
            elem.filename,
            elem.full_path
        ])

    write_sheet(sheets, '2023_Catalog', rows)

    # Print summary
    print('\n  Summary:')
    summary = defaultdict(lambda: {'total': 0, 'size': 0})
    for elem in elements:
        key = elem.content_type
        summary[key]['total'] += 1
        summary[key]['size'] += elem.size_bytes

    for content_type in ['GOG', 'WSOP_ME', 'WSOP_BR', 'OTHER']:
        if content_type in summary:
            s = summary[content_type]
            size_gb = s['size'] / (1024**3)
            print(f'    {content_type}: {s["total"]} files ({size_gb:.1f} GB)')

    total_size = sum(e.size_bytes for e in elements) / (1024**3)
    print(f'    Total: {len(elements)} files ({total_size:.1f} GB)')


# =============================================================================
# Main
# =============================================================================

def main():
    print('=' * 70)
    print('2023 NAS Matching')
    print('=' * 70)

    # Step 1: Load data
    print('\n[Step 1] Loading 2023 NAS files...')
    db = next(get_db())
    elements = load_nas_files(db)
    print(f'  Total files: {len(elements)}')

    # Step 2: Analysis
    print('\n[Step 2] File Analysis:')
    type_counts = defaultdict(int)
    for elem in elements:
        type_counts[elem.content_type] += 1

    print('\n  By Content Type:')
    for ct in ['GOG', 'WSOP_ME', 'WSOP_BR', 'OTHER']:
        if ct in type_counts:
            print(f'    {ct:10s}: {type_counts[ct]:3d}')

    # Step 3: Export
    print('\n[Step 3] Exporting to Google Sheets...')
    export_to_sheets(elements)

    print('\n' + '=' * 70)
    print('[OK] 2023 Matching completed!')
    print(f'URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit')
    print('=' * 70)


if __name__ == '__main__':
    main()
