"""
PokerGO JSON Data Chunking Optimizer
====================================
대용량 JSON을 최적화된 청크로 분할

출력 구조:
    data/pokergo/chunked/
    ├── index.json              # 전체 인덱스 (경량)
    ├── collections/            # 컬렉션별 청크
    │   ├── high-stakes-poker.json
    │   ├── wsop-2024.json
    │   └── ...
    ├── seasons/                # 시즌별 청크
    │   ├── hsp-season-14.json
    │   └── ...
    └── search/                 # 검색용 경량 인덱스
        ├── titles.json         # 제목만
        └── metadata.json       # 메타데이터만
"""

import json
import re
import gzip
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 경로 설정
DATA_DIR = Path("D:/AI/claude01/pokergo_crawling/data/pokergo")
CHUNK_DIR = DATA_DIR / "chunked"


def slugify(text: str) -> str:
    """텍스트를 파일명 안전한 slug로 변환"""
    text = text.lower()
    text = re.sub(r'[|]', '', text)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text


def load_data():
    """원본 데이터 로드"""
    with open(DATA_DIR / "episodes.json", 'r', encoding='utf-8') as f:
        episodes_data = json.load(f)

    with open(DATA_DIR / "collections.json", 'r', encoding='utf-8') as f:
        collections_data = json.load(f)

    return episodes_data['episodes'], collections_data['collections']


def create_collection_chunks(episodes: list, collections: list):
    """컬렉션별 청크 생성"""
    chunk_dir = CHUNK_DIR / "collections"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    # 컬렉션별 그룹화
    by_collection = defaultdict(list)
    for ep in episodes:
        coll_title = ep.get('collection_title', 'unknown')
        by_collection[coll_title].append(ep)

    chunk_files = []

    for coll_title, coll_episodes in by_collection.items():
        slug = slugify(coll_title)
        filename = f"{slug}.json"
        filepath = chunk_dir / filename

        # 컬렉션 메타데이터 찾기
        coll_meta = next(
            (c for c in collections if c.get('title') == coll_title),
            {'title': coll_title}
        )

        chunk_data = {
            'collection': {
                'id': coll_meta.get('id'),
                'title': coll_title,
                'slug': slug,
                'description': coll_meta.get('description', '')[:200]
            },
            'stats': {
                'total_episodes': len(coll_episodes),
                'total_duration_min': sum(ep.get('duration_min', 0) for ep in coll_episodes),
                'seasons': len(set(ep.get('season_title') for ep in coll_episodes))
            },
            'episodes': coll_episodes
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, ensure_ascii=False, separators=(',', ':'))

        chunk_files.append({
            'collection': coll_title,
            'slug': slug,
            'file': filename,
            'size_kb': filepath.stat().st_size / 1024,
            'episodes': len(coll_episodes)
        })

    return chunk_files


def create_season_chunks(episodes: list):
    """시즌별 청크 생성 (더 세분화된 청킹)"""
    chunk_dir = CHUNK_DIR / "seasons"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    # 시즌별 그룹화
    by_season = defaultdict(list)
    for ep in episodes:
        season_title = ep.get('season_title', 'unknown')
        by_season[season_title].append(ep)

    chunk_files = []

    for season_title, season_episodes in by_season.items():
        slug = slugify(season_title)[:50]  # 파일명 길이 제한
        filename = f"{slug}.json"
        filepath = chunk_dir / filename

        chunk_data = {
            'season': {
                'title': season_title,
                'slug': slug,
                'collection': season_episodes[0].get('collection_title') if season_episodes else None
            },
            'stats': {
                'total_episodes': len(season_episodes),
                'total_duration_min': sum(ep.get('duration_min', 0) for ep in season_episodes)
            },
            'episodes': season_episodes
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, ensure_ascii=False, separators=(',', ':'))

        chunk_files.append({
            'season': season_title,
            'slug': slug,
            'file': filename,
            'size_kb': filepath.stat().st_size / 1024,
            'episodes': len(season_episodes)
        })

    return chunk_files


