"""2005 NAS Matching Script.

2005 Structure:
- Shows 7-20: Bracelet Events (BR)
- Shows 21-32: Main Event Episodes 1-12 (ME)
- MXF files: WSOP_2005_01.mxf ~ _32.mxf (all BACKUP)
- Generic/Master versions: Master = PRIMARY, Generic = BACKUP
- Tournament of Champions: 3 episodes
- Circuit Events: Lake Tahoe, New Orleans, Rio, Rincon
- EOE Final Table, Best Hand Ever Played

Grouping Rules:
- Same Show number: Master > Generic > Plain (by filename)
- mxf = BACKUP (lower priority than mov)
- TOC: Group by ES code suffix, largest = PRIMARY
- Circuit Events: Each unique, all PRIMARY
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

# Main Event show mapping: Show 21 = ME EP01, Show 22 = ME EP02, etc.
ME_SHOW_START = 21
ME_SHOW_END = 32


@dataclass
class NasElement:
    file_id: int
    full_path: str
    filename: str
    content_type: str     # WSOP_ME, WSOP_BR, WSOP_TOC, WSOP_CIRCUIT, WSOP_EOE, WSOP_BEST, WSOP_MXF
    show_num: int | None
    episode_num: int | None
    event_name: str
    version: str          # master, generic, plain, mxf
    size_bytes: int
    role: str = 'PRIMARY'
    group_id: str = ''


def extract_show_num(filename: str) -> int | None:
    """Extract show number from filename."""
    match = re.search(r'Show\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    # mxf pattern: WSOP_2005_01.mxf
    match = re.search(r'WSOP_2005_(\d+)\.mxf', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def extract_me_episode(show_num: int | None) -> int | None:
    """Convert show number to ME episode number."""
    if show_num is None:
        return None
    if ME_SHOW_START <= show_num <= ME_SHOW_END:
        return show_num - ME_SHOW_START + 1
    return None


def extract_event_name(filename: str) -> str:
    """Extract event name from filename."""
    fn = filename

    # Remove common prefixes/suffixes
    fn = re.sub(r'^WSOP 2005\s*', '', fn)
    fn = re.sub(r'_ES\w+\.mov$', '', fn)
    fn = re.sub(r'\.mov$', '', fn)
    fn = re.sub(r'\.mxf$', '', fn)

    # Remove Show X prefix
    fn = re.sub(r'^Show\s*\d+\s*', '', fn)

    # Remove ME X suffix
    fn = re.sub(r'\s*ME\s*\d+\s*', '', fn)

    # Remove Generic/Master suffix
    fn = re.sub(r'\s*(Generic|Master)$', '', fn, flags=re.I)

    return fn.strip()


def classify_file(filename: str) -> tuple[str, str]:
    """
    Classify file and determine version.
    Returns: (content_type, version)
    """
    fn_lower = filename.lower()

    # MXF files
    if fn_lower.endswith('.mxf'):
        return ('WSOP_MXF', 'mxf')

    # Tournament of Champions
    if 'tournament of champ' in fn_lower:
        return ('WSOP_TOC', 'plain')

    # EOE
    if 'eoe' in fn_lower:
        return ('WSOP_EOE', 'plain')

    # Best Of
    if 'best' in fn_lower:
        return ('WSOP_BEST', 'plain')

    # Circuit Events
    if any(x in fn_lower for x in ['lake tahoe', 'rio hour', 'rincon', 'new orleans']):
        return ('WSOP_CIRCUIT', 'plain')

    # Show patterns
    show_match = re.search(r'Show\s*(\d+)', filename, re.I)
    if show_match:
        show_num = int(show_match.group(1))

        # Determine version
        if 'master' in fn_lower:
            version = 'master'
        elif 'generic' in fn_lower:
            version = 'generic'
        else:
            version = 'plain'

        # ME or BR
        if ME_SHOW_START <= show_num <= ME_SHOW_END:
            return ('WSOP_ME', version)
        else:
            return ('WSOP_BR', version)

    return ('WSOP_OTHER', 'plain')


def generate_group_id(elem: NasElement) -> str:
    """Generate group ID for PRIMARY/BACKUP assignment."""
    if elem.content_type == 'WSOP_MXF':
        # Group mxf with corresponding Show
        if elem.show_num:
            if ME_SHOW_START <= elem.show_num <= ME_SHOW_END:
                return f'WSOP_2005_ME_S{elem.show_num}'
            return f'WSOP_2005_BR_S{elem.show_num}'
        return 'WSOP_2005_MXF_UNMATCHED'

    if elem.content_type in ('WSOP_ME', 'WSOP_BR'):
        prefix = 'ME' if elem.content_type == 'WSOP_ME' else 'BR'
        return f'WSOP_2005_{prefix}_S{elem.show_num}'

    if elem.content_type == 'WSOP_TOC':
        # Each TOC file is a separate episode (different ES codes)
        return f'WSOP_2005_TOC_EP{elem.episode_num}'

    # Each Circuit/EOE/Best is unique
    return f'WSOP_2005_{elem.content_type}_{elem.event_name}'


# Version priority: master > plain > generic > mxf
VERSION_PRIORITY = {'master': 1, 'plain': 2, 'generic': 3, 'mxf': 4}


def assign_roles(elements: list[NasElement]) -> list[NasElement]:
    """Assign PRIMARY/BACKUP roles within groups."""
    groups = defaultdict(list)
    for elem in elements:
        elem.group_id = generate_group_id(elem)
        groups[elem.group_id].append(elem)

    result = []
    for group_id, group_elements in groups.items():
        # Sort by version priority, then by size descending
        group_elements.sort(key=lambda x: (VERSION_PRIORITY.get(x.version, 99), -x.size_bytes))

        # MXF-only groups (Shows 1-6): all BACKUP (for later manual processing)
        if len(group_elements) == 1 and group_elements[0].content_type == 'WSOP_MXF':
            group_elements[0].role = 'BACKUP'
            result.append(group_elements[0])
            continue

        # Single file = PRIMARY
        if len(group_elements) == 1:
            group_elements[0].role = 'PRIMARY'
            result.append(group_elements[0])
            continue

        # First file = PRIMARY, rest = BACKUP
        group_elements[0].role = 'PRIMARY'
        for elem in group_elements[1:]:
            elem.role = 'BACKUP'
        result.extend(group_elements)

    return result


def generate_entry_key(elem: NasElement) -> str:
    """Generate entry key for catalog."""
    if elem.content_type == 'WSOP_ME':
        ep = extract_me_episode(elem.show_num)
        return f'WSOP_2005_ME_EP{ep:02d}' if ep else f'WSOP_2005_ME_S{elem.show_num}'
    elif elem.content_type == 'WSOP_BR':
        return f'WSOP_2005_BR_S{elem.show_num:02d}'
    elif elem.content_type == 'WSOP_MXF':
        return f'WSOP_2005_MXF_S{elem.show_num:02d}' if elem.show_num else 'WSOP_2005_MXF'
    elif elem.content_type == 'WSOP_TOC':
        return f'WSOP_2005_TOC_EP{elem.episode_num:02d}' if elem.episode_num else 'WSOP_2005_TOC'
    elif elem.content_type == 'WSOP_CIRCUIT':
        return f'WSOP_2005_CIRCUIT'
    elif elem.content_type == 'WSOP_EOE':
        return 'WSOP_2005_EOE'
    elif elem.content_type == 'WSOP_BEST':
        return 'WSOP_2005_BEST'
    return 'WSOP_2005_OTHER'


def generate_category(elem: NasElement) -> str:
    """Generate category name."""
    if elem.content_type == 'WSOP_ME':
        return 'WSOP 2005 Main Event'
    elif elem.content_type == 'WSOP_BR':
        return 'WSOP 2005 Bracelet Events'
    elif elem.content_type == 'WSOP_MXF':
        return 'WSOP 2005 MXF Masters'
    elif elem.content_type == 'WSOP_TOC':
        return 'WSOP 2005 Tournament of Champions'
    elif elem.content_type == 'WSOP_CIRCUIT':
        return 'WSOP 2005 Circuit Events'
    elif elem.content_type == 'WSOP_EOE':
        return 'WSOP 2005 Event of Events'
    elif elem.content_type == 'WSOP_BEST':
        return 'WSOP 2005 Best Of'
    return 'WSOP 2005 Other'


def generate_title(elem: NasElement) -> str:
    """Generate display title."""
    if elem.content_type == 'WSOP_ME':
        ep = extract_me_episode(elem.show_num)
        title = f'2005 Main Event Episode {ep}' if ep else f'2005 Main Event Show {elem.show_num}'
    elif elem.content_type == 'WSOP_BR':
        if elem.event_name:
            title = f'2005 Show {elem.show_num}: {elem.event_name}'
        else:
            title = f'2005 Bracelet Event Show {elem.show_num}'
    elif elem.content_type == 'WSOP_MXF':
        title = f'2005 MXF Show {elem.show_num}' if elem.show_num else '2005 MXF'
    elif elem.content_type == 'WSOP_TOC':
        title = f'2005 Tournament of Champions Episode {elem.episode_num}' if elem.episode_num else '2005 Tournament of Champions'
    elif elem.content_type == 'WSOP_CIRCUIT':
        title = f'2005 {elem.event_name}'
    elif elem.content_type == 'WSOP_EOE':
        title = '2005 Event of Events Final Table'
    elif elem.content_type == 'WSOP_BEST':
        title = f'2005 Best Of: {elem.event_name}'
    else:
        title = f'2005 {elem.event_name}'

    if elem.role == 'BACKUP':
        title += ' (Back up)'

    return title


def load_nas_files(db) -> list[NasElement]:
    """Load 2005 NAS files from database."""
    files = db.query(NasFile).filter(
        NasFile.year == 2005,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    elements = []
    toc_episode = 0  # Counter for TOC episodes

    for f in files:
        content_type, version = classify_file(f.filename)
        show_num = extract_show_num(f.filename)
        episode_num = extract_me_episode(show_num) if content_type == 'WSOP_ME' else None
        event_name = extract_event_name(f.filename)

        # Assign TOC episode numbers (each TOC file is a different episode)
        if content_type == 'WSOP_TOC':
            toc_episode += 1
            episode_num = toc_episode

        elements.append(NasElement(
            file_id=f.id,
            full_path=f.full_path or '',
            filename=f.filename,
            content_type=content_type,
            show_num=show_num,
            episode_num=episode_num,
            event_name=event_name,
            version=version,
            size_bytes=f.size_bytes or 0,
            role='PRIMARY'
        ))

    # Assign PRIMARY/BACKUP roles
    elements = assign_roles(elements)
    return elements


def get_sheets_service():
    creds = Credentials.from_service_account_file(
        str(CREDENTIALS_PATH),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)
    return service.spreadsheets()


def ensure_sheet_exists(sheets, sheet_name: str):
    spreadsheet = sheets.get(spreadsheetId=GOOGLE_SHEETS_ID).execute()
    existing_sheets = [s['properties']['title'] for s in spreadsheet['sheets']]
    if sheet_name not in existing_sheets:
        sheets.batchUpdate(
            spreadsheetId=GOOGLE_SHEETS_ID,
            body={'requests': [{'addSheet': {'properties': {'title': sheet_name}}}]}
        ).execute()
        print(f'  Created new sheet: {sheet_name}')


def write_sheet(sheets, sheet_name: str, rows: list):
    ensure_sheet_exists(sheets, sheet_name)
    sheets.values().clear(spreadsheetId=GOOGLE_SHEETS_ID, range=f'{sheet_name}!A:Z').execute()
    result = sheets.values().update(
        spreadsheetId=GOOGLE_SHEETS_ID,
        range=f'{sheet_name}!A1',
        valueInputOption='RAW',
        body={'values': rows}
    ).execute()
    return result.get('updatedRows', 0)


def export_to_sheet(sheets, elements: list[NasElement]) -> int:
    sheet_name = '2005_Catalog'

    headers = [
        'No', 'Entry Key', 'Match Type', 'Role', 'Backup Type',
        'Category', 'Title', 'PokerGO Title',
        'Region', 'Event Type', 'Event #', 'Day', 'Part', 'RAW',
        'Size (GB)', 'Filename', 'Full Path'
    ]
    rows = [headers]

    # Sort: ME first, then BR, then others; by show/episode number
    def sort_key(x):
        type_order = {
            'WSOP_ME': 0,
            'WSOP_BR': 1,
            'WSOP_TOC': 2,
            'WSOP_CIRCUIT': 3,
            'WSOP_EOE': 4,
            'WSOP_BEST': 5,
            'WSOP_MXF': 6,
            'WSOP_OTHER': 7
        }
        role_order = 0 if x.role == 'PRIMARY' else 1
        return (
            type_order.get(x.content_type, 9),
            x.show_num or 0,
            role_order,
            -x.size_bytes
        )

    for idx, elem in enumerate(sorted(elements, key=sort_key), 1):
        entry_key = generate_entry_key(elem)
        category = generate_category(elem)
        title = generate_title(elem)
        size_gb = elem.size_bytes / (1024**3)

        event_type = 'ME' if elem.content_type == 'WSOP_ME' else \
                     'BR' if elem.content_type == 'WSOP_BR' else \
                     'TOC' if elem.content_type == 'WSOP_TOC' else \
                     'CIRCUIT' if elem.content_type == 'WSOP_CIRCUIT' else 'OTHER'

        rows.append([
            idx, entry_key, 'NAS_ONLY', elem.role, '-',
            category, title, '',
            'LV', event_type, '', '', '', '',
            f'{size_gb:.2f}', elem.filename, elem.full_path
        ])

    return write_sheet(sheets, sheet_name, rows)


def main():
    print('=' * 70)
    print('2005 NAS Matching')
    print('=' * 70)

    db = next(get_db())
    sheets = get_sheets_service()

    # Load files
    print('\n[Step 1] Loading 2005 files...')
    elements = load_nas_files(db)
    print(f'  Total: {len(elements)} files')

    # Analysis
    print('\n[Step 2] Analysis by type:')
    type_counts = defaultdict(lambda: {'primary': 0, 'backup': 0})
    for e in elements:
        if e.role == 'PRIMARY':
            type_counts[e.content_type]['primary'] += 1
        else:
            type_counts[e.content_type]['backup'] += 1

    for ct in ['WSOP_ME', 'WSOP_BR', 'WSOP_TOC', 'WSOP_CIRCUIT', 'WSOP_EOE', 'WSOP_BEST', 'WSOP_MXF', 'WSOP_OTHER']:
        if ct in type_counts:
            c = type_counts[ct]
            print(f'  {ct}: P:{c["primary"]} B:{c["backup"]}')

    # Export
    print('\n[Step 3] Exporting to Google Sheets...')
    rows_written = export_to_sheet(sheets, elements)
    print(f'  2005_Catalog: {rows_written} rows')

    # Summary
    total_primary = sum(1 for e in elements if e.role == 'PRIMARY')
    total_backup = sum(1 for e in elements if e.role == 'BACKUP')
    total_size = sum(e.size_bytes for e in elements) / (1024**3)

    print('\n' + '=' * 70)
    print('[OK] 2005 Matching completed!')
    print(f'  Files: {len(elements)} (PRIMARY: {total_primary}, BACKUP: {total_backup})')
    print(f'  Size: {total_size:.1f} GB')
    print('=' * 70)


if __name__ == '__main__':
    main()
