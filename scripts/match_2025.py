"""2025 NAS-PokerGO Matching Script.

Matches NAS files with PokerGO data based on MATCHING_STRATEGY_2025.md.
Exports results to Google Sheets.
"""
import sys
import re
import json
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
POKERGO_DATA_PATH = Path('data/pokergo/wsop_final.json')


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class NasElement:
    """Normalized NAS file element."""
    file_id: int
    full_path: str
    filename: str
    region: str           # LV, EU, CYPRUS, CIRCUIT
    event_type: str       # BR, ME
    event_num: int | None
    event_name: str
    day: str
    part: int | None
    is_raw: bool
    size_bytes: int
    cyprus_event: str = ''     # Cyprus specific event name
    session: int | None = None  # Session number for MPP Main Event
    version: str = ''          # NC (No Commentary), STREAM, or empty
    role: str = 'PRIMARY'      # PRIMARY or BACKUP
    backup_type: str = ''      # NC, RAW, or empty for PRIMARY


@dataclass
class PkgElement:
    """Normalized PokerGO element."""
    title: str
    event_type: str       # BR, ME
    event_num: int | None
    day: str
    part: int | None
    table: str            # B, C for Table B Only, Table C Only


@dataclass
class MatchEntry:
    """Matched entry with NAS files and PokerGO info."""
    entry_key: str
    category: str
    title: str
    match_type: str       # EXACT, NAS_ONLY, POKERGO_ONLY
    nas_files: list
    pkg_title: str | None
    region: str
    event_type: str


# =============================================================================
# Extractors
# =============================================================================

def extract_region(full_path: str) -> str:
    """Extract region from full path."""
    if not full_path:
        return 'UNKNOWN'
    p = full_path.upper()
    if 'WSOP-LAS VEGAS' in p:
        return 'LV'
    elif 'WSOP-EUROPE' in p:
        return 'EU'
    elif 'MPP' in p and 'CYPRUS' in p:
        return 'CYPRUS'
    elif 'CIRCUIT' in p:
        return 'CIRCUIT'
    return 'UNKNOWN'


def extract_event_type(full_path: str, filename: str, event_num: int | None = None, region: str = '') -> str:
    """Extract event type (BR or ME).

    For EU region: Only #14 is Main Event, all others are Bracelet Events.
    """
    p = (full_path or '').upper()
    f = filename.upper()

    # EU region: check event number first
    if region == 'EU':
        if event_num is not None:
            if event_num == 14:  # Only #14 is Main Event
                return 'ME'
            else:
                return 'BR'  # All other numbered events are Bracelet Events

    # General logic
    if 'MAIN EVENT' in p or 'MAIN EVENT' in f:
        return 'ME'
    elif 'BRACELET' in p or 'SIDE EVENT' in p or 'EVENT #' in f or 'WSOPE #' in f:
        return 'BR'
    return 'OTHER'


def extract_event_num(text: str) -> int | None:
    """Extract event number from text."""
    match = re.search(r'Event\s*#(\d+)', text, re.I)
    if match:
        return int(match.group(1))
    match = re.search(r'WSOPE\s*#(\d+)', text, re.I)
    if match:
        return int(match.group(1))
    match = re.search(r'WSOP-EUROPE\s*#(\d+)', text, re.I)
    if match:
        return int(match.group(1))
    match = re.search(r'\[BRACELET(?:\s+EVENT)?\s*#(\d+)\]', text, re.I)
    if match:
        return int(match.group(1))
    return None


def extract_event_name(filename: str) -> str:
    """Extract event name from filename."""
    match = re.search(r'Event\s*#\d+\s+(.+?)(?:\s*[_|]\s*Day|\s*\(|\s*\.mp4|$)', filename, re.I)
    if match:
        name = match.group(1).strip()
        # Clean up: remove trailing underscores, pipes, "Final Table"
        name = re.sub(r'[_|]+$', '', name).strip()
        name = re.sub(r'[_|]*\s*Final\s*Table\s*$', '', name, flags=re.I).strip()
        name = re.sub(r'[_|]+$', '', name).strip()  # Clean again after removal
        # Replace underscores with spaces
        name = name.replace('_', ' ').strip()
        return name
    match = re.search(r'WSOPE\s*#\d+\s+(.+?)(?:\s+Part|\s+Final|\s*_|\s*\.mp4|$)', filename, re.I)
    if match:
        name = match.group(1).strip()
        name = re.sub(r'[_|]+$', '', name).strip()
        return name
    return ''


