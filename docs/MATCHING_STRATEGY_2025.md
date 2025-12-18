# 2025 매칭 전략

**버전**: 1.4
**날짜**: 2025-12-18

---

## 1. 요소 분석

### 1.1 NAS 파일 (분석 대상: `full_path`)

```
Z:\ARCHIVE\WSOP\WSOP Bracelet Event\WSOP-LAS VEGAS\2025 WSOP-LAS VEGAS\WSOP 2025 BRACELET SIDE EVENT\WSOP 2025 Bracelet Events _ Event #13 $1.5K No-Limit Hold'em 6-Max\(PokerGO) WSOP 2025 Bracelet Events _ Event #13 $1.5K No-Limit Hold'em 6-Max.mp4
├── [1] 드라이브: Z:
├── [2] 폴더: ARCHIVE
├── [3] 시리즈: WSOP
├── [4] 카테고리: WSOP Bracelet Event
├── [5] 지역: WSOP-LAS VEGAS → LV
├── [6] 연도폴더: 2025 WSOP-LAS VEGAS
├── [7] 이벤트타입: WSOP 2025 BRACELET SIDE EVENT → BR
├── [8] 콘텐츠폴더: WSOP 2025 Bracelet Events _ Event #13...
│   └── Event #: 13
├── [9] 파일명: (PokerGO) WSOP 2025 Bracelet Events _ Event #13...mp4
│   ├── 소스: (PokerGO), (YouTube)
│   └── Event #: 13
└── [10] 확장자: .mp4
```

### 1.2 추출 요소 정의

| 요소 | 추출 위치 | 정규식 | 예시 |
|------|-----------|--------|------|
| **Region** | 경로 [5] | `WSOP-(LAS VEGAS\|EUROPE)` | LV, EU |
| **Year** | 경로 [6] | `(20\d{2})` | 2025 |
| **Event Type** | 경로 [7] | `(BRACELET\|MAIN EVENT)` | BR, ME |
| **Event #** | 경로 [8] + 파일명 [9] | `Event #?(\d+)` | 13 |
| **Day** | 파일명 | `Day (\d+[A-D]?)` | 1A, 2, FT |
| **Part** | 파일명 | `Part (\d+)` | 1, 2 |
| **Source** | 파일명 | `\((PokerGO\|YouTube)\)` | PokerGO |

### 1.3 PokerGO (분석 대상: `title`)

```
WSOP 2025 Bracelet Events | Event #13 $1.5K No-Limit Hold'em 6-Max
├── [1] 시리즈: WSOP
├── [2] 연도: 2025
├── [3] 이벤트타입: Bracelet Events → BR
├── [4] Event #: 13
├── [5] Buy-in: $1.5K
└── [6] 이벤트명: No-Limit Hold'em 6-Max
```

```
WSOP 2025 Main Event | Day 5 | Table B Only (Part 1)
├── [1] 시리즈: WSOP
├── [2] 연도: 2025
├── [3] 이벤트타입: Main Event → ME
├── [4] Day: 5
├── [5] Table: B (변형)
└── [6] Part: 1
```

---

## 2. 매칭 규칙

### 2.1 지역별 매칭

```
┌─────────────────────────────────────────────────────────┐
│                    매칭 가능성                           │
├─────────────┬───────────────┬───────────────────────────┤
│ NAS 지역    │ PokerGO 매칭  │ 결과                       │
├─────────────┼───────────────┼───────────────────────────┤
│ LV          │ O             │ EXACT / POKERGO_ONLY      │
│ EU          │ X             │ NAS_ONLY                  │
│ CYPRUS_MPP  │ X             │ NAS_ONLY                  │
│ CIRCUIT     │ X             │ EXCLUDED                  │
└─────────────┴───────────────┴───────────────────────────┘
```

### 2.2 Bracelet Event 매칭

```python
# 매칭 키: Event #
nas_key = f"BR_E{event_num}"      # BR_E13
pkg_key = f"BR_E{event_num}"      # BR_E13

# 규칙
if nas_region == 'LV' and nas_event_num == pkg_event_num:
    match_type = 'EXACT'
elif nas_region == 'LV' and nas_event_num not in pkg_events:
    match_type = 'NAS_ONLY'  # LV이지만 PKG에 없음
elif nas_region in ['EU', 'CYPRUS']:
    match_type = 'NAS_ONLY'  # 지역 커버리지 없음
```

### 2.3 Main Event 매칭

