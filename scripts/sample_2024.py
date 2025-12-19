"""Random sample 10 items from Catalog sheet."""
import random
import sys
import io
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

GOOGLE_SHEETS_ID = '1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4'
CREDENTIALS_PATH = Path('D:/AI/claude01/json/service_account_key.json')

# Get sheet name from argument (default: 2024_Catalog)
sheet_name = sys.argv[1] if len(sys.argv) > 1 else '2024_Catalog'

creds = Credentials.from_service_account_file(
    str(CREDENTIALS_PATH),
    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
)
service = build('sheets', 'v4', credentials=creds)
sheets = service.spreadsheets()

# Get all data
result = sheets.values().get(spreadsheetId=GOOGLE_SHEETS_ID, range=f'{sheet_name}!A1:Q500').execute()
rows = result.get('values', [])

headers = rows[0]
data = rows[1:]

# Random sample 10
random.seed(999)  # Fresh sample
samples = random.sample(data, min(10, len(data)))

print(f'{sheet_name} 무작위 10개 샘플 분석 (총 {len(data)}개 중)')
print('=' * 100)

for i, row in enumerate(samples, 1):
    # Pad row to ensure all columns exist
    row = row + [''] * (17 - len(row))

    no = row[0]
    entry_key = row[1]
    category = row[5]
    title = row[6]
    region = row[8]
    event_type = row[9]
    event_num = row[10]
    day = row[11]
    part = row[12]
    size = row[14]
    filename = row[15]

    print(f'[{i}] No.{no} | {region} {event_type}')
    print(f'    Entry Key: {entry_key}')
    print(f'    Title: {title}')
    print(f'    Category: {category}')
    print(f'    Event#: {event_num or "-"} | Day: {day or "-"} | Part: {part or "-"}')
    print(f'    Size: {size} GB')
    fn_display = filename[:70] + '...' if len(filename) > 70 else filename
    print(f'    File: {fn_display}')
    print()
