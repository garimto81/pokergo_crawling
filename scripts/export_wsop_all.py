"""Export all WSOP episodes from PokerGO to Google Sheets."""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.database import get_db, PokergoEpisode
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

GOOGLE_SHEETS_ID = '1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4'
CREDENTIALS_PATH = Path('D:/AI/claude01/json/service_account_key.json')


def extract_year(ep):
    """Extract year from episode."""
    for text in [ep.title, ep.collection_title, ep.season_title]:
        if text:
            match = re.search(r'\b(19|20)\d{2}\b', text)
            if match:
                return int(match.group())
    return None


def main():
    db = next(get_db())

    # WSOP 포함 에피소드
    wsop_episodes = db.query(PokergoEpisode).filter(
        PokergoEpisode.title.ilike('%WSOP%') |
        PokergoEpisode.collection_title.ilike('%WSOP%') |
        PokergoEpisode.season_title.ilike('%WSOP%')
    ).all()

    print(f'WSOP episodes: {len(wsop_episodes)}')

    # 시트 데이터 준비
    headers = ['Year', 'Collection', 'Season', 'Title', 'Duration (min)', 'ID']
    rows = [headers]

    for ep in sorted(wsop_episodes, key=lambda x: (extract_year(x) or 9999, x.collection_title or '', x.title or '')):
        year = extract_year(ep)
        duration = f'{int(ep.duration_sec // 60)}' if ep.duration_sec else ''
        rows.append([
            year or '',
            (ep.collection_title or '').strip(),
            (ep.season_title or '').strip(),
            (ep.title or '').strip(),
            duration,
            ep.id
        ])

    print(f'Rows prepared: {len(rows)}')

    # Google Sheets Export
    creds = Credentials.from_service_account_file(
        str(CREDENTIALS_PATH),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)
    sheets = service.spreadsheets()

    sheet_name = 'PokerGO_WSOP_All'

    # 시트 확인 및 생성
    spreadsheet = sheets.get(spreadsheetId=GOOGLE_SHEETS_ID).execute()
    existing_sheets = [s['properties']['title'] for s in spreadsheet['sheets']]

    if sheet_name not in existing_sheets:
        sheets.batchUpdate(
            spreadsheetId=GOOGLE_SHEETS_ID,
            body={'requests': [{'addSheet': {'properties': {'title': sheet_name}}}]}
        ).execute()
        print(f'Created new sheet: {sheet_name}')

    # Clear and write
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

    print(f'[OK] Export complete: {result.get("updatedRows", 0)} rows')
    print(f'URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit')


if __name__ == '__main__':
    main()