```python
# 매칭 키: Day + Part + Table
nas_key = f"ME_D{day}P{part}"           # ME_D5P1
pkg_key = f"ME_D{day}P{part}"           # ME_D5P1
pkg_key_table = f"ME_D{day}T{table}P{part}"  # ME_D5TBP1 (Table B Only)

# 규칙
if nas_day_part == pkg_day_part:
    match_type = 'EXACT'
elif pkg_has_table_variant:
    match_type = 'POKERGO_ONLY'  # Table B/C Only는 NAS 없음
```

---

## 3. Entry 생성 규칙

### 3.1 Entry Code 패턴

| 조건 | 패턴 | 예시 |
|------|------|------|
| LV Bracelet | `WSOP_{YEAR}_BR_E{N}` | WSOP_2025_BR_E13 |
| LV Bracelet Day | `WSOP_{YEAR}_BR_E{N}_D{D}` | WSOP_2025_BR_E66_D3 |
| LV Main Event | `WSOP_{YEAR}_ME_D{D}P{P}` | WSOP_2025_ME_D5P1 |
| LV Main Event Table | `WSOP_{YEAR}_ME_D{D}T{T}P{P}` | WSOP_2025_ME_D5TBP1 |
| EU Bracelet | `WSOP_{YEAR}_EU_E{N}` | WSOP_2025_EU_E10 |
| Cyprus MPP | `MPP_{YEAR}_{EVENT}` | MPP_2025_POKEROK |

### 3.2 Match Type 결정

```
┌─────────────────────────────────────────────────────────────┐
│                    Match Type 결정 로직                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. NAS 파일 존재?                                          │
│     ├── Yes → 2번으로                                       │
│     └── No  → 3번으로                                       │
│                                                             │
│  2. NAS 지역이 LV?                                          │
│     ├── Yes → PokerGO 매칭 존재?                            │
│     │         ├── Yes → EXACT                              │
│     │         └── No  → NAS_ONLY (LV지만 PKG 없음)          │
│     └── No  → NAS_ONLY (EU/Cyprus)                         │
│                                                             │
│  3. PokerGO Only (NAS 없음)                                 │
│     └── POKERGO_ONLY                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 스크립트 구조

### 4.1 전체 흐름

```
┌──────────────────────────────────────────────────────────────┐
│                      매칭 파이프라인                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Step 1: 데이터 로드                                         │
│  ├── NAS 파일 (DB: nas_files WHERE year=2025)               │
│  └── PokerGO 데이터 (JSON: wsop_final.json WHERE 2025)      │
│                                                              │
│  Step 2: 요소 추출                                           │
│  ├── NAS: extract_nas_elements(full_path) → NasElement      │
│  └── PKG: extract_pkg_elements(title) → PkgElement          │
│                                                              │
│  Step 3: Entry 생성                                          │
│  ├── NAS 기반 Entry 생성 (지역별)                            │
│  └── PokerGO Only Entry 생성                                 │
│                                                              │
│  Step 4: 매칭                                                 │
│  ├── LV: Event # / Day+Part 매칭                            │
│  └── EU/Cyprus: NAS_ONLY 설정                               │
│                                                              │
│  Step 5: 파일 연결                                           │
│  └── NAS 파일 → Entry 연결                                  │
│                                                              │
│  Step 6: 검증 & 리포트                                       │
│  ├── 미연결 파일 확인                                        │
│  ├── 중복 Entry 확인                                         │
│  └── 통계 출력                                               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 핵심 함수

```python
# === Step 2: 요소 추출 ===

@dataclass
class NasElement:
    file_id: int
    full_path: str
    filename: str
    region: str          # LV, EU, CYPRUS_MPP, CIRCUIT
    event_type: str      # BR, ME
    event_num: int       # Event #13 → 13
    day: str             # Day 5 → "5", Day 1A → "1A", Final Table → "FT"
    part: int            # Part 1 → 1
    source: str          # (PokerGO), (YouTube)
    is_excluded: bool

@dataclass
class PkgElement:
    title: str
    event_type: str      # BR, ME
    event_num: int
    day: str
    part: int
    table: str           # Table B → "B"

def extract_nas_elements(full_path: str, filename: str) -> NasElement:
    """경로 + 파일명에서 요소 추출."""
    region = extract_region(full_path)
    event_type = extract_event_type(full_path)
    event_num = extract_event_num(full_path + ' ' + filename)
    day, part = extract_day_part(filename)
    source = extract_source(filename)
    ...

def extract_pkg_elements(title: str) -> PkgElement:
    """Title에서 요소 추출."""
    event_type = 'BR' if 'Bracelet' in title else 'ME'
    event_num = extract_event_num(title)
    day, part, table = extract_day_part_table(title)
    ...
```

