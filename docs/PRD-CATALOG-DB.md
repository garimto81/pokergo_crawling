# PRD: NAS 중심 카탈로그 DB 설계

> NAS 파일 기반 WSOP 콘텐츠 카탈로그 시스템

**Version**: 1.0 | **Date**: 2025-12-17

---

## 1. 배경 및 문제 정의

### 1.1 기존 접근 방식의 한계

```
┌─────────────────────────────────────────────────────────────────┐
│                    데이터 성격 불일치                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [PokerGO 828개]              [NAS 1,405개]                     │
│  ├─ 편집된 에피소드            ├─ 생방송 스트리밍 원본           │
│  ├─ 30-60분 단위              ├─ 수시간 Raw footage            │
│  ├─ 제목/설명 완비             ├─ 파일명만 존재                 │
│  └─ 방송용 최종본              └─ 소스 영상                     │
│                                                                 │
│              1:1 매칭 본질적 불가능                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**기존 문제점:**
- PokerGO 에피소드와 NAS 생방송 원본은 성격이 다름
- 1:1 매칭률을 KPI로 삼는 것 자체가 부적절
- 어떤 단일 DB도 완전하지 않음

### 1.2 새로운 접근: NAS 중심 카탈로그

```
[NAS 파일] → [패턴 추출] → [자체 카탈로그 생성] → [PokerGO는 참조용]
```

**핵심 원칙:**
1. NAS 파일이 실제 보유 자산 → 이를 기준으로 카탈로그 구축
2. PokerGO 메타데이터는 참조 정보로만 활용
3. 자동 생성 + 수동 검증 하이브리드 워크플로우

---

## 2. 데이터 모델

### 2.1 ERD 개요

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Category     │     │  CatalogEntry   │     │    NasFile      │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)         │     │ id (PK)         │
│ code            │◄────│ category_id(FK) │     │ catalog_id (FK)─│───┐
│ name            │     │ display_title   │◄────│ file_path       │   │
│ year            │     │ year            │     │ filename        │   │
│ description     │     │ event_type      │     │ drive           │   │
└─────────────────┘     │ sequence        │     │ file_size       │   │
                        │ source          │     │ duration        │   │
┌─────────────────┐     │ verified        │     │ is_excluded     │   │
│  PokerGoRef     │     │ notes           │     │ role            │   │
├─────────────────┤     └─────────────────┘     └─────────────────┘   │
│ id (PK)         │            ▲                                      │
│ catalog_id (FK)─│────────────┘                                      │
│ pokergo_ep_id   │                                                   │
│ pokergo_title   │     ┌─────────────────────────────────────────────┘
│ relation_type   │     │ 1:N 관계 (하나의 카탈로그에 여러 NAS 파일)
└─────────────────┘     └─────────────────────────────────────────────
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
| description | TEXT | 설명 |
| created_at | DATETIME | 생성일 |

**예시 데이터:**
```
| code         | name              | year | region   |
|--------------|-------------------|------|----------|
| WSOP_2022    | WSOP 2022         | 2022 | LV       |
| WSOP_2022_EU | WSOP Europe 2022  | 2022 | EU       |
| WSOP_1995    | WSOP Classic 1995 | 1995 | LV       |
| WSOP_PARADISE_2024 | WSOP Paradise 2024 | 2024 | PARADISE |
```

#### CatalogEntry (카탈로그 항목)

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
| source | VARCHAR(20) | 생성 방식 (`AUTO`, `MANUAL`, `HYBRID`) |
| verified | BOOLEAN | 검증 완료 여부 |
| verified_at | DATETIME | 검증 일시 |
| verified_by | VARCHAR(100) | 검증자 |
| notes | TEXT | 메모 |
| created_at | DATETIME | 생성일 |
| updated_at | DATETIME | 수정일 |

**예시 데이터:**
```
| entry_code      | display_title                    | event_type | sequence | verified |
|-----------------|----------------------------------|------------|----------|----------|
| WSOP_2022_ME_D1 | WSOP 2022 Main Event Day 1       | ME         | 1        | true     |
| WSOP_2022_ME_D2 | WSOP 2022 Main Event Day 2       | ME         | 2        | true     |
| WSOP_2022_BR_01 | WSOP 2022 Bracelet Event #1      | BR         | 1        | false    |
| WSOP_1995_ME    | WSOP Classic 1995 Main Event     | ME         | NULL     | true     |
```

#### NasFile (NAS 파일)

실제 NAS 드라이브의 파일 정보.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | 자동 증가 |
| catalog_id | INTEGER FK | CatalogEntry 참조 (nullable) |
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

**역할(role) 정의:**
- `PRIMARY`: 주 파일 (Z: Archive 또는 최고 품질)
- `BACKUP`: 백업 파일 (Y: Origin)
- `SOURCE`: PokerGO 소스 (X:)

#### PokerGoRef (PokerGO 참조)

PokerGO 메타데이터 참조 정보. 1:N 관계로 하나의 카탈로그에 여러 에피소드 연결 가능.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | 자동 증가 |
| catalog_id | INTEGER FK | CatalogEntry 참조 |
| pokergo_ep_id | VARCHAR(50) | PokerGO 에피소드 ID |
| pokergo_title | VARCHAR(300) | PokerGO 제목 |
| pokergo_description | TEXT | PokerGO 설명 |
| relation_type | VARCHAR(20) | 관계 유형 (`EXACT`, `PARTIAL`, `RELATED`) |
| notes | TEXT | 메모 |

**관계 유형(relation_type):**
- `EXACT`: 정확히 일치 (드묾)
- `PARTIAL`: 부분 일치 (NAS 1개 = PokerGO 여러 개)
- `RELATED`: 관련 콘텐츠

---

## 3. 카탈로그 생성 로직

### 3.1 자동 생성 파이프라인

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  NAS 스캔    │───▶│  패턴 추출   │───▶│ 카탈로그 생성│───▶│  제목 생성   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
   파일 목록           Year/Event/         CatalogEntry        Display Title
   수집                Sequence 추출        레코드 생성         자동 생성
```

