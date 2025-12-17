# PRD: NAMS 매칭 시스템

> **버전**: 2.0
> **날짜**: 2025-12-17
> **상태**: Active

---

## 1. 개요

### 1.1 프로젝트 목적

NAS Archive 파일과 PokerGO 콘텐츠 메타데이터를 **100% 매칭**하여 완전한 카탈로그를 구축하는 시스템.

### 1.2 핵심 목표

| # | 목표 | 설명 |
|---|------|------|
| 1 | **원본-아카이브 검증** | NAS 원본(Origin)에서 누락된 파일이 Archive에 있는지 확인 |
| 2 | **양방향 매칭 검증** | PokerGO WSOP 데이터 ↔ NAS Archive가 모두 매칭되어야 함 |
| 3 | **매칭 실패 원인 분석** | 매칭 안되는 항목의 원인 파악 → 규칙 수정 → 매칭률 100% 달성 |
| 4 | **카탈로그/제목 설계** | 매칭 불가 NAS Archive 파일의 표준 카탈로그/제목 규칙 정의 |

---

## 2. 현재 상태 분석

### 2.1 데이터 현황 (2025-12-17)

```
┌─────────────────────────────────────────────────────────┐
│                    Data Summary                         │
├─────────────────────────────────────────────────────────┤
│  PokerGO Episodes:       828                           │
│  NAS Groups:             221                           │
│  ├─ MATCHED:             101  (45.7%)                  │
│  ├─ NAS_ONLY_HISTORIC:    18  (8.1%)  ← PokerGO 없음   │
│  └─ NAS_ONLY_MODERN:     102  (46.2%) ← PokerGO 없음   │
│  DUPLICATE:                0                           │
│  Average Match Score:   0.94                           │
└─────────────────────────────────────────────────────────┘
```

**DUPLICATE 문제 100% 해결됨** (374 → 0)

### 2.2 매칭 분류 체계 (4분류)

| 분류 | 건수 | 설명 | 조치 |
|------|------|------|------|
| **MATCHED** | 101 | NAS + PokerGO 매칭 완료 | 완료 |
| **NAS_ONLY_HISTORIC** | 18 | 1973-2002 (PokerGO 데이터 없음) | 카탈로그 자체 생성 |
| **NAS_ONLY_MODERN** | 102 | 2003+ (지역 데이터 없음) | 카탈로그 자체 생성 |
| **POKERGO_ONLY** | - | PokerGO만 존재 | 수집 필요 확인 |

### 2.3 PokerGO 지역별 데이터 가용성

| Region | PokerGO 데이터 | 연도 범위 | NAS 매칭 |
|--------|---------------|----------|----------|
| **LV** (Las Vegas) | 있음 | 1973-2024 | MATCHED |
| **EU** (Europe) | 있음 | 2008-2021 | MATCHED |
| **APAC** | **없음** | - | NAS_ONLY_MODERN |
| **PARADISE** | **없음** | - | NAS_ONLY_MODERN |
| **CYPRUS** | **없음** | - | NAS_ONLY_MODERN |
| **LONDON** | **없음** | - | NAS_ONLY_MODERN |
| **LA** (Circuit) | **없음** | - | NAS_ONLY_MODERN |

---

## 3. 세부 요구사항

### 3.1 목표 1: 원본-아카이브 검증

**목적**: NAS Origin(원본)에서 누락된 파일이 Archive에 있는지 확인

#### 검증 로직

```
[NAS Origin]              [NAS Archive]
    │                          │
    ▼                          ▼
┌──────────┐              ┌──────────┐
│ 원본파일  │  ─────────▶ │ 아카이브  │
│ 목록     │   비교      │ 목록     │
└──────────┘              └──────────┘
    │                          │
    ▼                          ▼
┌────────────────────────────────────────┐
│ 결과:                                   │
│ - 원본+아카이브 모두 존재: Primary     │
│ - 아카이브만 존재: Archive Only        │
│ - 원본만 존재: Origin Only (경고)      │
└────────────────────────────────────────┘
```

#### 출력 데이터

| 필드 | 설명 |
|------|------|
| `origin_exists` | 원본 폴더에 파일 존재 여부 |
| `archive_exists` | 아카이브 폴더에 파일 존재 여부 |
| `sync_status` | `BOTH`, `ORIGIN_ONLY`, `ARCHIVE_ONLY` |

