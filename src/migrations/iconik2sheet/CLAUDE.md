# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Iconik MAM 시스템 데이터를 Google Sheets로 내보내기/동기화하는 Python CLI 도구

## Commands

```powershell
# 환경 설정
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cp .env.example .env

# 스크립트 실행
python -m scripts.test_connection    # 연결 테스트
python -m scripts.run_full_sync      # 전체 동기화
python -m scripts.run_incremental    # 증분 동기화

# 린트/테스트
ruff check . --fix
pytest tests/ -v
```

## Architecture

```
iconik2sheet/
├── config/
│   └── settings.py        # Pydantic Settings
├── iconik/
│   ├── client.py          # Iconik API 클라이언트
│   └── models.py          # Pydantic 모델
├── sheets/
│   └── writer.py          # Sheets 쓰기
├── sync/
│   ├── full_sync.py       # 전체 동기화
│   ├── incremental_sync.py # 증분 동기화
│   └── state.py           # 상태 관리
└── scripts/               # CLI 엔트리포인트
```

### IconikClient (`iconik/client.py`)

```python
with IconikClient() as client:
    # 페이지네이션 지원 Generator
    for asset in client.get_all_assets():
        print(asset.id)

    # 단일 조회
    asset = client.get_asset("asset-id")
```

**API 메서드**:
- `get_assets_page(page)` / `get_all_assets()` - 페이지네이션 지원
- `get_asset(asset_id)` - 단일 Asset 조회
- `get_asset_metadata(asset_id, view_id)` - 메타데이터
- `get_collections_page(page)` / `get_all_collections()` - 컬렉션
- `health_check()` - 연결 테스트

### FullSync (`sync/full_sync.py`)

```python
sync = FullSync()
result = sync.run()  # 전체 동기화 실행
```

**동기화 흐름**:
1. `_sync_assets()` - Iconik에서 모든 Asset 가져와 Sheets에 쓰기
2. `_sync_collections()` - 모든 Collection 가져와 Sheets에 쓰기
3. `SyncState.mark_sync_complete()` - 상태 저장
4. `SheetsWriter.write_sync_log()` - 로그 기록

### 출력 시트

| 시트명 | 내용 |
|--------|------|
| Iconik_Assets | 전체 Asset 목록 |
| Iconik_Collections | 컬렉션 계층 |
| Iconik_Metadata | 메타데이터 (선택) |
| Sync_Log | 동기화 이력 |

## Environment

```env
# Iconik API
ICONIK_APP_ID=your-app-id
ICONIK_AUTH_TOKEN=your-auth-token
ICONIK_BASE_URL=https://app.iconik.io

# Google Sheets
GOOGLE_SERVICE_ACCOUNT_PATH=path/to/service_account.json
GOOGLE_SPREADSHEET_ID=spreadsheet-id

# 선택적
STATE_FILE=data/sync_state.json
BATCH_SIZE=100
RATE_LIMIT_PER_SEC=50
```

## Key Dependencies

| 패키지 | 용도 |
|--------|------|
| httpx | Iconik API 호출 |
| google-api-python-client | Sheets API |
| pydantic-settings | 환경변수 관리 |
| rich | CLI 출력 (Progress bar) |