### 3.2 제목 생성 규칙

```python
def generate_display_title(entry: CatalogEntry) -> str:
    """카탈로그 표시 제목 생성"""

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
        seq_type = entry.sequence_type or 'DAY'
        seq_suffix = f" {seq_type.title()} {entry.sequence}"

    return f"{prefix} {entry.year} {event}{seq_suffix}".strip()
```

### 3.3 그룹화 규칙

동일 콘텐츠 파일을 하나의 CatalogEntry로 그룹화:

```python
def create_catalog_key(nas_file: NasFile) -> str:
    """NAS 파일에서 카탈로그 키 생성"""
    year = nas_file.extracted_year
    event = nas_file.extracted_event or 'ME'
    seq = nas_file.extracted_sequence or 0
    region = detect_region(nas_file.file_path)

    return f"{region}_{year}_{event}_{seq:02d}"

# 동일 키를 가진 파일들 → 하나의 CatalogEntry
# 예: WSOP_2022_ME_01 키를 가진 파일 3개 → 1개 CatalogEntry에 3개 NasFile
```

---

## 4. 상태 관리

### 4.1 검증 워크플로우

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   AUTO      │───▶│  REVIEW     │───▶│  VERIFIED   │
│  (자동생성)  │    │  (검토대기)  │    │  (검증완료)  │
└─────────────┘    └─────────────┘    └─────────────┘
       │                                     │
       │         ┌─────────────┐             │
       └────────▶│   MANUAL    │─────────────┘
                 │  (수동입력)  │
                 └─────────────┘
