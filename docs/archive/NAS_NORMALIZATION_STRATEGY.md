# NAS 데이터 정규화 전략

**버전**: 1.7
**날짜**: 2025-12-18

---

## 0. 검증 결과 요약 (v1.4)

### 0.1 성공 지표

| 지표 | v1.0 | v1.1 | v1.2 | v1.3 | v1.4 |
|------|------|------|------|------|------|
| 전체 파일 | 134 | 134 | 134 | 134 | 134 |
| 유효 파일 | 99 | 99 | 128 | 128 | **126** |
| 제외 파일 | 35 | 35 | 6 | 6 | **8** |
| 패턴 분류율 | 100% | 100% | 100% | 100% | **100%** |
| 고유 키 수 | 91 | 94 | 103 | 123 | **123** |

### 0.2 수정 이력

| 버전 | 문제 | 해결 |
|------|------|------|
| v1.1 | EU Main Event Event # 누락 | 경로 `WSOP-EUROPE #N` 패턴 추가 |
| v1.1 | Day 2A_B_C 추출 오류 | 복합 Day 패턴 우선 처리 |
| v1.1 | Cyprus 이벤트 중복 | `cyprus_event` 필드 추가 |
| v1.1 | Session 미추출 | `session` 필드 추가 |
| v1.2 | HyperDeck 29개 제외 | 경로 기반 정규화 추가 |
| v1.3 | HyperDeck Part 번호 누락 | 파일명 순차 번호 기반 Part 할당 |
| **v1.4** | **제외 파일 정규화 전략 부재** | **37개 제외 파일 분석 및 처리 전략** |

### 0.3 HyperDeck 정규화 (v1.3)

| 이벤트 | 파일 수 | 영상 수 | 키 패턴 |
|--------|---------|---------|---------|
| E#4 2K Monsterstack | 5 | 1 | `EU_WSOPE_BR_E4_DFinal_P{1-5}_NC_RAW` |
| E#6 2K PLO | 2 | 1 | `EU_WSOPE_BR_E6_DFinal_P{1-2}_NC_RAW` |
| E#13 GGMillion€ | 3 | 1 | `EU_WSOPE_BR_E13_DFinal_P{1-3}_NC_RAW` |
| E#14 Main Event | 19 | 6 | `EU_WSOPE_ME_E14_D{N}_P{M}_NC_RAW` |
| **Total** | **29** | **9** | |

### 0.4 제외 파일 처리 전략 (v1.4)

| 유형 | 수량 | 정규화 | 권장 처리 |
|------|------|--------|-----------|
| HyperDeck | 29 | ✅ v1.3 적용 | **유효화** |
| Circuit | 6 | ✅ 새 전략 | 선택적 (기본 제외) |
| Small/Dup | 2 | ✅ 가능 | **제외 유지** |

---

## 1. 파일명 패턴 분류

### 1.1 패턴별 분포

| 패턴 ID | 수량 | 패턴 | 예시 |
|---------|------|------|------|
| **P1** | 38 | WSOP Bracelet (LV) | `WSOP 2025 Bracelet Events _ Event #13...` |
| **P2** | 20 | WSOP Main Event (LV) | `WSOP 2025 Main Event _ Day 1A.mp4` |
| **P3** | 17 | WSOPE Stream (EU) | `🏆 WSOPE NLH King's Million...` |
| **P4** | 10 | WSOPE NC (EU) | `1_2025 WSOPE #2 €350...Part1_NC.mp4` |
| **P5** | 7 | Cyprus PokerOK/Luxon | `$1M GTD $1K PokerOK Mystery Bounty...` |
| **P6** | 6 | WSOP Circuit | `$5M GTD WSOP Super Circuit Cyprus...` |
| **P7** | 4 | Cyprus MPP | `$5M GTD $5K MPP Main Event...` |
| **P8** | 29 | HyperDeck (제외) | `HyperDeck_0009-002.mp4` |
| **P9** | 2 | Source Prefix | `(PokerGO) WSOP 2025...` |
| **P10** | 1 | Date Prefix | `250602_WSOP 2025...` |

---

## 2. 요소 추출 규칙

### 2.1 Region (지역)

**추출 위치**: 경로 (full_path)

```python
def extract_region(full_path: str) -> str:
    path_upper = full_path.upper()

    if 'WSOP-LAS VEGAS' in path_upper:
        return 'LV'
    elif 'WSOP-EUROPE' in path_upper:
        return 'EU'
    elif 'MPP' in path_upper and 'CYPRUS' in path_upper:
        return 'CYPRUS_MPP'
    elif 'CIRCUIT' in path_upper:
        return 'CIRCUIT'

    return 'UNKNOWN'
```

| 경로 패턴 | Region |
|-----------|--------|
| `WSOP-LAS VEGAS` | LV |
| `WSOP-EUROPE` | EU |
| `MPP\2025 MPP Cyprus` | CYPRUS_MPP |
| `WSOP Circuit Event` | CIRCUIT |

### 2.2 Series (시리즈)

**추출 위치**: 경로 + 파일명

```python
def extract_series(full_path: str, filename: str) -> str:
    combined = (full_path + filename).upper()

    if 'WSOPE' in combined:
        return 'WSOPE'  # WSOP Europe
    elif 'WSOP' in combined:
        return 'WSOP'
    elif 'MPP' in combined:
        return 'MPP'

    return 'OTHER'
```

