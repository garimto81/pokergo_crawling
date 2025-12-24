# 2025 매칭 분석

**버전**: 2.0
**날짜**: 2025-12-18
**분석 대상**: 경로 + 파일명 (NAS), Title (PokerGO)

---

## 1. 데이터 구조

### 1.1 NAS 파일 (분석 대상: `full_path`)

```
경로에서 추출 가능한 정보:
- 지역: WSOP-LAS VEGAS, WSOP-EUROPE, MPP Cyprus, Circuit
- 이벤트 타입: BRACELET SIDE EVENT, MAIN EVENT
- 연도: 2025
- Event #: Event #13, Event #26 등
```

### 1.2 PokerGO (분석 대상: `title`)

```
Title 구조:
- "WSOP 2025 Bracelet Events | Event #N $XXK Event Name"
- "WSOP 2025 Main Event | Day N (Part N)"
- "WSOP 2025 Main Event | Day N | Table B Only (Part N)"

Collection/Season: 빈 값 (사용 불가)
```

---

## 2. NAS 파일 경로 분류

### 2.1 경로 패턴

| 경로 패턴 | 지역 | 파일 수 | 유효 | 제외 |
|-----------|------|---------|------|------|
| `Z:\ARCHIVE\WSOP\...\WSOP-LAS VEGAS\2025 WSOP-LAS VEGAS\WSOP 2025 BRACELET SIDE EVENT\` | LV | 41 | 39 | 2 |
| `Z:\ARCHIVE\WSOP\...\WSOP-LAS VEGAS\2025 WSOP-LAS VEGAS\WSOP 2025 MAIN EVENT\` | LV | 20 | 20 | 0 |
| `Z:\ARCHIVE\WSOP\...\WSOP-EUROPE\2025 WSOP-Europe\` | EU | 56 | 27 | 29 |
| `Z:\ARCHIVE\MPP\2025 MPP Cyprus\` | CYPRUS | 11 | 11 | 0 |
| `Z:\ARCHIVE\WSOP\WSOP Circuit Event\...\2025 WSOP Super Circuit Cyprus\` | CIRCUIT | 6 | 0 | 6 |

### 2.2 제외 파일

| 패턴 | 수량 | 사유 |
|------|------|------|
| `HyperDeck_*.mp4` | 29 | 원본 녹화 파일 |
| `*_789647313.mp4` | 1 | 중복 파일 |
| `*_79684924.mp4` | 1 | 중복 파일 |
| `*_725964551.mp4` | 1 | 중복 파일 |
| `Super Circuit Cyprus` | 6 | Circuit 이벤트 |

---

## 3. PokerGO 데이터 분류

### 3.1 Bracelet Events (35개)

```
Event #1, #3, #7, #9, #13, #14, #19, #20, #22, #26,
#30, #32, #37, #38, #41, #46, #48, #51, #53, #57,
#59, #66, #67, #70, #74, #76

Day/Part 변형:
- Event #7: Final, Final Four (2개)
- Event #26: Base, Day 2 (2개)
- Event #38: Base, Day 2 (2개)
- Event #46: Base, Day 2 (2개)
- Event #51: Base, Day 3 (2개)
- Event #59: Base, Day 2 (2개)
- Event #66: Base, Day 3, Day 4 Part 1/2 (4개)
```

### 3.2 Main Event (35개)

```
기본 Day:
- Day 1A, 1B, 1C, 1D (4개)
- Day 2A/B/C Part 1/2, Day 2D (3개)
- Day 3 (1개)
- Day 4-8 Part 1/2 (각 2개, 총 10개)
- Final Table Day 1/2 (2개)

