# Iconik to Sheet Migration

Iconik MAM 시스템 데이터를 Google Sheets로 내보내기/동기화

## Overview

- **Python**: 3.11+
- **API**: httpx (Iconik), google-api-python-client (Sheets)
- **모델**: Pydantic v2
- **상태**: JSON / SQLite

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

# 전체 동기화
python -m scripts.run_full_sync

# 증분 동기화
python -m scripts.run_incremental
```

## 디렉토리 구조

```
iconik2sheet/
├── config/
│   └── settings.py        # 환경 설정
│
├── iconik/
│   ├── client.py          # HTTP 클라이언트
│   ├── assets.py          # Assets API 래퍼
│   ├── metadata.py        # Metadata API 래퍼
│   ├── collections.py     # Collections API 래퍼
│   └── models.py          # Pydantic 모델
│
├── sheets/
│   ├── writer.py          # Sheets 쓰기
│   └── formatter.py       # 데이터 포매팅
│
├── sync/
│   ├── full_sync.py       # 전체 동기화
│   ├── incremental_sync.py # 증분 동기화
│   └── state.py           # 상태 관리
│
├── scripts/
│   ├── run_full_sync.py   # 전체 동기화 CLI
│   ├── run_incremental.py # 증분 동기화 CLI
│   └── test_connection.py # 연결 테스트
│
└── tests/
    └── ...
```

## 출력 시트

| 시트명 | 내용 |
|--------|------|
| Iconik_Assets | 전체 Asset 목록 |
| Iconik_Metadata | 메타데이터 추출 |
| Iconik_Collections | 컬렉션 계층 |
| Sync_Log | 동기화 이력 |

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

## 관련 문서

- [PRD-ICONIK2SHEET.md](../../../docs/prds/PRD-ICONIK2SHEET.md)
- [Iconik API 문서](https://app.iconik.io/docs/api.html)