def create_search_indexes(episodes: list):
    """검색용 경량 인덱스 생성"""
    search_dir = CHUNK_DIR / "search"
    search_dir.mkdir(parents=True, exist_ok=True)

    # 1. 제목 인덱스 (검색용)
    titles_index = [
        {
            'id': ep['id'],
            'title': ep['title'],
            'collection': ep.get('collection_title', ''),
            'season': ep.get('season_title', ''),
            'duration_min': ep.get('duration_min', 0)
        }
        for ep in episodes
    ]

    with open(search_dir / "titles.json", 'w', encoding='utf-8') as f:
        json.dump({
            'total': len(titles_index),
            'items': titles_index
        }, f, ensure_ascii=False, separators=(',', ':'))

    # 2. 메타데이터 인덱스 (통계/필터용)
    metadata = {
        'collections': list(set(ep.get('collection_title', '') for ep in episodes)),
        'seasons': list(set(ep.get('season_title', '') for ep in episodes)),
        'date_range': {
            'earliest': min((ep.get('aired_at', '') for ep in episodes if ep.get('aired_at')), default=''),
            'latest': max((ep.get('aired_at', '') for ep in episodes if ep.get('aired_at')), default='')
        },
        'duration_stats': {
            'min': min(ep.get('duration_min', 0) for ep in episodes),
            'max': max(ep.get('duration_min', 0) for ep in episodes),
            'avg': sum(ep.get('duration_min', 0) for ep in episodes) / len(episodes) if episodes else 0,
            'total': sum(ep.get('duration_min', 0) for ep in episodes)
        }
    }

    with open(search_dir / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # 3. ID 매핑 인덱스 (빠른 조회용)
    id_map = {
        ep['id']: {
            'collection': slugify(ep.get('collection_title', 'unknown')),
            'season': slugify(ep.get('season_title', 'unknown'))[:50]
        }
        for ep in episodes
    }

    with open(search_dir / "id_map.json", 'w', encoding='utf-8') as f:
        json.dump(id_map, f, ensure_ascii=False, separators=(',', ':'))

    return {
        'titles': search_dir / "titles.json",
        'metadata': search_dir / "metadata.json",
        'id_map': search_dir / "id_map.json"
    }


def create_master_index(collection_chunks: list, season_chunks: list, search_files: dict):
    """마스터 인덱스 파일 생성"""
    index = {
        'created_at': datetime.now().isoformat(),
        'version': '1.0',
        'stats': {
            'total_collections': len(collection_chunks),
            'total_seasons': len(season_chunks),
            'total_episodes': sum(c['episodes'] for c in collection_chunks)
        },
        'chunks': {
            'collections': {
                'path': 'collections/',
                'files': collection_chunks
            },
            'seasons': {
                'path': 'seasons/',
                'files': season_chunks
            }
        },
        'search': {
            'titles': 'search/titles.json',
            'metadata': 'search/metadata.json',
            'id_map': 'search/id_map.json'
        }
    }

    with open(CHUNK_DIR / "index.json", 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    return index


def create_compressed_archive(episodes: list):
    """압축된 전체 데이터 아카이브"""
    archive_path = CHUNK_DIR / "episodes.json.gz"

    with gzip.open(archive_path, 'wt', encoding='utf-8') as f:
        json.dump({
            'total': len(episodes),
            'episodes': episodes
        }, f, ensure_ascii=False, separators=(',', ':'))

    return archive_path


def main():
    """메인 실행"""
    print("=" * 50)
    print("PokerGO JSON Data Chunking")
    print("=" * 50)

    # 출력 디렉토리 생성
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)

    # 데이터 로드
    print("\n[1/5] Loading data...")
    episodes, collections = load_data()
    print(f"  Loaded {len(episodes)} episodes, {len(collections)} collections")

    # 컬렉션별 청크
    print("\n[2/5] Creating collection chunks...")
    collection_chunks = create_collection_chunks(episodes, collections)
    print(f"  Created {len(collection_chunks)} collection chunks")

    # 시즌별 청크
    print("\n[3/5] Creating season chunks...")
    season_chunks = create_season_chunks(episodes)
    print(f"  Created {len(season_chunks)} season chunks")

    # 검색 인덱스
    print("\n[4/5] Creating search indexes...")
    search_files = create_search_indexes(episodes)
    print(f"  Created 3 search index files")

    # 마스터 인덱스
    print("\n[5/5] Creating master index and compressed archive...")
    index = create_master_index(collection_chunks, season_chunks, search_files)
    archive_path = create_compressed_archive(episodes)

    # 결과 요약
    print("\n" + "=" * 50)
    print("CHUNKING COMPLETE")
    print("=" * 50)

    # 파일 크기 비교
    original_size = (DATA_DIR / "episodes.json").stat().st_size
    compressed_size = archive_path.stat().st_size

    print(f"\nOriginal size:   {original_size / 1024:.1f} KB")
    print(f"Compressed size: {compressed_size / 1024:.1f} KB ({compressed_size / original_size * 100:.1f}%)")

    print(f"\nOutput directory: {CHUNK_DIR}")
    print(f"\nStructure:")
    print(f"  chunked/")
    print(f"  ├── index.json")
    print(f"  ├── episodes.json.gz")
    print(f"  ├── collections/ ({len(collection_chunks)} files)")
    print(f"  ├── seasons/ ({len(season_chunks)} files)")
    print(f"  └── search/ (3 files)")

    # 상위 청크 파일들
    print(f"\nTop collection chunks by size:")
    for chunk in sorted(collection_chunks, key=lambda x: -x['size_kb'])[:5]:
        print(f"  {chunk['file']}: {chunk['size_kb']:.1f} KB ({chunk['episodes']} episodes)")


if __name__ == "__main__":
    main()
