# PRD: Sheet to Iconik Migration

> Google Sheets 데이터를 Iconik MAM 시스템으로 마이그레이션

**Version**: 1.0 | **Date**: 2025-12-19 | **Status**: Draft

---

## 1. 개요

### 1.1 배경

현재 NAMS 시스템은 Google Sheets에 다음 데이터를 관리합니다:
- **NAS_Origin_Raw**: Y: 드라이브 원본 파일 (1,568개)
- **NAS_Archive_Raw**: Z: 드라이브 아카이브 파일 (1,405개)
- **NAS_PokerGO_Raw**: X: 드라이브 PokerGO 소스 (828개)
- **PokerGO_Raw**: PokerGO 에피소드 메타데이터 (828개)
- **Matching_Integrated**: 통합 매칭 결과

이 데이터를 Iconik MAM(Media Asset Management) 시스템으로 마이그레이션하여 통합 자산 관리를 구현합니다.

### 1.2 목표

1. **데이터 추출**: Google Sheets에서 5개 시트 데이터 읽기
2. **변환**: Sheets 스키마 → Iconik 스키마 매핑
3. **업로드**: Iconik API를 통한 Asset/Metadata/Collection 생성
4. **추적**: 마이그레이션 상태 및 에러 로깅

### 1.3 범위

#### In Scope

- Google Sheets 5개 시트 데이터 추출
- Iconik Asset 생성 (메타데이터만, 파일 업로드 제외)
- Custom Metadata 할당
- Collection 구조 생성
- 배치 처리 및 재시도 로직

#### Out of Scope

- 실제 미디어 파일 업로드 (별도 프로세스)
- Iconik Storage 연동
- 실시간 동기화 (일회성 마이그레이션)

---

## 2. 아키텍처

### 2.1 시스템 구조도

```
┌─────────────────────────────────────────────────────────────┐
│                    Migration CLI                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ SheetReader │  │ Transformer │  │ IconikUploader      │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
└─────────┼────────────────┼─────────────────────┼─────────────┘
          │                │                     │
          ▼                │                     ▼
┌─────────────────┐        │        ┌─────────────────────────┐
│  Google Sheets  │        │        │      Iconik API         │
│  ┌───────────┐  │        │        │  ┌─────────────────┐    │
│  │ 5 Sheets  │  │────────┘        │  │ Assets API      │    │
│  └───────────┘  │                 │  │ Metadata API    │    │
└─────────────────┘                 │  │ Collections API │    │
                                    │  └─────────────────┘    │
                                    └─────────────────────────┘
                                              │
                                              ▼
                                    ┌─────────────────────────┐
                                    │   SQLite (Tracking)     │
                                    │   migration_records     │
                                    └─────────────────────────┘
```

### 2.2 데이터 흐름

```
[마이그레이션 흐름]

1. Google Sheets 데이터 읽기
   └── Matching_Integrated 시트 → 전체 행 추출
   └── 필터링: Excluded 항목 제외

2. 데이터 변환
   └── Pydantic 모델로 검증
   └── 필드 매핑 규칙 적용
   └── Era별 특수 처리

3. Iconik Asset 생성
   └── POST /API/assets/v1/assets/
   └── 응답에서 asset_id 획득

4. Metadata 할당
   └── PUT /API/metadata/v1/assets/{asset_id}/views/{view_id}/
   └── Year, Era, Region, Event_Type 등 설정

5. Collection 할당
   └── 연도/시리즈별 컬렉션에 Asset 추가

6. 상태 저장
   └── SQLite에 마이그레이션 기록
```

---

## 3. 데이터 모델

### 3.1 Google Sheets 스키마

#### Matching_Integrated 시트

| 컬럼 | 타입 | 설명 |
|------|------|------|
| Year | Integer | 연도 |
| NAS Filename | String | NAS 파일명 |
| Full_Path | String | 전체 경로 |
| PokerGO Title | String | PokerGO 원본 제목 |
| Catalog Title | String | 카탈로그 표시 제목 |
| Collection | String | 컬렉션명 |
| Season | String | 시즌명 |
| Origin | Boolean | Y: 드라이브 존재 여부 |
| Archive | Boolean | Z: 드라이브 존재 여부 |
| PokerGO_Src | Boolean | X: 드라이브 존재 여부 |
| PKG | Boolean | PokerGO 매칭 여부 |
| Action | String | OK/Excluded/DUPLICATE 등 |

### 3.2 Iconik 스키마

#### Asset

| 필드 | 타입 | 매핑 소스 |
|------|------|-----------|
| title | String | Catalog Title |
| external_id | String | NAS Filename |
| status | String | "ACTIVE" |

#### Custom Metadata (View)

| 필드 | 타입 | 매핑 소스 |
|------|------|-----------|
| year | Integer | Year |
| era | String | CLASSIC/BOOM/HD (계산) |
| region | String | Collection에서 추출 |
| event_type | String | Collection에서 추출 |
| source_path | String | Full_Path |
| pokergo_title | String | PokerGO Title |
| file_locations | Object | Origin/Archive/PokerGO_Src |

### 3.3 필드 매핑 테이블

| Sheets 필드 | Iconik 필드 | 변환 규칙 |
|-------------|-------------|-----------|
| Catalog Title | asset.title | 그대로 (없으면 NAS Filename) |
| NAS Filename | asset.external_id | 그대로 |
| Year | metadata.year | Integer 변환 |
| Year | metadata.era | 연도 기반 계산 |
| Collection | metadata.region | 정규식 추출 |
| Collection | metadata.event_type | 매핑 테이블 참조 |
| Full_Path | metadata.source_path | 그대로 |
| PokerGO Title | metadata.pokergo_title | 그대로 |

