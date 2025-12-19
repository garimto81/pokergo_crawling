# 2025 매칭 계획

**버전**: 1.0
**날짜**: 2025-12-18
**상위 문서**: `PRD-DB-ARCHIVING-PLAN.md`

---

## 1. 2025 데이터 현황

### 1.1 요약

| 구분 | 수량 | 비고 |
|------|------|------|
| **총 Entry** | 39개 | |
| **총 NAS Files** | 126개 | 2,420.8 GB |
| **EXACT** | 0개 | 매칭 전 |
| **NONE** | 10개 | NAS Only |
| **POKERGO_ONLY** | 29개 | PokerGO Only |

### 1.2 카테고리별 분포

```
WSOP 2025 (LV)           31 entries
├── Bracelet Events      22 entries (POKERGO_ONLY 20, NONE 2)
└── Main Event            9 entries (POKERGO_ONLY 9)

WSOP EU 2025              5 entries
├── Bracelet Events       3 entries (NONE 3)
└── Main Event            2 entries (NONE 2)

WSOP CYPRUS 2025          3 entries (NONE 3)
```

---

## 2. NAS 파일 분석

### 2.1 파일 분류

| 분류 | 파일 수 | 용량 | 패턴 |
|------|---------|------|------|
| **Bracelet Events** | 39 | - | `Event #N` |
| **Main Event** | 20 | - | `Main Event Day N` |
| **WSOPE** | 27 | - | `WSOPE #N` |
| **Cyprus** | 7 | 111.6 GB | `PokerOK`, `Luxon Pay` |
| **Other** | 33 | - | `HyperDeck` 등 |

### 2.2 Bracelet Events 상세

