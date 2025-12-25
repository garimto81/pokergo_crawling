"""Check ISG Scan Directories."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from iconik import IconikClient

def main():
    with IconikClient() as client:
        storage_id = "d2de5d18-ee58-11ef-852e-da5f3e9a002a"

        # Get scan directories
        print("=== Scan Directories ===\n")
        try:
            scan_dirs = client._get(f"/files/v1/storages/{storage_id}/scan_directories/")
            for d in scan_dirs.get("objects", []):
                print(f"Path: {d.get('path', 'N/A')}")
                print(f"Name: {d.get('name', 'N/A')}")
                print(f"Enabled: {d.get('enabled', 'N/A')}")
                print(f"Recursive: {d.get('recursive', 'N/A')}")
                print("---")

            if not scan_dirs.get("objects"):
                print("No scan directories configured (scanning entire storage)")
        except Exception as e:
            print(f"Error: {e}")

        # Get root files
        print("\n=== Root Directory ===\n")
        try:
            files = client._get(f"/files/v1/storages/{storage_id}/files/", params={"path": "/", "per_page": 30})
            for f in files.get("objects", []):
                ftype = "DIR" if f.get("is_dir") else "FILE"
                print(f"[{ftype}] {f.get('name', 'N/A')}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
