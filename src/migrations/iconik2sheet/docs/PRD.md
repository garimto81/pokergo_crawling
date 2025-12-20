# PRD: Iconik to Sheet Migration

> Iconik MAM 시스템 데이터를 Google Sheets로 내보내기/동기화

**Version**: 2.0 | **Date**: 2025-12-20 | **Status**: Active

---

## 1. 개요

### 1.1 배경

Iconik MAM 시스템에 저장된 Asset 및 Custom Metadata를 Google Sheets로 내보내기하여:
- 포커 핸드 클립 메타데이터 관리
- 비기술 사용자를 위한 데이터 접근성 제공
- WSOP 영상 카탈로그 검색/분석 지원

### 1.2 목표

1. **데이터 추출**: Iconik API에서 Assets + Custom Metadata 조회
2. **페이지네이션**: 대량 데이터 효율적 처리
3. **26개 컬럼 출력**: 레퍼런스 시트 구조에 맞게 포매팅
4. **증분 동기화**: 변경사항만 업데이트

### 1.3 범위

#### In Scope

- Iconik Assets 전체 목록 내보내기
- Custom Metadata View 추출 (26개 필드)
- Timecode 정보 추출 (Subclip)
- 증분 동기화 (updated_at 기반)
- 동기화 로그 기록

#### Out of Scope

- 실제 미디어 파일 다운로드
- Iconik Storage 직접 접근
- 실시간 동기화 (웹훅)

---

## 2. 대상 스프레드시트

### 2.1 레퍼런스 시트