---

## 4. 기능 요구사항

### 4.1 Google Sheets 읽기 (FR-1xx)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| FR-101 | 시트 연결 | 서비스 계정으로 인증 | P0 |
| FR-102 | 데이터 추출 | 5개 시트 전체 데이터 읽기 | P0 |
| FR-103 | 필터링 | Action=Excluded 제외 | P0 |
| FR-104 | 변경 감지 | 증분 마이그레이션용 | P2 |

### 4.2 Iconik API 연동 (FR-2xx)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| FR-201 | 인증 | App-ID + Auth-Token | P0 |
| FR-202 | Asset 생성 | POST /assets/ | P0 |
| FR-203 | Metadata 할당 | PUT /metadata/views/ | P0 |
| FR-204 | Collection 관리 | 컬렉션 생성/조회/할당 | P1 |
| FR-205 | 중복 체크 | external_id로 기존 Asset 검색 | P0 |

### 4.3 데이터 변환 (FR-3xx)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| FR-301 | 필드 매핑 | Sheets → Iconik 변환 | P0 |
| FR-302 | Era 계산 | 연도 기반 자동 분류 | P0 |
| FR-303 | Region 추출 | Collection에서 정규식 추출 | P1 |
| FR-304 | 검증 | Pydantic 모델 검증 | P0 |

### 4.4 배치 처리 (FR-4xx)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| FR-401 | 배치 크기 | 100건 단위 처리 | P0 |
| FR-402 | Rate Limiting | 50 req/sec 준수 | P0 |
| FR-403 | 재시도 | 지수 백오프 재시도 | P0 |
| FR-404 | 에러 분류 | recoverable/skip/abort | P0 |

### 4.5 상태 추적 (FR-5xx)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| FR-501 | 상태 저장 | SQLite 기록 | P0 |
| FR-502 | 재개 기능 | 중단 시점부터 재개 | P1 |
| FR-503 | 리포트 생성 | 성공/실패 요약 | P1 |
| FR-504 | 로그 출력 | Rich 기반 콘솔 로그 | P0 |

---

## 5. Iconik API 통합

### 5.1 인증 설정

```python
ICONIK_CONFIG = {
    "base_url": "https://app.iconik.io/API",
    "app_id": "환경변수: ICONIK_APP_ID",
    "auth_token": "환경변수: ICONIK_AUTH_TOKEN",
    "timeout": 30,
    "max_retries": 3
}

headers = {
    "App-ID": app_id,
    "Auth-Token": auth_token,
    "Content-Type": "application/json"
}
```

### 5.2 주요 API 엔드포인트

| 작업 | Method | Endpoint |
|------|--------|----------|
| Asset 생성 | POST | `/assets/v1/assets/` |
| Asset 조회 | GET | `/assets/v1/assets/{id}/` |
| Metadata 할당 | PUT | `/metadata/v1/assets/{id}/views/{view}/` |
| Collection 생성 | POST | `/assets/v1/collections/` |
| Collection 추가 | PUT | `/assets/v1/collections/{id}/contents/` |
| 검색 | POST | `/search/v1/search/` |

### 5.3 에러 처리

| HTTP 코드 | 분류 | 처리 |
|-----------|------|------|
| 429 | recoverable | 재시도 (백오프) |
| 500-504 | recoverable | 재시도 (백오프) |
| 404, 409 | skip | 스킵 후 로그 |
| 401, 403 | abort | 즉시 중단 |

---

## 6. 기술 스택

| 구성 요소 | 선택 |
|-----------|------|
| Python | 3.11+ |
| HTTP 클라이언트 | httpx |
| Google API | google-api-python-client |
| 데이터 검증 | Pydantic v2 |
| 상태 저장 | SQLAlchemy + SQLite |
| 재시도 로직 | tenacity |
| CLI 출력 | rich |
| 테스트 | pytest |

---

## 7. 구현 계획

### Phase 1: 기반 구축

| 작업 | 파일 |
|------|------|
| 프로젝트 설정 | pyproject.toml |
| 환경 설정 | config/settings.py |
| Pydantic 모델 | models/*.py |
| Sheets 클라이언트 | clients/sheets_client.py |
| Iconik 클라이언트 | clients/iconik_client.py |

### Phase 2: 핵심 기능

| 작업 | 파일 |
|------|------|
| 데이터 읽기 | services/sheet_reader.py |
| 데이터 변환 | services/data_transformer.py |
| Iconik 업로드 | services/iconik_uploader.py |
| 배치 처리 | services/batch_processor.py |

### Phase 3: 추적 및 안정화

| 작업 | 파일 |
|------|------|
| 상태 추적 | services/migration_tracker.py |
| 리포트 생성 | services/reporter.py |
| CLI 스크립트 | scripts/migrate.py |
| Dry-run | scripts/dry_run.py |

---

## 8. 성공 기준

| 지표 | 목표 |
|------|------|
| 마이그레이션 성공률 | > 95% |
| 처리 속도 | 100건/분 |
| 에러 복구율 | > 90% (recoverable) |
| 상태 추적 정확도 | 100% |

---

## 9. 참고 자료

- [Iconik API 문서](https://app.iconik.io/docs/api.html)
- [Iconik Metadata 가이드](https://app.iconik.io/help/pages/asset/metadata)
- [기존 export_4sheets.py](../../../scripts/export_4sheets.py)
- [MATCHING_RULES.md](../MATCHING_RULES.md)
