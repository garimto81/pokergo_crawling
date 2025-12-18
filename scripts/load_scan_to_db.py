"""Load scanned NAS files into database."""
import sys
import json
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.database import get_db
from src.nams.api.database.models import NasFile

JSON_PATH = Path('data/sources/nas/nas_files.json')

def extract_year(full_path: str, filename: str) -> int | None:
    """Extract year from path or filename."""
    # GOG files are always 2023
    if 'GOG' in full_path.upper() or 'GOG' in filename.upper():
        return 2023

    # From path: WSOP 2024, WSOP-LAS VEGAS\2024, etc.
    match = re.search(r'WSOP[E]?\s*(\d{4})', full_path, re.I)
    if match:
        return int(match.group(1))

    # From path: \2024\, \2023\, etc.
    match = re.search(r'[/\\](\d{4})[/\\]', full_path)
    if match:
        return int(match.group(1))

    # From filename: wsop-2024-, WSOP_2024_, etc.
    match = re.search(r'wsop[_-]?(\d{4})', filename, re.I)
    if match:
        return int(match.group(1))

    # From filename: 2024 WSOP
    match = re.search(r'(\d{4})\s*WSOP', filename, re.I)
    if match:
        return int(match.group(1))

    return None


def main():
    if not JSON_PATH.exists():
        print(f'[ERROR] {JSON_PATH} not found. Run scan_nas.py first.')
        return

    data = json.loads(JSON_PATH.read_text(encoding='utf-8'))
    files = data.get('files', [])

    print(f'Loading {len(files)} files from {JSON_PATH}')

    db = next(get_db())

    # Get existing file paths
    existing = set(f.full_path for f in db.query(NasFile.full_path).all())
    print(f'Existing files in DB: {len(existing)}')

    added = 0
    updated = 0

    for f in files:
        full_path = f.get('full_path', '')
        filename = f.get('filename', '')
        size_bytes = f.get('size_bytes', 0)

        # Extract year
        year = extract_year(full_path, filename)

        # Determine if excluded (size < 1GB)
        is_excluded = size_bytes < 1_000_000_000

        # Extract extension
        ext = Path(filename).suffix.lower() if filename else ''

        if full_path in existing:
            # Update existing
            db.query(NasFile).filter(NasFile.full_path == full_path).update({
                'size_bytes': size_bytes,
                'year': year,
                'is_excluded': is_excluded
            })
            updated += 1
        else:
            # Add new
            nas_file = NasFile(
                filename=filename,
                extension=ext,
                full_path=full_path,
                size_bytes=size_bytes,
                year=year,
                is_excluded=is_excluded
            )
            db.add(nas_file)
            added += 1

    db.commit()

    print(f'\n[OK] Added: {added}, Updated: {updated}')

    # Show 2024 stats
    files_2024 = db.query(NasFile).filter(NasFile.year == 2024).all()
    active_2024 = [f for f in files_2024 if not f.is_excluded]
    print(f'\n2024 files in DB: {len(files_2024)} (Active: {len(active_2024)})')


if __name__ == '__main__':
    main()
