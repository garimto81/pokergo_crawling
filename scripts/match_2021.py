"""2021 NAS Matching Script.

Matches and exports 2021 NAS files:
- WSOP 2021 Main Event (Event #67): 17 files (Day-based)
- WSOP 2021 Bracelet Events: 25 files
- WSOP Europe 2021: 4 files
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
    """Normalized NAS file element for 2021."""
    file_id: int
    full_path: str
    filename: str
    content_type: str     # WSOP_ME, WSOP_BR, WSOPE
    region: str           # LV or EU
    event_type: str       # ME, BR, HR, etc.
    event_num: int | None
    event_name: str
    day: str              # Day info (1A, 2AB, 3, etc.)
    day_display: str      # Display format (Day 1A, Day 2AB, etc.)
    part: int | None
    size_bytes: int
    role: str = 'PRIMARY'


# =============================================================================
# Extractors (2021-specific)
# =============================================================================

def extract_content_type(filename: str) -> str:
    """Determine content type from filename."""
    fn_lower = filename.lower()

    # WSOP Europe pattern: wsope-2021-*
    if fn_lower.startswith('wsope-'):
        return 'WSOPE'

    fn_upper = filename.upper()
    if 'MAIN EVENT' in fn_upper:
        return 'WSOP_ME'
    elif 'EVENT #' in fn_upper or 'EVENT' in fn_upper:
        return 'WSOP_BR'
    return 'OTHER'


def extract_region(filename: str) -> str:
    """Extract region from filename."""
    if filename.lower().startswith('wsope-'):
        return 'EU'
    return 'LV'


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
    - No buy-in events: Event #79 - $1,979 Poker Hall of Fame Bounty
    """
    # $ amount is optional
    match = re.search(r'Event #\d+\s*-\s*((?:\$[\d,.]+[KM]?\s+)?.+?)(?:\s+Final Table|\.mp4|\.mov|$)', filename, re.I)
    if match:
        name = match.group(1).strip()
        return name
    return ''


def extract_wsope_info(filename: str) -> tuple[str, str]:
    """Extract WSOP Europe event info.

    Pattern: wsope-2021-{buyin}-{event}-ft-{seq}.mp4
    Examples:
    - wsope-2021-10k-me-ft-004.mp4 -> (ME, €10K Main Event)
    - wsope-2021-10k-nlh6max-ft-009.mp4 -> (BR, €10K NLH 6-Max)
    - wsope-2021-1650-nlh6max-ft-010.mp4 -> (BR, €1,650 NLH 6-Max)
    - wsope-2021-25k-platinumhighroller-ft-001.mp4 -> (HR, €25K Platinum High Roller)
    """
    # Handle both "10k" and "1650" formats
    match = re.search(r'wsope-2021-(\d+k?)-([a-z0-9]+)-ft-(\d+)', filename.lower())
    if match:
        buyin_raw = match.group(1)  # 10k, 25k, 1650, etc.
        event = match.group(2)  # me, nlh6max, platinumhighroller, etc.

        # Format buyin
        if buyin_raw.endswith('k'):
            buyin = buyin_raw.upper()  # 10K, 25K
        else:
            # Format number with comma: 1650 -> 1,650
            buyin = f'{int(buyin_raw):,}'

        # Determine event type
        if event == 'me':
            event_type = 'ME'
            event_name = f'€{buyin} Main Event'
        elif 'highroller' in event:
            event_type = 'HR'
            event_name = f'€{buyin} Platinum High Roller'
        else:
            event_type = 'BR'
            # Convert nlh6max -> NLH 6-Max
            event_formatted = event.upper()
            if 'nlh' in event.lower():
                event_formatted = event.replace('nlh', 'NLH ').replace('6max', '6-Max').strip()
            event_name = f'€{buyin} {event_formatted}'

        return (event_type, event_name)

    return ('BR', '')


def extract_day_info(filename: str) -> tuple[str, str]:
    """Extract day info from filename.

    Returns: (day_raw, day_display)
    Examples:
    - "Day 1A" -> ("1A", "Day 1A")
    - "Day 2ABC" -> ("2ABC", "Day 2ABC")
    - "Day 2CE" -> ("2CE", "Day 2CE")
    - "Day 3" -> ("3", "Day 3")
    - "Final Table Day 1" -> ("FT1", "Final Table Day 1")
    - "Final Table" -> ("FT", "Final Table")
    """
    # Check "Final Table Day X" FIRST (before general Day pattern)
    match = re.search(r'Final Table Day\s*(\d+)', filename, re.I)
    if match:
        day_num = match.group(1)
        return (f'FT{day_num}', f'Final Table Day {day_num}')

    # Check for "Final Table" without Day number
    if re.search(r'Final Table', filename, re.I):
        return ('FT', 'Final Table')

    # Day N[suffix] - e.g., Day 1A, Day 2AB, Day 2CE, Day 3
    # Must NOT be preceded by "Final Table"
    match = re.search(r'(?<!Final Table )Day\s*(\d+)([A-Z]*)', filename, re.I)
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
    """Generate entry key for 2021 NAS file."""
    parts = []

    if elem.content_type == 'WSOPE':
        parts.append('WSOPE_2021')
        parts.append(elem.event_type)
        # Add sequence from filename for uniqueness
        match = re.search(r'-(\d+)\.mp4', elem.filename)
        if match:
            parts.append(f'S{match.group(1)}')

    elif elem.content_type == 'WSOP_ME':
        parts.append('WSOP_2021_ME')
        if elem.day:
            parts.append(f'D{elem.day}')
        if elem.part:
            parts.append(f'P{elem.part}')

    elif elem.content_type == 'WSOP_BR':
        parts.append('WSOP_2021_BR')
        if elem.event_num:
            parts.append(f'E{elem.event_num}')

    else:
        parts.append('WSOP_2021_OTHER')
        parts.append(elem.filename[:20])

    return '_'.join(parts)