### 2.3 Event Type (이벤트 타입)

**추출 위치**: 경로 (우선) + 파일명

```python
def extract_event_type(full_path: str, filename: str) -> str:
    path_upper = full_path.upper()

    # 경로 기반 (우선)
    if 'MAIN EVENT' in path_upper:
        return 'ME'
    elif 'BRACELET' in path_upper or 'SIDE EVENT' in path_upper:
        return 'BR'

    # 파일명 기반
    fname_upper = filename.upper()
    if 'MAIN EVENT' in fname_upper:
        return 'ME'
    elif 'BRACELET' in fname_upper or 'EVENT #' in fname_upper:
        return 'BR'

    return 'OTHER'
```

### 2.4 Event # (이벤트 번호)

**추출 위치**: 경로 + 파일명

```python
def extract_event_num(full_path: str, filename: str) -> int | None:
    combined = full_path + ' ' + filename

    # Pattern 1: Event #N (WSOP LV)
    match = re.search(r'Event\s*#(\d+)', combined, re.I)
    if match:
        return int(match.group(1))

    # Pattern 2: [BRACELET #N] or [BRACELET EVENT #N]
    match = re.search(r'\[BRACELET(?:\s+EVENT)?\s*#(\d+)\]', combined, re.I)
    if match:
        return int(match.group(1))

    # Pattern 3: WSOPE #N (WSOP Europe) - 파일명
    match = re.search(r'WSOPE\s*#(\d+)', filename, re.I)
    if match:
        return int(match.group(1))

    # Pattern 4: WSOP-EUROPE #N (경로) ★ v1.1 추가
    match = re.search(r'WSOP-EUROPE\s*#(\d+)', full_path, re.I)
    if match:
        return int(match.group(1))

    return None
```

**주의**: EU Main Event Day 3+ 파일은 파일명에 Event #가 없지만, 경로에 `2025 WSOP-EUROPE #14 MAIN EVENT`로 존재함.

### 2.5 Day (날짜/단계)

**추출 위치**: 파일명

```python
def extract_day(filename: str) -> str:
    # Pattern 1: Day NA_B_C or Day NA/B/C (복합 Day) ★ v1.1 우선 처리
    match = re.search(r'Day\s*(\d+)([A-D])(?:[_/])([A-D])(?:[_/])?([A-D])?', filename, re.I)
    if match:
        day = match.group(1)
        parts = [match.group(2), match.group(3)]
        if match.group(4):
            parts.append(match.group(4))
        return day + ''.join(parts)  # 예: 2ABC

    # Pattern 2: Day N[A-D] (e.g., Day 1A, Day 2)
    match = re.search(r'Day\s*(\d+)\s*([A-D])?', filename, re.I)
    if match:
        day = match.group(1)
        suffix = match.group(2) or ''
        return day + suffix

    # Pattern 3: Final Table _ Day N
    match = re.search(r'Final Table.*Day\s*(\d+)', filename, re.I)
    if match:
        return 'FT_D' + match.group(1)

    # Pattern 4: Final Table (no day specified)
    if 'Final Table' in filename:
        return 'FT'

    # Pattern 5: Final Day
    if 'Final Day' in filename:
        return 'FinalDay'

    # Pattern 6: Final (Heads-Up Final, etc.)
    if re.search(r'(?<!Event\s)Final(?!\s*Table)', filename):
        if 'Final Four' not in filename:
            return 'Final'

    # Pattern 7: Final Four
    if 'Final Four' in filename:
        return 'F4'

    return ''
```

### 2.6 Part (파트)

**추출 위치**: 파일명

```python
def extract_part(filename: str) -> int | None:
    # Pattern 1: (Part N) or Part N
    match = re.search(r'Part\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))

    # Pattern 2: PartN (no space)
    match = re.search(r'Part(\d+)', filename, re.I)
    if match:
        return int(match.group(1))

    return None
```

### 2.7 Sequence Prefix (순서 접두사)

**추출 위치**: 파일명 앞부분

```python
def extract_sequence(filename: str) -> int | None:
    # Pattern: N_2025 WSOPE... (1자리 숫자 = Part 순서)
    match = re.match(r'^(\d)_\d{4}\s+WSOPE', filename)
    if match:
        return int(match.group(1))

    return None
```

**정규화**: Sequence → Part 변환
```
1_2025 WSOPE #2... → Part 1
2_2025 WSOPE #2... → Part 2
3_2025 WSOPE #2... → Part 3
```

### 2.8 Source (소스)

**추출 위치**: 파일명 접두사

```python
def extract_source(filename: str) -> str:
    match = re.match(r'\((PokerGO|YouTube)\)', filename, re.I)
    if match:
        return match.group(1)
    return ''
```

### 2.9 Version (버전)

**추출 위치**: 파일명 또는 경로

```python
def extract_version(full_path: str, filename: str) -> str:
    if '_NC' in filename:
        return 'NC'  # No Commentary
    if 'NO COMMENTARY' in full_path.upper():
        return 'NC'
    if 'STREAM' in full_path.upper():
        return 'STREAM'
    return ''
```

### 2.10 Resolution (해상도)

**추출 위치**: 파일명