```python
# === Step 3: Entry 생성 ===

def generate_entry_code(elem: NasElement | PkgElement, source: str) -> str:
    """Entry Code 생성."""
    if isinstance(elem, NasElement):
        if elem.region == 'LV':
            if elem.event_type == 'BR':
                return f"WSOP_2025_BR_E{elem.event_num}"
            elif elem.event_type == 'ME':
                day_str = elem.day or ''
                part_str = f"P{elem.part}" if elem.part else ''
                return f"WSOP_2025_ME_D{day_str}{part_str}"
        elif elem.region == 'EU':
            return f"WSOP_2025_EU_E{elem.event_num}"
        elif elem.region == 'CYPRUS_MPP':
            return f"MPP_2025_CYPRUS"
    else:  # PkgElement
        if elem.event_type == 'BR':
            return f"WSOP_2025_BR_E{elem.event_num}"
        elif elem.event_type == 'ME':
            table_str = f"T{elem.table}" if elem.table else ''
            return f"WSOP_2025_ME_D{elem.day}{table_str}P{elem.part}"
```

```python
# === Step 4: 매칭 ===

def match_entries(nas_elements: list, pkg_elements: list) -> dict:
    """NAS와 PokerGO 매칭."""
    results = {}

    # NAS 기반 Entry 생성
    for nas in nas_elements:
        entry_code = generate_entry_code(nas, 'NAS')
        if entry_code not in results:
            results[entry_code] = {
                'nas_files': [],
                'pkg_title': None,
                'match_type': 'NAS_ONLY' if nas.region != 'LV' else 'NAS_ONLY'
            }
        results[entry_code]['nas_files'].append(nas.file_id)

    # PokerGO 매칭
    for pkg in pkg_elements:
        entry_code = generate_entry_code(pkg, 'PKG')
        if entry_code in results:
            results[entry_code]['pkg_title'] = pkg.title
            results[entry_code]['match_type'] = 'EXACT'
        else:
            results[entry_code] = {
                'nas_files': [],
                'pkg_title': pkg.title,
                'match_type': 'POKERGO_ONLY'
            }

    return results
```

### 4.3 스크립트 파일 구조

```
scripts/
├── match_2025.py              # 메인 매칭 스크립트
│   ├── load_data()            # Step 1
│   ├── extract_elements()     # Step 2
│   ├── generate_entries()     # Step 3
│   ├── match_pokergo()        # Step 4
│   ├── connect_files()        # Step 5
│   └── report()               # Step 6
│
├── export_2025_analysis.py    # Google Sheets 내보내기
└── verify_2025_matching.py    # 검증 스크립트
```

---

## 5. 구현 계획

### Phase 1: 요소 추출 함수

```python
# extractors.py
def extract_region(full_path: str) -> str
def extract_event_type(full_path: str) -> str
def extract_event_num(text: str) -> int
def extract_day_part(text: str) -> tuple[str, int]
def extract_source(filename: str) -> str
def extract_table(title: str) -> str
```

### Phase 2: Entry 생성 로직

```python
# entry_generator.py
def generate_entry_code(elem, source) -> str
def create_entry(entry_code, match_type, pkg_title) -> CategoryEntry
```

### Phase 3: 매칭 로직

```python
# matcher.py
def match_bracelet(nas_elements, pkg_elements) -> dict
def match_main_event(nas_elements, pkg_elements) -> dict
def match_eu_cyprus(nas_elements) -> dict
```

### Phase 4: DB 업데이트

```python
# updater.py
def reset_2025_entries(db)      # 기존 Entry 초기화
def create_entries(db, results) # Entry 생성
def connect_files(db, results)  # 파일 연결
def update_stats(db)            # 통계 업데이트
```

---

## 6. 예상 결과

| Match Type | Entry 수 | 파일 수 |
|------------|----------|---------|
| **EXACT** | 46 | 59 |
| **NAS_ONLY** | 10 | 38 |
| **POKERGO_ONLY** | 16 | 0 |
| **제외** | - | 37 |
| **Total** | 72 | 97 (valid) |

---

