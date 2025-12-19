# PRD: Iconik to Sheet Migration

> Iconik MAM 시스템 데이터를 Google Sheets로 내보내기/동기화

**Version**: 1.0 | **Date**: 2025-12-19 | **Status**: Draft

---

## 1. 개요

### 1.1 배경

Iconik MAM 시스템에 저장된 Asset, Metadata, Collection 정보를 Google Sheets로 내보내기하여:
- NAMS 시스템과의 데이터 비교/검증
- 비기술 사용자를 위한 데이터 접근성 제공
- 오프라인 데이터 분석 지원

### 1.2 목표

1. **데이터 추출**: Iconik API에서 Assets, Metadata, Collections 조회
2. **페이지네이션**: 대량 데이터 효율적 처리
3. **Sheets 출력**: 4개 시트 생성/업데이트
4. **증분 동기화**: 변경사항만 업데이트

### 1.3 범위

#### In Scope

- Iconik Assets 전체 목록 내보내기
- Custom Metadata 추출
- Collection 계층 구조 내보내기
- 증분 동기화 (updated_at 기반)
- 동기화 로그 기록

#### Out of Scope

- 실제 미디어 파일 다운로드
- Iconik Storage 직접 접근
- 실시간 동기화 (웹훅)

---

## 2. 아키텍처

### 2.1 시스템 구조도

```
┌─────────────────────────────────────────────────────────────┐
│                    Sync CLI                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │IconikClient │  │ Formatter   │  │ SheetsWriter        │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
└─────────┼────────────────┼─────────────────────┼─────────────┘
          │                │                     │
          ▼                │                     ▼
┌─────────────────────────┐│        ┌─────────────────────────┐
│      Iconik API         ││        │    Google Sheets        │
│  ┌─────────────────┐    ││        │  ┌───────────────────┐  │
│  │ Assets API      │    │└────────│  │ Iconik_Assets     │  │
│  │ Metadata API    │────┘         │  │ Iconik_Metadata   │  │
│  │ Collections API │              │  │ Iconik_Collections│  │
│  │ Search API      │              │  │ Sync_Log          │  │
│  └─────────────────┘              │  └───────────────────┘  │
└─────────────────────────┘         └─────────────────────────┘
          │
          ▼
┌─────────────────────────┐
│   State Storage         │
│   (JSON / SQLite)       │
│   last_sync_at          │
└─────────────────────────┘
```

### 2.2 데이터 흐름

```
[전체 동기화]
1. Iconik API 호출
   └── GET /assets/ (페이지네이션)
   └── GET /assets/{id}/metadata/ (각 Asset별)
   └── GET /collections/ (전체)

2. 데이터 변환
   └── Pydantic 모델 검증
   └── 시트 형식으로 포매팅

3. Google Sheets 출력
   └── 시트 생성 또는 초기화
   └── 배치 쓰기 (1000행 단위)

4. 상태 저장
   └── last_sync_at 기록

[증분 동기화]
1. 마지막 동기화 시점 조회
2. updated_at > last_sync_at 항목만 조회
3. 해당 행만 업데이트
```

---

## 3. 데이터 모델

### 3.1 Iconik 데이터 구조

#### Asset

```python
class IconikAsset(BaseModel):
    id: str
    title: str
    external_id: Optional[str]
    status: str  # ACTIVE, INACTIVE
    is_online: bool
    analyze_status: Optional[str]
    archive_status: Optional[str]
    created_at: datetime
    updated_at: datetime
```

#### Metadata

```python
class IconikMetadata(BaseModel):
    asset_id: str
    view_id: str
    fields: dict[str, Any]  # 동적 필드
```

#### Collection

```python
class IconikCollection(BaseModel):
    id: str
    title: str
    parent_id: Optional[str]
    is_root: bool
    created_at: datetime
```

### 3.2 출력 시트 구조

#### Iconik_Assets 시트

| 컬럼 | 타입 | 설명 |
|------|------|------|
| ID | String | Iconik Asset ID |
| Title | String | 자산 제목 |
| External_ID | String | 외부 식별자 |
| Status | String | ACTIVE/INACTIVE |
| Is_Online | Boolean | 온라인 여부 |
| Created_At | DateTime | 생성일 |
| Updated_At | DateTime | 수정일 |

#### Iconik_Metadata 시트

| 컬럼 | 타입 | 설명 |
|------|------|------|
| Asset_ID | String | Iconik Asset ID |
| View_Name | String | Metadata View 이름 |
| Field_Name | String | 필드명 |
| Field_Value | String | 필드값 |

#### Iconik_Collections 시트

| 컬럼 | 타입 | 설명 |
|------|------|------|
| Collection_ID | String | 컬렉션 ID |
| Title | String | 컬렉션 제목 |
| Parent_ID | String | 상위 컬렉션 ID |
| Depth | Integer | 계층 깊이 |
| Asset_Count | Integer | 포함된 Asset 수 |

#### Sync_Log 시트