```python
def extract_resolution(filename: str) -> str:
    match = re.search(r'\((\d+[pP])\)', filename)
    if match:
        return match.group(1).lower()
    return ''
```

### 2.11 Session (세션) ★ v1.1 추가

**추출 위치**: 파일명 (Cyprus MPP Main Event)

```python
def extract_session(filename: str) -> int | None:
    # Pattern: Session N (e.g., "Day 3 Session 1")
    match = re.search(r'Session\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    return None
```

**적용 대상**: `$5M GTD $5K MPP Main Event – Day 3 Session 1.mp4`

### 2.12 Cyprus Event Name (이벤트명) ★ v1.1 추가

**추출 위치**: 경로 (parent folder) 또는 파일명

```python
def extract_cyprus_event(full_path: str, filename: str) -> str:
    """Cyprus MPP 이벤트 구분."""
    fname_upper = filename.upper()

    if 'POKEROK' in fname_upper or 'MYSTERY BOUNTY' in fname_upper:
        return 'POKEROK'
    elif 'LUXON' in fname_upper:
        return 'LUXON'
    elif 'MPP MAIN EVENT' in fname_upper:
        return 'MPP_ME'

    # Fallback: 경로의 parent folder에서 추출
    parts = full_path.replace('/', '\\').split('\\')
    for part in parts:
        if 'PokerOK' in part:
            return 'POKEROK'
        elif 'Luxon' in part:
            return 'LUXON'
        elif 'MPP Main Event' in part:
            return 'MPP_ME'

    return 'CYPRUS'  # Default
```

**이벤트 분류**:

| 이벤트명 | 코드 | 파일 수 |
|----------|------|---------|
| $1K PokerOK Mystery Bounty | POKEROK | 4 |
| $2K Luxon Pay Grand Final | LUXON | 3 |
| $5K MPP Main Event | MPP_ME | 4 |

---

## 3. 정규화 규칙

### 3.1 Day 정규화

| 원본 | 정규화 |
|------|--------|
| `Day 1A` | `1A` |
| `Day 1B` | `1B` |
| `Day 2A_B_C` | `2ABC` |
| `Day 2A/B/C` | `2ABC` |
| `Day 2D` | `2D` |
| `Day 3` | `3` |
| `Final Table _ Day 1` | `FT_D1` |
| `Final Table _ Day 2` | `FT_D2` |
| `Final Table` | `FT` |
| `Final Day` | `FinalDay` |
| `Final` | `Final` |
| `Final Four` | `F4` |

### 3.2 Event # 정규화

| 지역 | 원본 | 정규화 |
|------|------|--------|
| LV | `Event #13` | `E13` |
| EU | `WSOPE #2` | `E2` |
| EU | `[BRACELET EVENT #7]` | `E7` |

### 3.3 Sequence → Part 변환 (EU NC 파일)

```
원본: 1_2025 WSOPE #2 €350 No-Limit Hold'em King's Million Part1_NC.mp4
      2_2025 WSOPE #2 €350 No-Limit Hold'em King's Million Part2_NC.mp4
      3_2025 WSOPE #2 €350 No-Limit Hold'em King's Million Part3_NC.mp4

정규화:
  - Event #: 2
  - Parts: 1, 2, 3
```

### 3.4 Source 제거 (정규화 시)

```
원본: (PokerGO) WSOP 2025 Bracelet Events _ Event #13...
정규화: WSOP 2025 Bracelet Events _ Event #13...

→ Source는 별도 필드로 저장
```

### 3.5 Resolution 제거 (정규화 시)

```
원본: WSOP 2025 Bracelet Events _ Event #1 $1K Mystery Millions (720p).mp4
정규화: WSOP 2025 Bracelet Events _ Event #1 $1K Mystery Millions

→ Resolution은 별도 필드로 저장, 높은 해상도 우선
```

---

## 4. 정규화 결과 스키마

### 4.1 NasFileNormalized

```python
@dataclass
class NasFileNormalized:
    # 원본 정보
    file_id: int
    full_path: str
    filename: str

    # 정규화된 요소
    region: str           # LV, EU, CYPRUS_MPP, CIRCUIT
    series: str           # WSOP, WSOPE, MPP
    event_type: str       # BR, ME, OTHER
    event_num: int | None # 1, 2, 3, 7, 10, 13...
    day: str              # 1, 1A, 2ABC, 3, FT, FT_D1, Final, F4
    part: int | None      # 1, 2, 3, 4
    session: int | None   # 1, 2 (MPP Main Event Day 3) ★ v1.1

    # Cyprus 전용 ★ v1.1
    cyprus_event: str     # POKEROK, LUXON, MPP_ME

    # 부가 정보
    source: str           # PokerGO, YouTube
    version: str          # NC, STREAM
    resolution: str       # 1080p, 720p
    is_raw: bool          # HyperDeck raw file ★ v1.2
    hd_sequence: tuple    # HyperDeck 순차 번호 (main, sub) ★ v1.3

    # 메타
    pattern_id: str       # P1, P2, P3...
    is_excluded: bool
    exclusion_reason: str
```

### 4.2 정규화 키 생성

