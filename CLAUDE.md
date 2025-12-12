# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube PokerGO 채널 메타데이터 크롤러. **다운로드 기능 없음** - 4K Downloader 외부 프로그램 사용.

**핵심 기능:**
- YouTube 채널 메타데이터 수집 (yt-dlp)
- SQLite 데이터베이스 저장
- URL 내보내기 (4K Downloader용)
- YouTube-NAS 비디오 매칭 시스템 (계획)

## Commands

```powershell
# Install
pip install -e .

# Crawl YouTube channel
pokergo crawl youtube              # Basic metadata (fast)
pokergo crawl youtube --full       # Full metadata including view/like counts
pokergo crawl youtube -n 100       # Last 100 videos only

# List data
pokergo list videos                # Video list
pokergo list playlists             # Playlist list
pokergo stats                      # Database statistics
pokergo search "WSOP"              # Search by title

# Export
pokergo export                     # Export to chunked JSON (5MB/file)
pokergo export-urls                # URL list for 4K Downloader

# Lint & Test
ruff check src/ --fix
pytest tests/test_database.py -v
```

## Architecture

```
src/pokergo_downloader/
├── main.py             # CLI entrypoint (Typer)
├── config.py           # Settings, path management
├── exporter.py         # Chunked JSON export
├── database/
│   ├── models.py       # SQLAlchemy models (Channel, Playlist, Video, etc.)
│   └── repository.py   # Repository pattern for DB access
├── crawler/
│   └── youtube.py      # yt-dlp wrapper for metadata extraction
└── downloader/         # Reserved for Phase 2 (not implemented)
```

### Key Data Models

- **Source**: `YOUTUBE`, `POKERGO_WEB`, `ARCHIVE`
- **DownloadStatus**: `PENDING`, `QUEUED`, `DOWNLOADING`, `COMPLETED`, `FAILED`, `SKIPPED`
- **Video**: Core entity with metadata (title, duration, view_count, etc.)
- **ContentMapping**: Cross-source linking (YouTube ↔ NAS)

### Data Flow

1. `YouTubeCrawler.full_sync()` → yt-dlp extracts metadata
2. `Repository.upsert_video()` → SQLite storage
3. `ChunkedExporter.export_all()` → JSON files + index.json
4. `export-urls` → URL list for external downloader

## Data Storage

```
data/
├── db/pokergo.db                    # SQLite database
├── sources/
│   ├── youtube/exports/
│   │   ├── index.json               # Searchable video index
│   │   ├── channel.json             # Channel info
│   │   ├── videos/videos_001.json   # Chunked video data
│   │   ├── playlists/               # Playlist data
│   │   └── urls/youtube_urls.txt    # 4K Downloader URLs
│   └── nas/                         # NAS scan results
└── analysis/                        # Analysis outputs
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/scan_nas.py` | Scan NAS and extract file metadata |
| `scripts/export_by_playlist.py` | Export videos by playlist |
| `scripts/test_matching.py` | Test YouTube-NAS matching |

## Tech Stack

- **Python** 3.11+
- **yt-dlp** - Metadata extraction (no download)
- **SQLAlchemy 2.0** - ORM
- **Typer + Rich** - CLI
- **ruff** - Linter
- **pytest** - Testing

## Key Design Decisions

1. **No direct download**: YouTube policy compliance - use 4K Downloader
2. **Chunked exports**: 5MB per JSON file for large datasets
3. **Multi-source**: Supports YouTube, PokerGO.com, and local Archive files
4. **Repository pattern**: Clean separation of DB access logic

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POKERGO_DATA_DIR` | `data` | Data directory path |
| `POKERGO_MAX_FILE_SIZE_MB` | `5` | Max export file size |
| `POKERGO_VERBOSE` | `false` | Verbose logging |
