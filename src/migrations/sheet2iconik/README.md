# Sheet to Iconik Migration

Google Sheets 데이터를 Iconik MAM 시스템으로 마이그레이션

## Overview

- **Python**: 3.11+
- **API**: httpx (Iconik), google-api-python-client (Sheets)
- **모델**: Pydantic v2
- **상태**: SQLite

## Quick Start

```powershell
# 가상환경 생성
python -m venv .venv
.venv\Scripts\Activate.ps1

# 의존성 설치
pip install -e .

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집

# 연결 테스트
python -m scripts.test_connection

# Dry Run
python -m scripts.dry_run

# 마이그레이션 실행
python -m scripts.migrate
```

## 디렉토리 구조

```
sheet2iconik/
├── config/
│   ├── settings.py        # 환경 설정
│   ├── iconik_config.py   # Iconik API 설정
│   └── sheets_config.py   # Google Sheets 설정
│
├── clients/
│   ├── sheets_client.py   # Sheets API 클라이언트
│   └── iconik_client.py   # Iconik API 클라이언트
│
├── models/
│   ├── sheet_models.py    # Sheets 데이터 모델
│   ├── iconik_models.py   # Iconik 데이터 모델
│   └── mapping_models.py  # 매핑 규칙 모델
│
├── services/
│   ├── sheet_reader.py    # Sheets 데이터 읽기
│   ├── data_transformer.py # 데이터 변환
│   ├── iconik_uploader.py # Iconik 업로드
│   └── migration_tracker.py # 상태 추적
│
├── scripts/
│   ├── migrate.py         # 메인 마이그레이션 CLI
│   ├── dry_run.py         # 테스트 실행
│   └── test_connection.py # 연결 테스트
│
└── tests/
    └── ...
```

## 환경 변수

```env
# Iconik API
ICONIK_APP_ID=your-app-id
ICONIK_AUTH_TOKEN=your-auth-token
ICONIK_BASE_URL=https://app.iconik.io

# Google Sheets
GOOGLE_SERVICE_ACCOUNT_PATH=path/to/service_account.json
GOOGLE_SHEETS_ID=spreadsheet-id
```

## 핵심 기능

| 기능 | 설명 |
|------|------|
| Sheets 읽기 | 5개 시트 데이터 추출 |
| Iconik 업로드 | Asset 생성, Metadata 할당 |
| 데이터 매핑 | 필드 변환, Era별 규칙 |
| 상태 추적 | 진행률, 에러 로깅 |

## 관련 문서

- [PRD-SHEET2ICONIK.md](../../../docs/prds/PRD-SHEET2ICONIK.md)
- [Iconik API 문서](https://app.iconik.io/docs/api.html)
