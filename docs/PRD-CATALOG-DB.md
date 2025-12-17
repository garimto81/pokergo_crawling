# PRD: NAS 중심 카테고리 DB 설계

> NAS 파일 기반 WSOP 콘텐츠 카테고리 시스템 (하이브리드 접근)

**Version**: 2.0 | **Date**: 2025-12-17

---

## 1. 배경 및 문제 정의

### 1.1 현재 상황 (복잡함)

```
┌─────────────────────────────────────────────────────────────────┐
│                    데이터 관계: 부분 매칭                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [PokerGO 828개]              [NAS 858개 Active]                │
│  ├─ 완성된 카테고리            ├─ 일부: PokerGO와 매칭 가능      │
│  ├─ 완성된 제목                └─ 일부: PokerGO와 매칭 불가      │
│  └─ 편집된 에피소드                                              │
│                                                                 │
│  핵심 인사이트:                                                  │
│  ├─ 전부 매칭되는 것도 아님                                      │
│  ├─ 전부 매칭 안 되는 것도 아님                                  │
│  └─ 개별 검사 + 매칭 작업 필요                                   │
│                                                                 │
│  PokerGO의 가치:                                                 │
│  └─ 카테고리와 제목이 가장 완성도 높음 → 최대한 활용             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 하이브리드 접근

```
NAS 파일 858개
    │
    ├─[매칭 가능]──▶ PokerGO 카테고리/제목 활용
    │                 (완성된 메타데이터)
    │
    └─[매칭 불가]──▶ 자체 카테고리/제목 생성
                      (패턴 기반 자동 생성)
```

**핵심 원칙:**
1. PokerGO 매칭 가능 → PokerGO 카테고리/제목 우선 사용
2. PokerGO 매칭 불가 → 자체 카테고리/제목 생성
3. 개별 파일 검사를 통한 정확한 매칭
4. 수동 검증 워크플로우

---

## 2. 데이터 모델

### 2.1 ERD 개요

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Category     │     │  CategoryEntry  │     │    NasFile      │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)         │     │ id (PK)         │
│ code            │◄────│ category_id(FK) │     │ entry_id (FK)───│───┐
│ name            │     │ display_title   │◄────│ file_path       │   │
│ year            │     │ year            │     │ filename        │   │
│ region          │     │ event_type      │     │ drive           │   │
│ source          │     │ sequence        │     │ file_size       │   │
└─────────────────┘     │ source          │     │ is_excluded     │   │
                        │ pokergo_ep_id   │     │ role            │   │
                        │ verified        │     └─────────────────┘   │
                        └─────────────────┘                           │
                               ▲                                      │
                               └──────────────────────────────────────┘
                                    1:N (하나의 Entry에 여러 NAS 파일)
```

### 2.2 테이블 정의

#### Category (카테고리)

콘텐츠의 최상위 분류. 연도별 시리즈 단위.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | 자동 증가 |
| code | VARCHAR(50) | 고유 코드 (예: `WSOP_2022`) |
| name | VARCHAR(200) | 표시명 (예: `WSOP 2022`) |
| year | INTEGER | 연도 |
| region | VARCHAR(20) | 지역 (LV, EU, APAC, PARADISE, ...) |
| source | VARCHAR(20) | 출처 (`POKERGO`, `NAS_ONLY`, `HYBRID`) |
| pokergo_category | VARCHAR(100) | PokerGO 원본 카테고리명 (있으면) |
| description | TEXT | 설명 |
| created_at | DATETIME | 생성일 |

**source 정의:**
- `POKERGO`: PokerGO에서 가져온 카테고리
- `NAS_ONLY`: NAS 파일에서 자체 생성
- `HYBRID`: 둘 다 혼합

