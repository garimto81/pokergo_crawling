"""
NAS-PokerGO Matching Data Export & Chunking
============================================
NAS-PokerGO 매칭 결과를 JSON으로 저장하고 최적화된 청크로 분할

출력 구조:
    data/matching/
    ├── index.json              # 전체 인덱스 (경량)
    ├── full_matching.json      # 전체 매칭 결과
    ├── full_matching.json.gz   # 압축 아카이브
    ├── by_year/                # 연도별 청크
    │   ├── 2011.json
    │   ├── 2012.json
    │   └── ...
    ├── by_directory/           # 디렉토리별 청크
    │   ├── archive-wsop.json
    │   └── ...
    └── search/                 # 검색용 경량 인덱스
        ├── matched.json        # 매칭된 항목만
        ├── unmatched.json      # 미매칭 항목만
        └── summary.json        # 통계 요약
"""

import json
import re
import gzip
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 경로 설정
DATA_DIR = Path("D:/AI/claude01/pokergo_crawling/data")
NAS_FILE = DATA_DIR / "sources/nas/nas_files.json"
POKERGO_FILE = DATA_DIR / "pokergo/episodes.json"
OUTPUT_DIR = DATA_DIR / "matching"

MIN_SIZE_GB = 1.0
NAS_BASE_PATH = r'\\10.10.100.122\ggpwsop\WSOP backup'


def slugify(text: str) -> str:
    """텍스트를 파일명 안전한 slug로 변환"""
    text = text.lower()
    text = re.sub(r'[|\\/:*?"<>]', '', text)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text[:50] if len(text) > 50 else text


def extract_year_from_text(text):
    """Extract year from text, excluding PRE-XXXX patterns."""
    text = str(text)
    cleaned = re.sub(r'PRE-\d{4}', '', text, flags=re.IGNORECASE)
    match = re.search(r'(19|20)\d{2}', cleaned)
    return match.group(0) if match else None


