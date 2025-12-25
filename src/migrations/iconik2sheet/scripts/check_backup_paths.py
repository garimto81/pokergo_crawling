"""Check Backup file paths in Master_Catalog."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sync.backup_loader import get_backup_loader


def main():
    loader = get_backup_loader()
    data = loader.load_backup_data()

    print("\n=== Backup File Paths Check ===\n")

    found = []
    not_found = []
    no_path = []

    for item in data:
        fp = item.get("full_path", "")
        if not fp:
            no_path.append(item.get("stem", "?"))
            continue

        path = Path(fp)
        if path.exists():
            found.append(fp)
        else:
            not_found.append(fp)

    print(f"Total Backup files: {len(data)}")
    print(f"Files FOUND in NAS: {len(found)}")
    print(f"Files NOT FOUND: {len(not_found)}")
    print(f"No path in sheet: {len(no_path)}")

    if not_found:
        print("\n--- Sample NOT FOUND paths (first 10) ---")
        for fp in not_found[:10]:
            print(f"  {fp}")

    if found:
        print("\n--- Sample FOUND paths (first 5) ---")
        for fp in found[:5]:
            print(f"  {fp}")


if __name__ == "__main__":
    main()