**예시 데이터:**
```
| code         | name              | year | region   | source   |
|--------------|-------------------|------|----------|----------|
| WSOP_2022    | WSOP 2022         | 2022 | LV       | POKERGO  |
| WSOP_2022_EU | WSOP Europe 2022  | 2022 | EU       | POKERGO  |
| WSOP_1995    | WSOP Classic 1995 | 1995 | LV       | POKERGO  |
| WSOP_PARADISE_2024 | WSOP Paradise 2024 | 2024 | PARADISE | NAS_ONLY |
```

#### CategoryEntry (카테고리 항목)

개별 콘텐츠 단위. NAS 파일 그룹의 논리적 단위.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | 자동 증가 |
| category_id | INTEGER FK | Category 참조 |
| entry_code | VARCHAR(100) | 고유 코드 (예: `WSOP_2022_ME_D1`) |
| display_title | VARCHAR(300) | 표시 제목 |
| year | INTEGER | 연도 |
| event_type | VARCHAR(20) | 이벤트 타입 (ME, BR, HU, GM, ...) |
| event_name | VARCHAR(200) | 이벤트명 (예: `Main Event`) |
| sequence | INTEGER | 순서 (Day/Episode/Part 번호) |
| sequence_type | VARCHAR(20) | 순서 유형 (`DAY`, `EPISODE`, `PART`) |
| source | VARCHAR(20) | 출처 (`POKERGO`, `NAS_ONLY`) |
| pokergo_ep_id | VARCHAR(50) | PokerGO 에피소드 ID (있으면) |
| pokergo_title | VARCHAR(300) | PokerGO 원본 제목 (있으면) |
| match_type | VARCHAR(20) | 매칭 유형 (`EXACT`, `PARTIAL`, `MANUAL`, `NONE`) |
| verified | BOOLEAN | 검증 완료 여부 |
| verified_at | DATETIME | 검증 일시 |
| verified_by | VARCHAR(100) | 검증자 |
| notes | TEXT | 메모 |
| created_at | DATETIME | 생성일 |
| updated_at | DATETIME | 수정일 |

**source 정의:**
- `POKERGO`: PokerGO 매칭 성공 → PokerGO 제목 사용
- `NAS_ONLY`: PokerGO 매칭 실패 → 자체 제목 생성

**match_type 정의:**
- `EXACT`: PokerGO와 정확히 1:1 매칭
- `PARTIAL`: PokerGO와 부분 매칭 (1:N 또는 N:1)
- `MANUAL`: 수동으로 매칭/지정
- `NONE`: 매칭 없음 (자체 생성)

**예시 데이터:**
```
| entry_code      | display_title                    | source   | match_type | pokergo_ep_id |
|-----------------|----------------------------------|----------|------------|---------------|
| WSOP_2022_ME_D1 | 2022 WSOP Main Event Day 1       | POKERGO  | EXACT      | ep_12345      |
| WSOP_2022_ME_D2 | 2022 WSOP Main Event Day 2       | POKERGO  | PARTIAL    | ep_12346      |
| WSOP_2024_PAR_01| WSOP Paradise 2024 Day 1         | NAS_ONLY | NONE       | NULL          |
| WSOP_1995_ME    | WSOP Classic 1995 - Dan Harrington| POKERGO | EXACT      | ep_00123      |
```

#### NasFile (NAS 파일)

실제 NAS 드라이브의 파일 정보.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | 자동 증가 |
| entry_id | INTEGER FK | CategoryEntry 참조 (nullable) |
| file_path | VARCHAR(500) | 전체 경로 |
| filename | VARCHAR(300) | 파일명 |
| drive | VARCHAR(10) | 드라이브 (`X:`, `Y:`, `Z:`) |
| folder | VARCHAR(20) | 폴더 유형 (`pokergo`, `origin`, `archive`) |
| file_size | BIGINT | 파일 크기 (bytes) |
| duration | INTEGER | 영상 길이 (초) |
| extension | VARCHAR(10) | 확장자 |
| is_excluded | BOOLEAN | 제외 여부 |
| exclude_reason | VARCHAR(100) | 제외 사유 |
| role | VARCHAR(20) | 역할 (`PRIMARY`, `BACKUP`, `SOURCE`) |
| extracted_year | INTEGER | 패턴 추출 연도 |
| extracted_event | VARCHAR(20) | 패턴 추출 이벤트 |
| extracted_sequence | INTEGER | 패턴 추출 순서 |
| created_at | DATETIME | 생성일 |
| updated_at | DATETIME | 수정일 |