```python
def generate_normalized_key(elem: NasFileNormalized) -> str:
    """정규화된 고유 키 생성."""
    parts = [elem.region, elem.series]

    # Cyprus MPP: 이벤트명으로 구분 ★ v1.1
    if elem.region == 'CYPRUS_MPP' and elem.cyprus_event:
        parts.append(elem.cyprus_event)
    elif elem.event_type == 'BR':
        parts.append('BR')
        if elem.event_num:
            parts.append(f'E{elem.event_num}')
    elif elem.event_type == 'ME':
        parts.append('ME')

    if elem.day:
        parts.append(f'D{elem.day}')

    # Session (Cyprus MPP Main Event) ★ v1.1
    if elem.session:
        parts.append(f'S{elem.session}')

    if elem.part:
        parts.append(f'P{elem.part}')

    if elem.version:
        parts.append(elem.version)

    # HyperDeck RAW 마커 ★ v1.3
    if elem.is_raw:
        parts.append('RAW')

    return '_'.join(parts)

# 예시:
# LV_WSOP_BR_E13 → WSOP 2025 Event #13
# LV_WSOP_ME_D1A → WSOP 2025 Main Event Day 1A
# LV_WSOP_ME_D2ABC_P1 → WSOP 2025 Main Event Day 2A/B/C Part 1 ★ v1.1
# EU_WSOPE_BR_E2_P1_NC → WSOPE 2025 #2 Part 1 (NC)
# EU_WSOPE_ME_D3 → WSOPE 2025 Main Event Day 3
# CYPRUS_MPP_MPP_POKEROK_D1A → PokerOK Mystery Bounty Day 1A ★ v1.1
# CYPRUS_MPP_MPP_MPP_ME_D3_S1 → MPP Main Event Day 3 Session 1 ★ v1.1
# EU_WSOPE_BR_E4_DFinal_P1_NC_RAW → HyperDeck E#4 Final Part 1 ★ v1.3
# EU_WSOPE_ME_E14_D1A_P3_NC_RAW → HyperDeck Main Event Day 1A Part 3 ★ v1.3
```

---

## 5. 패턴별 처리 전략

### 5.1 P1: WSOP Bracelet (LV)

```
파일: WSOP 2025 Bracelet Events _ Event #13 $1.5K No-Limit Hold'em 6-Max.mp4

추출:
  region: LV (경로)
  series: WSOP
  event_type: BR
  event_num: 13
  day: (없음)
  part: (없음)

정규화 키: LV_WSOP_BR_E13
```

### 5.2 P2: WSOP Main Event (LV)

```
파일: WSOP 2025 Main Event _ Day 2A_B_C (Part 1).mp4

추출:
  region: LV (경로)
  series: WSOP
  event_type: ME
  event_num: (없음)
  day: 2ABC (정규화: 2A_B_C → 2ABC)
  part: 1

정규화 키: LV_WSOP_ME_D2ABC_P1
```

### 5.3 P3: WSOPE Stream (EU)

```
파일: 🏆 WSOPE NLH King's Million - Final Day [BRACELET EVENT #2] live from King's 👑 #wsop #poker.mp4

추출:
  region: EU (경로)
  series: WSOPE
  event_type: BR
  event_num: 2 ([BRACELET EVENT #2])
  day: FinalDay
  part: (없음)
  version: STREAM (경로)

정규화 키: EU_WSOPE_BR_E2_DFinalDay
```

### 5.4 P4: WSOPE NC (EU)

```
파일: 1_2025 WSOPE #2 €350 No-Limit Hold'em King's Million Part1_NC.mp4

추출:
  region: EU (경로)
  series: WSOPE
  event_type: BR
  event_num: 2
  day: (없음)
  part: 1 (Sequence 1 → Part 1)
  version: NC

정규화 키: EU_WSOPE_BR_E2_P1
```

### 5.5 P5/P7: Cyprus MPP/PokerOK

```
파일: $5M GTD   $5K MPP Main Event – Day 2.mp4

추출:
  region: CYPRUS_MPP (경로)
  series: MPP
  event_type: ME
  event_num: (없음)
  day: 2
  part: (없음)

정규화 키: CYPRUS_MPP_ME_D2
```

### 5.6 P8: HyperDeck (경로 기반 정규화) ★ v1.2

**특징**: 파일명에 정보가 없으므로 **경로 기반 추론** 필요

```
경로 구조:
Z:\ARCHIVE\WSOP\WSOP Bracelet Event\WSOP-EUROPE\2025 WSOP-Europe\
  └── 2025 WSOP-EUROPE #14 MAIN EVENT\       ← Event #, Event Name
      └── NO COMMENTARY WITH GRAPHICS VER\   ← Version: NC
          └── Day 1 A\                       ← Day
              └── HyperDeck_0010-004.mp4     ← 파일
```

**추출 규칙**:

```python
def normalize_hyperdeck(full_path: str, filename: str) -> NasFileNormalized:
    """경로 기반 HyperDeck 정규화."""
    result = NasFileNormalized(...)

    # Region: 항상 EU (WSOP-EUROPE 경로)
    result.region = 'EU'
    result.series = 'WSOPE'

    # Event # from path: WSOP-EUROPE #N
    match = re.search(r'WSOP-EUROPE\s*#(\d+)', full_path, re.I)
    result.event_num = int(match.group(1)) if match else None

    # Event Type: MAIN EVENT → ME, 그 외 → BR
    if 'MAIN EVENT' in full_path.upper():
        result.event_type = 'ME'
    else:
        result.event_type = 'BR'

    # Day from folder: "Day 1 A", "Day 2", etc.
    match = re.search(r'Day\s*(\d+)\s*([A-D])?', full_path, re.I)
    if match:
        result.day = match.group(1) + (match.group(2) or '')
    else:
        # No Day folder = Final Day (Bracelet events)
        result.day = 'Final'

    # Version: 항상 NC (NO COMMENTARY 폴더)
    result.version = 'NC'

    # Raw file marker
    result.is_raw = True

    return result
```

