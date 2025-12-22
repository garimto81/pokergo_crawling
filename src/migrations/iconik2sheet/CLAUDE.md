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
python -m scripts.run_full_sync      # 전체 동기화 (기본 정보 7컬럼)
python -m scripts.run_full_metadata  # 전체 메타데이터 (35컬럼) ★
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
│   ├── exceptions.py      # 커스텀 예외 (404 graceful handling)
│   └── models.py          # Pydantic 모델
├── sheets/
│   └── writer.py          # Sheets 쓰기
├── sync/
│   ├── full_sync.py       # 전체 동기화
│   ├── full_metadata_sync.py # 전체 메타데이터 (35컬럼) ★
│   ├── stats.py           # 동기화 통계 (SyncStats)
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
- `get_asset_metadata(asset_id, view_id, raise_for_404=True)` - 메타데이터
- `get_asset_segments(asset_id, raise_for_404=True)` - 세그먼트 (timecode + **metadata_values**)
  - **현재**: 타임코드만 추출
  - **필요**: metadata_values 필드도 추출 필요 (Segment에 메타데이터 저장됨)
- `get_collections_page(page)` / `get_all_collections()` - 컬렉션
- `health_check()` - 연결 테스트

**Iconik 데이터 구조** (상세: `docs/etc/ICONIK_DATA_STRUCTURE.md`):
- **Segment** = 타임코드 + 메타데이터 (Generic 타입이 메타데이터 저장용)
- **Subclip** = Parent Segment에서 파생된 별도 Asset (양방향 동기화)

**Graceful 404 Handling** (v1.1+):
```python
# 메타데이터 없는 Asset도 계속 처리
metadata = client.get_asset_metadata(asset_id, view_id, raise_for_404=False)
if metadata is None:
    # 메타데이터 없음 - 계속 진행
    pass

# 세그먼트 없으면 빈 리스트 반환
segments = client.get_asset_segments(asset_id, raise_for_404=False)  # []
```

**예외 클래스** (`iconik/exceptions.py`):
- `IconikNotFoundError` - 404 Not Found
- `IconikAuthError` - 401/403 인증 오류
- `IconikRateLimitError` - 429 Too Many Requests

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

### FullMetadataSync (`sync/full_metadata_sync.py`) ★

```python
sync = FullMetadataSync()
result = sync.run(skip_sampling=False)  # 35컬럼 메타데이터 동기화
```

**주요 기능**:
- **샘플링**: 10개 Asset으로 메타데이터 가용성 확인
- **Graceful 404**: 메타데이터 없는 Asset도 계속 처리
- **통계 리포트**: 성공/404/에러 카운트, 필드 커버리지

**출력 예시**:
```
[Metadata]
  Success: 2,427 (85.5%)
  Not found (404): 413

[Field Coverage]
  Source: 92.3%
  Description: 80.6%
```

### SyncStats (`sync/stats.py`)

동기화 통계를 추적하는 데이터클래스:
```python
from sync import SyncStats

stats = SyncStats()
stats.record_metadata_success({"Description": "test"})
stats.record_metadata_404("asset-123")

report = stats.to_report()  # 상세 보고서 생성
```

### 출력 시트

| 시트명 | 컬럼 수 | 내용 |
|--------|---------|------|
| Iconik_Assets | 7 | 기본 Asset 정보 |
| Iconik_Full_Metadata | 35 | 전체 메타데이터 (GGmetadata_and_timestamps 동일) ★ |
| Iconik_Collections | 5 | 컬렉션 계층 |
| Sync_Log | 7 | 동기화 이력 |

## Environment

```env
# Iconik API
ICONIK_APP_ID=your-app-id
ICONIK_AUTH_TOKEN=your-auth-token
ICONIK_BASE_URL=https://app.iconik.io
ICONIK_METADATA_VIEW_ID=view-uuid  # ★ 메타데이터 추출에 필수

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
