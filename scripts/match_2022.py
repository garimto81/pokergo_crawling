"""2022 NAS Matching Script.

Matches and exports 2022 NAS files:
- WSOP 2022 Main Event: 11 files (Day-based)
- WSOP 2022 Bracelet Events: 20 files (Final Tables)
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
    """Normalized NAS file element for 2022."""
    file_id: int
    full_path: str
    filename: str
    content_type: str     # WSOP_ME, WSOP_BR
    region: str           # LV (default for 2022)
    event_type: str       # ME, BR
    event_num: int | None
    event_name: str
    day: str              # Day info (1D, 2ABC, 3, etc.)
    day_display: str      # Display format (Day 1D, Day 2ABC, etc.)
    part: int | None
    size_bytes: int
    role: str = 'PRIMARY'


# =============================================================================
# Extractors (2022-specific)
# =============================================================================

def extract_content_type(filename: str) -> str:
    """Determine content type from filename."""
    fn_upper = filename.upper()
    if 'MAIN EVENT' in fn_upper or 'EVENT #70' in fn_upper:
        return 'WSOP_ME'
    elif 'EVENT #' in fn_upper:
        return 'WSOP_BR'
    return 'OTHER'


def extract_event_num(filename: str) -> int | None:
    """Extract event number from filename."""
    match = re.search(r'Event #(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def extract_event_name(filename: str) -> str:
    """Extract event name from filename.

    Handles:
    - Standard events: Event #XX - $XXK EventName Final Table
    - No buy-in events: Event #89 - WSOP Tournament of Champions Final Table
    """
    # $ amount is optional to handle events like Tournament of Champions
    match = re.search(r'Event #\d+\s*-\s*((?:\$[\d,.]+[KM]?\s+)?.+?)(?:\s+Final Table|\.mp4|\.mov|$)', filename, re.I)
    if match:
        name = match.group(1).strip()
        return name
    return ''


def extract_day_info(filename: str) -> tuple[str, str]:
    """Extract day info from filename.

    Returns: (day_raw, day_display)
    Examples:
    - "Day 1D" -> ("1D", "Day 1D")
    - "Day 2ABC" -> ("2ABC", "Day 2ABC")
    - "Day 3" -> ("3", "Day 3")
    - "Final Table Day 1" -> ("FT1", "Final Table Day 1")
    - "Final Table" -> ("FT", "Final Table")
    """
    # Final Table Day X (must check first)
    match = re.search(r'Final Table Day\s*(\d+)', filename, re.I)
    if match:
        day_num = match.group(1)
        return (f'FT{day_num}', f'Final Table Day {day_num}')

    # Standalone "Final Table" without Day number
    if re.search(r'Final Table', filename, re.I):
        return ('FT', 'Final Table')

    # Day N[suffix] - e.g., Day 1D, Day 2ABC, Day 3
    match = re.search(r'Day\s*(\d+)([A-Z]*)', filename, re.I)
    if match:
        day_num = match.group(1)
        suffix = match.group(2).upper() if match.group(2) else ''
        day_raw = f'{day_num}{suffix}'
        day_display = f'Day {day_raw}'
        return (day_raw, day_display)

    return ('', '')


def extract_part(filename: str) -> int | None:
    """Extract part number from filename."""
    match = re.search(r'Part\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


# =============================================================================
# Entry Key Generation
# =============================================================================

def generate_entry_key(elem: NasElement) -> str:
    """Generate entry key for 2022 NAS file."""
    parts = []

    if elem.content_type == 'WSOP_ME':
        parts.append('WSOP_2022_ME')
        if elem.day:
            parts.append(f'D{elem.day}')
        if elem.part:
            parts.append(f'P{elem.part}')

    elif elem.content_type == 'WSOP_BR':
        parts.append('WSOP_2022_BR')
        if elem.event_num:
            parts.append(f'E{elem.event_num}')

    else:
        parts.append('WSOP_2022_OTHER')
        parts.append(elem.filename[:20])

    return '_'.join(parts)


# =============================================================================
# Category and Title Generation
# =============================================================================

def generate_category(elem: NasElement) -> str:
    """Generate category name."""
    if elem.content_type == 'WSOP_ME':
        return 'WSOP 2022 Main Event'
    elif elem.content_type == 'WSOP_BR':
        return 'WSOP 2022 Bracelet Events'
    return 'WSOP 2022 Other'


def generate_title(elem: NasElement) -> str:
    """Generate display title from NAS element."""
    if elem.content_type == 'WSOP_ME':
        title = 'Main Event'
        if elem.day_display:
            title += f' {elem.day_display}'
        if elem.part:
            title += f' Part {elem.part}'
        return title

    elif elem.content_type == 'WSOP_BR':
        if elem.event_num and elem.event_name:
            title = f'Event #{elem.event_num} {elem.event_name}'
        elif elem.event_num:
            title = f'Event #{elem.event_num}'
        else:
            title = elem.filename[:40]
        # Add Final Table if day is FT
        if elem.day == 'FT':
            title += ' Final Table'
        return title

    return elem.filename[:50]


# =============================================================================
# Data Loading
# =============================================================================

def load_nas_files(db) -> list[NasElement]:
    """Load 2022 NAS files from database."""
    files = db.query(NasFile).filter(
        NasFile.year == 2022,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    elements = []
    for f in files:
        content_type = extract_content_type(f.filename)
        event_num = extract_event_num(f.filename)
        event_name = extract_event_name(f.filename)
        day_raw, day_display = extract_day_info(f.filename)
        part = extract_part(f.filename)

        # Determine event_type
        if content_type == 'WSOP_ME':
            event_type = 'ME'
        elif content_type == 'WSOP_BR':
            event_type = 'BR'
        else:
            event_type = 'OTHER'

        elements.append(NasElement(
            file_id=f.id,
            full_path=f.full_path or '',
            filename=f.filename,
            content_type=content_type,
            region='LV',  # All 2022 is Las Vegas
            event_type=event_type,
            event_num=event_num,
            event_name=event_name,
            day=day_raw,
            day_display=day_display,
            part=part,
            size_bytes=f.size_bytes or 0,
            role='PRIMARY'  # All 2022 files are PRIMARY (no duplicates)
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
    """Export 2022 results to Google Sheets."""
    sheets = get_sheets_service()

    # 2022_Catalog - Same structure as 2023/2024/2025
    print('\n[Export] 2022_Catalog')
    headers = [
        'No', 'Entry Key', 'Match Type', 'Role', 'Backup Type',
        'Category', 'Title', 'PokerGO Title',
        'Region', 'Event Type', 'Event #', 'Day', 'Part', 'RAW',
        'Size (GB)', 'Filename', 'Full Path'
    ]
    rows = [headers]

    # Sort: Main Event first (by day), then Bracelet Events (by event #)
    def sort_key(x):
        type_order = {'WSOP_ME': 0, 'WSOP_BR': 1, 'OTHER': 2}
        # For ME, sort by day numerically (extract first digit)
        day_num = 0
        if x.day:
            match = re.match(r'(\d+)', x.day)
            if match:
                day_num = int(match.group(1))
            elif x.day.startswith('FT'):
                day_num = 100 + int(x.day[2:]) if len(x.day) > 2 else 100
        return (type_order.get(x.content_type, 9), day_num, x.event_num or 999, x.part or 0)

    for idx, elem in enumerate(sorted(elements, key=sort_key), 1):
        entry_key = generate_entry_key(elem)
        category = generate_category(elem)
        title = generate_title(elem)
        size_gb = elem.size_bytes / (1024**3)

        rows.append([
            idx,
            entry_key,
            'NAS_ONLY',      # Match Type
            elem.role,       # Role (all PRIMARY for 2022)
            '-',             # Backup Type (none for 2022)
            category,
            title,
            '',              # PokerGO Title
            elem.region,
            elem.event_type,
            elem.event_num or '',
            elem.day_display or '',
            elem.part or '',
            '',              # RAW
            f'{size_gb:.2f}',
            elem.filename,
            elem.full_path
        ])

    write_sheet(sheets, '2022_Catalog', rows)

    # Print summary
    print('\n  Summary:')
    summary = defaultdict(lambda: {'total': 0, 'size': 0})
    for elem in elements:
        key = elem.content_type
        summary[key]['total'] += 1
        summary[key]['size'] += elem.size_bytes

    for content_type in ['WSOP_ME', 'WSOP_BR', 'OTHER']:
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
    print('2022 NAS Matching')
    print('=' * 70)

    # Step 1: Load data
    print('\n[Step 1] Loading 2022 NAS files...')
    db = next(get_db())
    elements = load_nas_files(db)
    print(f'  Total files: {len(elements)}')

    # Step 2: Analysis
    print('\n[Step 2] File Analysis:')
    type_counts = defaultdict(int)
    for elem in elements:
        type_counts[elem.content_type] += 1

    print('\n  By Content Type:')
    for ct in ['WSOP_ME', 'WSOP_BR', 'OTHER']:
        if ct in type_counts:
            print(f'    {ct:10s}: {type_counts[ct]:3d}')

    # Step 3: Export
    print('\n[Step 3] Exporting to Google Sheets...')
    export_to_sheets(elements)

    print('\n' + '=' * 70)
    print('[OK] 2022 Matching completed!')
    print(f'URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit')
    print('=' * 70)


if __name__ == '__main__':
    main()