---

## 3. 매칭 워크플로우

### 3.1 전체 흐름

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  NAS 스캔    │───▶│  패턴 추출   │───▶│ PokerGO 매칭 │───▶│  검증 대기   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                               │
                          ┌────────────────────┼────────────────────┐
                          │                    │                    │
                          ▼                    ▼                    ▼
                    ┌──────────┐         ┌──────────┐         ┌──────────┐
                    │ EXACT    │         │ PARTIAL  │         │ NONE     │
                    │ 매칭     │         │ 매칭     │         │ 자체생성  │
                    └──────────┘         └──────────┘         └──────────┘
                          │                    │                    │
                          ▼                    ▼                    ▼
                    PokerGO 제목          PokerGO 제목         자체 제목
                    그대로 사용           + 수동 확인          자동 생성
```

### 3.2 매칭 판정 로직

```python
def determine_match_type(nas_file: NasFile, pokergo_episodes: List) -> MatchResult:
    """NAS 파일과 PokerGO 에피소드 매칭 판정"""

    # 1. 정확한 매칭 시도
    exact_matches = find_exact_matches(nas_file, pokergo_episodes)
    if len(exact_matches) == 1:
        return MatchResult(
            type='EXACT',
            pokergo_ep=exact_matches[0],
            title=exact_matches[0].title,
            source='POKERGO'
        )

    # 2. 부분 매칭 시도
    partial_matches = find_partial_matches(nas_file, pokergo_episodes)
    if partial_matches:
        return MatchResult(
            type='PARTIAL',
            pokergo_ep=partial_matches[0],  # 가장 유사한 것
            title=partial_matches[0].title,
            source='POKERGO',
            requires_verification=True
        )

    # 3. 매칭 실패 → 자체 생성
    return MatchResult(
        type='NONE',
        pokergo_ep=None,
        title=generate_title(nas_file),
        source='NAS_ONLY'
    )
```

### 3.3 제목 결정 우선순위

| 우선순위 | 조건 | 제목 출처 |
|----------|------|----------|
| 1 | EXACT 매칭 | PokerGO 제목 그대로 |
| 2 | PARTIAL 매칭 | PokerGO 제목 (검증 필요) |
| 3 | MANUAL 지정 | 수동 입력 제목 |
| 4 | NONE | 자동 생성 제목 |

---

## 4. 제목 생성 규칙

### 4.1 PokerGO 제목 사용 (EXACT/PARTIAL)

```python
# PokerGO 매칭 시 → PokerGO 제목 그대로 사용
entry.display_title = pokergo_episode.title
entry.source = 'POKERGO'
entry.pokergo_title = pokergo_episode.title
```

### 4.2 자체 제목 생성 (NONE)

```python
def generate_display_title(entry: CategoryEntry) -> str:
    """자체 카테고리/제목 생성 (PokerGO 매칭 실패 시)"""

    # Era별 처리
    if entry.year <= 2002:  # CLASSIC Era
        champion = WSOP_CHAMPIONS.get(entry.year, "")
        if champion:
            return f"WSOP Classic {entry.year} - {champion}"
        return f"WSOP Classic {entry.year}"

    # Region별 처리
    region_prefix = {
        'LV': 'WSOP',
        'EU': 'WSOP Europe',
        'APAC': 'WSOP APAC',
        'PARADISE': 'WSOP Paradise',
        'CYPRUS': 'WSOP Cyprus',
        'LA': 'WSOP Circuit LA',
    }

    prefix = region_prefix.get(entry.category.region, 'WSOP')

    # Event Type별 처리
    event_names = {
        'ME': 'Main Event',
        'BR': 'Bracelet Event',
        'HU': 'Heads Up Championship',
        'GM': 'Global Masters',
        'HR': 'High Roller',
    }

    event = event_names.get(entry.event_type, entry.event_name or '')

    # Sequence 처리
    seq_suffix = ""
    if entry.sequence:
        seq_type = entry.sequence_type or 'Day'
        seq_suffix = f" {seq_type} {entry.sequence}"

    return f"{prefix} {entry.year} {event}{seq_suffix}".strip()
