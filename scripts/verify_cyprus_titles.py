"""Verify Cyprus/Circuit titles in 2025_Catalog."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding='utf-8')

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

GOOGLE_SHEETS_ID = '1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4'
CREDENTIALS_PATH = Path('D:/AI/claude01/json/service_account_key.json')

creds = Credentials.from_service_account_file(
    str(CREDENTIALS_PATH),
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
service = build('sheets', 'v4', credentials=creds)
sheets = service.spreadsheets()

# Get 2025_Catalog data
result = sheets.values().get(
    spreadsheetId=GOOGLE_SHEETS_ID,
    range="'2025_Catalog'!A1:O140"
).execute()

rows = result.get('values', [])
print('=== Cyprus/Circuit Titles ===')
headers = rows[0]
title_idx = headers.index('Title')
region_idx = headers.index('Region')
category_idx = headers.index('Category')

for row in rows[1:]:
    if len(row) > region_idx:
        region = row[region_idx]
        if region in ['CYPRUS', 'CIRCUIT']:
            title = row[title_idx] if len(row) > title_idx else ''
            cat = row[category_idx] if len(row) > category_idx else ''
            print(f'{region:8s} | {title}')