## 7. Google Sheets 출력 형식 ★ v1.1

### 7.1 시트 구성

| 시트명 | 용도 | 행 수 |
|--------|------|-------|
| `2025_Catalog` | 전체 파일 카탈로그 (Match Type 포함) | 132+ (NAS 파일 수) |
| `2025_Summary` | Match Type별/지역별 요약 통계 | 15 |
| `2025_PokerGO_Only` | NAS 미확보 PokerGO 비디오 | 20+ |

### 7.2 2025_Catalog 컬럼 정의

| 컬럼 | 설명 | 예시 |
|------|------|------|
| **No** | 행 번호 | 1, 2, 3... |
| **Entry Key** | 정규화된 고유 키 | `WSOP_2025_BR_E13` |
| **Match Type** | 매칭 상태 | `EXACT`, `NAS_ONLY`, `POKERGO_ONLY` |
| **Category** | 카테고리명 | `WSOP 2025 Bracelet Events` |
| **Title** | 표시 제목 | `Event #13 $1.5K No-Limit Hold'em 6-Max` |
| **PokerGO Title** | 매칭된 PokerGO 제목 | (EXACT만 표시) |
| **Region** | 지역 코드 | `LV`, `EU`, `CYPRUS`, `CIRCUIT` |
| **Event Type** | 이벤트 타입 | `BR`, `ME` |
| **Event #** | 이벤트 번호 | 1, 13, 66... |
| **Day** | 날짜/단계 | `1A`, `2ABC`, `FT` |
| **Part** | 파트 번호 | 1, 2, 3... |
| **RAW** | HyperDeck 원본 여부 | `Yes` / (공백) |
| **Size (GB)** | 파일 크기 | 8.61 |
| **Filename** | 파일명 | `(PokerGO) WSOP 2025...mp4` |
| **Full Path** | 전체 경로 | `Z:\ARCHIVE\WSOP\...` |

### 7.3 Match Type 정의

| Match Type | 설명 | NAS | PokerGO |
|------------|------|-----|---------|
| **EXACT** | 완전 매칭 | ✓ | ✓ |
| **NAS_ONLY** | NAS만 존재 | ✓ | ✗ |
| **POKERGO_ONLY** | PokerGO만 존재 | ✗ | ✓ |

### 7.4 2025_Summary 구조

```
┌─────────────────────────────────────────────────────────┐
│ Match Type별 요약                                        │
├─────────────┬─────────┬─────────┬─────────┬─────────────┤
│ Match Type  │ Region  │ Entries │ Files   │ Size (GB)   │
├─────────────┼─────────┼─────────┼─────────┼─────────────┤
│ EXACT       │ LV      │ 48      │ 52      │ 420.5       │
│ NAS_ONLY    │ EU      │ 52      │ 56      │ 280.3       │
│ NAS_ONLY    │ CYPRUS  │ 6       │ 11      │ 45.2        │
│ NAS_ONLY    │ CIRCUIT │ 6       │ 6       │ 32.1        │
│ NAS_ONLY    │ LV      │ 7       │ 7       │ 38.4        │
│ POKERGO_ONLY│ LV      │ 20      │ 0       │ -           │
└─────────────┴─────────┴─────────┴─────────┴─────────────┘

┌─────────────────────────────────────────────────────────┐
│ Match Type Totals                                        │
├─────────────┬─────────┬─────────────────────────────────┤
│ EXACT       │ 48      │ 52 files                        │
│ NAS_ONLY    │ 71      │ 80 files                        │
│ POKERGO_ONLY│ 20      │ 0 files                         │
└─────────────┴─────────┴─────────────────────────────────┘
```

### 7.5 스크립트

**파일**: `scripts/match_2025.py`

**사용법**:
```bash
python scripts/match_2025.py
```

**출력**:
- Console: 매칭 통계 요약
- Google Sheets: 3개 시트 업데이트

---

## 8. 정규화 규칙 ★ v1.2

### 8.1 Final Table vs Final Day

| 구분 | 의미 | Day 값 | 표시 |
|------|------|--------|------|
| **Final Table** | 마지막 1 테이블 (9명 이하) | `FT` | `Final Table` |
| **Final Day** | 마지막 날 (여러 테이블 가능) | `FinalDay` | `Final Day` |

```python
# extract_day() 로직
if 'Final Table' in filename:
    return 'FT'           # → "Final Table"
if 'Final Day' in filename:
    return 'FinalDay'     # → "Final Day"
```

