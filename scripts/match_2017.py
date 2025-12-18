"""2017 NAS Matching Script.

Matches and exports 2017 NAS files:
- WSOP 2017 Main Event: 18 episodes
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


@dataclass
class NasElement:
    file_id: int
    full_path: str
    filename: str
    content_type: str
    region: str
    event_type: str
    episode_num: int | None
    size_bytes: int
    role: str = 'PRIMARY'


def extract_episode_num(filename: str) -> int | None:
    match = re.search(r'Episode\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def generate_entry_key(elem: NasElement) -> str:
    parts = ['WSOP_2017_ME']
    if elem.episode_num:
        parts.append(f'EP{elem.episode_num}')
    return '_'.join(parts)


def generate_title(elem: NasElement) -> str:
    if elem.episode_num:
        return f'Main Event Episode {elem.episode_num}'
    return 'Main Event'


def load_nas_files(db) -> list[NasElement]:
    files = db.query(NasFile).filter(
        NasFile.year == 2017,
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
    print(f'  Written: {result.get("updatedRows", 0)} rows')


def export_to_sheets(elements: list[NasElement]):
    sheets = get_sheets_service()
    print('\n[Export] 2017_Catalog')

    headers = [
        'No', 'Entry Key', 'Match Type', 'Role', 'Backup Type',
        'Category', 'Title', 'PokerGO Title',
        'Region', 'Event Type', 'Event #', 'Day', 'Part', 'RAW',
        'Size (GB)', 'Filename', 'Full Path'
    ]
    rows = [headers]

    for idx, elem in enumerate(sorted(elements, key=lambda x: x.episode_num or 0), 1):
        entry_key = generate_entry_key(elem)
        title = generate_title(elem)
        size_gb = elem.size_bytes / (1024**3)

        rows.append([
            idx, entry_key, 'NAS_ONLY', elem.role, '-',
            'WSOP 2017 Main Event', title, '',
            elem.region, elem.event_type, '', '', '', '',
            f'{size_gb:.2f}', elem.filename, elem.full_path
        ])

    write_sheet(sheets, '2017_Catalog', rows)
    total_size = sum(e.size_bytes for e in elements) / (1024**3)
    print(f'\n  Summary: {len(elements)} files ({total_size:.1f} GB)')


def main():
    print('=' * 70)
    print('2017 NAS Matching')
    print('=' * 70)

    db = next(get_db())
    elements = load_nas_files(db)
    print(f'\n[Step 1] Loaded {len(elements)} files')

    print('\n[Step 2] Exporting...')
    export_to_sheets(elements)

    print('\n' + '=' * 70)
    print('[OK] 2017 Matching completed!')
    print('=' * 70)


if __name__ == '__main__':
    main()
