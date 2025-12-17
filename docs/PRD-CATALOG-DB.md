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

### 4.2 AI 추론 기반 제목 생성 (NONE)

PokerGO 매칭 실패 시, **AI(LLM)를 활용**하여 파일명/경로에서 의미를 추론하여 제목 생성.

#### 왜 AI 추론인가?

| 방식 | 장점 | 단점 |
|------|------|------|
| **패턴 기반** | 빠름, 일관성 | 비표준 파일명 처리 불가 |
| **AI 추론** | 유연함, 맥락 이해 | API 비용, 속도 |

```
패턴 기반 한계 예시:
  "MPP_Cyprus_2025_Day3_Final_Table.mp4"
  → 패턴: 추출 실패 (비표준)
  → AI: "WSOP Cyprus 2025 Day 3 Final Table"
```

#### AI 추론 프롬프트 (PokerGO 컨텍스트 활용)

```python
def generate_title_with_ai(nas_file: NasFile, pokergo_context: List[dict]) -> str:
    """AI를 활용한 카테고리/제목 생성 (PokerGO 메타데이터 참조)"""

    # PokerGO 828개 에피소드 요약 (연도/카테고리별)
    context_summary = summarize_pokergo_context(pokergo_context)

    prompt = f"""
    다음 NAS 파일 정보와 PokerGO 메타데이터를 참고하여 WSOP 콘텐츠의 카테고리와 제목을 생성해주세요.

    ## NAS 파일 정보
    - 파일명: {nas_file.filename}
    - 경로: {nas_file.file_path}
    - 추출된 연도: {nas_file.extracted_year}
    - 추출된 이벤트: {nas_file.extracted_event}

    ## PokerGO 참조 데이터 (유사 콘텐츠)
    {context_summary}

    ## 생성 규칙
    1. PokerGO에 유사한 콘텐츠가 있으면 그 형식을 따름
    2. 카테고리 형식: "WSOP [지역] [연도]" (예: "WSOP 2024", "WSOP Europe 2022")
    3. 제목 형식: "[카테고리] [이벤트] [세부정보]"
    4. 이벤트: Main Event, Bracelet Event, High Roller, Mystery Bounty 등
    5. 세부정보: Day 1, Episode 3, Final Table, Part 2 등

    ## PokerGO 제목 예시 (참고)
    - "2024 WSOP Main Event Day 1A"
    - "2023 WSOP $10,000 Heads Up Championship Round of 16"
    - "WSOP Europe 2022 Main Event Episode 5"

    JSON 형식으로 출력:
    {{"category": "...", "title": "..."}}
    """

    response = llm.generate(prompt)
    return parse_json_response(response)
```

#### PokerGO 컨텍스트 활용

```
┌──────────────────────────────────────────────────────────────┐
│                 AI 추론 + PokerGO 컨텍스트                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  [Input]                                                     │
│  ├─ NAS 파일: "MPP_Cyprus_2025_Day3_FT.mp4"                 │
│  ├─ 경로: "Z:\WSOP\Cyprus\2025\"                            │
│  └─ PokerGO 참조:                                           │
│      ├─ "2024 WSOP Paradise Main Event Day 1" (유사)        │
│      ├─ "2023 WSOP Paradise $10K High Roller" (유사)        │
│      └─ (828개 중 관련 항목 제공)                            │
│                                                              │
│  [Output]                                                    │
│  ├─ category: "WSOP Cyprus 2025"                            │
│  └─ title: "WSOP Cyprus 2025 Main Event Day 3 Final Table"  │
│                                                              │
│  [장점]                                                      │
│  └─ PokerGO 제목 스타일과 일관성 유지                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### 처리 흐름

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  NONE 항목   │───▶│  AI 추론     │───▶│  검증 대기   │
│  (매칭 실패)  │    │  제목 생성   │    │  (UNVERIFIED)│
└──────────────┘    └──────────────┘    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Batch 처리  │
                    │  (비용 최적화)│
                    └──────────────┘
```

#### 비용 최적화

| 전략 | 설명 |
|------|------|
| **Batch 처리** | 여러 파일을 한 번에 처리 |
| **캐싱** | 동일 패턴 결과 재사용 |
| **Fallback** | AI 실패 시 패턴 기반으로 대체 |
| **모델 선택** | **Gemini** (Google AI) 사용 |

#### Gemini 모델 설정

```python
import google.generativeai as genai

# Gemini 설정
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")  # 저비용, 빠른 추론

def generate_with_gemini(prompt: str) -> str:
    response = model.generate_content(prompt)
    return response.text
```

| 모델 | 용도 | 비용 |
|------|------|------|
| **gemini-1.5-flash** | 대량 처리 (권장) | 저비용 |
| gemini-1.5-pro | 복잡한 추론 | 중비용 |

#### 패턴 기반 Fallback

AI 추론 실패 또는 비용 절감 시 사용:

```python
def generate_title_fallback(entry: CategoryEntry) -> str:
    """패턴 기반 제목 생성 (Fallback)"""

    region_prefix = {
        'LV': 'WSOP', 'EU': 'WSOP Europe', 'APAC': 'WSOP APAC',
        'PARADISE': 'WSOP Paradise', 'CYPRUS': 'WSOP Cyprus', 'LA': 'WSOP Circuit LA',
    }
    event_names = {
        'ME': 'Main Event', 'BR': 'Bracelet Event', 'HU': 'Heads Up',
        'GM': 'Global Masters', 'HR': 'High Roller',
    }

    prefix = region_prefix.get(entry.category.region, 'WSOP')
    event = event_names.get(entry.event_type, '')
    seq = f" Day {entry.sequence}" if entry.sequence else ""

    return f"{prefix} {entry.year} {event}{seq}".strip()
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