```

---

## 5. 상태 관리

### 5.1 검증 워크플로우

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ UNVERIFIED  │───▶│  REVIEWING  │───▶│  VERIFIED   │
│ (자동생성)   │    │  (검토중)   │    │  (검증완료)  │
└─────────────┘    └─────────────┘    └─────────────┘
       │                                     │
       │         ┌─────────────┐             │
       └────────▶│   MANUAL    │─────────────┘
                 │  (수동입력)  │
                 └─────────────┘
```

### 5.2 검증 우선순위

| 우선순위 | 대상 | 이유 |
|----------|------|------|
| 1 | PARTIAL 매칭 | 자동 매칭 불확실 |
| 2 | NONE (자체 생성) | 제목 정확성 확인 |
| 3 | EXACT 매칭 | 스팟 체크 |

---

## 6. 완성도 지표

### 6.1 KPI 정의

| 지표 | 정의 | 목표 |
|------|------|------|
| **카테고리 커버리지** | Entry 연결된 NasFile / Active NasFile | 95%+ |
| **제목 완성도** | display_title 있는 Entry / 전체 Entry | 100% |
| **PokerGO 활용률** | source='POKERGO' Entry / 전체 Entry | 60%+ |
| **검증 완료율** | verified=true Entry / 전체 Entry | 80%+ |

### 6.2 매칭 분포 목표

| 매칭 유형 | 예상 비율 | 비고 |
|----------|----------|------|
| EXACT | 40% | PokerGO 완전 매칭 |
| PARTIAL | 15% | 수동 확인 필요 |
| MANUAL | 5% | 수동 지정 |
| NONE | 40% | 자체 생성 (Paradise, Cyprus 등) |

---

## 7. API 엔드포인트

### 7.1 카테고리 관리

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/categories` | 카테고리 목록 |
| GET | `/api/categories/{id}/entries` | 카테고리별 항목 |
| GET | `/api/entries` | 항목 목록 (필터: source, match_type, verified) |
| GET | `/api/entries/{id}` | 항목 상세 (파일 포함) |
| PATCH | `/api/entries/{id}` | 항목 수정 (제목, 매칭 등) |
| POST | `/api/entries/{id}/verify` | 검증 완료 처리 |

### 7.2 매칭 작업

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/matching/run` | 자동 매칭 실행 |
| GET | `/api/matching/candidates/{file_id}` | 매칭 후보 조회 |
| POST | `/api/matching/manual` | 수동 매칭 지정 |

### 7.3 통계

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats/overview` | 전체 통계 |
| GET | `/api/stats/matching` | 매칭 유형별 통계 |
| GET | `/api/stats/by-year` | 연도별 통계 |

---

## 8. 성공 지표

### 최종 목표

| 지표 | 목표 |
|------|------|
| 카테고리 항목 수 | 800+ entries |
| 카테고리 커버리지 | 95%+ |
| 제목 완성도 | 100% |
| PokerGO 활용률 | 60%+ |
| 검증 완료율 | 80%+ |

### 핵심 원칙

1. **PokerGO 우선**: 매칭 가능하면 PokerGO 카테고리/제목 사용
2. **자체 생성 보완**: 매칭 불가 시 자체 카테고리/제목 생성
3. **개별 검증**: 모든 매칭 결과를 수동 검증

---

## 변경 이력

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2025-12-17 | 하이브리드 접근 반영, 카탈로그→카테고리 용어 변경 |
| 1.0 | 2025-12-17 | 초기 설계 - NAS 중심 모델 |
