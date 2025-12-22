"""Debug segment API response."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from iconik import IconikClient
import json

asset_id = "d206796c-4cf3-11f0-a812-fa75e68441df"

with IconikClient() as client:
    # 1. Raw API response
    print("=== Raw API Response ===")
    response = client.client.get(f"/assets/v1/assets/{asset_id}/segments/")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2, default=str)[:2000])

    # 2. Check asset detail for segment info
    print("\n=== Asset Detail ===")
    asset = client.get_asset(asset_id)
    print(f"Asset ID: {asset.id}")
    print(f"Title: {asset.title}")

    # 3. Try different endpoint (maybe /segments not /segments/)
    print("\n=== Alternative endpoint ===")
    try:
        response2 = client.client.get(f"/assets/v1/assets/{asset_id}/segments")
        print(f"Status: {response2.status_code}")
        print(response2.text[:500])
    except Exception as e:
        print(f"Error: {e}")