**이벤트별 HyperDeck 분포**:

| Event # | 이벤트명 | 파일 수 | Days |
|---------|----------|---------|------|
| #4 | 2K Monsterstack | 5 | Final |
| #6 | 2K PLO | 2 | Final |
| #13 | GGMillion€ | 3 | Final |
| #14 | Main Event | 19 | 1A, 1B, 2, 3, 4, 5 |
| **Total** | | **29** | |

**정규화 키 예시**:

```
파일: Z:\...\2025 WSOP-EUROPE #14 MAIN EVENT\NO COMMENTARY...\Day 1 A\HyperDeck_0010-004.mp4

정규화:
  region: EU
  series: WSOPE
  event_type: ME
  event_num: 14
  day: 1A
  version: NC
  is_raw: True

키: EU_WSOPE_ME_E14_D1A_NC_RAW
```

```
파일: Z:\...\2025 WSOP-EUROPE #4 2K MONSTERSTACK FINAL\NO COMMENTARY...\HyperDeck_0005-001.mp4

정규화:
  region: EU
  series: WSOPE
  event_type: BR
  event_num: 4
  day: Final
  version: NC
  is_raw: True

키: EU_WSOPE_BR_E4_DFinal_P1_NC_RAW
```

### 5.7 HyperDeck Part 번호 할당 ★ v1.3 신규

**원리**: 각 폴더 = 1개 영상의 분할 파트. 파일명 순차 번호로 Part 순서 결정.

**파일명 구조**:
```
HyperDeck_NNNN-MMM.mp4
         │    │
         │    └── Sub number (MMM)
         └── Main number (NNNN)
```

**순차 번호 추출**:
```python
def extract_hyperdeck_sequence(filename: str) -> tuple[int, int]:
    """HyperDeck 파일명에서 순차 번호 추출."""
    match = re.match(r'HyperDeck_(\d+)(?:-(\d+))?', filename)
    if match:
        main_num = int(match.group(1))
        sub_num = int(match.group(2)) if match.group(2) else 0
        return (main_num, sub_num)
    return (0, 0)

# 예시:
# HyperDeck_0005-001.mp4 → (5, 1)
# HyperDeck_0006-004.mp4 → (6, 4)
# HyperDeck_0007.mp4     → (7, 0)
```

**Part 할당 로직**:
```python
def assign_hyperdeck_parts(normalized_files: list) -> None:
    """폴더 기준 HyperDeck Part 번호 할당."""
    # 1. HyperDeck 파일만 필터링 후 폴더별 그룹화
    hd_groups = defaultdict(list)
    for f in normalized_files:
        if f.is_raw:  # HyperDeck 파일
            # 폴더 기준 키 (Part 제외)
            base_key = f"{f.region}_{f.series}_{f.event_type}_E{f.event_num}_D{f.day}_{f.version}"
            hd_groups[base_key].append(f)

    # 2. 각 그룹 내에서 순차 번호로 정렬 후 Part 할당
    for base_key, files in hd_groups.items():
        files.sort(key=lambda x: x.hd_sequence)  # (main, sub) 튜플 정렬
        for i, f in enumerate(files, 1):
            f.part = i  # P1, P2, P3...
```