### 3.2 목표 2: 양방향 매칭 검증

**목적**: PokerGO WSOP 데이터와 NAS Archive가 **모두** 매칭되어야 함

#### 매칭 방향

```
┌─────────────────────────────────────────────────────────┐
│                   양방향 매칭                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [NAS Archive]    ◀──────────▶    [PokerGO]            │
│                                                         │
│  Direction A:                                           │
│  NAS → PokerGO                                          │
│  "이 NAS 파일은 어떤 PokerGO 에피소드인가?"            │
│                                                         │
│  Direction B:                                           │
│  PokerGO → NAS                                          │
│  "이 PokerGO 에피소드는 NAS에 있는가?"                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 매칭 결과 카테고리

| 카테고리 | NAS | PokerGO | 조치 |
|----------|-----|---------|------|
| **완전 매칭** | 있음 | 있음 (매칭됨) | 완료 |
| **NAS Only** | 있음 | 없음 (미매칭) | 카탈로그 생성 필요 |
| **PokerGO Only** | 없음 | 있음 | 수집 필요 확인 |
| **Gap** | 있음 | 있음 (매칭 실패) | 규칙 수정 필요 |

### 3.3 목표 3: 매칭 실패 원인 분석

**목적**: 매칭 안되는 항목의 원인을 파악하고 규칙을 수정하여 매칭률 100% 달성

#### 분석 대상

1. **NAS 있음 + PokerGO 미매칭 (307건)**
   - 원인: NAS 패턴 규칙 미지원
   - 해결: 새 패턴 추가

2. **NAS 있음 + PokerGO 있음 but 매칭 실패**
   - 원인: 매칭 알고리즘 문제
   - 해결: 매칭 로직 개선

#### 원인 분류 체계

| 코드 | 원인 | 해결 방향 |
|------|------|-----------|
| `P01` | 패턴 미지원 | 새 패턴 추가 |
| `P02` | 연도 추출 실패 | 연도 추출 규칙 개선 |
| `P03` | 이벤트 타입 인식 실패 | 타입 감지 키워드 추가 |
| `P04` | 에피소드 번호 추출 실패 | 에피소드 정규식 개선 |
| `M01` | PokerGO 타이틀 형식 불일치 | 매칭 알고리즘 개선 |
| `M02` | 유사도 점수 임계값 문제 | 임계값 조정 |
| `D01` | PokerGO에 해당 콘텐츠 없음 | 카탈로그 자체 생성 |
| `D02` | NAS에 해당 콘텐츠 없음 | 수집 필요 여부 확인 |

#### 분석 프로세스

```
[매칭 실패 항목]
      │
      ▼
┌─────────────────────┐
│ 1. 원인 코드 분류   │
│    (P01~D02)        │
└─────────────────────┘
      │
      ▼
┌─────────────────────┐
│ 2. 패턴별 그룹화    │
│    - 유사 패턴 묶기 │
└─────────────────────┘
      │
      ▼
┌─────────────────────┐
│ 3. 규칙 수정 제안   │
│    - 새 패턴 정의   │
│    - 기존 규칙 수정 │
└─────────────────────┘
      │
      ▼
┌─────────────────────┐
│ 4. 테스트 & 검증    │
│    - 재매칭 실행    │
│    - 매칭률 확인    │
└─────────────────────┘
```

### 3.4 목표 4: 카탈로그/제목 설계

**목적**: 매칭 불가 NAS Archive 파일의 표준 카탈로그/제목 규칙 정의

#### 대상

- **PokerGO에 없는 콘텐츠** (D01 케이스)
  - 1973-2010 히스토릭 영상
  - WSOP Paradise (PokerGO 데이터 없음)
  - WSOP Circuit
  - Best Of / 하이라이트

#### 카탈로그 구조

```
┌─────────────────────────────────────────────────────────┐
│                  카탈로그 계층 구조                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Collection (컬렉션)                                     │
│  └─ Season (시즌)                                       │
│     └─ Episode (에피소드)                               │
│                                                         │
│  예시:                                                  │
│  - Collection: "WSOP Historic (1973-2010)"             │
│    └─ Season: "WSOP 1973"                              │
│       └─ Episode: "Main Event"                         │
│                                                         │
│  - Collection: "WSOP Paradise"                         │
│    └─ Season: "WSOP Paradise 2024"                     │
│       └─ Episode: "Super Main Event - Day 1"          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 제목 생성 규칙

