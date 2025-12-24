# DB 아카이빙 계획

**버전**: 1.0
**날짜**: 2025-12-18
**목적**: WSOP 콘텐츠의 체계적인 DB 아카이빙 전략 수립

---

## 1. 아카이빙 목표

### 1.1 핵심 목표

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         아카이빙의 핵심 목표                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. 콘텐츠 카탈로그 구축                                                     │
│     └─ 모든 WSOP 영상을 고유 Entry로 식별 가능하게 정리                       │
│                                                                             │
│  2. 파일 위치 추적                                                           │
│     └─ 각 Entry에 연결된 물리적 파일 위치 관리                               │
│                                                                             │
│  3. 메타데이터 보강                                                          │
│     └─ PokerGO 정보로 공식 타이틀, 설명, 재생시간 확보                        │
│                                                                             │
│  4. 갭 분석                                                                  │
│     └─ 보유하지 않은 콘텐츠 식별 (→ Find NAS)                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 아카이빙 vs 매칭

| 구분 | 아카이빙 | 매칭 |
|------|----------|------|
| **목적** | 콘텐츠 카탈로그 구축 | 메타데이터 보강 |
| **주체** | Category Entry | PokerGO Episode |
| **결과** | 782개 고유 Entry | 24개 EXACT Match |
| **우선순위** | **핵심** | 보조 |

**핵심 원칙**: 매칭 여부와 관계없이 모든 콘텐츠는 DB에 Entry로 존재해야 함

---

## 2. 데이터 모델

### 2.1 계층 구조

```
Category (카테고리)
    └── WSOP_2025 (WSOP 2025)
    └── WSOP_2025_EU (WSOP Europe 2025)
    └── WSOP_2024 (WSOP 2024)
    └── ...
        │
        ▼
CategoryEntry (콘텐츠 단위)
    └── WSOP_2025_ME_01 (Main Event Day 1)
    └── WSOP_2025_BR_E13 (Bracelet Event #13)
    └── ...
        │
        ▼
NasFile (물리적 파일)
    └── WSOP 2025 Main Event _ Day 1A.mp4
    └── WSOP 2025 Main Event _ Day 1B.mp4
    └── ...
```

### 2.2 Entry 코드 규칙

```
{SERIES}_{YEAR}_{REGION}_{TYPE}_{SEQ}

예시:
├── WSOP_2025_ME_01        → 2025 Main Event Episode 1
├── WSOP_2025_BR_E13       → 2025 Bracelet Event #13
├── WSOP_2025_EU_ME_01     → 2025 Europe Main Event Ep 1
├── WSOP_2025_EU_BR_01     → 2025 Europe Bracelet Event 1
├── WSOP_2025_CYPRUS       → 2025 Cyprus (전체)
└── WSOP_1987_ME           → 1987 Main Event (CLASSIC)
```

### 2.3 Match Type 정의

| Type | 의미 | 파일 | PokerGO |
|------|------|------|---------|
| **EXACT** | 완전 매칭 | O | O |
| **NONE** | NAS Only | O | X |
| **POKERGO_ONLY** | PokerGO Only | X | O |

---

## 3. 현재 DB 현황

### 3.1 전체 현황

```
┌─────────────────────────────────────────────────────────────────┐
│                    DB 현황 (2025-12-18)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Category Entries: 782개                                        │
│  ├── EXACT:        24개 ( 3.1%) - NAS + PokerGO 매칭            │
│  ├── NONE:        435개 (55.6%) - NAS Only                      │
│  └── POKERGO_ONLY: 323개 (41.3%) - PokerGO Only                 │
│                                                                 │
│  NAS Files: 858개 (17.9 TB)                                     │
│  ├── Z: Archive:  858개                                         │
│  └── Excluded:    547개                                         │
│                                                                 │
│  연도 범위: 1973 - 2025 (39개 연도)                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 연도별 분포

| Era | 연도 | Entry 수 | 특징 |
|-----|------|----------|------|
| **CLASSIC** | 1973-2002 | ~50 | 연도당 ME 1개 |
| **BOOM** | 2003-2010 | ~200 | 에피소드 단위 |
| **HD** | 2011-2025 | ~530 | Day/Part 단위 |

---

## 4. 아카이빙 전략

### 4.1 Entry 생성 원칙

```
┌─────────────────────────────────────────────────────────────────┐
│                    Entry 생성 우선순위                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1순위: PokerGO 메타데이터 기반                                  │
│         → 공식 타이틀, 에피소드 번호 확보                        │
│         → pokergo_title, pokergo_ep_id 설정                     │
│                                                                 │
│  2순위: NAS 파일명 패턴 분석                                     │
│         → 연도, 이벤트 타입, 에피소드 추출                       │
│         → entry_code 자동 생성                                  │
│                                                                 │
│  3순위: 수동 분류                                                │
│         → 패턴 불일치 파일 수동 검토                             │
│         → notes 필드에 분류 근거 기록                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 파일-Entry 연결

