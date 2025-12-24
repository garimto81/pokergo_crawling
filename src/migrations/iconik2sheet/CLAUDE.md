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
python -m scripts.run_full_metadata --limit 10  # 10개만 테스트
python -m scripts.run_full_metadata --mode combined  # legacy 단일 시트 모드
python -m scripts.run_incremental    # 증분 동기화
python -m scripts.analyze_full_gap   # GG 시트 vs Iconik 갭 분석
python -m scripts.analyze_master_catalog  # Master_Catalog 분류 분석 ★

# ISG 상태 조회 ★★
python -m scripts.check_isg                     # Storage 상태 요약
python -m scripts.check_isg --detail            # 상세 정보
python -m scripts.check_isg --jobs              # 진행 중인 작업 포함

# Jobs 조회 (인제스트 모니터링) ★★
python -m scripts.check_jobs                    # 최근 7일 전체
python -m scripts.check_jobs --status failed    # 실패한 작업만
python -m scripts.check_jobs --days 30          # 최근 30일
python -m scripts.check_jobs --type transfer    # Transfer 작업만
python -m scripts.check_jobs --output csv       # CSV 내보내기
python -m scripts.check_jobs --output json      # JSON 내보내기

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
│   ├── master_catalog.py  # Master_Catalog 기반 분류기 ★★
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
- `get_asset_segments(asset_id, raise_for_404=True)` - 세그먼트 (타임코드)
  - **GENERIC 타입만** 타임코드 추출 (COMMENT/MARKER 제외)
  - `segment.metadata_values`는 항상 비어있음 → Asset Metadata API 사용
- `get_collections_page(page)` / `get_all_collections()` - 컬렉션
- `health_check()` - 연결 테스트

**Jobs API** (ISG 인제스트 모니터링) ★★:
- `get_jobs_page(page, status, job_type, date_from)` - 작업 목록 페이지
- `get_all_jobs(status, job_type, days)` - 전체 작업 조회 (Generator)
- `get_job(job_id)` - 단일 작업 조회
- `get_failed_jobs(days, job_type)` - 실패한 작업만 조회

**Iconik 데이터 구조** (상세: `docs/etc/ICONIK_DATA_STRUCTURE.md`):
- **Asset (type=ASSET)**: 타임코드는 Segment API에서 조회
- **Subclip (type=SUBCLIP)**: 타임코드는 **Asset 자체**에 저장됨 ★
  - `time_start_milliseconds`, `time_end_milliseconds` 필드
  - `original_asset_id`: Parent Asset ID
  - Segment API는 빈 리스트 반환

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
result = sync.run(skip_sampling=False, limit=10)  # 10개만 테스트
result = sync.run()  # 전체 동기화
```

**주요 기능**:
- **Master_Catalog 기반 분류**: General vs Subclip 자동 분류 ★★
- **Subclip 타임코드 처리**: Asset 자체 또는 Segment에서 추출
- **샘플링**: 10개 Asset으로 메타데이터 가용성 확인
- **Graceful 404**: 메타데이터 없는 Asset도 계속 처리
- **통계 리포트**: 성공/404/에러 카운트, 필드 커버리지

**분류 로직** (v3.0 - Master_Catalog 기반):
```python
from sync.master_catalog import get_classifier

classifier = get_classifier()

# Master_Catalog에 Filename 매칭 → General
# Master_Catalog에 없음 → Subclip
is_subclip = classifier.is_subclip(asset.title)
```

**분류 기준**:
| 조건 | 분류 | 시트 |
|------|------|------|
| title ∈ Master_Catalog | General | Iconik_General_Metadata |
| title ∉ Master_Catalog | Subclip | Iconik_Subclips_Metadata |

**타임코드 추출 로직** (v3.0):
```python
if is_subclip:
    if asset.original_asset_id and asset.time_start_milliseconds:
        # type=SUBCLIP: Asset 자체에 타임코드 있음
        time_start = asset.time_start_milliseconds
    else:
        # Hand clips 등: Segment API에서 추출
        segments = client.get_asset_segments(asset.id)
        # GENERIC segment만 사용
else:
    # General: Segment API에서 타임코드 추출
    segments = client.get_asset_segments(asset.id)
```

**메타데이터 추출**: Asset Metadata API 사용 (`/metadata/v1/assets/{id}/views/{view_id}/`)

**출력 예시** (v3.0):
```
[MasterCatalog] Loaded 1051 unique filenames
Processed 2854 assets
  General (ASSET): 1042
  Subclips: 1812
```

### MasterCatalogClassifier (`sync/master_catalog.py`) ★★

```python
from sync.master_catalog import get_classifier

classifier = get_classifier()

# Master_Catalog에 있으면 General (NAS 원본 파일)
classifier.is_general_asset("2010 WSOP ME08")  # True

# Master_Catalog에 없으면 Subclip (파생 클립)
classifier.is_subclip("1217_Hand_31_Jaffe...")  # True
```

**동작 원리**:
1. UDM metadata 스프레드시트의 Master_Catalog 시트 조회
2. Filename 컬럼에서 확장자 제외한 파일명 Set 생성 (1051개)
3. Iconik Asset title과 매칭하여 분류

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
| Iconik_General_Metadata | 35 | General Asset (Master_Catalog 매칭) ★★ |
| Iconik_Subclips_Metadata | 37 | Subclip (Master_Catalog 미매칭) ★★ |
| Iconik_Assets | 7 | 기본 Asset 정보 |
| Iconik_Full_Metadata | 35 | 전체 메타데이터 (legacy, combined mode) |
| Iconik_Collections | 5 | 컬렉션 계층 |
| Sync_Log | 7 | 동기화 이력 |

**v3.0 분리 모드** (기본):
- `Iconik_General_Metadata`: 1,042개 (NAS 원본 파일)
- `Iconik_Subclips_Metadata`: 1,812개 (파생 클립 + Hand clips)

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
