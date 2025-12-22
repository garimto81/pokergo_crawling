"""Search specific titles in Iconik_Full_Metadata sheet only."""

import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sheets import SheetsWriter


# Target titles to search
TARGET_TITLES = [
    "serock vs griff",
    "1987 WSOP",
    "WSOP 2022 Final",
    "Phil Hellmuth Set over Set",
    "hellmuth tilted",
    "Amarillo Slim",
    "Nik Airball",
]


def search_in_iconik_sheet():
    """Search titles in Iconik_Full_Metadata sheet."""
    print("=" * 80)
    print("Iconik_Full_Metadata 시트에서 검색")
    print("=" * 80)

    writer = SheetsWriter()

    try:
        headers, data = writer.get_sheet_data("Iconik_Full_Metadata")
    except Exception as e:
        print(f"시트 읽기 실패: {e}")
        return

    print(f"\n총 {len(data)}건 중 검색...")
    print()

    for target in TARGET_TITLES:
        target_lower = target.lower()
        print(f"\n[검색] '{target}'")
        print("-" * 60)

        matches = []
        for row in data:
            title = row.get("title", "").strip()
            if target_lower in title.lower():
                matches.append(row)

        if matches:
            for m in matches:
                print(f"  Title: {m.get('title', 'N/A')}")
                print(f"  ID: {m.get('id', 'N/A')}")
                print(f"  time_start_ms: {m.get('time_start_ms', 'N/A')}")
                print(f"  time_end_ms: {m.get('time_end_ms', 'N/A')}")
                print()
        else:
            print("  -> 매칭 결과 없음")


if __name__ == "__main__":
    search_in_iconik_sheet()
