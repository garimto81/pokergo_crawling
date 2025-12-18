"""2004 NAS Matching Script.

Rules:
- Bracelet Event 폴더 (TOC 6개): EP01-EP06 순차 출력, 모두 PRIMARY
- Generics 폴더 Show 13-22: Main Event EP01-EP10
- Generics 폴더 Show 1-12: Bracelet Event
- Generics 폴더 Show 3: (noName) 처리
- Tournament of Champions Generic (3개): BACKUP
- 기타 3개: 파일 이름 그대로
- MXFs 폴더: 모두 BACKUP

Note: 나중에 메타데이터 작업 시 수작업 전면 수정 예정
"""
import sys
import io
import re
import os
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


@dataclass
class NasElement:
    file_id: int
    full_path: str
    filename: str
    folder: str
    content_type: str     # WSOP_ME, WSOP_BR, WSOP_TOC, WSOP_OTHER
    show_num: int | None
    episode_num: int | None
    event_name: str
    size_bytes: int
    role: str = 'PRIMARY'


def get_folder(path: str) -> str:
    """Extract folder name from path."""
    return os.path.basename(os.path.dirname(path))


def classify_file(filename: str, folder: str) -> tuple[str, int | None, int | None, str]:
    """
    Classify file and extract metadata.
    Returns: (content_type, show_num, episode_num, event_name)
    """
    fn_lower = filename.lower()

    # MXFs folder - all BACKUP
    if folder == 'MXFs (master)':
        match = re.search(r'WSOP_2004_(\d+)', filename)
        show_num = int(match.group(1)) if match else None
        return ('WSOP_MXF', show_num, None, '')

    # Bracelet Event folder - Tournament of Champions episodes
    if folder == 'Bracelet Event':
        return ('WSOP_TOC', None, None, 'Tournament of Champions')

    # Generics folder
    if folder == 'Generics(No Graphic)':
        # Tournament of Champions Generic - BACKUP
        if 'tournament of champ' in fn_lower or 'tounament of champ' in fn_lower:
            if 'generic' in fn_lower:
                return ('WSOP_TOC_GENERIC', None, None, 'Tournament of Champions')

        # Show pattern with ME (Main Event)
        match = re.search(r'Show\s*(\d+)\s*ME\s*(\d+)', filename, re.I)
        if match:
            show_num = int(match.group(1))
            ep_num = int(match.group(2))
            return ('WSOP_ME', show_num, ep_num, 'Main Event')

        # Show pattern (Bracelet Events)
        match = re.search(r'Show\s*(\d+)\s*(.+?)(?:_ES|_Generic|\.mov|$)', filename, re.I)
        if match:
            show_num = int(match.group(1))
            event_name = match.group(2).strip()
            if not event_name or event_name.startswith('_'):
                event_name = '(noName)'
            return ('WSOP_BR', show_num, None, event_name)

        # SHow 12 (typo in filename)
        match = re.search(r'SHow\s*(\d+)\s*(.+?)(?:_ES|_Generic|\.mov|$)', filename, re.I)
        if match:
            show_num = int(match.group(1))
            event_name = match.group(2).strip()
            return ('WSOP_BR', show_num, None, event_name)

        # Other files - use filename as event name
        # Remove extension and ES code
        event_name = re.sub(r'_ES\w+\.mov$', '', filename)
        event_name = re.sub(r'\.mov$', '', event_name)
        event_name = re.sub(r'^2004 WSOP\s*', '', event_name)
        return ('WSOP_OTHER', None, None, event_name)

    return ('WSOP_OTHER', None, None, filename)


def generate_entry_key(elem: NasElement) -> str:
    if elem.content_type == 'WSOP_ME':
        return f'WSOP_2004_ME_EP{elem.episode_num:02d}'
    elif elem.content_type == 'WSOP_BR':
        return f'WSOP_2004_BR_S{elem.show_num:02d}'
    elif elem.content_type == 'WSOP_TOC':
        return f'WSOP_2004_TOC_EP{elem.episode_num:02d}'
    elif elem.content_type == 'WSOP_TOC_GENERIC':
        return 'WSOP_2004_TOC_GENERIC'
    elif elem.content_type == 'WSOP_MXF':
        return f'WSOP_2004_MXF_S{elem.show_num:02d}' if elem.show_num else 'WSOP_2004_MXF'
    return 'WSOP_2004_OTHER'


def generate_category(elem: NasElement) -> str:
    if elem.content_type == 'WSOP_ME':
        return 'WSOP 2004 Main Event'
    elif elem.content_type == 'WSOP_BR':
        return 'WSOP 2004 Bracelet Events'
    elif elem.content_type in ('WSOP_TOC', 'WSOP_TOC_GENERIC'):
        return 'WSOP 2004 Tournament of Champions'
    elif elem.content_type == 'WSOP_MXF':
        return 'WSOP 2004 MXF Masters'
    return 'WSOP 2004 Other'