# =============================================================================
# Category and Title Generation
# =============================================================================

def generate_category(elem: NasElement) -> str:
    """Generate category name."""
    if elem.content_type == 'WSOPE':
        return 'WSOP Europe 2021'
    elif elem.content_type == 'WSOP_ME':
        return 'WSOP 2021 Main Event'
    elif elem.content_type == 'WSOP_BR':
        return 'WSOP 2021 Bracelet Events'
    return 'WSOP 2021 Other'


def generate_title(elem: NasElement) -> str:
    """Generate display title from NAS element."""
    if elem.content_type == 'WSOPE':
        title = elem.event_name if elem.event_name else 'WSOP Europe'
        # Add Final Table if ft is in the filename
        if elem.day == 'FT':
            title += ' Final Table'
        return title

    elif elem.content_type == 'WSOP_ME':
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
    """Load 2021 NAS files from database."""
    files = db.query(NasFile).filter(
        NasFile.year == 2021,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    elements = []
    for f in files:
        content_type = extract_content_type(f.filename)
        region = extract_region(f.filename)

        # WSOP Europe special handling
        if content_type == 'WSOPE':
            event_type, event_name = extract_wsope_info(f.filename)
            event_num = None
            # WSOPE files with "ft" are Final Table recordings
            if '-ft-' in f.filename.lower():
                day_raw, day_display = 'FT', 'Final Table'
            else:
                day_raw, day_display = '', ''
        else:
            event_num = extract_event_num(f.filename)
            event_name = extract_event_name(f.filename)
            day_raw, day_display = extract_day_info(f.filename)

            # Determine event_type
            if content_type == 'WSOP_ME':
                event_type = 'ME'
            elif content_type == 'WSOP_BR':
                event_type = 'BR'
            else:
                event_type = 'OTHER'

        part = extract_part(f.filename)

        elements.append(NasElement(
            file_id=f.id,
            full_path=f.full_path or '',
            filename=f.filename,
            content_type=content_type,
            region=region,
            event_type=event_type,
            event_num=event_num,
            event_name=event_name,
            day=day_raw,
            day_display=day_display,
            part=part,
            size_bytes=f.size_bytes or 0,
            role='PRIMARY'  # All 2021 files are PRIMARY (no duplicates)
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
    """Export 2021 results to Google Sheets."""
    sheets = get_sheets_service()

    # 2021_Catalog - Same structure as other years
    print('\n[Export] 2021_Catalog')
    headers = [
        'No', 'Entry Key', 'Match Type', 'Role', 'Backup Type',
        'Category', 'Title', 'PokerGO Title',
        'Region', 'Event Type', 'Event #', 'Day', 'Part', 'RAW',
        'Size (GB)', 'Filename', 'Full Path'
    ]
    rows = [headers]

    # Sort: WSOP Europe first, then Main Event (by day), then Bracelet Events (by event #)
    def sort_key(x):
        type_order = {'WSOPE': 0, 'WSOP_ME': 1, 'WSOP_BR': 2, 'OTHER': 3}
        # For ME, sort by day numerically (extract first digit)
        day_num = 0
        if x.day:
            match = re.match(r'(\d+)', x.day)
            if match:
                day_num = int(match.group(1))
            elif x.day.startswith('FT'):
                day_num = 100 + int(x.day[2:]) if len(x.day) > 2 and x.day[2:].isdigit() else 100
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
            elem.role,       # Role (all PRIMARY for 2021)
            '-',             # Backup Type (none for 2021)
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

    write_sheet(sheets, '2021_Catalog', rows)

    # Print summary
    print('\n  Summary:')
    summary = defaultdict(lambda: {'total': 0, 'size': 0})
    for elem in elements:
        key = elem.content_type
        summary[key]['total'] += 1
        summary[key]['size'] += elem.size_bytes

    for content_type in ['WSOPE', 'WSOP_ME', 'WSOP_BR', 'OTHER']:
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
    print('2021 NAS Matching')
    print('=' * 70)

    # Step 1: Load data
    print('\n[Step 1] Loading 2021 NAS files...')
    db = next(get_db())
    elements = load_nas_files(db)
    print(f'  Total files: {len(elements)}')

    # Step 2: Analysis
    print('\n[Step 2] File Analysis:')
    type_counts = defaultdict(int)
    for elem in elements:
        type_counts[elem.content_type] += 1

    print('\n  By Content Type:')
    for ct in ['WSOPE', 'WSOP_ME', 'WSOP_BR', 'OTHER']:
        if ct in type_counts:
            print(f'    {ct:10s}: {type_counts[ct]:3d}')

    # Step 3: Export
    print('\n[Step 3] Exporting to Google Sheets...')
    export_to_sheets(elements)

    print('\n' + '=' * 70)
    print('[OK] 2021 Matching completed!')
    print(f'URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit')
    print('=' * 70)


if __name__ == '__main__':
    main()
