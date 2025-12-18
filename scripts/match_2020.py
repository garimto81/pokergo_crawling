"""2020 NAS Matching Script.

Matches and exports 2020 NAS files:
- WSOP 2020 Main Event: 4 episodes (Online due to COVID-19)

Note: 2020 files are under 1GB but included as exception.
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


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class NasElement:
    """Normalized NAS file element for 2020."""
    file_id: int
    full_path: str
    filename: str
    content_type: str     # WSOP_ME
    region: str           # LV
    event_type: str       # ME
    episode_num: int | None
    size_bytes: int
    role: str = 'PRIMARY'


# =============================================================================
# Extractors (2020-specific)
# =============================================================================

def extract_episode_num(filename: str) -> int | None:
    """Extract episode number from filename.

    Pattern: WSOP 2020 Main Event _ Episode X.mp4
    """
    match = re.search(r'Episode\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


# =============================================================================
# Entry Key Generation
# =============================================================================

def generate_entry_key(elem: NasElement) -> str:
    """Generate entry key for 2020 NAS file."""
    parts = ['WSOP_2020_ME']
    if elem.episode_num:
        parts.append(f'EP{elem.episode_num}')
    return '_'.join(parts)


# =============================================================================
# Category and Title Generation
# =============================================================================

def generate_category(elem: NasElement) -> str:
    """Generate category name."""
    return 'WSOP 2020 Main Event (Online)'


def generate_title(elem: NasElement) -> str:
    """Generate display title from NAS element."""
    if elem.episode_num:
        return f'Main Event Episode {elem.episode_num}'
    return 'Main Event'


# =============================================================================
# Data Loading
# =============================================================================

def load_nas_files(db) -> list[NasElement]:
    """Load 2020 NAS files from database."""
    files = db.query(NasFile).filter(
        NasFile.year == 2020,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    elements = []
    for f in files:
        episode_num = extract_episode_num(f.filename)

        elements.append(NasElement(
            file_id=f.id,
            full_path=f.full_path or '',
            filename=f.filename,
            content_type='WSOP_ME',
            region='LV',
            event_type='ME',
            episode_num=episode_num,
            size_bytes=f.size_bytes or 0,
            role='PRIMARY'
        ))

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
    """Export 2020 results to Google Sheets."""
    sheets = get_sheets_service()

    print('\n[Export] 2020_Catalog')
    headers = [
        'No', 'Entry Key', 'Match Type', 'Role', 'Backup Type',
        'Category', 'Title', 'PokerGO Title',
        'Region', 'Event Type', 'Event #', 'Day', 'Part', 'RAW',
        'Size (GB)', 'Filename', 'Full Path'
    ]
    rows = [headers]

    # Sort by episode number
    for idx, elem in enumerate(sorted(elements, key=lambda x: x.episode_num or 0), 1):
        entry_key = generate_entry_key(elem)
        category = generate_category(elem)
        title = generate_title(elem)
        size_gb = elem.size_bytes / (1024**3)

        rows.append([
            idx,
            entry_key,
            'NAS_ONLY',
            elem.role,
            '-',
            category,
            title,
            '',              # PokerGO Title
            elem.region,
            elem.event_type,
            '',              # Event #
            '',              # Day
            '',              # Part
            '',              # RAW
            f'{size_gb:.2f}',
            elem.filename,
            elem.full_path
        ])

    write_sheet(sheets, '2020_Catalog', rows)

    # Print summary
    total_size = sum(e.size_bytes for e in elements) / (1024**3)
    print(f'\n  Summary:')
    print(f'    WSOP_ME: {len(elements)} files ({total_size:.1f} GB)')
    print(f'    Note: Online WSOP due to COVID-19')


# =============================================================================
# Main
# =============================================================================

def main():
    print('=' * 70)
    print('2020 NAS Matching')
    print('=' * 70)

    # Step 1: Load data
    print('\n[Step 1] Loading 2020 NAS files...')
    db = next(get_db())
    elements = load_nas_files(db)
    print(f'  Total files: {len(elements)}')

    if not elements:
        print('\n  No 2020 files found!')
        return

    # Step 2: Analysis
    print('\n[Step 2] File Analysis:')
    print(f'  Main Event Episodes: {len(elements)}')
    for elem in sorted(elements, key=lambda x: x.episode_num or 0):
        size_mb = elem.size_bytes / (1024**2)
        print(f'    Episode {elem.episode_num}: {size_mb:.0f} MB')

    # Step 3: Export
    print('\n[Step 3] Exporting to Google Sheets...')
    export_to_sheets(elements)

    print('\n' + '=' * 70)
    print('[OK] 2020 Matching completed!')
    print(f'URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit')
    print('=' * 70)


if __name__ == '__main__':
    main()
