"""2006 NAS Matching Script.

2006 Structure:
- Shows 11-22: Main Event Episodes 1-12 (ME)
- Shows 2-10, 23-32: Bracelet Events (BR)
- Shows 33-34: Tournament of Champions pt1/pt2
- MXF files: WSOP_2006_21.mxf, _22.mxf (match ME 11-12)
- Show 17 ME 7: mp4 + mov duplicate

Grouping Rules:
- Same Show + ME: mp4 > mov > mxf priority
- MXF matches Show number (21→ME11, 22→ME12)
- pt1/pt2 are separate parts, both PRIMARY
- EOE: single PRIMARY
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

# Main Event show mapping: Show 11 = ME EP01, Show 12 = ME EP02, etc.
ME_SHOW_START = 11
ME_SHOW_END = 22


@dataclass
class NasElement:
    file_id: int
    full_path: str
    filename: str
    content_type: str     # WSOP_ME, WSOP_BR, WSOP_TOC, WSOP_EOE, WSOP_MXF
    show_num: int | None
    episode_num: int | None  # ME episode or TOC part
    part_num: int | None     # For pt1/pt2
    event_name: str
    ext: str              # mp4, mov, mxf
    size_bytes: int
    role: str = 'PRIMARY'
    group_id: str = ''


def extract_show_num(filename: str) -> int | None:
    """Extract show number from filename."""
    match = re.search(r'Show\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    # mxf pattern: WSOP_2006_21.mxf
    match = re.search(r'WSOP_2006_(\d+)\.mxf', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def extract_me_episode(filename: str, show_num: int | None) -> int | None:
    """Extract ME episode number."""
    # Direct ME pattern in filename
    match = re.search(r'ME\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    # Derive from show number
    if show_num and ME_SHOW_START <= show_num <= ME_SHOW_END:
        return show_num - ME_SHOW_START + 1
    return None


def extract_part_num(filename: str) -> int | None:
    """Extract part number (pt1, pt2, Part 1, Part 2)."""
    match = re.search(r'pt\s*(\d+)|Part\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1) or match.group(2))
    return None


def extract_event_name(filename: str) -> str:
    """Extract event name from filename."""
    fn = filename

    # Remove common prefixes/suffixes
    fn = re.sub(r'^WSOP 2006\s*', '', fn)
    fn = re.sub(r'_ES\w*\.mov$', '', fn)
    fn = re.sub(r'_ESO?\d+', '', fn)  # Remove ES codes like _ES0600165716
    fn = re.sub(r'_GMPO\s*\d+.*$', '', fn)
    fn = re.sub(r'\.mov$|\.mp4$|\.mxf$', '', fn)

    # Remove Show X prefix
    fn = re.sub(r'^Show\s*\d+\s*', '', fn)

    # Remove ME X
    fn = re.sub(r'\s*ME\s*\d+\s*', '', fn)

    # Clean up pt1/pt2 to Part 1/Part 2
    fn = re.sub(r'\s*pt(\d+)', r' Part \1', fn, flags=re.I)

    return fn.strip()


def get_extension(filename: str) -> str:
    """Get file extension."""
    return filename.split('.')[-1].lower()


def classify_file(filename: str) -> str:
    """Classify file into content type."""
    fn_lower = filename.lower()

    # MXF files
    if fn_lower.endswith('.mxf'):
        return 'WSOP_MXF'

    # EOE
    if 'eoe' in fn_lower:
        return 'WSOP_EOE'

    # TOC
    if 'toc' in fn_lower:
        return 'WSOP_TOC'

    # Show patterns
    show_match = re.search(r'Show\s*(\d+)', filename, re.I)
    if show_match:
        show_num = int(show_match.group(1))
        # ME pattern in filename
        if re.search(r'ME\s*\d+', filename, re.I):
            return 'WSOP_ME'
        # Show 11-22 without explicit ME = still ME
        if ME_SHOW_START <= show_num <= ME_SHOW_END:
            return 'WSOP_ME'
        return 'WSOP_BR'

    return 'WSOP_OTHER'


def generate_group_id(elem: NasElement) -> str:
    """Generate group ID for PRIMARY/BACKUP assignment."""
    if elem.content_type == 'WSOP_MXF':
        # Group mxf with corresponding Show/ME
        if elem.show_num and ME_SHOW_START <= elem.show_num <= ME_SHOW_END:
            return f'WSOP_2006_ME_S{elem.show_num}'
        return f'WSOP_2006_MXF_S{elem.show_num}'

    if elem.content_type == 'WSOP_ME':
        return f'WSOP_2006_ME_S{elem.show_num}'

    if elem.content_type == 'WSOP_BR':
        # pt1/pt2 are separate groups
        if elem.part_num:
            return f'WSOP_2006_BR_S{elem.show_num}_PT{elem.part_num}'
        return f'WSOP_2006_BR_S{elem.show_num}'

    if elem.content_type == 'WSOP_TOC':
        # pt1/pt2 are separate groups
        if elem.part_num:
            return f'WSOP_2006_TOC_PT{elem.part_num}'
        return f'WSOP_2006_TOC_S{elem.show_num}'

    if elem.content_type == 'WSOP_EOE':
        return 'WSOP_2006_EOE'

    return f'WSOP_2006_OTHER_{elem.filename}'


# Extension priority: mp4 > mov > mxf
EXT_PRIORITY = {'mp4': 1, 'mov': 2, 'mxf': 3}


def assign_roles(elements: list[NasElement]) -> list[NasElement]:
    """Assign PRIMARY/BACKUP roles within groups."""
    groups = defaultdict(list)
    for elem in elements:
        elem.group_id = generate_group_id(elem)
        groups[elem.group_id].append(elem)

    result = []
    for group_id, group_elements in groups.items():
        # Sort by extension priority, then by size descending
        group_elements.sort(key=lambda x: (EXT_PRIORITY.get(x.ext, 99), -x.size_bytes))

        # MXF-only groups: all BACKUP
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
        ep = elem.episode_num
        return f'WSOP_2006_ME_EP{ep:02d}' if ep else f'WSOP_2006_ME_S{elem.show_num}'
    elif elem.content_type == 'WSOP_BR':
        key = f'WSOP_2006_BR_S{elem.show_num:02d}'
        if elem.part_num:
            key += f'_PT{elem.part_num}'
        return key
    elif elem.content_type == 'WSOP_MXF':
        return f'WSOP_2006_MXF_S{elem.show_num:02d}' if elem.show_num else 'WSOP_2006_MXF'
    elif elem.content_type == 'WSOP_TOC':
        return f'WSOP_2006_TOC_PT{elem.part_num}' if elem.part_num else f'WSOP_2006_TOC_S{elem.show_num}'
    elif elem.content_type == 'WSOP_EOE':
        return 'WSOP_2006_EOE'
    return 'WSOP_2006_OTHER'


def generate_category(elem: NasElement) -> str:
    """Generate category name."""
    if elem.content_type == 'WSOP_ME':
        return 'WSOP 2006 Main Event'
    elif elem.content_type == 'WSOP_BR':
        return 'WSOP 2006 Bracelet Events'
    elif elem.content_type == 'WSOP_MXF':
        return 'WSOP 2006 MXF Masters'
    elif elem.content_type == 'WSOP_TOC':
        return 'WSOP 2006 Tournament of Champions'
    elif elem.content_type == 'WSOP_EOE':
        return 'WSOP 2006 Event of Events'
    return 'WSOP 2006 Other'


def generate_title(elem: NasElement) -> str:
    """Generate display title."""
    if elem.content_type == 'WSOP_ME':
        ep = elem.episode_num
        title = f'2006 Main Event Episode {ep}' if ep else f'2006 Main Event Show {elem.show_num}'
    elif elem.content_type == 'WSOP_BR':
        if elem.event_name:
            title = f'2006 Show {elem.show_num}: {elem.event_name}'
        else:
            title = f'2006 Bracelet Event Show {elem.show_num}'
    elif elem.content_type == 'WSOP_MXF':
        title = f'2006 MXF Show {elem.show_num}' if elem.show_num else '2006 MXF'
    elif elem.content_type == 'WSOP_TOC':
        title = f'2006 Tournament of Champions Part {elem.part_num}' if elem.part_num else '2006 Tournament of Champions'
    elif elem.content_type == 'WSOP_EOE':
        title = '2006 Event of Events Final Table'
    else:
        title = f'2006 {elem.event_name}'

    if elem.role == 'BACKUP':
        title += ' (Back up)'

    return title


def load_nas_files(db) -> list[NasElement]:
    """Load 2006 NAS files from database."""
    files = db.query(NasFile).filter(
        NasFile.year == 2006,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    elements = []
    for f in files:
        content_type = classify_file(f.filename)
        show_num = extract_show_num(f.filename)
        episode_num = extract_me_episode(f.filename, show_num) if content_type in ('WSOP_ME', 'WSOP_MXF') else None
        part_num = extract_part_num(f.filename)
        event_name = extract_event_name(f.filename)
        ext = get_extension(f.filename)

        elements.append(NasElement(
            file_id=f.id,
            full_path=f.full_path or '',
            filename=f.filename,
            content_type=content_type,
            show_num=show_num,
            episode_num=episode_num,
            part_num=part_num,
            event_name=event_name,
            ext=ext,
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
    sheet_name = '2006_Catalog'

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
            'WSOP_EOE': 3,
            'WSOP_MXF': 4,
            'WSOP_OTHER': 5
        }
        role_order = 0 if x.role == 'PRIMARY' else 1
        return (
            type_order.get(x.content_type, 9),
            x.episode_num or x.show_num or 0,
            x.part_num or 0,
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
                     'TOC' if elem.content_type == 'WSOP_TOC' else 'OTHER'

        rows.append([
            idx, entry_key, 'NAS_ONLY', elem.role, '-',
            category, title, '',
            'LV', event_type, '', '', elem.part_num or '', '',
            f'{size_gb:.2f}', elem.filename, elem.full_path
        ])

    return write_sheet(sheets, sheet_name, rows)


def main():
    print('=' * 70)
    print('2006 NAS Matching')
    print('=' * 70)

    db = next(get_db())
    sheets = get_sheets_service()

    # Load files
    print('\n[Step 1] Loading 2006 files...')
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

    for ct in ['WSOP_ME', 'WSOP_BR', 'WSOP_TOC', 'WSOP_EOE', 'WSOP_MXF', 'WSOP_OTHER']:
        if ct in type_counts:
            c = type_counts[ct]
            print(f'  {ct}: P:{c["primary"]} B:{c["backup"]}')

    # Export
    print('\n[Step 3] Exporting to Google Sheets...')
    rows_written = export_to_sheet(sheets, elements)
    print(f'  2006_Catalog: {rows_written} rows')

    # Summary
    total_primary = sum(1 for e in elements if e.role == 'PRIMARY')
    total_backup = sum(1 for e in elements if e.role == 'BACKUP')
    total_size = sum(e.size_bytes for e in elements) / (1024**3)

    print('\n' + '=' * 70)
    print('[OK] 2006 Matching completed!')
    print(f'  Files: {len(elements)} (PRIMARY: {total_primary}, BACKUP: {total_backup})')
    print(f'  Size: {total_size:.1f} GB')
    print('=' * 70)


if __name__ == '__main__':
    main()