| 컬럼 | 타입 | 설명 |
|------|------|------|
| Sync_ID | String | 동기화 ID |
| Sync_Type | String | full/incremental |
| Started_At | DateTime | 시작 시간 |
| Completed_At | DateTime | 완료 시간 |
| Assets_New | Integer | 신규 Asset 수 |
| Assets_Updated | Integer | 업데이트된 Asset 수 |
| Status | String | success/failed |

---

## 4. 기능 요구사항

### 4.1 Iconik API 읽기 (FR-1xx)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| FR-101 | 인증 | App-ID + Auth-Token | P0 |
| FR-102 | Assets 조회 | 전체 목록 (페이지네이션) | P0 |
| FR-103 | Metadata 조회 | Asset별 메타데이터 | P0 |
| FR-104 | Collections 조회 | 컬렉션 계층 구조 | P1 |
| FR-105 | Search API | 조건부 검색 | P2 |

### 4.2 페이지네이션 (FR-2xx)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| FR-201 | 페이지 크기 | per_page=100 | P0 |
| FR-202 | 커서 기반 | first_id 사용 | P0 |
| FR-203 | Rate Limit | 50 req/sec 준수 | P0 |
| FR-204 | 진행률 표시 | tqdm/rich progress | P1 |

### 4.3 Google Sheets 출력 (FR-3xx)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| FR-301 | 시트 생성 | 4개 시트 자동 생성 | P0 |
| FR-302 | 배치 쓰기 | 1000행 단위 | P0 |
| FR-303 | 헤더 설정 | 고정 헤더, 필터 | P0 |
| FR-304 | 서식 적용 | 날짜/숫자 포맷 | P1 |
| FR-305 | 체크박스 | Boolean → 체크박스 | P1 |

### 4.4 증분 동기화 (FR-4xx)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| FR-401 | 변경 감지 | updated_at 비교 | P1 |
| FR-402 | 상태 저장 | JSON/SQLite | P1 |
| FR-403 | 행 업데이트 | 기존 행 수정 | P1 |
| FR-404 | 새 행 추가 | 신규 Asset 추가 | P1 |

---

## 5. Iconik API 상세

### 5.1 인증

```python
headers = {
    "App-ID": os.getenv("ICONIK_APP_ID"),
    "Auth-Token": os.getenv("ICONIK_AUTH_TOKEN"),
    "Content-Type": "application/json"
}
```

### 5.2 주요 엔드포인트

| 작업 | Method | Endpoint | 파라미터 |
|------|--------|----------|----------|
| Assets 목록 | GET | `/assets/v1/assets/` | per_page, page, sort |
| Asset 상세 | GET | `/assets/v1/assets/{id}/` | - |
| Metadata | GET | `/metadata/v1/assets/{id}/views/{view}/` | - |
| Collections | GET | `/assets/v1/collections/` | per_page, page |
| 검색 | POST | `/search/v1/search/` | query, filter |

### 5.3 페이지네이션 응답

```json
{
  "objects": [...],
  "page": 1,
  "pages": 10,
  "per_page": 100,
  "total": 1000,
  "first_id": "abc123",
  "last_id": "xyz789"
}
```

---

## 6. 기술 스택

| 구성 요소 | 선택 |
|-----------|------|
| Python | 3.11+ |
| HTTP 클라이언트 | httpx (async) |
| Google API | google-api-python-client |
| 데이터 검증 | Pydantic v2 |
| 상태 저장 | JSON 파일 또는 SQLite |
| CLI 출력 | rich |
| 테스트 | pytest, pytest-asyncio |

---

## 7. 구현 계획

### Phase 1: Iconik 클라이언트

| 작업 | 파일 |
|------|------|
| 프로젝트 설정 | pyproject.toml |
| 환경 설정 | config/settings.py |
| HTTP 클라이언트 | iconik/client.py |
| Assets API | iconik/assets.py |
| Metadata API | iconik/metadata.py |
| Collections API | iconik/collections.py |
| Pydantic 모델 | iconik/models.py |

### Phase 2: Sheets 출력

| 작업 | 파일 |
|------|------|
| Sheets 클라이언트 | sheets/writer.py |
| 데이터 포매터 | sheets/formatter.py |
| 배치 쓰기 | sheets/batch.py |

### Phase 3: 동기화 로직

| 작업 | 파일 |
|------|------|
| 전체 동기화 | sync/full_sync.py |
| 증분 동기화 | sync/incremental_sync.py |
| 상태 관리 | sync/state.py |
| CLI 스크립트 | scripts/run_full_sync.py |
| 테스트 스크립트 | scripts/test_connection.py |

---

## 8. 성공 기준

| 지표 | 목표 |
|------|------|
| 전체 동기화 완료 시간 | < 10분 (1000 Assets) |
| 증분 동기화 완료 시간 | < 1분 (100 변경) |
| API 호출 성공률 | > 99% |
| 데이터 정확도 | 100% |

---

## 9. 참고 자료

- [Iconik API 문서](https://app.iconik.io/docs/api.html)
- [Iconik Assets API](https://app.iconik.io/docs/api/assets.html)
- [기존 export_4sheets.py](../../../scripts/export_4sheets.py)
- [Google Sheets API](https://developers.google.com/sheets/api)