**NAS 파일 (Event # 추출)**:
```
Event #1:  2 files → WSOP_2025_BR_E01
Event #3:  2 files → (PokerGO 없음)
Event #7:  2 files → WSOP_2025_BR_E07
Event #9:  1 file  → WSOP_2025_BR_E09
Event #13: 2 files → WSOP_2025_BR_E13
Event #14: 1 file  → WSOP_2025_BR_E14
Event #19: 1 file  → WSOP_2025_BR_E19
Event #20: 1 file  → WSOP_2025_BR_E20
Event #22: 1 file  → WSOP_2025_BR_E22
Event #26: 2 files → WSOP_2025_BR_02
Event #30: 1 file  → WSOP_2025_BR_E30
Event #32: 2 files → WSOP_2025_BR_E32
Event #37: 1 file  → WSOP_2025_BR_E37
Event #38: 2 files → (PokerGO 없음)
Event #41: 1 file  → WSOP_2025_BR_E41
Event #46: 2 files → (PokerGO 없음)
Event #48: 1 file  → WSOP_2025_BR_E48
Event #51: 2 files → WSOP_2025_BR_03
Event #53: 1 file  → WSOP_2025_BR_E53
Event #57: 1 file  → WSOP_2025_BR_E57
Event #59: 2 files → (PokerGO 없음)
Event #66: 4 files → (PokerGO 없음)
Event #67: 1 file  → WSOP_2025_BR_E67
Event #70: 1 file  → WSOP_2025_BR_E70
Event #74: 1 file  → WSOP_2025_BR_E74
Event #76: 1 file  → WSOP_2025_BR_E76
```

**매칭 가능**: 21개 이벤트
**NAS Only**: 5개 이벤트 (#3, #38, #46, #59, #66)

### 2.3 Main Event 상세

**NAS 파일**:
```
Day 1: 4 files (1A, 1B, 1C, 1D)
Day 2: 3 files (2A_B_C Part 1/2, 2D)
Day 3: 1 file
Day 4: 2 files (Part 1/2)
Day 5: 2 files (Part 1/2)
Day 6: 2 files (Part 1/2)
Day 7: 2 files (Part 1/2)
Day 8: 2 files (Part 1/2)
Final Table: 2 files (Day 1/2)
```

**PokerGO Entry**:
```
WSOP_2025_ME_01: Day 1B & $100K PLO Final Table
WSOP_2025_ME_02: Day 2A/B/C (Part 1)
WSOP_2025_ME_03: Day 3
WSOP_2025_ME_04: Day 4 (Part 1)
WSOP_2025_ME_05: Day 5 (Part 1)
WSOP_2025_ME_06: Day 6 (Part 1)
WSOP_2025_ME_07: Day 7 (Part 1)
WSOP_2025_ME_08: Day 8 (Part 1)
```

**매칭 전략**: Day + Part 조합으로 매칭

| NAS File | PokerGO Entry | 매칭 |
|----------|---------------|------|
| Day 1B | ME_01 | EXACT |
| Day 2A_B_C (Part 1) | ME_02 | EXACT |
| Day 3 | ME_03 | EXACT |
| Day 4 (Part 1) | ME_04 | EXACT |
| Day 5 (Part 1) | ME_05 | EXACT |
| Day 6 (Part 1) | ME_06 | EXACT |
| Day 7 (Part 1) | ME_07 | EXACT |
| Day 8 (Part 1) | ME_08 | EXACT |
| Day 1A, 1C, 1D | - | NONE (새 Entry) |
| Day N (Part 2) | - | NONE (새 Entry) |
| Final Table | - | NONE (새 Entry) |

### 2.4 WSOPE 파일

```
WSOPE #2:  2 files (King's Million Part1/2)
WSOPE #7:  2 files (Colossus Part1/2)
WSOPE #10: 2 files (PLO Mystery Bounty Part1/2)
기타 WSOPE 파일: 21 files
```

→ 별도 카테고리 `WSOP_2025_EU` Entry로 관리

### 2.5 제외 대상

| 파일 패턴 | 수량 | 사유 |
|-----------|------|------|
| `HyperDeck_XXXX-XXX.mp4` | ~29 | 원본 녹화 파일 |
| `$1M GTD PokerOK...` | 4 | Cyprus (비-WSOP) |
| `$2M GTD Luxon Pay...` | 3 | Cyprus (비-WSOP) |
| `$5M GTD MPP Main Event` | 4 | 비-WSOP 이벤트 |

---

## 3. 매칭 계획

### 3.1 Phase 1: Bracelet Events

**작업**:
1. NAS 파일에서 `Event #(\d+)` 추출
2. PokerGO Entry의 `pokergo_title`에서 Event # 매칭
3. 일치 시 NAS 파일을 해당 Entry에 연결
4. `match_type` → `EXACT` 업데이트

**예상 결과**: 21개 Entry EXACT 매칭

### 3.2 Phase 2: Main Event

**작업**:
1. NAS 파일에서 `Day (\d+)` + `(Part \d+)` 추출
2. PokerGO Entry Title과 Day/Part 매칭
3. 일치 시 연결, 불일치 시 새 Entry 생성

**새 Entry 생성 필요**:
```
WSOP_2025_ME_D1A   → Day 1A
WSOP_2025_ME_D1C   → Day 1C
WSOP_2025_ME_D1D   → Day 1D
WSOP_2025_ME_D2_P2 → Day 2 Part 2
WSOP_2025_ME_D2D   → Day 2D
... (Part 2 파일들)
WSOP_2025_ME_FT_D1 → Final Table Day 1
WSOP_2025_ME_FT_D2 → Final Table Day 2
```

### 3.3 Phase 3: WSOPE

**작업**:
1. `WSOPE #(\d+)` 패턴으로 Entry 생성
2. 기존 `WSOP_2025_EU_BR_99` 분리

**새 Entry**:
```
WSOP_2025_EU_BR_02  → WSOPE #2 King's Million
WSOP_2025_EU_BR_07  → WSOPE #7 Colossus
WSOP_2025_EU_BR_10  → WSOPE #10 PLO Mystery Bounty
```

### 3.4 Phase 4: 제외 처리

**작업**:
1. HyperDeck 파일 → `is_excluded = True`
2. Cyprus 비-WSOP 파일 → 별도 카테고리 또는 제외

---

## 4. 구현 순서

```
Step 1: 제외 처리
└── HyperDeck, 비-WSOP 파일 제외 (is_excluded=True)

Step 2: Bracelet Event 매칭
└── Event # 기반 NAS-PokerGO 연결

Step 3: Main Event Entry 재구성
├── 기존 ME_01~08 유지 (PokerGO 매칭)
└── 새 Entry 생성 (NAS Only 파일용)

Step 4: WSOPE Entry 재구성
├── BR_99 분리
└── WSOPE #N별 Entry 생성

Step 5: 검증
├── 모든 파일 Entry 연결 확인
├── match_type 정확성 검증
└── 중복 Entry 체크
```

---

## 5. 예상 결과

### 5.1 Entry 변화

| 구분 | Before | After | 변화 |
|------|--------|-------|------|
| **EXACT** | 0 | 29 | +29 |
| **NONE** | 10 | 25 | +15 |
| **POKERGO_ONLY** | 29 | 0 | -29 |
| **제외 파일** | 0 | 40 | +40 |

### 5.2 최종 Entry 목록 (예상)

```
WSOP 2025 LV (Bracelet)
├── WSOP_2025_BR_E01  [EXACT] Event #1
├── WSOP_2025_BR_E03  [NONE]  Event #3 (PokerGO 없음)
├── WSOP_2025_BR_E07  [EXACT] Event #7
├── ... (26개)

WSOP 2025 LV (Main Event)
├── WSOP_2025_ME_01   [EXACT] Day 1B
├── WSOP_2025_ME_D1A  [NONE]  Day 1A
├── WSOP_2025_ME_D1C  [NONE]  Day 1C
├── ... (20개)

WSOP 2025 EU
├── WSOP_2025_EU_BR_02 [NONE] WSOPE #2
├── WSOP_2025_EU_BR_07 [NONE] WSOPE #7
├── ... (10개)

WSOP 2025 CYPRUS
├── WSOP_2025_CYPRUS   [NONE] Cyprus 이벤트
```

---

## 6. SQL 스크립트

### 6.1 Bracelet Event 매칭

```sql
-- Event # 추출 및 매칭
UPDATE nas_files
SET entry_id = (
    SELECT e.id FROM category_entries e
    WHERE e.year = 2025
    AND e.event_type = 'BR'
    AND e.pokergo_title LIKE '%Event #' ||
        CAST(regexp_extract(nas_files.filename, 'Event #(\d+)', 1) AS TEXT) || '%'
)
WHERE year = 2025
AND filename LIKE '%Event #%'
AND entry_id IS NULL;
```

### 6.2 제외 처리

```sql
-- HyperDeck 파일 제외
UPDATE nas_files
SET is_excluded = 1
WHERE filename LIKE 'HyperDeck_%'
AND year = 2025;

-- 비-WSOP Cyprus 파일 제외
UPDATE nas_files
SET is_excluded = 1
WHERE year = 2025
AND (filename LIKE '%PokerOK%' OR filename LIKE '%Luxon Pay%' OR filename LIKE '%MPP Main Event%');
```

---

## 7. 검증 쿼리

```sql
-- 미연결 파일 확인
SELECT filename, folder
FROM nas_files
WHERE year = 2025 AND entry_id IS NULL AND is_excluded = 0;

-- Entry별 파일 수 확인
SELECT e.entry_code, e.match_type, COUNT(f.id) as file_count
FROM category_entries e
LEFT JOIN nas_files f ON f.entry_id = e.id
WHERE e.year = 2025
GROUP BY e.id
ORDER BY e.entry_code;

-- EXACT 매칭 검증
SELECT e.entry_code, e.pokergo_title, f.filename
FROM category_entries e
JOIN nas_files f ON f.entry_id = e.id
WHERE e.year = 2025 AND e.match_type = 'EXACT';
```

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2025-12-18 | 초기 문서 작성 |
