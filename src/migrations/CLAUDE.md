# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

마이그레이션 서브 프로젝트 모음 - Google Sheets와 Iconik MAM 시스템 간 데이터 동기화

## 서브 프로젝트

| 프로젝트 | 용도 | 기술 스택 | 상세 문서 |
|----------|------|-----------|-----------|
| `sheet2sheet/` | Sheets 간 마이그레이션 PWA | CLASP + React 19 | `sheet2sheet/CLAUDE.md` |
| `sheet2sheet_migrate/` | Archive Metadata → Iconik 시트 통합 | Python 3.11+ | `sheet2sheet_migrate/CLAUDE.md` |
| `sheet2iconik/` | Sheets → Iconik 업로드 | Python 3.11+ / httpx | `sheet2iconik/CLAUDE.md` |
| `iconik2sheet/` | Iconik → Sheets 내보내기 | Python 3.11+ / httpx | `iconik2sheet/CLAUDE.md` |

## Commands

### sheet2sheet (GAS + PWA)

```powershell
# GAS 배포
cd sheet2sheet/gas
clasp push && clasp deploy

# PWA 개발 (port 5175 - NAMS UI 5174와 충돌 방지)
cd sheet2sheet/pwa
npm install && npm run dev
npm run lint && npm run build

# 루트에서 실행
cd sheet2sheet
npm run dev          # PWA 개발 서버
npm run gas:push     # GAS 푸시
```

### Python 프로젝트 (sheet2iconik / iconik2sheet)

```powershell
cd sheet2iconik  # 또는 iconik2sheet

# 환경 설정
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cp .env.example .env

# 실행
python -m scripts.test_connection    # 연결 테스트
python -m scripts.dry_run            # Dry run (sheet2iconik)
python -m scripts.migrate            # 마이그레이션 (sheet2iconik)
python -m scripts.run_full_sync      # 전체 동기화 (iconik2sheet)
python -m scripts.run_incremental    # 증분 동기화 (iconik2sheet)

# 린트/테스트
ruff check . --fix
pytest tests/ -v                     # 전체 테스트
pytest tests/test_client.py -v       # 개별 테스트 (권장)
pytest tests/test_client.py::test_health_check -v  # 단일 테스트
```

### sheet2sheet_migrate (Archive Metadata → Iconik)

```powershell
# 프로젝트 루트에서 실행
python scripts/analyze_source_sheet.py       # 소스 시트 분석
python scripts/run_sheet_migration.py        # Dry run
python scripts/run_sheet_migration.py --show-mapping  # 매핑 미리보기
python scripts/run_sheet_migration.py --execute       # 실행 (append)
python scripts/run_sheet_migration.py --execute --mode overwrite  # 실행 (overwrite)
```

## Architecture

### Python 프로젝트 공통 구조

```
project/
├── config/settings.py     # Pydantic Settings (ICONIK_*, GOOGLE_*)
├── clients/ 또는 iconik/  # API 클라이언트 (httpx + tenacity)
├── services/ 또는 sync/   # 비즈니스 로직
└── scripts/               # CLI 엔트리포인트 (-m 실행)
```

### API 클라이언트 패턴

```python
# Context manager 지원
with IconikClient() as client:
    asset = client.get_asset("asset-id")

# 설정 조회
from config.settings import get_settings
settings = get_settings()  # 캐싱된 인스턴스
```

### 환경 변수

```env
# Iconik API (sheet2iconik, iconik2sheet 공통)
ICONIK_APP_ID=your-app-id
ICONIK_AUTH_TOKEN=your-auth-token
ICONIK_BASE_URL=https://app.iconik.io

# Google Sheets
GOOGLE_SERVICE_ACCOUNT_PATH=path/to/service_account.json
GOOGLE_SPREADSHEET_ID=spreadsheet-id
```

## 독립 프로젝트 운영

각 서브 프로젝트는 **완전 독립적**:
- 자체 의존성 관리 (package.json / pyproject.toml)
- 별도의 가상환경
- **별도의 Claude Code 세션**에서 개발 권장 (각 프로젝트 디렉토리에서 실행)

## Key Docs

| 문서 | 내용 |
|------|------|
| `../../docs/prds/PRD-SHEET2SHEET.md` | Sheet to Sheet PRD |
| `../../docs/prds/PRD-SHEET2SHEET-MIGRATE.md` | Archive Metadata → Iconik 마이그레이션 PRD |
| `../../docs/prds/PRD-SHEET2ICONIK.md` | Sheet to Iconik PRD |
| `../../docs/prds/PRD-ICONIK2SHEET.md` | Iconik to Sheet PRD |