| 항목 | 값 |
|------|-----|
| **제목** | iconik Metadata with Timecode |
| **ID** | `1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk` |
| **URL** | [링크](https://docs.google.com/spreadsheets/d/1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk) |

### 2.2 시트 구조

| 시트명 | 용도 | 컬럼 수 |
|--------|------|---------|
| **iconik_api_export** | Iconik API 내보내기 결과 | 26 |
| **iconik_export_compare** | 비교/검증용 | 26 |
| **Sync_Log** | 동기화 이력 | 7 |

---

## 3. 데이터 모델

### 3.1 출력 컬럼 구조 (26개)

| # | 컬럼명 | 타입 | Iconik 소스 | 설명 |
|---|--------|------|-------------|------|
| 1 | id | UUID | Asset.id | Iconik Asset ID |
| 2 | title | String | Asset.title | 클립 제목 |
| 3 | time_start_ms | Integer | Segment.time_base | 시작 시간 (밀리초) |
| 4 | time_end_ms | Integer | Segment.time_end | 종료 시간 (밀리초) |
| 5 | time_start_S | Float | 계산: ms/1000 | 시작 시간 (초) |
| 6 | time_end_S | Float | 계산: ms/1000 | 종료 시간 (초) |
| 7 | Description | String | Metadata | 설명 |
| 8 | ProjectName | String | Metadata | 프로젝트명 (WSOP 2024 등) |
| 9 | ProjectNameTag | String | Metadata | 프로젝트 태그 |
| 10 | SearchTag | String | Metadata | 검색 태그 |
| 11 | Year_ | Integer | Metadata | 연도 |
| 12 | Location | String | Metadata | 위치 (Las Vegas, London 등) |
| 13 | Venue | String | Metadata | 장소 (Rio 등) |
| 14 | EpisodeEvent | String | Metadata | 이벤트명 ($1.5K NLH 등) |
| 15 | Source | String | Metadata | 소스 (PGM/Subclip/Youtube) |
| 16 | Scene | String | Metadata | 장면 유형 (Hand Clip 등) |
| 17 | GameType | String | Metadata | 게임 타입 (NLH/PLO 등) |
| 18 | PlayersTags | String | Metadata | 플레이어 태그 (쉼표 구분) |
| 19 | HandGrade | String | Metadata | 핸드 등급 (★/★★/★★★) |
| 20 | HANDTag | String | Metadata | 핸드 태그 (KK vs AA 등) |
| 21 | EPICHAND | Boolean | Metadata | 에픽 핸드 여부 |
| 22 | Tournament | String | Metadata | 토너먼트 정보 |
| 23 | PokerPlayTags | String | Metadata | 포커 플레이 태그 |
| 24 | Adjective | String | Metadata | 형용사 (incredible 등) |
| 25 | Emotion | String | Metadata | 감정 (relief, intense 등) |
| 26 | AppearanceOutfit | String | Metadata | 외모/복장 |

### 3.2 Pydantic 모델

```python
class IconikAssetExport(BaseModel):
    """26개 컬럼 출력용 모델"""
    id: str
    title: str
    time_start_ms: Optional[int] = None
    time_end_ms: Optional[int] = None
    time_start_S: Optional[float] = None
    time_end_S: Optional[float] = None
    Description: Optional[str] = None
    ProjectName: Optional[str] = None
    ProjectNameTag: Optional[str] = None
    SearchTag: Optional[str] = None
    Year_: Optional[int] = None
    Location: Optional[str] = None
    Venue: Optional[str] = None
    EpisodeEvent: Optional[str] = None
    Source: Optional[str] = None
    Scene: Optional[str] = None
    GameType: Optional[str] = None
    PlayersTags: Optional[str] = None
    HandGrade: Optional[str] = None
    HANDTag: Optional[str] = None
    EPICHAND: Optional[bool] = None
    Tournament: Optional[str] = None
    PokerPlayTags: Optional[str] = None
    Adjective: Optional[str] = None
    Emotion: Optional[str] = None
    AppearanceOutfit: Optional[str] = None
```

### 3.3 Sync_Log 시트

| 컬럼 | 타입 | 설명 |
|------|------|------|
| Sync_ID | String | 동기화 UUID |
| Sync_Type | String | full/incremental |
| Started_At | DateTime | 시작 시간 |
| Completed_At | DateTime | 완료 시간 |
| Assets_Count | Integer | 처리된 Asset 수 |
| Status | String | success/failed |
| Error | String | 에러 메시지 (실패 시) |

---

## 4. 아키텍처

### 4.1 시스템 구조도

```
┌─────────────────────────────────────────────────────────────┐
│                    Sync CLI                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │IconikClient │  │MetadataMapper│  │ SheetsWriter        │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
└─────────┼────────────────┼─────────────────────┼─────────────┘
          │                │                     │
          ▼                │                     ▼
┌─────────────────────────┐│        ┌─────────────────────────┐
│      Iconik API         ││        │    Google Sheets        │
│  ┌─────────────────┐    ││        │  ┌───────────────────┐  │
│  │ Assets API      │    │└────────│  │ iconik_api_export │  │
│  │ Metadata API    │────┘         │  │ (26 컬럼)          │  │
│  │ Segments API    │              │  │ Sync_Log          │  │
│  └─────────────────┘              │  └───────────────────┘  │
└─────────────────────────┘         └─────────────────────────┘
          │
          ▼
┌─────────────────────────┐
│   State Storage         │
│   (JSON)                │
│   last_sync_at          │
└─────────────────────────┘
```

### 4.2 데이터 흐름

```
[전체 동기화]
1. Iconik API 호출
   └── GET /assets/ (페이지네이션)
   └── GET /assets/{id}/metadata/{view_id}/ (각 Asset별)
   └── GET /assets/{id}/segments/ (Subclip 타임코드)

2. 데이터 변환
   └── MetadataMapper: Iconik 필드 → 26개 컬럼 매핑
   └── 타임코드 계산: ms → 초 변환

3. Google Sheets 출력
   └── iconik_api_export 시트 덮어쓰기
   └── 배치 쓰기 (1000행 단위)

4. 상태 저장
   └── last_sync_at 기록
   └── Sync_Log에 결과 기록
```

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

| 작업 | Method | Endpoint | 용도 |
|------|--------|----------|------|
| Assets 목록 | GET | `/assets/v1/assets/` | 전체 Asset 조회 |
| Asset 상세 | GET | `/assets/v1/assets/{id}/` | 단일 Asset |
| Metadata | GET | `/metadata/v1/assets/{id}/views/{view_id}/` | Custom Metadata |
| Segments | GET | `/assets/v1/assets/{id}/segments/` | Subclip 타임코드 |

### 5.3 Metadata View 매핑

Iconik Metadata View에서 26개 필드 추출:

```python
METADATA_VIEW_ID = "poker_hand_metadata"  # 실제 View ID로 교체

def map_metadata(asset: dict, metadata: dict, segments: list) -> dict:
    """Iconik 데이터를 26개 컬럼으로 매핑"""
    fields = metadata.get("metadata_values", {})

    # 타임코드 추출 (첫 번째 segment)
    time_start_ms = None
    time_end_ms = None
    if segments:
        segment = segments[0]
        time_start_ms = segment.get("time_base")
        time_end_ms = segment.get("time_end")

    return {
        "id": asset["id"],
        "title": asset["title"],
        "time_start_ms": time_start_ms,
        "time_end_ms": time_end_ms,
        "time_start_S": time_start_ms / 1000 if time_start_ms else None,
        "time_end_S": time_end_ms / 1000 if time_end_ms else None,
        "Description": fields.get("description"),
        "ProjectName": fields.get("project_name"),
        "ProjectNameTag": fields.get("project_name_tag"),
        "SearchTag": fields.get("search_tag"),
        "Year_": fields.get("year"),
        "Location": fields.get("location"),
        "Venue": fields.get("venue"),
        "EpisodeEvent": fields.get("episode_event"),
        "Source": fields.get("source"),
        "Scene": fields.get("scene"),
        "GameType": fields.get("game_type"),
        "PlayersTags": fields.get("players_tags"),
        "HandGrade": fields.get("hand_grade"),
        "HANDTag": fields.get("hand_tag"),
        "EPICHAND": fields.get("epic_hand"),
        "Tournament": fields.get("tournament"),
        "PokerPlayTags": fields.get("poker_play_tags"),
        "Adjective": fields.get("adjective"),
        "Emotion": fields.get("emotion"),
        "AppearanceOutfit": fields.get("appearance_outfit"),
    }
```

---

## 6. 환경 변수

```env
# Iconik API
ICONIK_APP_ID=your-app-id
ICONIK_AUTH_TOKEN=your-auth-token
ICONIK_BASE_URL=https://app.iconik.io
ICONIK_METADATA_VIEW_ID=poker_hand_metadata

# Google Sheets
GOOGLE_SERVICE_ACCOUNT_PATH=D:\AI\claude01\json\service_account_key.json
TARGET_SHEET_ID=1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk
TARGET_SHEET_NAME=iconik_api_export

# Sync 설정
STATE_FILE=data/sync_state.json
BATCH_SIZE=100
RATE_LIMIT_PER_SEC=50
```

---

## 7. 기술 스택

| 구성 요소 | 선택 |
|-----------|------|
| Python | 3.11+ |
| HTTP 클라이언트 | httpx |
| Google API | google-api-python-client |
| 데이터 검증 | Pydantic v2 |
| 상태 저장 | JSON 파일 |
| CLI 출력 | rich |
| 테스트 | pytest |

---

## 8. 구현 계획

### Phase 1: 메타데이터 매퍼 (신규)

| 작업 | 파일 |
|------|------|
| 필드 매핑 로직 | iconik/metadata_mapper.py |
| 26컬럼 모델 | iconik/models.py (수정) |
| 설정 업데이트 | config/settings.py (수정) |

### Phase 2: Sheets 출력 수정

| 작업 | 파일 |
|------|------|
| 26컬럼 Writer | sheets/writer.py (수정) |
| 헤더 포맷 | sheets/formatter.py (신규) |

### Phase 3: 동기화 로직 수정

| 작업 | 파일 |
|------|------|
| 전체 동기화 | sync/full_sync.py (수정) |
| CLI 스크립트 | scripts/run_full_sync.py (수정) |

---

## 9. 성공 기준

| 지표 | 목표 |
|------|------|
| 전체 동기화 완료 시간 | < 15분 (1000 Assets) |
| 26개 컬럼 정확도 | 100% |
| API 호출 성공률 | > 99% |
| 레퍼런스 시트와 일치 | 100% |

---

## 10. 참고 자료

- [Iconik API 문서](https://app.iconik.io/docs/api.html)
- [레퍼런스 시트](https://docs.google.com/spreadsheets/d/1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk)
- [Google Sheets API](https://developers.google.com/sheets/api)