Table B/C Only 변형 (NAS 없음):
- Day 5 Table B Only Part 1/2 (2개)
- Day 5 Table C Only Part 1/2 (2개)
- Day 6 Table B Only Part 1/2 (2개)
- Day 6 Table C Only Part 1/2 (2개)
- Day 7 Table B Only Part 1/2 (2개)
- Day 7 Table C Only Part 1/2 (2개)
- Day 8 Table B Only Part 1/2 (2개)
- Day 8 Table C Only Part 1/2 (2개)
```

---

## 4. 매칭 분석

### 4.1 LV Bracelet Events

| NAS Event # | NAS Files | PokerGO Entries | 매칭 |
|-------------|-----------|-----------------|------|
| #1 | 2 | 1 | EXACT |
| #3 | 2 | 1 | EXACT |
| #7 | 2 | 2 (Final, F4) | EXACT |
| #9 | 1 | 1 | EXACT |
| #13 | 2 | 1 | EXACT |
| #14 | 1 | 1 | EXACT |
| ... | ... | ... | ... |
| **Total** | **39** | **35** | **26 Events** |

### 4.2 LV Main Event

| NAS Files | PokerGO Entries | 상태 |
|-----------|-----------------|------|
| Day 1A | Day 1A | EXACT |
| Day 1B & $100K PLO | Day 1B & $100K PLO | EXACT |
| Day 1C | Day 1C | EXACT |
| Day 1D | Day 1D | EXACT |
| Day 2A/B/C Part 1/2 | Day 2A/B/C Part 1/2 | EXACT |
| Day 2D | Day 2D | EXACT |
| Day 3 | Day 3 | EXACT |
| Day 4 Part 1/2 | Day 4 Part 1/2 | EXACT |
| Day 5 Part 1/2 | Day 5 Part 1/2 | EXACT |
| Day 6 Part 1/2 | Day 6 Part 1/2 | EXACT |
| Day 7 Part 1/2 | Day 7 Part 1/2 | EXACT |
| Day 8 Part 1/2 | Day 8 Part 1/2 | EXACT |
| Final Table Day 1/2 | Final Table Day 1/2 | EXACT |
| - | Day 5-8 Table B/C Only | POKERGO_ONLY |

### 4.3 EU / Cyprus

| 지역 | NAS Files | PokerGO | 상태 |
|------|-----------|---------|------|
| EU | 27 valid | 0 | NAS_ONLY |
| CYPRUS_MPP | 11 valid | 0 | NAS_ONLY |
| CYPRUS_CIRCUIT | 0 valid | 0 | EXCLUDED |

---

## 5. 최종 매칭 결과 (예상)

### 5.1 Entry 분류

| Match Type | Entry 수 | 설명 |
|------------|----------|------|
| **EXACT** | ~50 | LV Bracelet + LV Main Event |
| **POKERGO_ONLY** | ~15 | Main Event Table B/C Only |
| **NAS_ONLY** | ~38 | EU + Cyprus |

### 5.2 파일 분류

| 상태 | 파일 수 | 설명 |
|------|---------|------|
| **Connected** | 97 | Entry에 연결됨 |
| **Excluded** | 37 | HyperDeck, Circuit 등 |
| **Total** | 134 | |

---

## 6. 구현 계획

### 6.1 매칭 규칙

```python
# 1. 경로에서 지역 추출
def extract_region(full_path):
    if 'WSOP-LAS VEGAS' in full_path.upper():
        return 'LV'
    elif 'WSOP-EUROPE' in full_path.upper():
        return 'EU'
    elif 'MPP CYPRUS' in full_path.upper():
        return 'CYPRUS_MPP'
    elif 'CIRCUIT' in full_path.upper():
        return 'CYPRUS_CIRCUIT'
    return 'OTHER'

# 2. Event # 추출 (경로 + 파일명)
def extract_event_num(full_path):
    match = re.search(r'Event #?(\d+)', full_path, re.I)
    return int(match.group(1)) if match else None

# 3. Main Event Day/Part 추출
def extract_main_event_info(full_path):
    day_match = re.search(r'Day (\d+[A-D]?)', full_path, re.I)
    part_match = re.search(r'Part (\d+)', full_path, re.I)
    return {
        'day': day_match.group(1) if day_match else None,
        'part': int(part_match.group(1)) if part_match else None
    }

# 4. PokerGO 매칭 (LV만)
def match_pokergo(nas_file, pokergo_entries):
    region = extract_region(nas_file.full_path)
    if region != 'LV':
        return None  # NAS_ONLY

    # Event # 또는 Day/Part로 매칭
    ...
```

### 6.2 Entry 생성 규칙

| 조건 | Entry Code 패턴 | 예시 |
|------|-----------------|------|
| LV Bracelet | `WSOP_2025_BR_E{N}` | WSOP_2025_BR_E13 |
| LV Main Event | `WSOP_2025_ME_D{N}P{M}` | WSOP_2025_ME_D4P1 |
| EU Bracelet | `WSOP_2025_EU_E{N}` | WSOP_2025_EU_E10 |
| Cyprus MPP | `MPP_2025_CYPRUS_{EVENT}` | MPP_2025_CYPRUS_POKEROK |

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2025-12-18 | 초기 문서 |
| 2.0 | 2025-12-18 | 경로 기반 분석으로 재작성 |