def generate_title(elem: NasElement) -> str:
    if elem.content_type == 'WSOP_ME':
        title = f'2004 Main Event Episode {elem.episode_num}'
    elif elem.content_type == 'WSOP_BR':
        title = f'2004 Show {elem.show_num}: {elem.event_name}'
    elif elem.content_type == 'WSOP_TOC':
        title = f'2004 Tournament of Champions Episode {elem.episode_num}'
    elif elem.content_type == 'WSOP_TOC_GENERIC':
        title = '2004 Tournament of Champions'
    elif elem.content_type == 'WSOP_MXF':
        title = f'2004 MXF Show {elem.show_num}' if elem.show_num else '2004 MXF'
    else:
        title = f'2004 {elem.event_name}'

    if elem.role == 'BACKUP':
        title += ' (Back up)'

    return title


def load_nas_files(db) -> list[NasElement]:
    """Load 2004 NAS files from database."""
    files = db.query(NasFile).filter(
        NasFile.year == 2004,
        NasFile.is_excluded == False
    ).order_by(NasFile.full_path).all()

    elements = []
    toc_episode = 0  # Counter for TOC episodes

    for f in files:
        folder = get_folder(f.full_path)
        content_type, show_num, episode_num, event_name = classify_file(f.filename, folder)

        # Assign TOC episode numbers
        if content_type == 'WSOP_TOC':
            toc_episode += 1
            episode_num = toc_episode

        # Determine role
        if content_type == 'WSOP_MXF':
            role = 'BACKUP'
        elif content_type == 'WSOP_TOC_GENERIC':
            role = 'BACKUP'
        else:
            role = 'PRIMARY'

        elements.append(NasElement(
            file_id=f.id,
            full_path=f.full_path or '',
            filename=f.filename,
            folder=folder,
            content_type=content_type,
            show_num=show_num,
            episode_num=episode_num,
            event_name=event_name,
            size_bytes=f.size_bytes or 0,
            role=role
        ))

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
    sheet_name = '2004_Catalog'

    headers = [
        'No', 'Entry Key', 'Match Type', 'Role', 'Backup Type',
        'Category', 'Title', 'PokerGO Title',
        'Region', 'Event Type', 'Event #', 'Day', 'Part', 'RAW',
        'Size (GB)', 'Filename', 'Full Path'
    ]
    rows = [headers]

    # Sort: ME first, then BR, then TOC, then MXF, then Other
    def sort_key(x):
        type_order = {
            'WSOP_ME': 0,
            'WSOP_BR': 1,
            'WSOP_TOC': 2,
            'WSOP_TOC_GENERIC': 3,
            'WSOP_OTHER': 4,
            'WSOP_MXF': 5
        }
        role_order = 0 if x.role == 'PRIMARY' else 1
        return (
            type_order.get(x.content_type, 9),
            x.episode_num or 0,
            x.show_num or 0,
            role_order,
            -x.size_bytes
        )

    for idx, elem in enumerate(sorted(elements, key=sort_key), 1):
        entry_key = generate_entry_key(elem)
        category = generate_category(elem)
        title = generate_title(elem)
        size_gb = elem.size_bytes / (1024**3)

        event_type = 'ME' if elem.content_type == 'WSOP_ME' else 'BR' if elem.content_type == 'WSOP_BR' else 'TOC' if 'TOC' in elem.content_type else 'OTHER'

        rows.append([
            idx, entry_key, 'NAS_ONLY', elem.role, '-',
            category, title, '',
            'LV', event_type, '', '', '', '',
            f'{size_gb:.2f}', elem.filename, elem.full_path
        ])

    return write_sheet(sheets, sheet_name, rows)


def main():
    print('=' * 70)
    print('2004 NAS Matching')
    print('=' * 70)

    db = next(get_db())
    sheets = get_sheets_service()

    # Load files
    print('\n[Step 1] Loading 2004 files...')
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

    for ct in ['WSOP_ME', 'WSOP_BR', 'WSOP_TOC', 'WSOP_TOC_GENERIC', 'WSOP_OTHER', 'WSOP_MXF']:
        if ct in type_counts:
            c = type_counts[ct]
            print(f'  {ct}: P:{c["primary"]} B:{c["backup"]}')

    # Export
    print('\n[Step 3] Exporting to Google Sheets...')
    rows_written = export_to_sheet(sheets, elements)
    print(f'  2004_Catalog: {rows_written} rows')

    # Summary
    total_primary = sum(1 for e in elements if e.role == 'PRIMARY')
    total_backup = sum(1 for e in elements if e.role == 'BACKUP')
    total_size = sum(e.size_bytes for e in elements) / (1024**3)

    print('\n' + '=' * 70)
    print('[OK] 2004 Matching completed!')
    print(f'  Files: {len(elements)} (PRIMARY: {total_primary}, BACKUP: {total_backup})')
    print(f'  Size: {total_size:.1f} GB')
    print('  Note: Manual metadata work planned for future')
    print('=' * 70)


if __name__ == '__main__':
    main()
