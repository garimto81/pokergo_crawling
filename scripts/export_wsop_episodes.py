"""Export WSOP Episodes to Google Sheets."""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'nams' / 'api'))
from database import get_db, PokergoEpisode

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

GOOGLE_SHEETS_ID = '1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4'
CREDENTIALS_PATH = Path('D:/AI/claude01/json/service_account_key.json')


def is_actual_episode(title):
    """Check if title is an actual episode (not collection/season header)."""
    if not title:
        return False

    title_stripped = title.strip()
    if title_stripped.endswith('| Episodes') or title_stripped.endswith('| Livestreams'):
        return False

    title_lower = title.lower()

    episode_keywords = [
        'episode', 'event #', 'event#', '| day', 'show ',
        'final table', 'heads-up', '(part', 'part 1', 'part 2',
        'stand up for'
    ]
    return any(kw in title_lower for kw in episode_keywords)


def extract_year(ep):
    """Extract year from episode title/collection/season."""
    for text in [ep.title, ep.collection_title, ep.season_title]:
        if text:
            match = re.search(r'\b(19|20)\d{2}\b', text)
            if match:
                return int(match.group())
    return None


def main():
    db = next(get_db())

    # Filter WSOP episodes (Main Event + Bracelet only)
    episodes = db.query(PokergoEpisode).filter(
        PokergoEpisode.collection_title.ilike('%WSOP%')
    ).all()

    filtered = []
    for ep in episodes:
        season = (ep.season_title or '').lower()
        title = ep.title or ''

        # Main Event or Bracelet only
        if 'main event' not in season and 'bracelet' not in season:
            continue

        # Actual episodes only (exclude headers)
        if not is_actual_episode(title):
            continue

        filtered.append(ep)

    print(f'Total filtered episodes: {len(filtered)}')

    # Prepare sheet data
    headers = ['Year', 'Collection', 'Season', 'Title', 'Duration (min)']
    rows = [headers]

    for ep in sorted(filtered, key=lambda x: (extract_year(x) or 0, x.title or '')):
        year = extract_year(ep)
        duration = f'{int(ep.duration_sec // 60)}' if ep.duration_sec else ''
        rows.append([
            year or '',
            (ep.collection_title or '').strip(),
            (ep.season_title or '').strip(),
            (ep.title or '').strip(),
            duration
        ])

    print(f'Rows prepared: {len(rows)} (including header)')

    # Export to Google Sheets
    creds = Credentials.from_service_account_file(
        str(CREDENTIALS_PATH),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)
    sheets = service.spreadsheets()

    sheet_name = 'PokerGO_WSOP_Episodes'

    # Check if sheet exists
    spreadsheet = sheets.get(spreadsheetId=GOOGLE_SHEETS_ID).execute()
    existing_sheets = [s['properties']['title'] for s in spreadsheet['sheets']]

    if sheet_name not in existing_sheets:
        sheets.batchUpdate(
            spreadsheetId=GOOGLE_SHEETS_ID,
            body={
                'requests': [{'addSheet': {'properties': {'title': sheet_name}}}]
            }
        ).execute()
        print(f'Created new sheet: {sheet_name}')

    # Clear existing data
    sheets.values().clear(
        spreadsheetId=GOOGLE_SHEETS_ID,
        range=f'{sheet_name}!A:Z'
    ).execute()

    # Write data
    result = sheets.values().update(
        spreadsheetId=GOOGLE_SHEETS_ID,
        range=f'{sheet_name}!A1',
        valueInputOption='RAW',
        body={'values': rows}
    ).execute()

    print(f'Export complete: {result.get("updatedRows", 0)} rows')
    print(f'URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit')


if __name__ == '__main__':
    main()