def load_matching_data():
    """매칭 데이터 생성 (create_nas_pokergo_sheet.py 로직 재사용)"""
    from difflib import SequenceMatcher

    # Load NAS data
    with open(NAS_FILE, 'r', encoding='utf-8') as f:
        nas_data = json.load(f)
    nas_files = nas_data.get('files', [])

    # Load PokerGO data
    with open(POKERGO_FILE, 'r', encoding='utf-8') as f:
        pokergo_data = json.load(f)

    pokergo_all = [ep for ep in pokergo_data.get('episodes', [])
                   if 'WSOP' in ep.get('collection_title', '')]
    pokergo_eps = [ep for ep in pokergo_all
                   if '|' in ep.get('title', '')]

    # Build PokerGO index
    pokergo_by_year = defaultdict(list)
    for ep in pokergo_eps:
        title = ep.get('title', '')
        year = extract_year_from_text(title)
        if year:
            pokergo_by_year[year].append({
                'title': title,
                'collection': ep.get('collection_title', ''),
                'season': ep.get('season_title', ''),
                'duration_min': ep.get('duration_min', 0)
            })

    # Helper functions
    def normalize_text(text):
        text = str(text).lower()
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def text_similarity(a, b):
        return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()

    def has_wsop(filename, directory):
        combined = f"{filename} {directory}".upper()
        return 'WSOP' in combined

    def extract_wsop_code_info(text):
        text_upper = str(text).upper()
        ws_match = re.search(r'WS(\d{2})[_\-]', text_upper)
        if ws_match:
            year_2digit = int(ws_match.group(1))
            year = f"20{year_2digit:02d}" if year_2digit <= 30 else f"19{year_2digit:02d}"
            me_match = re.search(r'ME(\d{1,2})', text_upper)
            if me_match:
                return year, 'main_event', int(me_match.group(1))
            return year, None, None

        wsop_match = re.search(r'WSOP(\d{2})[_\-]', text_upper)
        if wsop_match:
            year_2digit = int(wsop_match.group(1))
            year = f"20{year_2digit:02d}" if year_2digit <= 30 else f"19{year_2digit:02d}"
            me_match = re.search(r'ME(\d{1,2})', text_upper)
            if me_match:
                return year, 'main_event', int(me_match.group(1))
            return year, None, None

        return None, None, None

    # Process NAS files
    all_items = []
    stats = {
        'total_nas_files': len(nas_files),
        'excluded_small': 0,
        'excluded_clip': 0,
        'wsop_files': 0,
        'non_wsop_files': 0,
        'matched': 0,
        'unmatched': 0
    }

    for f in nas_files:
        filename = f.get('filename', '')
        directory = f.get('directory', '')
        rel_path = f.get('relative_path', '')
        size_gb = f.get('size_bytes', 0) / (1024**3)
        origin = f'{NAS_BASE_PATH}\\{rel_path}' if rel_path else ''

        # Skip small files
        if size_gb < MIN_SIZE_GB:
            stats['excluded_small'] += 1
            continue

        # Skip clip/circuit/paradise
        combined_lower = f"{filename} {directory}".lower()
        if 'clip' in combined_lower or 'circuit' in combined_lower or 'paradise' in combined_lower:
            stats['excluded_clip'] += 1
            continue

        is_wsop = has_wsop(filename, directory)
        code_year, code_event_type, code_episode = extract_wsop_code_info(filename)

        item = {
            'origin': origin,
            'filename': filename,
            'directory': directory,
            'relative_path': rel_path,
            'size_gb': round(size_gb, 2),
            'is_wsop': is_wsop,
            'is_matched': False,
            'matched_pokergo': '',
            'matched_collection': '',
            'matched_season': '',
            'match_score': 0,
            'match_reason': '',
            'source': 'NAS'
        }

        if not is_wsop:
            item['match_reason'] = '[제외] WSOP 콘텐츠 아님'
            stats['non_wsop_files'] += 1
        else:
            stats['wsop_files'] += 1
            nas_year = code_year or extract_year_from_text(f"{filename} {directory}")
            item['year'] = nas_year or ''

            if code_year and code_event_type is None:
                # WS code but not ME
                code_match = re.search(r'WS\d{2}_([A-Z]{2})\d', filename.upper())
                code_type = code_match.group(1) if code_match else 'unknown'
                item['match_reason'] = f'[{nas_year}] WS코드 {code_type} 타입 - ME만 매칭'
            elif nas_year and nas_year in pokergo_by_year:
                # Try matching
                combined_text = f"{filename} {directory}"
                best_score = 0
                best_match = None

                for ep in pokergo_by_year[nas_year]:
                    score = text_similarity(ep['title'], combined_text)
                    if score > best_score:
                        best_score = score
                        best_match = ep

                threshold = 1.0 if code_episode else 0.35
                if code_episode or best_score > threshold:
                    item['is_matched'] = True
                    item['matched_pokergo'] = best_match['title']
                    item['matched_collection'] = best_match['collection']
                    item['matched_season'] = best_match['season']
                    item['match_score'] = round(best_score * 100, 1)
                    item['match_reason'] = f'[{nas_year}] 매칭 완료'
                    stats['matched'] += 1
                else:
                    item['match_reason'] = f'[{nas_year}] 유사도 부족 ({best_score*100:.0f}%)'
            elif nas_year:
                item['match_reason'] = f'[{nas_year}] PokerGO 데이터 없음'
            else:
                item['match_reason'] = '[연도미상] 연도 추출 실패'

        if not item['is_matched'] and item['is_wsop']:
            stats['unmatched'] += 1

        all_items.append(item)

    # Add PokerGO-only episodes
    matched_titles = set(item['matched_pokergo'] for item in all_items if item['is_matched'])
    pokergo_only = []

    for ep in pokergo_eps:
        title = ep.get('title', '')
        if title not in matched_titles:
            year = extract_year_from_text(title)
            pokergo_only.append({
                'origin': '',
                'filename': '',
                'directory': '[PokerGO Only]',
                'relative_path': '',
                'size_gb': 0,
                'is_wsop': True,
                'is_matched': False,
                'year': year or '',
                'matched_pokergo': title,
                'matched_collection': ep.get('collection_title', ''),
                'matched_season': ep.get('season_title', ''),
                'match_score': 0,
                'match_reason': f'[{year}] NAS에 해당 파일 없음',
                'source': 'PokerGO'
            })

    stats['pokergo_only'] = len(pokergo_only)

    return all_items + pokergo_only, stats


