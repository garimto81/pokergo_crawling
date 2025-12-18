"""2003 NAS Matching Script.

Special year - Chris Moneymaker's historic win.
- Main Event Episodes 1-7 (+ Episode 7 text version)
- Main Event Final Table
- Best Of compilations (4 topics, mov/mxf pairs)

Grouping Rules:
- Best Of: Group by normalized topic, mxf = PRIMARY, mov = BACKUP
- Main Event: Episode 1-6 single PRIMARY, Episode 7 has 2 versions (both PRIMARY)
- Final Table: Single PRIMARY
- "text" version: Separate PRIMARY with (text) in title
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

# Topic normalization for Best Of
TOPIC_NORMALIZE = {
    'all ins': 'All-Ins',
    'all-ins': 'All-Ins',
    'all_ins': 'All-Ins',
    'amazing all-ins': 'All-Ins',
    'amazing_all-ins': 'All-Ins',
    'bluffs': 'Bluffs',
    'best bluffs': 'Bluffs',
    'amazing bluffs': 'Bluffs',
    'amazing_bluffs': 'Bluffs',
    'moneymaker': 'Moneymaker',
    'memorable moments': 'Memorable Moments',
    'memorable_moments': 'Memorable Moments',
}


@dataclass
class NasElement:
    file_id: int
    full_path: str
    filename: str
    content_type: str     # WSOP_ME, WSOP_ME_FT, WSOP_BEST
    episode: int | None
    topic: str            # For Best Of
    is_text_version: bool
    size_bytes: int
    role: str = 'PRIMARY'
    group_id: str = ''


def normalize_topic(raw_topic: str) -> str:
    """Normalize Best Of topic name."""
    key = raw_topic.lower().strip()
    return TOPIC_NORMALIZE.get(key, raw_topic.title())


def extract_best_of_topic(filename: str) -> str | None:
    """Extract and normalize topic from Best Of filename."""
    match = re.search(r'best[_ ]of[_ ](.+?)(?:_ES|\d{10}|\.mxf|\.mov|$)', filename, re.I)
    if match:
        raw = match.group(1).strip()
        # Remove "Amazing " prefix
        raw = re.sub(r'^amazing\s+', '', raw, flags=re.I)
        return normalize_topic(raw)
    return None


def extract_episode(filename: str) -> int | None:
    """Extract episode number from Main Event filename."""
    # WSOP_2003-01.mxf pattern
    match = re.search(r'WSOP_2003-(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    # Show 7_text pattern
    match = re.search(r'Show\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def is_text_version(filename: str) -> bool:
    """Check if file is a text version."""
    return '_text' in filename.lower() or 'text.' in filename.lower()


def classify_file(filename: str) -> str:
    """Classify file into content type."""
    fn_lower = filename.lower()

    if 'best of' in fn_lower or 'best_of' in fn_lower:
        return 'WSOP_BEST'
    elif 'final table' in fn_lower:
        return 'WSOP_ME_FT'
    elif re.search(r'wsop_2003-\d+', fn_lower) or re.search(r'show\s*\d+', fn_lower):
        return 'WSOP_ME'
    return 'OTHER'


def generate_group_id(elem: NasElement) -> str:
    """Generate group ID for PRIMARY/BACKUP assignment."""
    if elem.content_type == 'WSOP_BEST':
        # Group by normalized topic
        topic_key = elem.topic.replace(' ', '').replace('-', '')
        return f'WSOP_2003_BEST_{topic_key}'
    elif elem.content_type == 'WSOP_ME_FT':
        return 'WSOP_2003_ME_FT'
    elif elem.content_type == 'WSOP_ME':
        # Text version is separate group
        if elem.is_text_version:
            return f'WSOP_2003_ME_EP{elem.episode}_TEXT'
        return f'WSOP_2003_ME_EP{elem.episode}'
    return 'WSOP_2003_OTHER'


def generate_entry_key(elem: NasElement) -> str:
    """Generate entry key for catalog."""
    if elem.content_type == 'WSOP_BEST':
        topic_key = elem.topic.replace(' ', '').replace('-', '')
        return f'WSOP_2003_BEST_{topic_key}'
    elif elem.content_type == 'WSOP_ME_FT':
        return 'WSOP_2003_ME_FT'
    elif elem.content_type == 'WSOP_ME':
        key = f'WSOP_2003_ME_EP{elem.episode}'
        if elem.is_text_version:
            key += '_TEXT'
        return key
    return 'WSOP_2003_OTHER'


def generate_category(elem: NasElement) -> str:
    """Generate category name."""
    if elem.content_type == 'WSOP_BEST':
        return 'WSOP 2003 Best Of'
    return 'WSOP 2003 Main Event'


def generate_title(elem: NasElement) -> str:
    """Generate display title."""
    if elem.content_type == 'WSOP_BEST':
        title = f'2003 Best Of: {elem.topic}'
    elif elem.content_type == 'WSOP_ME_FT':
        title = '2003 Main Event Final Table'
    elif elem.content_type == 'WSOP_ME':
        title = f'2003 Main Event Episode {elem.episode}'
        if elem.is_text_version:
            title += ' (text)'
    else:
        title = '2003 Other'

    if elem.role == 'BACKUP':
        title += ' (Back up)'

    return title


# Extension priority: mp4 > mov > mxf (from MATCHING_RULES.md)
EXT_PRIORITY = {'.mp4': 1, '.mov': 2, '.mxf': 3}


def get_ext_priority(filename: str) -> int:
    """Get extension priority (lower = higher priority)."""
    ext = '.' + filename.lower().split('.')[-1]
    return EXT_PRIORITY.get(ext, 99)


def assign_roles(elements: list[NasElement]) -> list[NasElement]:
    """Assign PRIMARY/BACKUP roles within groups."""
    groups = defaultdict(list)
    for elem in elements:
        elem.group_id = generate_group_id(elem)
        groups[elem.group_id].append(elem)

    result = []
    for group_id, group_elements in groups.items():
        # Sort by extension priority first, then by size descending
        group_elements.sort(key=lambda x: (get_ext_priority(x.filename), -x.size_bytes))

        # Single file = PRIMARY
        if len(group_elements) == 1:
            group_elements[0].role = 'PRIMARY'
            result.append(group_elements[0])
            continue

        # First file (highest ext priority) = PRIMARY, rest = BACKUP
        group_elements[0].role = 'PRIMARY'
        for elem in group_elements[1:]:
            elem.role = 'BACKUP'
        result.extend(group_elements)

    return result


def load_nas_files(db) -> list[NasElement]:
    """Load 2003 NAS files from database."""
    files = db.query(NasFile).filter(
        NasFile.year == 2003,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    elements = []
    for f in files:
        content_type = classify_file(f.filename)
        episode = extract_episode(f.filename) if content_type == 'WSOP_ME' else None
        topic = extract_best_of_topic(f.filename) if content_type == 'WSOP_BEST' else ''
        text_ver = is_text_version(f.filename)

        elements.append(NasElement(
            file_id=f.id,
            full_path=f.full_path or '',
            filename=f.filename,
            content_type=content_type,
            episode=episode,
            topic=topic or '',
            is_text_version=text_ver,
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
    sheet_name = '2003_Catalog'

    headers = [
        'No', 'Entry Key', 'Match Type', 'Role', 'Backup Type',
        'Category', 'Title', 'PokerGO Title',
        'Region', 'Event Type', 'Event #', 'Day', 'Part', 'RAW',
        'Size (GB)', 'Filename', 'Full Path'
    ]
    rows = [headers]

    # Sort: ME first (by episode), then FT, then Best Of (by topic)
    def sort_key(x):
        type_order = {'WSOP_ME': 0, 'WSOP_ME_FT': 1, 'WSOP_BEST': 2, 'OTHER': 3}
        role_order = 0 if x.role == 'PRIMARY' else 1
        return (
            type_order.get(x.content_type, 9),
            x.episode or 99,
            1 if x.is_text_version else 0,
            role_order,
            x.topic,
            -x.size_bytes
        )

    for idx, elem in enumerate(sorted(elements, key=sort_key), 1):
        entry_key = generate_entry_key(elem)
        category = generate_category(elem)
        title = generate_title(elem)
        size_gb = elem.size_bytes / (1024**3)

        event_type = 'ME' if elem.content_type in ('WSOP_ME', 'WSOP_ME_FT') else 'BEST'

        rows.append([
            idx, entry_key, 'NAS_ONLY', elem.role, '-',
            category, title, '',
            'LV', event_type, '', '', '', '',
            f'{size_gb:.2f}', elem.filename, elem.full_path
        ])

    return write_sheet(sheets, sheet_name, rows)


def main():
    print('=' * 70)
    print('2003 NAS Matching (Moneymaker Year)')
    print('=' * 70)

    db = next(get_db())
    sheets = get_sheets_service()

    # Load files
    print('\n[Step 1] Loading 2003 files...')
    elements = load_nas_files(db)
    print(f'  Total: {len(elements)} files')

    # Analysis
    print('\n[Step 2] Analysis:')
    type_counts = defaultdict(lambda: {'primary': 0, 'backup': 0})
    for e in elements:
        if e.role == 'PRIMARY':
            type_counts[e.content_type]['primary'] += 1
        else:
            type_counts[e.content_type]['backup'] += 1

    for ct in ['WSOP_ME', 'WSOP_ME_FT', 'WSOP_BEST', 'OTHER']:
        if ct in type_counts:
            c = type_counts[ct]
            print(f'  {ct}: P:{c["primary"]} B:{c["backup"]}')

    # Export
    print('\n[Step 3] Exporting to Google Sheets...')
    rows_written = export_to_sheet(sheets, elements)
    print(f'  2003_Catalog: {rows_written} rows')

    # Summary
    total_primary = sum(1 for e in elements if e.role == 'PRIMARY')
    total_backup = sum(1 for e in elements if e.role == 'BACKUP')
    total_size = sum(e.size_bytes for e in elements) / (1024**3)

    print('\n' + '=' * 70)
    print('[OK] 2003 Matching completed!')
    print(f'  Files: {len(elements)} (PRIMARY: {total_primary}, BACKUP: {total_backup})')
    print(f'  Size: {total_size:.1f} GB')
    print('=' * 70)


if __name__ == '__main__':
    main()