```

### 4.2 완성도 지표

| 지표 | 정의 | 목표 |
|------|------|------|
| **카탈로그 커버리지** | CatalogEntry 연결된 NasFile / 전체 Active NasFile | 95%+ |
| **제목 완성도** | display_title 있는 Entry / 전체 Entry | 100% |
| **검증 완료율** | verified=true Entry / 전체 Entry | 80%+ |
| **PokerGO 참조율** | PokerGoRef 있는 Entry / 전체 Entry | 50%+ (참고) |

---

## 5. API 엔드포인트

### 5.1 카탈로그 관리

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/categories` | 카테고리 목록 |
| GET | `/api/categories/{id}/entries` | 카테고리별 항목 |
| GET | `/api/entries` | 카탈로그 항목 목록 |
| GET | `/api/entries/{id}` | 항목 상세 (파일 포함) |
| PATCH | `/api/entries/{id}` | 항목 수정 (제목, 검증 등) |
| POST | `/api/entries/{id}/verify` | 검증 완료 처리 |
| POST | `/api/entries/generate` | 자동 카탈로그 생성 |

### 5.2 파일 관리

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/files` | NAS 파일 목록 |
| GET | `/api/files/unassigned` | 미할당 파일 |
| PATCH | `/api/files/{id}/assign` | 카탈로그 할당 |

### 5.3 통계

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats/overview` | 전체 통계 |
| GET | `/api/stats/coverage` | 커버리지 통계 |
| GET | `/api/stats/by-year` | 연도별 통계 |

---

## 6. UI 요구사항

### 6.1 대시보드

```
┌─────────────────────────────────────────────────────────────────┐
│                        NAMS 대시보드                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │ 카탈로그 │  │  검증   │  │  파일   │  │ 미할당  │            │
│  │   826   │  │  320    │  │  1,405  │  │   45    │            │
│  │ entries │  │ verified│  │  files  │  │  files  │            │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘            │
│                                                                 │
│  [연도별 분포 차트]                  [검증 상태 파이차트]        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 카탈로그 목록

- 필터: 연도, Region, Event Type, 검증 상태
- 정렬: 연도, 제목, 생성일
- 인라인 편집: 제목, 메모
- 일괄 검증 기능

### 6.3 카탈로그 상세

- 기본 정보 (제목, 연도, 이벤트)
- 연결된 NAS 파일 목록
- PokerGO 참조 정보
- 수정 이력

---

## 7. 마이그레이션 계획

### 7.1 기존 데이터 마이그레이션

```python
# Phase 1: Category 생성
# 기존 AssetGroup의 year/region 조합으로 Category 생성

# Phase 2: CatalogEntry 생성
# 기존 AssetGroup → CatalogEntry 변환
# group_id → entry_code
# pokergo_title → display_title (있으면)
# 없으면 자동 생성

# Phase 3: NasFile 연결
# 기존 nas_files → catalog_id 설정
# group_id 기반으로 매핑

# Phase 4: PokerGoRef 생성
# 기존 pokergo_episode_id → PokerGoRef 레코드
```

### 7.2 스키마 변경

```sql
-- 새 테이블 생성
CREATE TABLE categories (...);
CREATE TABLE catalog_entries (...);
CREATE TABLE pokergo_refs (...);

-- nas_files 테이블 수정
ALTER TABLE nas_files ADD COLUMN catalog_id INTEGER REFERENCES catalog_entries(id);

-- 기존 테이블 백업 후 삭제 (마이그레이션 완료 후)
-- asset_groups, file_groups 등
```

---

## 8. 성공 지표

### 기존 vs 신규 KPI

| 기존 KPI | 신규 KPI |
|----------|----------|
| PokerGO 매칭률 53% | **카탈로그 커버리지** 95%+ |
| MATCHED/NAS_ONLY | **VERIFIED/UNVERIFIED** |
| 패턴 추출률 97.6% | **제목 완성도** 100% |
| - | **검증 완료율** 80%+ |

### 최종 목표

| 지표 | 목표 |
|------|------|
| 카탈로그 항목 수 | 800+ entries |
| 카탈로그 커버리지 | 95%+ (NAS 파일) |
| 제목 완성도 | 100% |
| 검증 완료율 | 80%+ |
| PokerGO 참조율 | 50%+ (보조 지표) |

---

## 변경 이력

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-17 | 초기 설계 - NAS 중심 카탈로그 모델 |