| 콘텐츠 타입 | 제목 패턴 | 예시 |
|-------------|-----------|------|
| Main Event | `WSOP {YYYY} Main Event \| Episode {N}` | WSOP 2011 Main Event \| Episode 25 |
| Historic | `WSOP {YYYY} Main Event` | WSOP 1973 Main Event |
| Europe | `WSOPE {YYYY} \| Episode {N}` | WSOPE 2011 \| Episode 1 |
| APAC | `WSOP APAC {YYYY} {Event} \| Show {N}` | WSOP APAC 2013 Main Event \| Show 1 |
| Paradise | `WSOP Paradise {YYYY} {Event} \| {Day}` | WSOP Paradise 2024 Super Main Event \| Day 1 |
| Best Of | `WSOP {YYYY} Best Of {Type}` | WSOP 2003 Best Of All-Ins |

---

## 4. DUPLICATE 해결 규칙

### 4.1 DUPLICATE 정의

동일한 PokerGO 에피소드가 여러 NAS 그룹에 매칭되는 현상.

```
DUPLICATE 발생 예시:
├─ 2023_LA_ME_01 → "WSOP 2023 Ladies Championship Event 71 Day 1"
├─ 2023_BR_E71   → "WSOP 2023 Ladies Championship Event 71 Day 1"  ← 중복!
```

### 4.2 해결된 DUPLICATE 원인

| 원인 | 건수 | 해결 방법 |
|------|------|-----------|
| LA Circuit vs Ladies 혼동 | 17 | LA = Los Angeles Circuit (PokerGO 데이터 없음) |
| Event # 미매칭 | 10 | Event # 있으면 필수 매칭 요구 |
| EU 내부 중복 | 7 | EU 2009 Bracelet = Caesars Cup만 존재 |
| Region Mismatch | 기타 | EU/APAC 그룹 → LV 에피소드 매칭 방지 |

### 4.3 LA Circuit vs Ladies 구분

**중요**: LA는 Los Angeles Circuit이며, Ladies Championship과 다름.

| 구분 | LA (Circuit) | Ladies |
|------|-------------|--------|
| 전체 이름 | WSOP Circuit Los Angeles | Ladies No-Limit Hold'em Championship |
| 지역 | LA | LV |
| Event 번호 | 없음 | Event #71 |
| PokerGO | **없음** | 있음 |
| Group ID | 2023_LA_ME_01 | 2023_BR_E71 |

**규칙**: `WCLA`, `Los Angeles` 키워드 → Region = LA → NAS_ONLY_MODERN

### 4.4 Region Mismatch 규칙

```python
# 매칭 서비스 로직 (matching.py)
if region_code in ('EU', 'APAC', 'PARADISE', 'CYPRUS', 'LONDON', 'LA'):
    if not ep_is_regional:
        # EU/APAC 그룹인데 LV 에피소드 → SKIP
        continue
elif region_code == 'LV':
    if ep_is_regional:
        # LV 그룹인데 Regional 에피소드 → SKIP
        continue
```

### 4.5 Event # 필수 매칭

Bracelet Event 그룹에 event_num이 있으면 반드시 일치해야 매칭.

```python
if group_event_num:
    event_num_patterns = [
        rf'event\s*#?\s*{group_event_num}\b',
        rf'#\s*{group_event_num}\b',
    ]
    if not any(re.search(p, title, re.I) for p in event_num_patterns):
        continue  # Event # 불일치 → SKIP
```

### 4.6 NAS_ONLY 보호

NAS_ONLY_HISTORIC, NAS_ONLY_MODERN으로 분류된 그룹은 재매칭에서 제외.

```python
if group.match_category in (NAS_ONLY_HISTORIC, NAS_ONLY_MODERN):
    continue  # 이미 "PokerGO 없음" 확정
```

---

## 5. 구현 계획

### 5.1 Phase 1: 데이터 분석 (완료)

| 작업 | 상태 | 설명 |
|------|------|------|
| NAS 스캔 | 완료 | 1,529개 파일 스캔 |
| 패턴 매칭 | 완료 | 221개 그룹 생성 |
| PokerGO 매칭 | 완료 | 101개 매칭 |
| Gap 분석 | 완료 | DUPLICATE 100% 해결 |