def create_year_chunks(items: list):
    """연도별 청크 생성"""
    chunk_dir = OUTPUT_DIR / "by_year"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    by_year = defaultdict(list)
    for item in items:
        year = item.get('year', '')
        if year:
            by_year[year].append(item)
        else:
            by_year['unknown'].append(item)

    chunk_files = []
    for year, year_items in sorted(by_year.items()):
        filename = f"{year}.json"
        filepath = chunk_dir / filename

        matched = sum(1 for i in year_items if i['is_matched'])
        nas_items = [i for i in year_items if i['source'] == 'NAS']
        pg_items = [i for i in year_items if i['source'] == 'PokerGO']

        chunk_data = {
            'year': year,
            'stats': {
                'total': len(year_items),
                'matched': matched,
                'nas_files': len(nas_items),
                'pokergo_only': len(pg_items),
                'total_size_gb': round(sum(i['size_gb'] for i in year_items), 2)
            },
            'items': year_items
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, ensure_ascii=False, separators=(',', ':'))

        chunk_files.append({
            'year': year,
            'file': filename,
            'size_kb': round(filepath.stat().st_size / 1024, 1),
            'count': len(year_items),
            'matched': matched
        })

    return chunk_files


def create_directory_chunks(items: list):
    """디렉토리별 청크 생성"""
    chunk_dir = OUTPUT_DIR / "by_directory"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    by_dir = defaultdict(list)
    for item in items:
        if item['source'] == 'NAS':
            dir_name = item.get('directory', '').split('\\')[0] if item.get('directory') else 'root'
            by_dir[dir_name].append(item)

    chunk_files = []
    for dir_name, dir_items in sorted(by_dir.items()):
        slug = slugify(dir_name) or 'root'
        filename = f"{slug}.json"
        filepath = chunk_dir / filename

        matched = sum(1 for i in dir_items if i['is_matched'])

        chunk_data = {
            'directory': dir_name,
            'stats': {
                'total': len(dir_items),
                'matched': matched,
                'match_rate': round(matched / len(dir_items) * 100, 1) if dir_items else 0,
                'total_size_gb': round(sum(i['size_gb'] for i in dir_items), 2)
            },
            'items': dir_items
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, ensure_ascii=False, separators=(',', ':'))

        chunk_files.append({
            'directory': dir_name,
            'slug': slug,
            'file': filename,
            'size_kb': round(filepath.stat().st_size / 1024, 1),
            'count': len(dir_items),
            'matched': matched
        })

    return chunk_files


def create_search_indexes(items: list, stats: dict):
    """검색용 경량 인덱스 생성"""
    search_dir = OUTPUT_DIR / "search"
    search_dir.mkdir(parents=True, exist_ok=True)

    # Matched items only
    matched_items = [
        {
            'filename': i['filename'],
            'pokergo_title': i['matched_pokergo'],
            'year': i.get('year', ''),
            'score': i['match_score'],
            'size_gb': i['size_gb']
        }
        for i in items if i['is_matched']
    ]

    with open(search_dir / "matched.json", 'w', encoding='utf-8') as f:
        json.dump({
            'total': len(matched_items),
            'items': matched_items
        }, f, ensure_ascii=False, separators=(',', ':'))

    # Unmatched items only
    unmatched_items = [
        {
            'filename': i['filename'],
            'directory': i['directory'],
            'year': i.get('year', ''),
            'reason': i['match_reason'],
            'size_gb': i['size_gb'],
            'source': i['source']
        }
        for i in items if not i['is_matched'] and i['is_wsop']
    ]

    with open(search_dir / "unmatched.json", 'w', encoding='utf-8') as f:
        json.dump({
            'total': len(unmatched_items),
            'items': unmatched_items
        }, f, ensure_ascii=False, separators=(',', ':'))

    # Summary stats
    summary = {
        'created_at': datetime.now().isoformat(),
        **stats,
        'years': sorted(set(i.get('year', '') for i in items if i.get('year'))),
        'directories': sorted(set(i['directory'].split('\\')[0] for i in items if i['source'] == 'NAS' and i['directory']))
    }

    with open(search_dir / "summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return {
        'matched': search_dir / "matched.json",
        'unmatched': search_dir / "unmatched.json",
        'summary': search_dir / "summary.json"
    }


