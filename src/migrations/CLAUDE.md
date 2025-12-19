# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

마이그레이션 서브 프로젝트 모음 - Google Sheets와 Iconik MAM 시스템 간 데이터 동기화

## 서브 프로젝트

| 프로젝트 | 용도 | 기술 스택 |
|----------|------|-----------|
| `sheet2sheet/` | Sheets 간 마이그레이션 PWA | CLASP + React 19 |
| `sheet2iconik/` | Sheets → Iconik 업로드 | Python 3.11+ / httpx |
| `iconik2sheet/` | Iconik → Sheets 내보내기 | Python 3.11+ / httpx |

## Commands

### sheet2sheet (GAS + PWA)

```powershell
# GAS 배포
cd sheet2sheet/gas
clasp push && clasp deploy

# PWA 개발 (port 5175)
cd sheet2sheet/pwa
npm install && npm run dev
npm run lint && npm run build
```

### sheet2iconik / iconik2sheet (Python)

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
python -m scripts.run_full_sync      # 전체 동기화 (iconik2sheet)

# 린트/테스트
ruff check . --fix
pytest tests/ -v
```

## Architecture

### Python 프로젝트 공통 구조

```
project/
├── config/settings.py     # Pydantic Settings (환경변수: ICONIK_*, GOOGLE_*)
├── clients/               # API 클라이언트 (httpx)
├── services/ 또는 sync/   # 비즈니스 로직
└── scripts/               # CLI 엔트리포인트 (-m 실행)
```

### 설정 패턴

- `pydantic-settings` 사용
- `.env` 파일 로드 (`python-dotenv`)
- `get_settings()` 함수로 캐싱된 설정 조회

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
- 별도의 Claude Code 세션에서 개발 권장

## Key Docs

| 문서 | 내용 |
|------|------|
| `docs/prds/PRD-SHEET2SHEET.md` | Sheet to Sheet PRD |
| `docs/prds/PRD-SHEET2ICONIK.md` | Sheet to Iconik PRD |
| `docs/prds/PRD-ICONIK2SHEET.md` | Iconik to Sheet PRD |
