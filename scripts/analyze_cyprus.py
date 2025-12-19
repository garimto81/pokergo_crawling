"""Analyze Cyprus files for event information."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding='utf-8')

from src.nams.api.database import get_db
from src.nams.api.database.models import NasFile

db = next(get_db())
files = db.query(NasFile).filter(
    NasFile.year == 2025,
    NasFile.is_excluded == False
).all()

# Cyprus/MPP 파일 분석
print('=== Cyprus/MPP Files ===')
for f in files:
    p = (f.full_path or '').upper()
    if 'CYPRUS' in p or ('MPP' in p and 'LAS VEGAS' not in p and 'EUROPE' not in p):
        fn = f.filename.replace('\u2013', '-')  # en-dash to hyphen
        print(f'File: {fn}')
        # 경로에서 이벤트 폴더 추출
        parts = f.full_path.split('\\') if f.full_path else []
        for part in parts:
            if any(kw in part for kw in ['PokerOK', 'Luxon', 'MPP Main', 'Circuit', 'Mystery']):
                print(f'  Event folder: {part}')
        print()