def create_master_index(year_chunks: list, dir_chunks: list, stats: dict):
    """마스터 인덱스 생성"""
    index = {
        'created_at': datetime.now().isoformat(),
        'version': '1.0',
        'stats': stats,
        'chunks': {
            'by_year': {
                'path': 'by_year/',
                'files': year_chunks
            },
            'by_directory': {
                'path': 'by_directory/',
                'files': dir_chunks
            }
        },
        'search': {
            'matched': 'search/matched.json',
            'unmatched': 'search/unmatched.json',
            'summary': 'search/summary.json'
        },
        'archives': {
            'full': 'full_matching.json',
            'compressed': 'full_matching.json.gz'
        }
    }

    with open(OUTPUT_DIR / "index.json", 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    return index


def save_full_data(items: list, stats: dict):
    """전체 데이터 저장 (JSON + 압축)"""
    full_data = {
        'created_at': datetime.now().isoformat(),
        'stats': stats,
        'total': len(items),
        'items': items
    }

    # Full JSON
    full_path = OUTPUT_DIR / "full_matching.json"
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)

    # Compressed
    gz_path = OUTPUT_DIR / "full_matching.json.gz"
    with gzip.open(gz_path, 'wt', encoding='utf-8') as f:
        json.dump(full_data, f, ensure_ascii=False, separators=(',', ':'))

    return full_path, gz_path


def main():
    print("=" * 60)
    print("NAS-PokerGO Matching Data Export & Chunking")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load and process data
    print("\n[1/6] Loading and processing matching data...")
    items, stats = load_matching_data()
    print(f"  Total items: {len(items)}")
    print(f"  NAS files processed: {stats['wsop_files'] + stats['non_wsop_files']}")
    print(f"  Matched: {stats['matched']}")
    print(f"  PokerGO only: {stats['pokergo_only']}")

    # Save full data
    print("\n[2/6] Saving full matching data...")
    full_path, gz_path = save_full_data(items, stats)
    print(f"  Full JSON: {full_path.stat().st_size / 1024:.1f} KB")
    print(f"  Compressed: {gz_path.stat().st_size / 1024:.1f} KB")

    # Year chunks
    print("\n[3/6] Creating year chunks...")
    year_chunks = create_year_chunks(items)
    print(f"  Created {len(year_chunks)} year chunks")

    # Directory chunks
    print("\n[4/6] Creating directory chunks...")
    dir_chunks = create_directory_chunks(items)
    print(f"  Created {len(dir_chunks)} directory chunks")

    # Search indexes
    print("\n[5/6] Creating search indexes...")
    search_files = create_search_indexes(items, stats)
    print("  Created 3 search index files")

    # Master index
    print("\n[6/6] Creating master index...")
    index = create_master_index(year_chunks, dir_chunks, stats)

    # Summary
    print("\n" + "=" * 60)
    print("EXPORT & CHUNKING COMPLETE")
    print("=" * 60)

    original_size = full_path.stat().st_size
    compressed_size = gz_path.stat().st_size

    print(f"\nOriginal size:   {original_size / 1024:.1f} KB")
    print(f"Compressed size: {compressed_size / 1024:.1f} KB ({compressed_size / original_size * 100:.1f}%)")

    print(f"\nOutput directory: {OUTPUT_DIR}")
    print(f"\nStructure:")
    print(f"  matching/")
    print(f"  ├── index.json")
    print(f"  ├── full_matching.json")
    print(f"  ├── full_matching.json.gz")
    print(f"  ├── by_year/ ({len(year_chunks)} files)")
    print(f"  ├── by_directory/ ({len(dir_chunks)} files)")
    print(f"  └── search/ (3 files)")

    print(f"\nYear chunks:")
    for chunk in sorted(year_chunks, key=lambda x: x['year']):
        print(f"  {chunk['year']}: {chunk['count']} items, {chunk['matched']} matched ({chunk['size_kb']:.1f} KB)")

    print(f"\nDirectory chunks (top 5 by count):")
    for chunk in sorted(dir_chunks, key=lambda x: -x['count'])[:5]:
        print(f"  {chunk['directory']}: {chunk['count']} items, {chunk['matched']} matched ({chunk['size_kb']:.1f} KB)")


if __name__ == "__main__":
    main()
