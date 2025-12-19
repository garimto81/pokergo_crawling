# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Google Sheets 데이터를 Iconik MAM 시스템으로 마이그레이션하는 Python CLI 도구

## Commands

```powershell
# 환경 설정
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cp .env.example .env

# 스크립트 실행
python -m scripts.test_connection    # 연결 테스트
python -m scripts.dry_run            # Dry run (실제 업로드 없음)
python -m scripts.migrate            # 마이그레이션 실행

# 린트/테스트
ruff check . --fix
pytest tests/ -v
```

## Architecture

```
sheet2iconik/
├── config/
│   └── settings.py        # Pydantic Settings (ICONIK_*, GOOGLE_*)
├── clients/
│   ├── iconik_client.py   # Iconik API (httpx + tenacity)
│   └── sheets_client.py   # Google Sheets API
├── services/              # 비즈니스 로직
│   ├── sheet_reader.py
│   ├── data_transformer.py
│   ├── iconik_uploader.py
│   └── migration_tracker.py
└── scripts/               # CLI 엔트리포인트
    ├── migrate.py
    ├── dry_run.py
    └── test_connection.py
```

### API 클라이언트 패턴

**IconikClient** (`clients/iconik_client.py`):
- Context manager 지원 (`with IconikClient() as client`)
- Tenacity 기반 재시도 (3회, 지수 백오프)
- Assets API: `create_asset`, `get_asset`, `search_assets`
- Metadata API: `set_metadata`, `get_metadata`
- Collections API: `create_collection`, `add_to_collection`

**SheetsClient** (`clients/sheets_client.py`):
- 서비스 계정 인증
- `get_sheet_data(sheet_name, range)` - 시트 데이터 조회
- `get_matching_integrated()` - Matching_Integrated 시트 → dict 변환

### 설정

```python
from config.settings import get_settings
settings = get_settings()  # 캐싱된 인스턴스
```

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
DATABASE_URL=sqlite:///data/migration.db
BATCH_SIZE=100
RATE_LIMIT_PER_SEC=50
```

## Key Dependencies

| 패키지 | 용도 |
|--------|------|
| httpx | Iconik API 호출 |
| tenacity | 재시도 로직 |
| google-api-python-client | Sheets API |
| pydantic-settings | 환경변수 관리 |
| sqlalchemy | 상태 추적 (SQLite) |
| rich | CLI 출력 |