def extract_day(filename: str) -> str:
    """Extract day information."""
    # Final Table Day N (e.g., "Final Table Day 1")
    match = re.search(r'Final Table.*Day\s*(\d+)', filename, re.I)
    if match:
        return f'FT_D{match.group(1)}'
    # Final Table / FT → 'FT' (마지막 1 테이블)
    if 'Final Table' in filename:
        return 'FT'
    # Final Day → 'FinalDay' (마지막 날, 여러 테이블 가능)
    if 'Final Day' in filename:
        return 'FinalDay'
    if 'Final Four' in filename:
        return 'F4'
    # Day NA_B_C
    match = re.search(r'Day\s*(\d+)([A-D])(?:[_/])([A-D])(?:[_/])?([A-D])?', filename, re.I)
    if match:
        day = match.group(1)
        parts = [match.group(2), match.group(3)]
        if match.group(4):
            parts.append(match.group(4))
        return f'{day}{"".join(parts)}'  # 2ABC
    # Day N[A-D]
    match = re.search(r'Day\s*(\d+)\s*([A-D])?', filename, re.I)
    if match:
        day = match.group(1)
        suffix = match.group(2) or ''
        return f'{day}{suffix}'
    return ''


def extract_part(filename: str, full_path: str = '') -> int | None:
    """Extract part number.

    Patterns:
    - 'Part 1', 'Part1' → 1
    - '-003.mp4' suffix (NC files) → 3
    """
    # Pattern 1: "Part X"
    match = re.search(r'Part\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))

    # Pattern 2: "-XXX.mp4" suffix (NC version files)
    # Only apply to NC files to avoid false positives
    if 'NO COMMENTARY' in (full_path or '').upper():
        match = re.search(r'-(\d{3})\.mp4$', filename)
        if match:
            return int(match.group(1))

    return None


def extract_day_from_path(full_path: str) -> str:
    """Extract Day from folder path (e.g., '\\Day 3\\').

    Used for NC files where Day info is in folder name, not filename.
    """
    if not full_path:
        return ''
    # Match "Day X" or "Day X Y" folder (e.g., "Day 1 A", "Day 3")
    match = re.search(r'\\Day\s*(\d+)\s*([A-D])?\\', full_path, re.I)
    if match:
        day = match.group(1)
        suffix = match.group(2) or ''
        return f'{day}{suffix}'
    return ''


def extract_event_name_from_path(full_path: str) -> str:
    """Extract event name from folder path.

    Folder patterns:
    - '2025 WSOP-EUROPE #2 KING'S MILLION FINAL' → King's Million
    - '2025 WSOP-EUROPE #4 2K MONSTERSTACK FINAL' → 2K Monsterstack
    - '2025 WSOP-EUROPE #5 MINI MAIN EVENT' → Mini Main Event
    - '2025 WSOP-EUROPE #14 MAIN EVENT' → Main Event
    """
    if not full_path:
        return ''

    # Match event folder: "2025 WSOP-EUROPE #N <EVENT_NAME> [FINAL]"
    match = re.search(r'2025 WSOP-EUROPE #\d+\s+(.+?)(?:\\|$)', full_path, re.I)
    if match:
        event_part = match.group(1).strip()
        # Remove trailing "FINAL" if present
        event_part = re.sub(r'\s+FINAL$', '', event_part, flags=re.I)
        # Normalize event names
        event_upper = event_part.upper()

        if event_upper == 'MAIN EVENT':
            return 'Main Event'
        elif event_upper == 'MINI MAIN EVENT':
            return 'Mini Main Event'
        elif "KING'S MILLION" in event_upper or 'KINGS MILLION' in event_upper:
            return "King's Million"
        elif 'MONSTERSTACK' in event_upper:
            return '2K Monsterstack'
        elif 'COLOSSUS' in event_upper:
            return 'Colossus'
        elif 'PLO MY.BO' in event_upper or 'PLO MYSTERY' in event_upper:
            return '10K PLO Mystery Bounty'
        elif 'GGMILLION' in event_upper:
            return 'GGMillion€'
        elif '2K PLO' in event_upper:
            return '2K PLO'
        else:
            # Return cleaned version
            return event_part.title()

    return ''


def extract_table(title: str) -> str:
    """Extract table from PokerGO title (Table B Only, Table C Only)."""
    match = re.search(r'Table\s+([A-C])\s+Only', title, re.I)
    if match:
        return match.group(1)
    return ''


def is_hyperdeck(filename: str) -> bool:
    """Check if file is HyperDeck raw."""
    return filename.startswith('HyperDeck_')


def extract_version(full_path: str) -> str:
    """Extract version from path (NC = No Commentary, STREAM).

    NC and STREAM are different edits of the same content:
    - NC: No Commentary with graphics
    - STREAM: Original stream recording
    """
    p = (full_path or '').upper()
    if 'NO COMMENTARY' in p or '_NC.' in p or '_NC_' in p:
        return 'NC'
    if '\\STREAM\\' in p or '/STREAM/' in p:
        return 'STREAM'
    return ''


def extract_cyprus_event_name(filename: str) -> str:
    """Extract Cyprus event name from filename.

    Returns full event name like '$1K PokerOK Mystery Bounty' or 'Main Event'.
    """
    fn = filename.upper()

    # PokerOK Mystery Bounty
    if 'POKEROK' in fn or 'MYSTERY BOUNTY' in fn:
        return '$1K PokerOK Mystery Bounty'

    # Luxon Pay Grand Final
    if 'LUXON' in fn:
        return '$2K Luxon Pay Grand Final'

    # MPP Main Event - this IS a Main Event
    if 'MPP MAIN EVENT' in fn:
        return 'Main Event'

    # WSOP Circuit - this IS a Main Event
    if 'CIRCUIT' in fn or 'SUPER CIRCUIT' in fn:
        return 'Main Event'

    return ''


def extract_session(filename: str) -> int | None:
    """Extract session number from filename (e.g., 'Day 3 Session 1')."""
    match = re.search(r'Session\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def determine_role(is_raw: bool, version: str) -> tuple[str, str]:
    """Determine file role and backup type.

    Returns:
        (role, backup_type) tuple
        - role: 'PRIMARY' or 'BACKUP'
        - backup_type: 'NC', 'RAW', or '' for PRIMARY

    Rules:
        - NC (No Commentary) → BACKUP, NC
        - HyperDeck RAW → BACKUP, RAW
        - STREAM or normal → PRIMARY, ''
    """
    if version == 'NC':
        return ('BACKUP', 'NC')
    if is_raw:
        return ('BACKUP', 'RAW')
    return ('PRIMARY', '')


# =============================================================================
# EU Event Names Mapping
# =============================================================================

EU_EVENT_NAMES = {
    2: "€350 King's Million",
    4: '€2K Monsterstack',
    5: '€1.1K Mini Main Event',
    6: '€2K PLO',
    7: '€550 Colossus',
    10: '€10K PLO Mystery Bounty',
    13: '€1K GGMillion€',
    14: '€10.35K Main Event'  # #14 is the actual Main Event
}

# EU Main Event is #14
EU_MAIN_EVENT_NUM = 14


# =============================================================================
# Entry Key Generation
# =============================================================================

def generate_nas_entry_key(elem: NasElement) -> str:
    """Generate entry key for NAS file."""
    parts = []

    if elem.region == 'LV':
        parts.append('WSOP_2025')
        if elem.event_type == 'BR':
            parts.append('BR')
            if elem.event_num:
                parts.append(f'E{elem.event_num}')
            if elem.day:
                parts.append(f'D{elem.day}')
        else:  # ME
            parts.append('ME')
            if elem.day:
                parts.append(f'D{elem.day}')
            if elem.part:
                parts.append(f'P{elem.part}')
    elif elem.region == 'EU':
        parts.append('WSOP_2025_EU')
        if elem.event_type == 'ME':
            parts.append('ME')
            if elem.day:
                parts.append(f'D{elem.day}')
        else:
            # Bracelet Event: use event number
            parts.append('BR')
            if elem.event_num:
                parts.append(f'E{elem.event_num}')
            if elem.day:
                parts.append(f'D{elem.day}')
        if elem.part:
            parts.append(f'P{elem.part}')
        # Version: NC (No Commentary) or STREAM
        if elem.version:
            parts.append(elem.version)
        if elem.is_raw:
            parts.append('RAW')
    elif elem.region == 'CYPRUS':
        parts.append('MPP_2025')
        # Include event name to differentiate PokerOK, Luxon, MPP Main Event
        event_code = ''
        if elem.cyprus_event == '$1K PokerOK Mystery Bounty':
            event_code = 'POKEROK'
        elif elem.cyprus_event == '$2K Luxon Pay Grand Final':
            event_code = 'LUXON'
        elif elem.cyprus_event == 'Main Event':
            event_code = 'ME'
        else:
            event_code = 'OTHER'
        parts.append(event_code)
        if elem.day:
            parts.append(f'D{elem.day}')
        if elem.session:
            parts.append(f'S{elem.session}')
        if elem.part:
            parts.append(f'P{elem.part}')
    elif elem.region == 'CIRCUIT':
        parts.append('CIRCUIT_2025')
        parts.append('ME')
        if elem.day:
            parts.append(f'D{elem.day}')
        if elem.part:
            parts.append(f'P{elem.part}')

    return '_'.join(parts)


def generate_pkg_entry_key(elem: PkgElement) -> str:
    """Generate entry key for PokerGO video."""
    parts = ['WSOP_2025']

    if elem.event_type == 'BR':
        parts.append('BR')
        if elem.event_num:
            parts.append(f'E{elem.event_num}')
        if elem.day:
            parts.append(f'D{elem.day}')
    else:  # ME
        parts.append('ME')
        if elem.day:
            parts.append(f'D{elem.day}')
        if elem.table:
            parts.append(f'T{elem.table}')
        if elem.part:
            parts.append(f'P{elem.part}')

    return '_'.join(parts)


# =============================================================================
# Category and Title Generation
# =============================================================================

def normalize_day_display(day: str) -> str:
    """Normalize day for display.

    - FT → Final Table (마지막 1 테이블)
    - FinalDay → Final Day (마지막 날, 여러 테이블 가능)
    - numeric → Day N
    """
    if not day:
        return ''
    if day == 'FT':
        return 'Final Table'
    if day == 'FinalDay':
        return 'Final Day'
    if day == 'F4':
        return 'Final Four'
    if day.startswith('FT_D'):
        # Final Table Day N
        return f'Final Table Day {day[4:]}'
    if day[0].isdigit():
        return f'Day {day}'
    return day


def generate_category(region: str, event_type: str, cyprus_event: str = '', event_num: int | None = None) -> str:
    """Generate category name."""
    if region == 'LV':
        if event_type == 'ME':
            return 'WSOP 2025 Main Event'
        else:
            return 'WSOP 2025 Bracelet Events'
    elif region == 'EU':
        if event_type == 'ME':
            return 'WSOP Europe 2025 - Main Event'
        else:
            # Include event name for Bracelet Events
            event_name = EU_EVENT_NAMES.get(event_num, '')
            if event_name:
                return f'WSOP Europe 2025 - {event_name}'
            return 'WSOP Europe 2025 - Bracelet Event'
    elif region == 'CYPRUS':
        # Map event name to category
        if cyprus_event == '$1K PokerOK Mystery Bounty':
            return 'MPP Cyprus 2025 - PokerOK Mystery Bounty'
        elif cyprus_event == '$2K Luxon Pay Grand Final':
            return 'MPP Cyprus 2025 - Luxon Pay Grand Final'
        elif cyprus_event == 'Main Event':
            return 'MPP Cyprus 2025 - Main Event'
        return 'MPP Cyprus 2025'
    elif region == 'CIRCUIT':
        return 'WSOP Circuit Cyprus 2025'
    return 'Other 2025'


def generate_title(elem: NasElement) -> str:
    """Generate display title from NAS element."""
    if elem.region == 'LV':
        day_display = normalize_day_display(elem.day)
        if elem.event_type == 'ME':
            title = 'Main Event'
            if day_display:
                title += f' {day_display}'
            if elem.part:
                title += f' Part {elem.part}'
            return title
        else:
            # Bracelet Event
            if elem.event_num and elem.event_name:
                title = f'Event #{elem.event_num} {elem.event_name}'
            elif elem.event_num:
                title = f'Event #{elem.event_num}'
            else:
                title = 'Bracelet Event'
            if day_display:
                title += f' | {day_display}'
            if elem.part:
                title += f' Part {elem.part}'
            return title
    elif elem.region == 'EU':
        day_display = normalize_day_display(elem.day)
        if elem.event_type == 'ME':
            title = 'Main Event'
            if day_display:
                title += f' {day_display}'
            if elem.is_raw and elem.part:
                title += f' (Part {elem.part:02d}) [RAW]'
            elif elem.part:
                title += f' Part {elem.part}'
            elif elem.is_raw:
                title += ' [RAW]'
            # Add No Commentary suffix for NC version (backup archive)
            if elem.version == 'NC':
                title += ' (No Commentary)'
            return title
        else:
            # Bracelet Event
            event_name = elem.event_name or EU_EVENT_NAMES.get(elem.event_num, '')
            if elem.event_num and event_name:
                title = f'#{elem.event_num} {event_name}'
            elif elem.event_num:
                title = f'Event #{elem.event_num}'
            else:
                title = 'Bracelet Event'
            if day_display:
                title += f' | {day_display}'
            if elem.is_raw and elem.part:
                title += f' (Part {elem.part:02d}) [RAW]'
            elif elem.part:
                title += f' Part {elem.part}'
            elif elem.is_raw:
                title += ' [RAW]'
            # Add No Commentary suffix for NC version (backup archive)
            if elem.version == 'NC':
                title += ' (No Commentary)'
            return title
    elif elem.region == 'CYPRUS':
        # Cyprus event: Main Event or specific event name
        event_name = elem.cyprus_event or extract_cyprus_event_name(elem.filename)

        # Normalize day display: FT → Final Table, numeric → Day N
        day_display = normalize_day_display(elem.day)

        if event_name == 'Main Event':
            # MPP Main Event format: Main Event Day X [Session N]
            title = 'Main Event'
            if day_display:
                title += f' {day_display}'
            if elem.session:
                title += f' Session {elem.session}'
            if elem.part:
                title += f' Part {elem.part}'
        else:
            # Specific event: $1K PokerOK Mystery Bounty | Day X
            title = event_name if event_name else 'Unknown Event'
            if day_display:
                title += f' | {day_display}'
            if elem.part:
                title += f' Part {elem.part}'
        return title
    elif elem.region == 'CIRCUIT':
        # WSOP Circuit: always Main Event
        day_display = normalize_day_display(elem.day)
        title = 'Main Event'
        if day_display:
            title += f' {day_display}'
        if elem.part:
            title += f' Part {elem.part}'
        return title
    return 'Unknown'


# =============================================================================
# Data Loading
# =============================================================================

def load_nas_files(db) -> list[NasElement]:
    """Load NAS files from database."""
    files = db.query(NasFile).filter(
        NasFile.year == 2025,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    # Pre-process HyperDeck part numbers
    hyperdeck_parts = {}
    hyperdeck_groups = defaultdict(list)

    for f in files:
        if is_hyperdeck(f.filename):
            # Group by folder
            folder_key = get_hyperdeck_folder_key(f.full_path)
            seq = extract_hyperdeck_sequence(f.filename)
            hyperdeck_groups[folder_key].append((f.id, f.filename, seq))

    for folder_key, items in hyperdeck_groups.items():
        items.sort(key=lambda x: x[2])
        for idx, (file_id, filename, seq) in enumerate(items, 1):
            hyperdeck_parts[file_id] = idx

    # Process all files
    elements = []
    for f in files:
        region = extract_region(f.full_path)
        # Extract event_num first (needed for EU event_type determination)
        event_num = extract_event_num((f.full_path or '') + ' ' + f.filename)
        # Extract event_type with region and event_num for proper EU handling
        event_type = extract_event_type(f.full_path, f.filename, event_num, region)
        event_name = extract_event_name(f.filename)
        # Fallback: extract event name from folder path (for EU files)
        if not event_name and region == 'EU':
            event_name = extract_event_name_from_path(f.full_path)
        day = extract_day(f.filename)
        # Fallback: extract Day from path folder (for NC files)
        if not day:
            day = extract_day_from_path(f.full_path)
        part = extract_part(f.filename, f.full_path)
        raw = is_hyperdeck(f.filename)

        # HyperDeck path extraction
        if raw:
            match = re.search(r'WSOP-EUROPE\s*#(\d+)', f.full_path or '', re.I)
            if match:
                event_num = int(match.group(1))
            # EU: Only #14 is Main Event
            if event_num == EU_MAIN_EVENT_NUM:
                event_type = 'ME'
            else:
                event_type = 'BR'
            match = re.search(r'Day\s*(\d+)\s*([A-D])?', f.full_path or '', re.I)
            if match:
                day = f'{match.group(1)}{match.group(2) or ""}'
            elif 'FINAL' in (f.full_path or '').upper():
                day = 'Final'
            if event_num in EU_EVENT_NAMES and event_type == 'BR':
                event_name = EU_EVENT_NAMES[event_num]
            if f.id in hyperdeck_parts:
                part = hyperdeck_parts[f.id]

        # EU event name mapping
        if region == 'EU' and not event_name and event_num in EU_EVENT_NAMES:
            event_name = EU_EVENT_NAMES[event_num]

        # Circuit: extract part from suffix
        if region == 'CIRCUIT':
            suffix_match = re.search(r'-(\d+)\.mp4$', f.filename)
            if suffix_match:
                part = int(suffix_match.group(1))

        # Cyprus: extract event name and session
        cyprus_event = ''
        session = None
        if region == 'CYPRUS':
            cyprus_event = extract_cyprus_event_name(f.filename)
            session = extract_session(f.filename)

        # Extract version (NC = No Commentary, STREAM)
        version = extract_version(f.full_path)

        # Determine role (PRIMARY/BACKUP) and backup_type (NC/RAW)
        role, backup_type = determine_role(raw, version)

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
            is_raw=raw,
            size_bytes=f.size_bytes or 0,
            cyprus_event=cyprus_event,
            session=session,
            version=version,
            role=role,
            backup_type=backup_type
        ))

    return elements


def get_hyperdeck_folder_key(full_path: str) -> str:
    """Get folder key for grouping HyperDeck files."""
    parts = []
    match = re.search(r'WSOP-EUROPE\s*#(\d+)', full_path or '', re.I)
    if match:
        parts.append(f'E{match.group(1)}')
    if 'MAIN EVENT' in (full_path or '').upper():
        parts.append('ME')
    else:
        parts.append('BR')
    match = re.search(r'Day\s*(\d+)\s*([A-D])?', full_path or '', re.I)
    if match:
        parts.append(f'D{match.group(1)}{match.group(2) or ""}')
    elif 'FINAL' in (full_path or '').upper():
        parts.append('DFinal')
    return '_'.join(parts)


def extract_hyperdeck_sequence(filename: str) -> tuple:
    """Extract sequence from HyperDeck filename."""
    match = re.match(r'HyperDeck_(\d+)(?:-(\d+))?', filename)
    if match:
        main_num = int(match.group(1))
        sub_num = int(match.group(2)) if match.group(2) else 0
        return (main_num, sub_num)
    return (0, 0)


def load_pokergo_data() -> list[PkgElement]:
    """Load PokerGO data from JSON."""
    data = json.loads(POKERGO_DATA_PATH.read_text(encoding='utf-8'))

    # Filter 2025 only
    wsop_2025 = [v for v in data if '2025' in v.get('title', '')]

    elements = []
    for v in wsop_2025:
        title = v.get('title', '')

        if 'Main Event' in title:
            event_type = 'ME'
            event_num = None
        elif 'Bracelet' in title:
            event_type = 'BR'
            event_num = extract_event_num(title)
        else:
            continue

        # Extract day
        day_match = re.search(r'Day\s*(\d+)([A-D])?(?:[/_]([A-D]))?(?:[/_]([A-D]))?', title, re.I)
        if day_match:
            day = day_match.group(1)
            if day_match.group(2):
                day += day_match.group(2)
            if day_match.group(3):
                day += day_match.group(3)
            if day_match.group(4):
                day += day_match.group(4)
        elif 'Final Table' in title:
            ft_match = re.search(r'Final Table.*Day\s*(\d+)', title, re.I)
            if ft_match:
                day = f'FT_D{ft_match.group(1)}'
            else:
                day = 'FT'
        elif 'Final' in title and event_type == 'BR':
            day = 'Final'
        else:
            day = ''

        part = extract_part(title)
        table = extract_table(title)

        elements.append(PkgElement(
            title=title,
            event_type=event_type,
            event_num=event_num,
            day=day,
            part=part,
            table=table
        ))

    return elements


# =============================================================================
# Matching Logic
# =============================================================================

def match_entries(nas_elements: list[NasElement], pkg_elements: list[PkgElement]) -> dict[str, MatchEntry]:
    """Match NAS files with PokerGO data."""
    results = {}

    # Build PokerGO index
    pkg_index = {}
    for pkg in pkg_elements:
        key = generate_pkg_entry_key(pkg)
        pkg_index[key] = pkg

    # Process NAS files
    for nas in nas_elements:
        entry_key = generate_nas_entry_key(nas)

        if entry_key not in results:
            # Determine match type
            if nas.region in ['EU', 'CYPRUS', 'CIRCUIT']:
                match_type = 'NAS_ONLY'
                pkg_title = None
            elif entry_key in pkg_index:
                match_type = 'EXACT'
                pkg_title = pkg_index[entry_key].title
            else:
                match_type = 'NAS_ONLY'
                pkg_title = None

            results[entry_key] = MatchEntry(
                entry_key=entry_key,
                category=generate_category(nas.region, nas.event_type, nas.cyprus_event, nas.event_num),
                title=generate_title(nas),
                match_type=match_type,
                nas_files=[nas],
                pkg_title=pkg_title,
                region=nas.region,
                event_type=nas.event_type
            )
        else:
            results[entry_key].nas_files.append(nas)

    # Add POKERGO_ONLY entries
    for pkg in pkg_elements:
        key = generate_pkg_entry_key(pkg)
        if key not in results:
            results[key] = MatchEntry(
                entry_key=key,
                category=generate_category('LV', pkg.event_type),
                title=pkg.title,
                match_type='POKERGO_ONLY',
                nas_files=[],
                pkg_title=pkg.title,
                region='LV',
                event_type=pkg.event_type
            )

    return results


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


def export_to_sheets(results: dict[str, MatchEntry]):
    """Export matching results to Google Sheets in 2025_Catalog format."""
    sheets = get_sheets_service()

    # Sheet 1: 2025_Catalog - Full file catalog with Match Type
    print('\n[1/3] 2025_Catalog')
    headers = [
        'No', 'Entry Key', 'Match Type', 'Role', 'Backup Type',
        'Category', 'Title', 'PokerGO Title',
        'Region', 'Event Type', 'Event #', 'Day', 'Part', 'RAW',
        'Size (GB)', 'Filename', 'Full Path'
    ]
    rows = [headers]
    idx = 1

    # Sort by Category, then Entry Key for consistent ordering
    for entry in sorted(results.values(), key=lambda x: (x.category, x.entry_key)):
        if entry.nas_files:
            # Output one row per NAS file
            for nas in entry.nas_files:
                size_gb = nas.size_bytes / (1024**3)
                rows.append([
                    idx,
                    entry.entry_key,
                    entry.match_type,
                    nas.role,
                    nas.backup_type or '-',
                    entry.category,
                    entry.title,
                    entry.pkg_title or '',
                    nas.region,
                    nas.event_type,
                    nas.event_num or '',
                    nas.day,
                    nas.part or '',
                    'Yes' if nas.is_raw else '',
                    f'{size_gb:.2f}',
                    nas.filename,
                    nas.full_path
                ])
                idx += 1

    write_sheet(sheets, '2025_Catalog', rows)

    # Sheet 2: 2025_Summary - Summary by match type and region
    print('\n[2/3] 2025_Summary')
    summary = defaultdict(lambda: {'entries': 0, 'files': 0, 'size': 0})

    for entry in results.values():
        key = (entry.match_type, entry.region)
        summary[key]['entries'] += 1
        summary[key]['files'] += len(entry.nas_files)
        summary[key]['size'] += sum(f.size_bytes for f in entry.nas_files)

    rows = [['Match Type', 'Region', 'Entries', 'Files', 'Size (GB)']]
    for (match_type, region) in sorted(summary.keys()):
        s = summary[(match_type, region)]
        size_gb = s['size'] / (1024**3)
        rows.append([match_type, region, s['entries'], s['files'], f'{size_gb:.2f}'])

    # Totals by match type
    rows.append([])
    rows.append(['=== Match Type Totals ===', '', '', '', ''])
    type_totals = defaultdict(lambda: {'entries': 0, 'files': 0, 'size': 0})
    for entry in results.values():
        type_totals[entry.match_type]['entries'] += 1
        type_totals[entry.match_type]['files'] += len(entry.nas_files)
        type_totals[entry.match_type]['size'] += sum(f.size_bytes for f in entry.nas_files)

    for match_type in ['EXACT', 'NAS_ONLY', 'POKERGO_ONLY']:
        if match_type in type_totals:
            t = type_totals[match_type]
            size_gb = t['size'] / (1024**3)
            rows.append([match_type, '', t['entries'], t['files'], f'{size_gb:.2f}'])

    # Grand total
    total_entries = len(results)
    total_files = sum(len(e.nas_files) for e in results.values())
    total_size = sum(sum(f.size_bytes for f in e.nas_files) for e in results.values()) / (1024**3)
    rows.append([])
    rows.append(['TOTAL', '', total_entries, total_files, f'{total_size:.2f}'])

    write_sheet(sheets, '2025_Summary', rows)

    # Sheet 3: 2025_PokerGO_Only - PokerGO titles without NAS files
    print('\n[3/3] 2025_PokerGO_Only')
    headers = ['No', 'Entry Key', 'Category', 'PokerGO Title', 'Event Type']
    rows = [headers]

    pkg_only = [e for e in results.values() if e.match_type == 'POKERGO_ONLY']
    for idx, entry in enumerate(sorted(pkg_only, key=lambda x: x.entry_key), 1):
        rows.append([
            idx,
            entry.entry_key,
            entry.category,
            entry.pkg_title,
            entry.event_type
        ])

    write_sheet(sheets, '2025_PokerGO_Only', rows)


# =============================================================================
# Main
# =============================================================================

def main():
    print('=' * 70)
    print('2025 NAS-PokerGO Matching')
    print('=' * 70)

    # Step 1: Load data
    print('\n[Step 1] Loading data...')
    db = next(get_db())
    nas_elements = load_nas_files(db)
    pkg_elements = load_pokergo_data()
    print(f'  NAS files: {len(nas_elements)}')
    print(f'  PokerGO videos: {len(pkg_elements)}')

    # Step 2: Match entries
    print('\n[Step 2] Matching entries...')
    results = match_entries(nas_elements, pkg_elements)

    # Step 3: Report
    print('\n[Step 3] Matching Results:')
    match_counts = defaultdict(int)
    for entry in results.values():
        match_counts[entry.match_type] += 1

    total_entries = len(results)
    total_files = sum(len(e.nas_files) for e in results.values())

    print(f'  Total Entries: {total_entries}')
    print(f'  Total NAS Files: {total_files}')
    print()
    for match_type in ['EXACT', 'NAS_ONLY', 'POKERGO_ONLY']:
        count = match_counts.get(match_type, 0)
        files = sum(len(e.nas_files) for e in results.values() if e.match_type == match_type)
        print(f'  {match_type:15s}: {count:3d} entries, {files:3d} files')

    # Step 4: Export to Google Sheets
    print('\n[Step 4] Exporting to Google Sheets...')
    export_to_sheets(results)

    print('\n' + '=' * 70)
    print('[OK] Matching completed!')
    print(f'URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit')
    print('=' * 70)


if __name__ == '__main__':
    main()
