"""Check for generic event titles."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

GOOGLE_SHEETS_ID = '1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4'
CREDENTIALS_PATH = Path('D:/AI/claude01/json/service_account_key.json')

creds = Credentials.from_service_account_file(
    str(CREDENTIALS_PATH),
    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
)
service = build('sheets', 'v4', credentials=creds)
sheets = service.spreadsheets()

print('Titles with generic Event names:')
print('=' * 60)

for sheet in ['2024_Catalog', '2025_Catalog']:
    result = sheets.values().get(spreadsheetId=GOOGLE_SHEETS_ID, range=f'{sheet}!G2:G200').execute()
    titles = [r[0] for r in result.get('values', []) if r]

    generic = []
    for t in titles:
        # Check for generic titles
        if t.startswith('Bracelet Event') and 'Event #' not in t:
            generic.append(t)
        elif t == 'Event':
            generic.append(t)

    if generic:
        print(f'\n[{sheet}] Found {len(generic)} generic titles:')
        for t in set(generic):
            count = generic.count(t)
            print(f'  - "{t}" ({count}x)')
    else:
        print(f'\n[{sheet}] No generic titles found')
