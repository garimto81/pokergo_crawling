# TDD Guide: Iconik2Sheet

> Iconik MAM 시스템 데이터 추출 테스트 가이드

## 개요

이 문서는 Iconik2Sheet 프로젝트의 Test-Driven Development 가이드입니다.

---

## Red-Green-Refactor 흐름

```
1. RED   → 실패하는 테스트 작성
2. GREEN → 테스트 통과하는 최소 코드 작성
3. REFACTOR → 코드 개선 (테스트 유지)
```

---

## 환경 설정

### 1. 가상환경 설정

```powershell
cd D:\AI\claude01\pokergo_crawling\src\migrations\iconik2sheet
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 2. 환경 변수 설정

`.env.local` 파일에 인증 정보 입력:

```env
# Iconik API (필수)
ICONIK_APP_ID=your-app-id
ICONIK_AUTH_TOKEN=your-auth-token
ICONIK_BASE_URL=https://app.iconik.io

# Metadata View (Integration 테스트로 조회 후 설정)
ICONIK_METADATA_VIEW_ID=

# Google Sheets (선택)
GOOGLE_SERVICE_ACCOUNT_PATH=D:/AI/claude01/json/service_account_key.json
GOOGLE_SPREADSHEET_ID=1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk
```

---

## 테스트 분류

### Unit Tests (Mock 기반, 오프라인 실행 가능)

| 테스트 파일 | 검증 내용 | 우선순위 |
|-------------|-----------|----------|
| `tests/unit/test_settings.py` | 환경변수 로드, 기본값, 캐싱 | 1 |
| `tests/unit/test_models.py` | Pydantic 모델, 26컬럼 검증 | 2 |
| `tests/unit/test_client.py` | IconikClient Mock 테스트 | 3 |

### Integration Tests (실제 API 호출, 인증 필요)

| 테스트 파일 | 목적 | 필수 설정 |
|-------------|------|-----------|
| `tests/integration/test_iconik_connection.py` | API 연결 확인 | ICONIK_* |
| `tests/integration/test_metadata_views.py` | View ID 조회 | ICONIK_* |

---

## 실행 방법

### Unit Tests (빠름, Mock)

```powershell
# 전체 Unit 테스트
pytest tests/unit/ -v

# 개별 테스트
pytest tests/unit/test_settings.py -v
pytest tests/unit/test_models.py::TestIconikAssetExport -v

# 특정 테스트 함수
pytest tests/unit/test_models.py::TestIconikAssetExport::test_all_26_columns_present -v
```

### Integration Tests (실제 API)

```powershell
# .env.local 필요!
# Metadata View 조회 (View ID 확인용)
pytest tests/integration/test_metadata_views.py -v -s

# Iconik 연결 테스트
pytest tests/integration/test_iconik_connection.py -v -s

# 전체 통합 테스트
pytest tests/integration/ -v -s -m integration
```

### 전체 테스트 (커버리지 포함)

```powershell
pytest tests/ -v --cov=. --cov-report=term-missing
```

---

## Metadata View ID 조회

Integration 테스트를 실행하면 사용 가능한 Metadata View 목록이 출력됩니다:

```powershell
pytest tests/integration/test_metadata_views.py::TestMetadataViews::test_get_all_views -v -s
```

출력 예시:
```
============================================================
AVAILABLE METADATA VIEWS
============================================================
Copy the ID you need to .env.local as ICONIK_METADATA_VIEW_ID
------------------------------------------------------------

  ID: 98e2bca2-504a-11e7-aebc-0a580a000282
  Name: Poker Hand Metadata
  Description: WSOP clips metadata...

  ID: d34e6f1c-d60f-11e9-a8cb-ee0a854c7179
  Name: Default View
  Description: System default...

============================================================
```

원하는 View ID를 `.env.local`에 복사:
```env
ICONIK_METADATA_VIEW_ID=98e2bca2-504a-11e7-aebc-0a580a000282
```

---

## 테스트 Fixtures

### conftest.py 주요 Fixtures

| Fixture | 용도 | 스코프 |
|---------|------|--------|
| `mock_settings` | Unit 테스트용 Mock 설정 | function |
| `mock_iconik_settings` | IconikSettings Mock | function |
| `sample_asset` | 샘플 Asset JSON (fixtures/sample_asset.json) | function |
| `sample_metadata` | 샘플 Metadata JSON | function |
| `sample_segments` | 샘플 Segments JSON | function |
| `sample_metadata_views` | 샘플 Views JSON | function |
| `iconik_client` | 실제 IconikClient (Integration) | function |
| `sheets_writer` | 실제 SheetsWriter (Integration) | function |

---

## 테스트 마커

```python
@pytest.mark.integration  # 실제 API 호출
@pytest.mark.slow         # 느린 테스트
```

### 마커로 필터링

```powershell
# Integration 테스트만
pytest -m integration -v

# Integration 제외
pytest -m "not integration" -v
```

---

## 26컬럼 모델 검증

`IconikAssetExport` 모델이 PRD와 일치하는지 검증:

```powershell
pytest tests/unit/test_models.py::TestIconikAssetExport -v
```

검증 항목:
- 필드 수 = 26개
- 필드 이름 PRD와 일치
- id, title만 필수
- 타임코드 필드 (ms, S)

---

## 디렉토리 구조

```
tests/
├── __init__.py
├── conftest.py                      # 공통 fixtures
├── unit/
│   ├── __init__.py
│   ├── test_settings.py             # Settings 테스트
│   ├── test_models.py               # Pydantic 모델 테스트
│   └── test_client.py               # Client Mock 테스트
├── integration/
│   ├── __init__.py
│   ├── test_iconik_connection.py    # API 연결 테스트
│   └── test_metadata_views.py       # Metadata View 조회
└── fixtures/
    ├── sample_asset.json
    ├── sample_metadata.json
    └── sample_segments.json
```

---

## 트러블슈팅

### ModuleNotFoundError

```powershell
# 개발 모드로 패키지 설치
pip install -e ".[dev]"
```

### 환경 변수 누락

```
SKIPPED [1] Missing env vars: ['ICONIK_APP_ID', 'ICONIK_AUTH_TOKEN']
```
→ `.env.local` 파일 확인

### httpx.HTTPStatusError: 401

→ ICONIK_AUTH_TOKEN 만료 또는 잘못된 값

### timeout 에러

→ `config/settings.py`에서 `timeout` 값 증가

---

## 참고

- [Iconik API 문서](https://app.iconik.io/docs/api.html)
- [pytest 문서](https://docs.pytest.org/)
- [PRD 문서](./PRD.md)