### 8.2 EU Bracelet Event 분류

EU region에서는 Event # 기준으로 분류:

| Event # | Event Type | Category |
|---------|------------|----------|
| #14 | ME (Main Event) | WSOP Europe 2025 - Main Event |
| 그 외 | BR (Bracelet) | WSOP Europe 2025 - {이벤트명} |

**EU Event 목록:**
| # | 이벤트명 |
|---|----------|
| 2 | €350 King's Million |
| 4 | €2K Monsterstack |
| 5 | €1.1K Mini Main Event |
| 6 | €2K PLO |
| 7 | €550 Colossus |
| 10 | €10K PLO Mystery Bounty |
| 13 | €1K GGMillion€ |
| 14 | €10.35K Main Event |

### 8.3 NC/STREAM 버전 분리 (EU only)

EU 파일에서 같은 콘텐츠의 다른 버전 구분:

| 버전 | 설명 | 경로 패턴 |
|------|------|-----------|
| **NC** | No Commentary (무해설 + 그래픽) | `NO COMMENTARY`, `_NC.`, `_NC_` |
| **STREAM** | 원본 스트림 | `\STREAM\` |

```python
# Entry Key 예시
WSOP_2025_EU_ME_D3_NC      # No Commentary 버전
WSOP_2025_EU_ME_D3_STREAM  # Stream 버전
```

### 8.4 Cyprus Entry Key 분리

Cyprus 이벤트별 Entry Key 생성:

| 이벤트 | Event Code | Entry Key 예시 |
|--------|------------|----------------|
| PokerOK Mystery Bounty | `POKEROK` | `MPP_2025_POKEROK_D1A` |
| Luxon Pay Grand Final | `LUXON` | `MPP_2025_LUXON_D1C` |
| MPP Main Event | `ME` | `MPP_2025_ME_D3_S1` |

### 8.5 경로 기반 추출 (Path-based Extraction) ★ v1.3

파일명에 정보가 없을 때 경로에서 추출:

**Day 폴더 추출:**
```
경로: ...\NO COMMENTARY WITH GRAPHICS VER\Day 3\filename.mp4
                                         ^^^^^
                                         Day 3 추출
```

**Part 접미사 추출 (NC 파일):**
```
파일명: 🏆€10,350 WSOPE MAIN EVENT... - Day 3 👑-003.mp4
                                           ^^^^
                                           Part 3 추출
```

| 추출 대상 | 패턴 | 적용 조건 |
|-----------|------|-----------|
| Day from path | `\Day X\` 또는 `\Day X Y\` | 파일명에 Day 없을 때 |
| Part from suffix | `-XXX.mp4` | NC 파일만 |

### 8.6 이벤트명 폴더 추출 (EU) ★ v1.4

EU 파일의 경우 파일명에 이벤트명이 없을 때 (HyperDeck RAW 등) 폴더 경로에서 추출:

**폴더 패턴:**
```
Z:\...\2025 WSOP-EUROPE #2 KING'S MILLION FINAL\...
                        ^^^^^^^^^^^^^^^^^^
                        이벤트명 추출
```

**매핑 테이블:**
| 폴더 이벤트명 | 정규화 결과 |
|---------------|-------------|
| `KING'S MILLION` | King's Million |
| `2K MONSTERSTACK` | 2K Monsterstack |
| `MINI MAIN EVENT` | Mini Main Event |
| `MAIN EVENT` | Main Event |
| `COLOSSUS` | Colossus |
| `10K PLO MY.BO` | 10K PLO Mystery Bounty |
| `GGMILLION€` | GGMillion€ |
| `2K PLO` | 2K PLO |

**적용 조건:**
- Region = EU
- 파일명에서 이벤트명 추출 실패 (HyperDeck 파일 등)

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2025-12-18 | 초기 문서 작성 |
| 1.1 | 2025-12-18 | Google Sheets 출력 형식 추가 (Section 7) |
| 1.2 | 2025-12-18 | 정규화 규칙 추가: Final Table/Day 분리, EU Bracelet 분류, NC/STREAM 버전, Cyprus Entry Key |
| 1.3 | 2025-12-18 | 경로 기반 추출 추가: Day 폴더, NC 파일 Part 접미사 (-XXX) |
| 1.4 | 2025-12-18 | EU 이벤트명 폴더 추출 추가: HyperDeck 등 파일명 없는 경우 경로에서 이벤트명 추출 |