**결과 예시** (E#4 2K Monsterstack - 5개 파일 = 1개 영상):

| 파일명 | hd_sequence | Part | 정규화 키 |
|--------|-------------|------|-----------|
| HyperDeck_0005-001.mp4 | (5, 1) | P1 | EU_WSOPE_BR_E4_DFinal_P1_NC_RAW |
| HyperDeck_0006-004.mp4 | (6, 4) | P2 | EU_WSOPE_BR_E4_DFinal_P2_NC_RAW |
| HyperDeck_0007-001.mp4 | (7, 1) | P3 | EU_WSOPE_BR_E4_DFinal_P3_NC_RAW |
| HyperDeck_0008-001.mp4 | (8, 1) | P4 | EU_WSOPE_BR_E4_DFinal_P4_NC_RAW |
| HyperDeck_0009-002.mp4 | (9, 2) | P5 | EU_WSOPE_BR_E4_DFinal_P5_NC_RAW |

**Main Event Day별 Part 분포**:

| Day | 파일 수 | Parts |
|-----|---------|-------|
| 1A | 4 | P1-P4 |
| 1B | 4 | P1-P4 |
| 2 | 4 | P1-P4 |
| 3 | 4 | P1-P4 |
| 4 | 2 | P1-P2 |
| 5 | 1 | P1 |

---

## 6. 제외 파일 정규화 전략 ★ v1.4 신규

### 6.1 제외 파일 분석 결과

| 유형 | 수량 | 제외 사유 | 정규화 가능 | 권장 처리 |
|------|------|-----------|-------------|-----------|
| **HyperDeck** | 29 | 패턴 미인식 (레거시) | ✅ v1.3 전략 적용 | **유효화** |
| **Circuit** | 6 | 'circuit' 키워드 | ✅ 새 전략 필요 | **선택적 유효화** |
| **Small/Duplicate** | 2 | Size < 1GB | ✅ 원본과 동일 | **제외 유지** |

### 6.2 HyperDeck 파일 (29개) → 유효화

**현재 상태**: DB에 `is_excluded=True`로 설정됨 (레거시)
**v1.3 전략**: 경로 기반 정규화로 100% 분류 가능

**처리 방법**:
```python
# DB 업데이트
UPDATE nas_files
SET is_excluded = FALSE, exclusion_reason = NULL
WHERE filename LIKE 'HyperDeck_%' AND year = 2025;
```

**결과 키 예시**:
```
EU_WSOPE_BR_E4_DFinal_P1_NC_RAW
EU_WSOPE_BR_E6_DFinal_P1_NC_RAW
EU_WSOPE_BR_E13_DFinal_P1_NC_RAW
EU_WSOPE_ME_E14_D1A_P1_NC_RAW
...
```

### 6.3 Circuit 파일 (6개) → 선택적 유효화

**현재 상태**: 'circuit' 키워드로 자동 제외
**경로**: `Z:\ARCHIVE\WSOP\WSOP Circuit Event\WSOP Super Ciruit\2025 WSOP Super Circuit Cyprus\`

**파일 목록**:

| 파일명 | Day | Suffix |
|--------|-----|--------|
| `$5M GTD WSOP Super Circuit Cyprus Main Event - Day 1A-006.mp4` | 1A | 006 |
| `$5M GTD WSOP Super Circuit Cyprus Main Event - Day 1C-003.mp4` | 1C | 003 |
| `$5M GTD WSOP Super Circuit Cyprus Main Event - Day 2-001.mp4` | 2 | 001 |
| `$5M GTD WSOP Super Circuit Cyprus Main Event - Day 3-002.mp4` | 3 | 002 |
| `$5M GTD WSOP Super Circuit Cyprus Main Event - Day 4-005.mp4` | 4 | 005 |
| `$5M GTD WSOP Super Circuit Cyprus Main Event - Final Day-004.mp4` | FinalDay | 004 |

**정규화 전략**:

```python
def normalize_circuit(full_path: str, filename: str) -> NasFileNormalized:
    """Circuit 이벤트 정규화."""
    result = NasFileNormalized(...)

    # Region: CIRCUIT (새 지역 코드)
    result.region = 'CIRCUIT'
    result.series = 'WSOP_CIRCUIT'
    result.event_type = 'ME'  # Main Event

    # Day 추출
    day_match = re.search(r'Day\s*(\d+[A-C]?)|Final Day', filename, re.I)
    if day_match:
        day_str = day_match.group(0)
        if 'Final Day' in day_str:
            result.day = 'FinalDay'
        else:
            result.day = day_match.group(1)

    # Suffix 추출 (Part 번호로 사용)
    suffix_match = re.search(r'-(\d+)\.mp4$', filename)
    if suffix_match:
        result.part = int(suffix_match.group(1))

    return result
```

**정규화 키**:
```
CIRCUIT_WSOP_CIRCUIT_ME_D1A_P6
CIRCUIT_WSOP_CIRCUIT_ME_D1C_P3
CIRCUIT_WSOP_CIRCUIT_ME_D2_P1
CIRCUIT_WSOP_CIRCUIT_ME_D3_P2
CIRCUIT_WSOP_CIRCUIT_ME_D4_P5
CIRCUIT_WSOP_CIRCUIT_ME_DFinalDay_P4
```

**유효화 여부**: 비즈니스 결정 필요
- PokerGO 매칭 대상 아님 (NAS_ONLY 확정)
- 필요시 제외 규칙에서 'circuit' 키워드 제거

### 6.4 Small/Duplicate 파일 (2개) → 제외 유지

**현재 상태**: Size < 1GB 규칙으로 제외

| 중복 파일 | Size | 원본 파일 | Size |
|-----------|------|-----------|------|
| `Event #26...Day 2_789647313.mp4` | 0.05 GB | `Event #26...Day 2.mp4` | 8.61 GB |
| `Event #22..._79684924.mp4` | 0.09 GB | `Event #22...mp4` | 6.26 GB |

**패턴 분석**:
```
원본: {파일명}.mp4
중복: {파일명}_{숫자ID}.mp4
```

**정규화 (참고용)**:
```python
def normalize_duplicate(filename: str) -> str:
    """중복 파일 정규화 (제외 유지하되 키 생성)."""
    # 숫자 ID 제거
    base_name = re.sub(r'_\d+\.mp4$', '.mp4', filename)

    # 원본과 동일한 키 + _DUP 접미사
    original_key = generate_key(base_name)
    return f"{original_key}_DUP"

# 예시:
# LV_WSOP_BR_E26_D2_DUP
# LV_WSOP_BR_E22_DUP
```

**권장**: 원본 존재하므로 **제외 유지**

---

## 7. 최종 처리 전략

### 7.1 권장 처리 요약

| 유형 | 현재 | 처리 | 결과 |
|------|------|------|------|
| HyperDeck (29) | 제외 | **유효화** | 유효 |
| Circuit (6) | 제외 | 선택적 (기본: 제외) | 제외/유효 |
| Small/Dup (2) | 제외 | 유지 | 제외 |

### 7.2 처리 후 예상 결과

**Option A: HyperDeck만 유효화 (권장)**

| 지표 | 현재 | 처리 후 |
|------|------|---------|
| 유효 파일 | 97 | **126** (+29) |
| 제외 파일 | 37 | **8** (-29) |
| 고유 키 | 94 | **123** (+29) |

**Option B: HyperDeck + Circuit 유효화**

| 지표 | 현재 | 처리 후 |
|------|------|---------|
| 유효 파일 | 97 | **132** (+35) |
| 제외 파일 | 37 | **2** (-35) |
| 고유 키 | 94 | **129** (+35) |

---

## 8. 카탈로그 생성 규칙 ★ v1.5 신규

### 8.1 카테고리 생성 규칙

| Region | Event Type | 카테고리 |
|--------|------------|----------|
| LV | ME | WSOP 2025 Main Event |
| LV | BR | WSOP 2025 Bracelet Events |
| EU | ME | WSOP Europe 2025 Main Event |
| EU | BR | WSOP Europe 2025 Bracelet Events |
| CYPRUS | - | MPP Cyprus 2025 - {이벤트명} |
| CIRCUIT | ME | WSOP Circuit Cyprus 2025 |

### 8.2 제목 생성 규칙

**Bracelet Events**: `Event #{번호} {이벤트명} | {Day} Part {N}`

```python
def generate_bracelet_title(event_num, event_name, day, part):
    title = f'Event #{event_num} {event_name}'
    if day:
        title += f' | {day}'
    if part:
        title += f' Part {part}'
    return title

# 예시:
# Event #13 $1.5K No-Limit Hold'em 6-Max
# Event #66 $50K Poker Players Championship | Day 4 Part 1
```

**Main Event**: `Main Event {Day} Part {N}`

```python
def generate_main_event_title(day, part, is_raw=False):
    title = 'Main Event'
    if day:
        title += f' {day}'
    if part:
        title += f' Part {part}'
    if is_raw:
        title += ' [RAW]'
    return title

# 예시:
# Main Event Day 1A
# Main Event Day 4 Part 2
# Main Event Final Table Day 1
```

**HyperDeck RAW**: `{title} (Part ##) [RAW]` ★ v1.6 추가

```python
def generate_hyperdeck_title(base_title, part, is_raw=True):
    """HyperDeck RAW 파일 제목 생성.

    Part 번호: 2자리 zero-padding (01, 02, 03...)
    폴더 내 파일명 순서대로 Part 번호 할당
    """
    if is_raw and part:
        return f'{base_title} (Part {part:02d}) [RAW]'
    return base_title

# 예시:
# Event #4 €2K Monsterstack | Final (Part 01) [RAW]
# Event #4 €2K Monsterstack | Final (Part 02) [RAW]
# Main Event Day 1A (Part 01) [RAW]
# Main Event Day 1A (Part 02) [RAW]
```

**HyperDeck Part 번호 할당 규칙**:

1. 동일 폴더(이벤트+Day) 내 파일들을 그룹화
2. 파일명의 순차 번호로 정렬 (`HyperDeck_NNNN-MMM.mp4`)
3. 정렬 순서대로 Part 01, 02, 03... 할당

```python
def get_hyperdeck_folder_key(full_path):
    """폴더 기준 그룹화 키 생성."""
    parts = []
    # Event # 추출
    match = re.search(r'WSOP-EUROPE\s*#(\d+)', full_path, re.I)
    if match:
        parts.append(f'E{match.group(1)}')
    # Event Type
    if 'MAIN EVENT' in full_path.upper():
        parts.append('ME')
    else:
        parts.append('BR')
    # Day
    match = re.search(r'Day\s*(\d+)\s*([A-D])?', full_path, re.I)
    if match:
        parts.append(f'D{match.group(1)}{match.group(2) or ""}')
    elif 'FINAL' in full_path.upper():
        parts.append('DFinal')
    return '_'.join(parts)

def extract_hyperdeck_sequence(filename):
    """파일명에서 순차 번호 추출 (정렬용)."""
    match = re.match(r'HyperDeck_(\d+)(?:-(\d+))?', filename)
    if match:
        main_num = int(match.group(1))
        sub_num = int(match.group(2)) if match.group(2) else 0
        return (main_num, sub_num)
    return (0, 0)

# 그룹별 정렬 후 Part 할당
for folder_key, items in hyperdeck_groups.items():
    items.sort(key=lambda x: extract_hyperdeck_sequence(x.filename))
    for idx, item in enumerate(items, 1):
        item.part = idx  # Part 01, 02, 03...
```

**Cyprus/Circuit**: `{이벤트명} | Day {N}` 또는 `Main Event Day {N}` ★ v1.7 추가

```python
def generate_cyprus_title(event_name, day, session=None, part=None):
    """Cyprus 이벤트 제목 생성.

    규칙:
    - Main Event인 경우: 'Main Event Day {N} [Session {M}]'
    - 특정 이벤트인 경우: '{이벤트명} | Day {N}'
    - 이벤트 정보 없으면 기본값 Main Event
    """
    if event_name == 'Main Event' or not event_name:
        title = 'Main Event'
        if day:
            title += f' Day {day}'
        if session:
            title += f' Session {session}'
    else:
        title = event_name
        if day:
            title += f' | Day {day}'
    if part:
        title += f' Part {part}'
    return title

# 예시:
# $1K PokerOK Mystery Bounty | Day 1A
# $1K PokerOK Mystery Bounty | Final Day
# $2K Luxon Pay Grand Final | Day 1C
# Main Event Day 2
# Main Event Day 3 Session 1
```

**Cyprus 이벤트 분류**:

| 파일명 키워드 | 이벤트명 | 제목 형식 |
|---------------|----------|-----------|
| `PokerOK`, `Mystery Bounty` | $1K PokerOK Mystery Bounty | `{이벤트명} \| Day {N}` |
| `Luxon` | $2K Luxon Pay Grand Final | `{이벤트명} \| Day {N}` |
| `MPP Main Event` | Main Event | `Main Event Day {N}` |
| `Circuit`, `Super Circuit` | Main Event | `Main Event Day {N}` |

**Circuit**: 항상 Main Event

```python
# WSOP Circuit Cyprus는 Main Event만 있음
title = 'Main Event'
if day:
    title += f' Day {day}'

# 예시:
# Main Event Day 1A
# Main Event Day 2
# Main Event Final Day
```

### 8.3 이벤트명 추출 규칙

**LV Bracelet**:
```python
# 파일명에서 추출: Event #N {이벤트명}
match = re.search(r'Event\s*#\d+\s+(.+?)(?:\s*[_|]\s*Day|\s*\(|\s*\.mp4|$)', filename)
event_name = match.group(1).strip()

# 예시:
# "Event #13 $1.5K No-Limit Hold'em 6-Max" → "$1.5K No-Limit Hold'em 6-Max"
```

**EU Bracelet**:
```python
# 파일명 또는 매핑 테이블 사용
EU_EVENT_NAMES = {
    2: "€350 NLH King's Million",
    4: '€2K Monsterstack',
    6: '€2K PLO',
    7: '€2.5K NLH 8-Max',
    10: '€10K PLO Mystery Bounty',
    13: '€1K GGMillion€',
    14: '€10.35K Main Event NLH'
}
```

### 8.4 카탈로그 결과 요약

| 카테고리 | 파일 수 | 고유 제목 |
|----------|---------|-----------|
| WSOP 2025 Bracelet Events | 39 | 35 |
| WSOP 2025 Main Event | 20 | 20 |
| WSOP Europe 2025 Bracelet Events | 26 | 19 |
| WSOP Europe 2025 Main Event | 30 | 13 |
| MPP Cyprus 2025 - PokerOK | 4 | 4 |
| MPP Cyprus 2025 - Luxon | 3 | 3 |
| MPP Cyprus 2025 - MPP Main Event | 4 | 3 |
| WSOP Circuit Cyprus 2025 | 6 | 6 |
| **Total** | **132** | **103** |

### 8.5 Google Sheets 내보내기

**시트 구성**:

| 시트명 | 내용 |
|--------|------|
| `2025_Catalog` | 전체 파일 목록 (Entry Key, Category, Title, 파일 정보) |
| `2025_Categories` | 카테고리별 요약 (파일 수, 제목 수, 용량) |
| `2025_Titles` | 고유 제목 목록 (Category, Title, Entry Key) |

**스크립트**: `scripts/export_2025_catalog.py`

---

## 9. 검증 체크리스트

```
□ 모든 134개 파일의 Region이 추출되었는가?
□ Event Type이 BR/ME/OTHER로 분류되었는가?
□ Event #가 정확히 추출되었는가? (LV: 26개, EU: 8개)
□ Day 정규화가 일관성 있게 되었는가?
□ Part 번호가 Sequence에서 올바르게 변환되었는가?
□ HyperDeck 29개가 정규화되었는가? ★ v1.4
□ Circuit 6개 처리 방침이 결정되었는가? ★ v1.4
□ Small/Duplicate 2개가 제외 유지되었는가? ★ v1.4
□ 정규화 키가 중복 없이 생성되었는가?
□ 카테고리/제목이 올바르게 생성되었는가? ★ v1.5
□ Google Sheets 내보내기가 완료되었는가? ★ v1.5
```

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2025-12-18 | 초기 문서 작성 |
| 1.1 | 2025-12-18 | EU Event # 경로 패턴, Day 복합 패턴, Session/Cyprus Event 추가 |
| 1.2 | 2025-12-18 | HyperDeck 경로 기반 정규화 추가 (29개 파일 정규화) |
| 1.3 | 2025-12-18 | HyperDeck Part 번호 할당 로직 추가 (파일명 순차 번호 → 폴더별 Part) |
| 1.4 | 2025-12-18 | 제외 파일 37개 분석 및 정규화 전략 (HyperDeck/Circuit/Duplicate) |
| 1.5 | 2025-12-18 | 카탈로그 생성 규칙 추가 (카테고리/제목 생성, Google Sheets 내보내기) |
| 1.6 | 2025-12-18 | HyperDeck RAW 제목 형식 추가 `(Part ##) [RAW]` (2자리 zero-padding) |
| 1.7 | 2025-12-18 | Cyprus/Circuit 제목 정규화 규칙 추가 (이벤트명 명시 필수) |
