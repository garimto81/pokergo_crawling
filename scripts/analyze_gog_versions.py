"""Analyze GOG episodes by version for PRIMARY selection."""
import sys
import io
import re
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.database import get_db
from src.nams.api.database.models import NasFile

db = next(get_db())

files = db.query(NasFile).filter(
    NasFile.year == 2023,
    NasFile.is_excluded == False
).all()

gog = [f for f in files if 'GOG' in f.full_path.upper()]

# Extract episode and version
episodes = defaultdict(list)
for f in gog:
    match = re.search(r'^E(\d+)_GOG', f.filename)
    if match:
        ep = int(match.group(1))
        fn = f.filename
        if '찐최종' in fn:
            ver = ('찐최종', 4)
        elif '최종' in fn and '찐최종' not in fn:
            ver = ('최종', 3)
        elif '클린본' in fn:
            ver = ('클린본', 1)
        else:
            ver = ('작업본', 2)
        episodes[ep].append((ver[0], ver[1], fn))

print('GOG Episode별 버전 분석:')
print('=' * 90)
print(f'{"Ep":<4} {"버전들":<25} {"최고우선순위":<10} {"PRIMARY 후보"}')
print('-' * 90)

for ep in sorted(episodes.keys()):
    versions = episodes[ep]
    versions.sort(key=lambda x: x[1], reverse=True)
    ver_list = ', '.join([v[0] for v in versions])
    highest = versions[0]
    print(f'{ep:<4} {ver_list:<25} {highest[0]:<10} {highest[2][:40]}')

print()
print('=' * 90)
print('분석 결과:')
print('-' * 90)

# Count by highest version
highest_counts = defaultdict(int)
for ep, versions in episodes.items():
    versions.sort(key=lambda x: x[1], reverse=True)
    highest_counts[versions[0][0]] += 1

for ver in ['찐최종', '최종', '작업본', '클린본']:
    if ver in highest_counts:
        print(f'  {ver} PRIMARY: {highest_counts[ver]}개 에피소드')

print()
print('결론: 각 에피소드에서 최고 우선순위 버전 1개를 PRIMARY로 선택')
print('  우선순위: 찐최종(4) > 최종(3) > 작업본(2) > 클린본(1)')
