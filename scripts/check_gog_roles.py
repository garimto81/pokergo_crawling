"""Check GOG file roles in 2023_Catalog."""
import sys
import io
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

GOOGLE_SHEETS_ID = '1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4'
CREDENTIALS_PATH = Path('D:/AI/claude01/json/service_account_key.json')

creds = Credentials.from_service_account_file(
    str(CREDENTIALS_PATH),
    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
)
service = build('sheets', 'v4', credentials=creds)
sheets = service.spreadsheets()

result = sheets.values().get(spreadsheetId=GOOGLE_SHEETS_ID, range='2023_Catalog!A2:Q100').execute()
rows = result.get('values', [])

print('GOG Files Role Assignment:')
print('=' * 90)
print(f'{"No":<4} {"Role":<8} {"Version":<8} {"Title":<20} {"Filename":<50}')
print('-' * 90)

for row in rows:
    row = row + [''] * (17 - len(row))
    event_type = row[9]
    if event_type == 'GOG':
        no = row[0]
        role = row[3]
        version = row[4]
        title = row[6][:18]
        filename = row[15][:48]
        print(f'{no:<4} {role:<8} {version:<8} {title:<20} {filename}')

# Summary
print('\n' + '=' * 90)
print('Summary by Episode:')
print('-' * 90)

# Group by episode
episodes = {}
for row in rows:
    row = row + [''] * (17 - len(row))
    if row[9] == 'GOG':
        # Extract episode from title
        title = row[6]
        ep_num = title.replace('Episode ', '') if 'Episode' in title else '?'
        if ep_num not in episodes:
            episodes[ep_num] = {'PRIMARY': 0, 'BACKUP': 0, 'files': []}
        role = row[3]
        episodes[ep_num][role] = episodes[ep_num].get(role, 0) + 1
        episodes[ep_num]['files'].append((role, row[4], row[15][:40]))

for ep in sorted(episodes.keys(), key=lambda x: int(x) if x.isdigit() else 99):
    info = episodes[ep]
    print(f'Episode {ep}: PRIMARY={info["PRIMARY"]}, BACKUP={info["BACKUP"]}')
    for role, version, fn in info['files']:
        marker = '★' if role == 'PRIMARY' else ' '
        print(f'  {marker} [{role:<7}] {version:<8} {fn}')
