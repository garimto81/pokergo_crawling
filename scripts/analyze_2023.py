"""Analyze 2023 NAS files."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.database import get_db
from src.nams.api.database.models import NasFile

db = next(get_db())

# 2023 active files
files = db.query(NasFile).filter(
    NasFile.year == 2023,
    NasFile.is_excluded == False
).order_by(NasFile.full_path).all()

wsop_files = [f for f in files if 'GOG' not in f.full_path.upper()]
gog_files = [f for f in files if 'GOG' in f.full_path.upper()]

print('2023 Active Files Detail')
print('=' * 80)

print(f'\n[GOG - Game of Gold] {len(gog_files)} files')
for f in gog_files[:8]:
    size_gb = f.size_bytes / (1024**3) if f.size_bytes else 0
    print(f'  [{size_gb:.1f}GB] {f.filename}')
if len(gog_files) > 8:
    print(f'  ... and {len(gog_files) - 8} more')

print(f'\n[WSOP 2023] {len(wsop_files)} files')

# Group by folder
folders = {}
for f in wsop_files:
    # Extract folder from path
    parts = f.full_path.replace('/', '\\').split('\\')
    # Find WSOP-related folder
    folder = 'Other'
    for i, p in enumerate(parts):
        if 'WSOP' in p.upper() or 'BRACELET' in p.upper() or 'MAIN EVENT' in p.upper():
            folder = p
            break
    folders.setdefault(folder, []).append(f)

for folder, folder_files in sorted(folders.items()):
    print(f'\n  [{folder}] {len(folder_files)} files')
    for f in folder_files[:3]:
        size_gb = f.size_bytes / (1024**3) if f.size_bytes else 0
        print(f'    [{size_gb:.1f}GB] {f.filename[:60]}')
    if len(folder_files) > 3:
        print(f'    ... and {len(folder_files) - 3} more')

# Total size
total_size = sum(f.size_bytes or 0 for f in files) / (1024**3)
print(f'\n' + '=' * 80)
print(f'Total: {len(files)} files ({total_size:.1f} GB)')
print(f'  - GOG: {len(gog_files)} files')
print(f'  - WSOP: {len(wsop_files)} files')