### 5.2 Phase 2: 규칙 개선 (완료)

| 작업 | 상태 | 설명 |
|------|------|------|
| DUPLICATE 원인 분류 | 완료 | LA/Event#/Region Mismatch 규칙 |
| Region Mismatch 규칙 | 완료 | EU/APAC → LV 매칭 방지 |
| Event # 필수 매칭 | 완료 | Bracelet Event 정확도 향상 |
| NAS_ONLY 보호 | 완료 | 재매칭 시 제외 |

### 5.3 Phase 3: 카탈로그 생성 (진행중)

| 작업 | 설명 |
|------|------|
| 카탈로그 구조 정의 | Collection → Season → Episode |
| 제목 생성기 구현 | NAS 메타데이터 → 표준 제목 |
| 누락 콘텐츠 목록 | PokerGO Only 항목 정리 |

### 5.4 Phase 4: 검증 및 배포

| 작업 | 설명 |
|------|------|
| 100% 매칭 검증 | 모든 NAS ↔ PokerGO 매칭 확인 |
| Google Sheets 내보내기 | 최종 카탈로그 시트 생성 |
| 문서화 | 규칙 문서 최종 업데이트 |

---

## 6. 성공 기준

### 6.1 매칭률 현황

```
┌─────────────────────────────────────────┐
│           매칭률 현황 (달성)             │
├─────────────────────────────────────────┤
│                                         │
│  초기:  57.1% (409/716)                │
│                     │                   │
│                     ▼                   │
│  현재: 100% (221/221) - DUPLICATE 0   │
│                                         │
│  - MATCHED:           101 (45.7%)      │
│  - NAS_ONLY_HISTORIC:  18 (8.1%)       │
│  - NAS_ONLY_MODERN:   102 (46.2%)      │
│                                         │
└─────────────────────────────────────────┘
```

### 6.2 완료 조건

| 조건 | 상태 | 설명 |
|------|------|------|
| **모든 NAS 파일 분류됨** | 완료 | 221개 그룹 분류 |
| **DUPLICATE 0건** | 완료 | 374 → 0 해결 |
| **양방향 매칭 완료** | 완료 | MATCHED/NAS_ONLY 구분 |
| **평균 매칭 점수 > 0.9** | 완료 | 0.94 달성 |

---

## 7. 시트 출력 구조

### 7.1 통합 시트 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                        NAMS Export Sheet                        │
├─────────────────────────────────────────────────────────────────┤
│ Section 1: NAS Groups (716 rows)                               │
│ ├─ PokerGO Matched = "Yes" (409)                               │
│ ├─ PokerGO Matched = "No" (307) → 카탈로그 자체 생성           │
│                                                                 │
│ --- SEPARATOR ---                                               │
│                                                                 │
│ Section 2: Unmatched PokerGO (957 rows)                        │
│ └─ PokerGO Matched = "No NAS" → 수집 필요 여부 확인            │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 컬럼 정의

| 컬럼 | NAS Groups | Unmatched PokerGO |
|------|------------|-------------------|
| Group ID | 2011_ME_25 | (빈값) |
| Year | 2011 | 2011 |
| Region | LV, EU, APAC | (빈값) |
| Event Type | ME, GM, HU | (빈값) |
| Episode | 25 | (빈값) |
| Primary File | WS11_ME25.mp4 | (빈값) |
| PokerGO Matched | Yes / No | No NAS |
| PokerGO Title | WSOP 2011... | WSOP 2011... |
| PokerGO Collection | | WSOP 2011 |
| Catalog Title | (생성됨) | (기존) |
| Match Reason | 매칭 성공/실패 이유 | NAS 없음 |

---

## 8. 관련 문서

| 문서 | 설명 |
|------|------|
| [MATCHING_RULES.md](MATCHING_RULES.md) | 파일 패턴 및 매칭 규칙 상세 (v4.0) |
| [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) | NAMS 시스템 아키텍처 |
| [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) | NAMS 대시보드 사용법 |

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2025-12-16 | 초기 PRD 작성 |
| 2.0 | 2025-12-17 | DUPLICATE 해결 규칙 추가, 4분류 체계 반영, Phase 2 완료 |
