"""2024 NAS Matching Script.

Matches and exports 2024 NAS files based on MATCHING_STRATEGY_2024.md.
Note: 2024 data is mostly clips - Episode count is ~33 vs 424 clips.
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
    """Normalized NAS file element for 2024."""
    file_id: int
    full_path: str
    filename: str
    region: str           # LV, EU, PARADISE, CIRCUIT, OTHER
    event_type: str       # BR, ME, OTHER
    event_num: int | None
    event_name: str
    day: str
    part: int | None
    size_bytes: int
    is_clip: bool         # Hand clip or vs clip
    file_type: str        # EPISODE or CLIP
    buy_in: str           # 5k, 25k (LV specific)
    game_type: str        # NLH, PLO, 2-7TD
    episode_num: int | None  # WE24-ME-XX, WCLA24-XX


# =============================================================================
# Extractors (2024-specific)
# =============================================================================

def extract_region(full_path: str) -> str:
    """Extract region from full path."""
    if not full_path:
        return 'OTHER'
    p = full_path.upper()
    if 'WSOP-LAS VEGAS' in p:
        return 'LV'
    elif 'WSOP-EUROPE' in p:
        return 'EU'
    elif 'WSOP-PARADISE' in p:
        return 'PARADISE'
    elif 'CIRCUIT' in p:
        return 'CIRCUIT'
    # X: drive WSOP 2024 = Las Vegas Bracelet Events
    elif 'POKERGO' in p and 'WSOP 2024' in p:
        return 'LV'
    return 'OTHER'


def extract_event_num(text: str) -> int | None:
    """Extract event number from text (2024 patterns)."""
    # Pattern 1: Event #N (standard)
    match = re.search(r'Event\s*#(\d+)', text, re.I)
    if match:
        return int(match.group(1))
    # Pattern 2: ev-NN (LV 2024 style)
    match = re.search(r'-ev-(\d+)', text, re.I)
    if match:
        return int(match.group(1))
    # Pattern 3: BRACELET EVENT #N
    match = re.search(r'BRACELET\s+EVENT\s*#(\d+)', text, re.I)
    if match:
        return int(match.group(1))
    # Pattern 4: [BRACELET EVENT #N]
    match = re.search(r'\[BRACELET(?:\s+EVENT)?\s*#(\d+)\]', text, re.I)
    if match:
        return int(match.group(1))
    return None


def extract_event_type(full_path: str, filename: str, region: str = '') -> str:
    """Extract event type (BR, ME, OTHER) - 2024 patterns."""
    p = (full_path or '').upper()
    f = filename.upper()

    # PARADISE: Super Main Event
    if region == 'PARADISE':
        if 'SUPER MAIN EVENT' in p or 'SUPER MAIN EVENT' in f:
            return 'ME'
        return 'OTHER'

    # CIRCUIT: Main Event or other
    if region == 'CIRCUIT' or 'CIRCUIT' in p:
        if 'MAIN EVENT' in f or 'MAIN EVENT' in p:
            return 'ME'
        return 'BR'

    # EU: Main Event (Event #13) or Bracelet Event
    if region == 'EU':
        # #13 is WSOPE Main Event
        if 'MAIN EVENT' in f or '#WSOPE 2024 NLH MAIN EVENT' in f:
            return 'ME'
        if 'EVENT #13' in f or 'BRACELET EVENT #13' in f:
            return 'ME'
        return 'BR'

    # LV: Check Main Event first (higher priority)
    if 'MAIN EVENT' in f and 'BRACELET' not in f:
        return 'ME'

    # LV: -be- indicates Bracelet Event
    if '-be-' in f.lower():
        return 'BR'
    if 'BRACELET' in p or 'BRACELET' in f:
        return 'BR'

    # LV region default to BR (most 2024 files are Bracelet Events)
    if region == 'LV':
        return 'BR'

    return 'OTHER'


def extract_day(filename: str) -> str:
    """Extract day information (2024 patterns)."""
    # -ft- pattern (LV Final Table)
    if '-ft-' in filename.lower():
        return 'FT'

    # Day NA-B-C pattern (e.g., Day 2A-B-C)
    match = re.search(r'Day\s*(\d+)([A-D])-([A-D])-([A-D])', filename, re.I)
    if match:
        return f'{match.group(1)}{match.group(2)}{match.group(3)}{match.group(4)}'

    # Day N[A-D] (standard) - A-D suffix must be followed by space, underscore, or end
    # to avoid matching "B" from "BRACELET" in "DAY 2   BRACELET"
    match = re.search(r'Day\s*(\d+)([A-D])?(?=\s|_|$|\.)', filename, re.I)
    if match:
        return f'{match.group(1)}{match.group(2) or ""}'

    # [Day N[A-D]] (CIRCUIT bracket style)
    match = re.search(r'\[Day\s*(\d+)\s*([A-D])?\]', filename, re.I)
    if match:
        return f'{match.group(1)}{match.group(2) or ""}'

    # dayNN (LV lowercase: -day02-)
    match = re.search(r'-day(\d+)', filename, re.I)
    if match:
        return match.group(1)

    return ''


def extract_episode_num(filename: str) -> int | None:
    """Extract episode number (2024-specific).

    Patterns:
    - WE24-ME-XX (EU Main Event episodes)
    - WCLA24-XX (CIRCUIT LA episodes)
    - Episode N (LV Main Event episodes)
    """
    # WE24-ME-NN
    match = re.search(r'WE24-ME-(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    # WCLA24-NN
    match = re.search(r'WCLA24-(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    # Episode N (LV Main Event)
    match = re.search(r'Episode\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def extract_buy_in(filename: str) -> str:
    """Extract buy-in from filename (LV 2024)."""
    # Pattern 1: -5k-, -25k- (clip style)
    match = re.search(r'(\d+k)-', filename, re.I)
    if match:
        return match.group(1).lower()
    # Pattern 2: $5K, $25K (X: drive style)
    match = re.search(r'\$(\d+(?:\.\d+)?K)', filename, re.I)
    if match:
        return match.group(1).lower()
    return ''


def extract_game_type(filename: str) -> str:
    """Extract game type from filename."""
    f = filename.upper()
    if 'NLH' in f or 'NLHE' in f or '-NL-' in f.upper():
        return 'NLH'
    if 'PLO' in f:
        return 'PLO'
    if '2-7TD' in f or '27TD' in f:
        return '2-7TD'
    if 'HORSE' in f:
        return 'HORSE'
    return ''


def is_hand_clip(filename: str) -> bool:
    """Check if file is a hand clip (excluded from service)."""
    # Hand_XX pattern
    if re.search(r'Hand_\d+', filename, re.I):
        return True
    # vs pattern (player matchup clips)
    if re.search(r'\w+\s+vs\s+\w+', filename, re.I):
        return True
    # hero- clips
    if 'hero-' in filename.lower():
        return True
    return False


def extract_part(filename: str) -> int | None:
    """Extract part number from filename."""
    # Pattern 1: (Part 1), (Part 2)
    match = re.search(r'\(Part\s*(\d+)\)', filename, re.I)
    if match:
        return int(match.group(1))
    # Pattern 2: Part 1, Part 2
    match = re.search(r'Part\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def extract_event_name(filename: str, full_path: str) -> str:
    """Extract event name from filename or path."""
    f = filename.upper()

    # X: drive style: Event #1 $5K Champions Reunion (Part 1)
    match = re.search(r'Event\s*#\d+\s+(\$[\d.]+K\s+.+?)(?:\s*\(Part|\s*\.mp4|$)', filename, re.I)
    if match:
        return match.group(1).strip()

    # LV clip style: -5k-champions-reunion-
    match = re.search(r'-(\d+k)-([a-z-]+)-', filename, re.I)
    if match:
        buy_in = match.group(1)
        name_part = match.group(2).replace('-', ' ').title()
        return f'${buy_in.upper()} {name_part}'

    # EU: Extract specific event names
    if '50K DIAMOND HIGH ROLLER' in f or 'DIAMOND HIGH ROLLER' in f:
        return '€50K Diamond High Roller'
    if 'NLH MAIN EVENT' in f or 'NLH_MAIN EVENT' in f:
        return 'NLH Main Event'
    if 'MAIN EVENT' in f and 'NLH' not in f:
        return 'Main Event'

    # PARADISE: Super Main Event
    if 'SUPER MAIN EVENT' in f:
        return 'Super Main Event'

    # CIRCUIT: Extract event name
    match = re.search(r'Circuit[^-]+-\s*([^[\]]+?)(?:\s*\[|$)', filename, re.I)
    if match:
        return match.group(1).strip()

    return ''


# =============================================================================
# Entry Key Generation
# =============================================================================

def generate_entry_key(elem: NasElement) -> str:
    """Generate entry key for 2024 NAS file."""
    parts = []

    if elem.region == 'LV':
        if elem.event_type == 'ME':
            parts.append('WSOP_2024_ME')
            if elem.day:
                parts.append(f'D{elem.day}')
            if elem.part:
                parts.append(f'P{elem.part}')
            if elem.episode_num:
                parts.append(f'EP{elem.episode_num}')
        else:
            parts.append('WSOP_2024_BR')
            if elem.event_num:
                parts.append(f'E{elem.event_num}')
            if elem.day:
                parts.append(f'D{elem.day}')
            if elem.part:
                parts.append(f'P{elem.part}')

    elif elem.region == 'EU':
        parts.append('WSOP_2024_EU')
        if elem.event_type == 'ME':
            parts.append('ME')
            if elem.episode_num:
                parts.append(f'EP{elem.episode_num:02d}')
            elif elem.day:
                parts.append(f'D{elem.day}')
        else:
            parts.append('BR')
            if elem.event_num:
                parts.append(f'E{elem.event_num}')
            if elem.day:
                parts.append(f'D{elem.day}')

    elif elem.region == 'PARADISE':
        parts.append('PARADISE_2024_SME')
        if elem.day:
            parts.append(f'D{elem.day}')

    elif elem.region == 'CIRCUIT':
        parts.append('CIRCUIT_2024_LA')
        if elem.event_type == 'ME':
            parts.append('ME')
            if elem.episode_num:
                parts.append(f'EP{elem.episode_num:02d}')
            elif elem.day:
                parts.append(f'D{elem.day}')
        else:
            parts.append('BR')
            if elem.day:
                parts.append(f'D{elem.day}')

    else:
        parts.append('WSOP_2024_OTHER')
        parts.append(elem.filename[:20])

    return '_'.join(parts)


# =============================================================================
# Category and Title Generation
# =============================================================================

def generate_category(region: str, event_type: str, event_num: int | None = None) -> str:
    """Generate category name."""
    if region == 'LV':
        if event_type == 'ME':
            return 'WSOP 2024 Main Event'
        return 'WSOP 2024 Bracelet Events'
    elif region == 'EU':
        if event_type == 'ME':
            return 'WSOP Europe 2024 - Main Event'
        return 'WSOP Europe 2024 - Bracelet Events'
    elif region == 'PARADISE':
        return 'WSOP Paradise 2024 - Super Main Event'
    elif region == 'CIRCUIT':
        return 'WSOP Circuit 2024 - LA'
    return 'WSOP 2024 Other'


def normalize_day_display(day: str) -> str:
    """Normalize day for display."""
    if not day:
        return ''
    if day == 'FT':
        return 'Final Table'
    if day[0].isdigit():
        return f'Day {day}'
    return day


def generate_title(elem: NasElement) -> str:
    """Generate display title from NAS element."""
    day_display = normalize_day_display(elem.day)

    if elem.region == 'LV':
        if elem.event_type == 'ME':
            # Main Event
            title = 'Main Event'
            if elem.episode_num:
                title += f' Episode {elem.episode_num}'
            elif day_display:
                title += f' {day_display}'
            if elem.part:
                title += f' Part {elem.part}'
        elif elem.event_num:
            # Bracelet Event with event number
            title = f'Event #{elem.event_num}'
            if elem.event_name:
                title += f' {elem.event_name}'
            elif elem.buy_in:
                title += f' ${elem.buy_in.upper()}'
                if elem.game_type:
                    title += f' {elem.game_type}'
            if day_display:
                title += f' | {day_display}'
            if elem.part:
                title += f' Part {elem.part}'
        else:
            # No event number - use specific event name (never generic "Bracelet Event")
            if elem.event_name:
                title = elem.event_name
            else:
                # Fallback to filename prefix
                title = elem.filename[:40].replace('.mp4', '').replace('.mov', '')
            if day_display:
                title += f' | {day_display}'
            if elem.part:
                title += f' Part {elem.part}'
        if elem.is_clip:
            title += ' [Clip]'
        return title

    elif elem.region == 'EU':
        if elem.event_type == 'ME':
            title = 'Main Event'
            if elem.episode_num:
                title += f' Ep.{elem.episode_num}'
            elif day_display:
                title += f' {day_display}'
        else:
            # Event number + event name OR specific event name (never generic "Bracelet Event")
            if elem.event_num and elem.event_name:
                title = f'Event #{elem.event_num} {elem.event_name}'
            elif elem.event_num:
                title = f'Event #{elem.event_num}'
            elif elem.event_name:
                title = elem.event_name
            else:
                # Fallback to filename prefix
                title = elem.filename[:40].replace('.mp4', '').replace('.mov', '')
            if day_display:
                title += f' | {day_display}'
        return title

    elif elem.region == 'PARADISE':
        title = 'Super Main Event'
        if day_display:
            title += f' {day_display}'
        if elem.is_clip:
            title += ' [Clip]'
        return title

    elif elem.region == 'CIRCUIT':
        if elem.event_type == 'ME':
            title = 'Main Event'
            if elem.episode_num:
                title += f' Ep.{elem.episode_num}'
            elif day_display:
                title += f' {day_display}'
        else:
            title = elem.event_name or 'Side Event'
            if day_display:
                title += f' | {day_display}'
        return title

    return elem.filename[:50]


# =============================================================================
# Data Loading
# =============================================================================

def load_nas_files(db) -> list[NasElement]:
    """Load 2024 NAS files from database."""
    files = db.query(NasFile).filter(
        NasFile.year == 2024,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    elements = []
    for f in files:
        region = extract_region(f.full_path)
        event_num = extract_event_num((f.full_path or '') + ' ' + f.filename)
        event_type = extract_event_type(f.full_path, f.filename, region)
        event_name = extract_event_name(f.filename, f.full_path)
        day = extract_day(f.filename)
        episode_num = extract_episode_num(f.filename)
        buy_in = extract_buy_in(f.filename)
        game_type = extract_game_type(f.filename)
        part = extract_part(f.filename)
        clip = is_hand_clip(f.filename)
        file_type = 'CLIP' if clip else 'EPISODE'

        # PARADISE: Check Day extraction from path
        if region == 'PARADISE' and not day:
            match = re.search(r'Day\s*(\d+)\s*([A-D])?', f.full_path or '', re.I)
            if match:
                day = f'{match.group(1)}{match.group(2) or ""}'

        elements.append(NasElement(
            file_id=f.id,
            full_path=f.full_path or '',
            filename=f.filename,
            region=region,
            event_type=event_type,
            event_num=event_num,
            event_name=event_name,
            day=day,
            part=part,
            size_bytes=f.size_bytes or 0,
            is_clip=clip,
            file_type=file_type,
            buy_in=buy_in,
            game_type=game_type,
            episode_num=episode_num
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
    """Export 2024 results to Google Sheets."""
    sheets = get_sheets_service()

    # 2024_Catalog - Full file catalog (same structure as 2025_Catalog)
    print('\n[Export] 2024_Catalog')
    headers = [
        'No', 'Entry Key', 'Match Type', 'Role', 'Backup Type',
        'Category', 'Title', 'PokerGO Title',
        'Region', 'Event Type', 'Event #', 'Day', 'Part', 'RAW',
        'Size (GB)', 'Filename', 'Full Path'
    ]
    rows = [headers]

    for idx, elem in enumerate(sorted(elements, key=lambda x: (x.region, x.event_type, x.day, x.filename)), 1):
        entry_key = generate_entry_key(elem)
        category = generate_category(elem.region, elem.event_type, elem.event_num)
        title = generate_title(elem)
        size_gb = elem.size_bytes / (1024**3)

        rows.append([
            idx,
            entry_key,
            'NAS_ONLY',      # Match Type: No PokerGO matching for 2024
            'PRIMARY',       # Role: All 2024 files are PRIMARY
            '-',             # Backup Type: No backup versions
            category,
            title,
            '',              # PokerGO Title: Empty for 2024
            elem.region,
            elem.event_type,
            elem.event_num or '',
            elem.day,
            elem.part or '',
            '',              # RAW: No HyperDeck files
            f'{size_gb:.2f}',
            elem.filename,
            elem.full_path
        ])

    write_sheet(sheets, '2024_Catalog', rows)

    # Print summary to console
    print('\n  Summary:')
    summary = defaultdict(lambda: {'total': 0, 'size': 0})
    for elem in elements:
        key = (elem.region, elem.event_type)
        summary[key]['total'] += 1
        summary[key]['size'] += elem.size_bytes

    for (region, event_type) in sorted(summary.keys()):
        s = summary[(region, event_type)]
        size_gb = s['size'] / (1024**3)
        print(f'    {region} {event_type}: {s["total"]} files ({size_gb:.1f} GB)')

    total_size = sum(e.size_bytes for e in elements) / (1024**3)
    print(f'    Total: {len(elements)} files ({total_size:.1f} GB)')


# =============================================================================
# Main
# =============================================================================

def main():
    print('=' * 70)
    print('2024 NAS Matching')
    print('=' * 70)

    # Step 1: Load data
    print('\n[Step 1] Loading 2024 NAS files...')
    db = next(get_db())
    elements = load_nas_files(db)
    print(f'  Total files: {len(elements)}')

    # Step 2: Analysis
    print('\n[Step 2] File Analysis:')
    region_counts = defaultdict(int)
    type_counts = {'EPISODE': 0, 'CLIP': 0}

    for elem in elements:
        region_counts[elem.region] += 1
        type_counts[elem.file_type] += 1

    print('\n  By Region:')
    for region in ['LV', 'EU', 'PARADISE', 'CIRCUIT', 'OTHER']:
        if region in region_counts:
            print(f'    {region:10s}: {region_counts[region]:3d}')

    print('\n  By File Type:')
    print(f'    Episodes: {type_counts["EPISODE"]}')
    print(f'    Clips:    {type_counts["CLIP"]}')

    # Step 3: Export
    print('\n[Step 3] Exporting to Google Sheets...')
    export_to_sheets(elements)

    print('\n' + '=' * 70)
    print('[OK] 2024 Matching completed!')
    print(f'URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit')
    print('=' * 70)


if __name__ == '__main__':
    main()
