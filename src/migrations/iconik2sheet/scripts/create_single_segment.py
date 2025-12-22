"""Create a single segment with specific timecode."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from iconik import IconikClient

asset_id = "fbb7e94e-4127-11f0-bf53-7216fc2efa1a"

# 1분 30초 = 90초 = 90000ms
# 2분 30초 = 150초 = 150000ms
time_start_ms = 90000
time_end_ms = 150000

segment_data = {
    "time_start_milliseconds": time_start_ms,
    "time_end_milliseconds": time_end_ms,
    "segment_type": "GENERIC",
}

print("=== Creating Segment ===")
print(f"Asset: {asset_id}")
print(f"Time: 1:30 - 2:30 ({time_start_ms}ms - {time_end_ms}ms)")
print()

with IconikClient() as client:
    response = client.client.post(f"/assets/v1/assets/{asset_id}/segments/", json=segment_data)

    if response.status_code == 201:
        data = response.json()
        print("OK - Segment Created!")
        print(f"Segment ID: {data.get('id')}")
        print(f"Created at: {data.get('date_created')}")
        print()
        print(f"View in iconik:")
        print(f"https://app.iconik.io/asset/{asset_id}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