| 상황 | 처리 |
|------|------|
| 1 Entry : N Files | 정상 (Day 1A, 1B, 1C → ME_D1) |
| N Entries : 1 File | 비정상 (검토 필요) |
| Entry without Files | POKERGO_ONLY (수집 필요) |
| File without Entry | 패턴 추가 또는 수동 분류 |

### 4.3 제외 vs 미분류

| 구분 | is_excluded | entry_id | 의미 |
|------|-------------|----------|------|
| **정상** | False | 있음 | Entry에 연결됨 |
| **제외** | True | 없음 | 아카이브 대상 아님 |
| **미분류** | False | 없음 | 패턴 추가 필요 |

---

## 5. 2025년 아카이빙 계획

### 5.1 현황 분석

| 구분 | Entry | Files | 상태 |
|------|-------|-------|------|
| **WSOP 2025 LV** | 31 | 39 | POKERGO_ONLY 29, NONE 2 |
| **WSOP 2025 EU** | 5 | 115 | NONE 5 (WSOPE 파일) |
| **WSOP 2025 CYPRUS** | 3 | 11 | NONE 3 |
| **미분류** | - | ~40 | HyperDeck 등 |

### 5.2 작업 계획

```
Phase 1: Entry 구조 정리
├── WSOP_2025_BR_E{N}: Bracelet Event #N (Event 번호 기준)
├── WSOP_2025_ME_{N}: Main Event Episode N (Day/Part 기준)
├── WSOP_2025_EU_BR_{N}: Europe Bracelet
└── WSOP_2025_CYPRUS: Cyprus 이벤트

Phase 2: 파일 연결
├── Event #N 패턴 → WSOP_2025_BR_E{N}
├── Main Event Day N → WSOP_2025_ME_{N}
├── WSOPE #N → WSOP_2025_EU_BR_{N}
└── HyperDeck → 제외 (is_excluded=True)

Phase 3: 메타데이터 보강
├── PokerGO title 연결
├── match_score 계산
└── match_type 업데이트
```

### 5.3 예상 결과

| 구분 | Before | After | 변화 |
|------|--------|-------|------|
| EXACT | 0 | ~29 | +29 |
| NONE | 10 | ~20 | +10 |
| POKERGO_ONLY | 29 | ~0 | -29 |
| 제외 | 0 | ~40 | +40 |

---

## 6. 품질 관리

### 6.1 검증 체크리스트

```
□ 모든 NAS 파일이 Entry에 연결되어 있는가?
□ 제외 파일이 명확한 기준으로 분류되었는가?
□ Entry 코드가 규칙을 따르는가?
□ POKERGO_ONLY Entry에 올바른 메타데이터가 있는가?
□ EXACT Entry의 매칭이 정확한가?
```

### 6.2 중복 방지

| 규칙 | 설명 |
|------|------|
| **Region 분리** | EU/APAC 파일 → LV Entry 연결 금지 |
| **Event # 필수** | Bracelet Event는 Event 번호 일치 필수 |
| **연도 일치** | 2024 파일 → 2025 Entry 연결 금지 |

### 6.3 갭 리포트

```sql
-- POKERGO_ONLY: 수집 필요 콘텐츠
SELECT entry_code, pokergo_title
FROM category_entries
WHERE match_type = 'POKERGO_ONLY';

-- 미연결 파일: 패턴 추가 필요
SELECT filename, folder
FROM nas_files
WHERE entry_id IS NULL AND is_excluded = 0;
```

---

## 7. 하위 문서

| 문서 | 내용 |
|------|------|
| `MATCHING_2025_PLAN.md` | 2025년 상세 매칭 계획 |
| `MATCHING_RULES.md` | 패턴 매칭 규칙 |
| `SYSTEM_OVERVIEW.md` | 시스템 전체 구조 |

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2025-12-18 | 초기 문서 작성 |
