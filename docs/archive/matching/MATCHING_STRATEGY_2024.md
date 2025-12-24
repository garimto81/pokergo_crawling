# 2024 매칭 전략

**버전**: 1.1
**날짜**: 2025-12-18

---

## 1. 데이터 현황

### 1.1 파일 분포

| Region | Files | 비고 |
|--------|-------|------|
| **PARADISE** | 286 | 대부분 Hand 클립 (279개) |
| **LV** | 101 | Bracelet Event 클립 |
| **CIRCUIT** | 40 | LA Circuit |
| **EU** | 30 | Europe Main Event |
| **OTHER** | 1 | GOG |
| **Total** | **458** | |

### 1.2 제외 현황

| 구분 | Files |
|------|-------|
| Total | 458 |
| Excluded (< 1GB) | 450 |
| Active | 8 |

**대부분 클립 파일로 제외됨**

---

## 2. 지역별 패턴 분석

### 2.1 LV (Las Vegas) - 101개

**파일명 패턴:**
```
1-wsop-2024-be-ev-01-5k-champions-reunion-ft-Conniff-hero-calls.mp4
14-wsop-2024-be-ev-26-25k-nlh-hr-ft-deeb-82-vs-li-54-Clean.mp4
13-wsop-2024-be-ev-26-25k-nlh-hr-day02-Bleznick-99-vs-sternheimer.mp4
```

**추출 요소:**
| 요소 | 패턴 | 예시 |
|------|------|------|
| Event # | `ev-(\d+)` | ev-01 → 1, ev-26 → 26 |
| Day | `day(\d+)` | day02 → 2 |
| Final Table | `-ft-` | ft → FT |
| Buy-in | `(\d+k)-` | 5k, 25k |
| Game Type | `nlh`, `2-7TD`, `plo` | NLH, 2-7 TD, PLO |

**특이사항:**
- 대부분 **Hand 클립** (특정 핸드 하이라이트)
- 에피소드 단위 아님
- Clean/PGM 버전 구분 있음

### 2.2 EU (Europe) - 30개

**파일명 패턴:**
```
#WSOPE 2024 NLH MAIN EVENT DAY 1B BRACELET EVENT #13.mp4
1003_WSOPE_2024_50K DIAMOND HIGH ROLLER_DAY1_BRACELET EVENT.mp4
WE24-ME-01.mp4
WE24-ME-02.mp4
```

**추출 요소:**
| 요소 | 패턴 | 예시 |
|------|------|------|
| Event # | `EVENT #(\d+)`, `BRACELET EVENT #(\d+)` | #13 |
| Day | `DAY\s*(\d+[A-D]?)` | DAY 1B, DAY1 |
| Episode | `WE24-ME-(\d+)` | WE24-ME-01 → Ep.1 |

**특이사항:**
- Main Event = Bracelet Event #13
- `WE24-ME-XX` 에피소드 번호 형식
- 50K Diamond High Roller 별도 이벤트

### 2.3 PARADISE - 286개

**파일명 패턴:**
```
2024 WSOP Paradise Super Main Event - Day 1B.mp4
2024 WSOP Paradise Super Main Event - Day 2 (Youtube Stream).mp4
1213_Hand_09_Hynes KJc vs Tony Paker ThTc vs Jiang_Clean.mp4
1213_Hand_12_Greenwood AhKs vs Boianovsky JhJd_Clean.mp4
```

**추출 요소:**
| 요소 | 패턴 | 예시 |
|------|------|------|
| Event | `Super Main Event` | 고정 |
| Day | `Day\s*(\d+[A-D]?)` | Day 1B, Day 2 |
| Hand # | `Hand_(\d+)` | Hand_09, Hand_12 |
| Source | `(Youtube Stream)` | YouTube 소스 |

**분류:**
| 유형 | Files | 비고 |
|------|-------|------|
| Day 에피소드 | 7 | 서비스 대상 |
| Hand 클립 | 279 | 제외 (클립) |

### 2.4 CIRCUIT - 40개

**파일명 패턴:**
```
2024 WSOP Circuit Los Angeles - Main Event [Day 1A].mp4
2024 WSOP Circuit Los Angeles - House Warming NL Hold'em [Day 2].mp4
2024 WSOP Circuit Los Angeles - Beat the Legends [Invitational].mp4
WCLA24-01.mp4
```

**추출 요소:**
| 요소 | 패턴 | 예시 |
|------|------|------|
| Location | `Circuit (.+?) -` | Los Angeles |
| Event | `- (.+?) \[` | Main Event, House Warming |
| Day | `\[Day\s*(\d+[A-D]?)\]` | [Day 1A], [Day 2] |
| Episode | `WCLA24-(\d+)` | WCLA24-01 → Ep.1 |

---

## 3. 정규화 규칙

### 3.1 Event # 추출 확장

```python
def extract_event_num_2024(text: str) -> int | None:
    """2024용 Event # 추출."""
    # Pattern 1: Event #N (기존)
    match = re.search(r'Event\s*#(\d+)', text, re.I)
    if match:
        return int(match.group(1))

    # Pattern 2: ev-N (LV 2024)
    match = re.search(r'ev-(\d+)', text, re.I)
    if match:
        return int(match.group(1))

    # Pattern 3: BRACELET EVENT #N
    match = re.search(r'BRACELET EVENT\s*#(\d+)', text, re.I)
    if match:
        return int(match.group(1))

    return None
```

### 3.2 Day 추출 확장

```python
def extract_day_2024(filename: str) -> str:
    """2024용 Day 추출."""
    # Pattern 1: Day N[A-D] (기존)
    match = re.search(r'Day\s*(\d+)\s*([A-D])?', filename, re.I)
    if match:
        return f'{match.group(1)}{match.group(2) or ""}'

    # Pattern 2: [Day N[A-D]] (CIRCUIT 대괄호)
    match = re.search(r'\[Day\s*(\d+)\s*([A-D])?\]', filename, re.I)
    if match:
        return f'{match.group(1)}{match.group(2) or ""}'

    # Pattern 3: dayNN (LV 소문자)
    match = re.search(r'day(\d+)', filename)
    if match:
        return match.group(1)

    # Pattern 4: -ft- (Final Table)
    if '-ft-' in filename.lower():
        return 'FT'

    return ''
```

### 3.3 Episode 번호 추출 (신규)

```python
def extract_episode_num(filename: str) -> int | None:
    """에피소드 번호 추출 (2024 특화)."""
    # Pattern 1: WE24-ME-NN (EU)
    match = re.search(r'WE24-ME-(\d+)', filename, re.I)
    if match:
        return int(match.group(1))

    # Pattern 2: WCLA24-NN (CIRCUIT)
    match = re.search(r'WCLA24-(\d+)', filename, re.I)
    if match:
        return int(match.group(1))

    return None
```

### 3.4 Hand 클립 제외

```python
def is_hand_clip(filename: str) -> bool:
    """Hand 클립 여부 확인."""
    # Hand_XX 패턴
    if re.search(r'Hand_\d+', filename, re.I):
        return True
    # vs 패턴 (플레이어 대결)
    if re.search(r'\w+\s+vs\s+\w+', filename, re.I):
        return True
    return False
```

---

## 4. Entry Key 생성

### 4.1 LV Bracelet Event

```
WSOP_2024_BR_E{event_num}_D{day}
WSOP_2024_BR_E{event_num}_FT

예시:
- WSOP_2024_BR_E1_FT (Event #1 Final Table)
- WSOP_2024_BR_E26_D2 (Event #26 Day 2)
```

### 4.2 EU Main Event

```
WSOP_2024_EU_ME_D{day}
WSOP_2024_EU_ME_EP{episode}

예시:
- WSOP_2024_EU_ME_D1B (Day 1B)
- WSOP_2024_EU_ME_EP01 (Episode 1)
```

### 4.3 PARADISE Super Main Event

```
PARADISE_2024_SME_D{day}

예시:
- PARADISE_2024_SME_D1B (Day 1B)
- PARADISE_2024_SME_D2 (Day 2)
```

### 4.4 CIRCUIT

```
CIRCUIT_2024_LA_{event}_D{day}
CIRCUIT_2024_LA_ME_EP{episode}

예시:
- CIRCUIT_2024_LA_ME_D1A (Main Event Day 1A)
- CIRCUIT_2024_LA_ME_EP01 (Episode 1)
```

---

## 5. 제외 규칙

### 5.1 클립 파일 제외

| 조건 | 적용 |
|------|------|
| `Hand_\d+` 패턴 | 제외 |
| `vs` 포함 (대결 클립) | 제외 |
| Size < 1GB | 제외 |
| Duration < 30min | 제외 |

### 5.2 실제 결과

| Region | Total | Excluded | Active |
|--------|-------|----------|--------|
| PARADISE | 286 | 286 | **0** |
| LV | 101 | 101 | **0** |
| CIRCUIT | 40 | 40 | **0** |
| EU | 30 | 23 | **7** |
| OTHER | 1 | 0 | **1** |
| **Total** | **458** | **450** | **8** |

**활성 파일 목록:**
- EU Main Event Day 1B, 2, 3, 4, 5 (5개)
- EU 50K Diamond High Roller Day 1, 2 (2개)
- GOG Final Edit (1개)

---

## 6. 구현 상태

### Phase 1: 패턴 확장 ✅
- [x] `extract_event_num()` 구현 (match_2024.py)
- [x] `extract_day()` 구현 (match_2024.py)
- [x] `extract_episode_num()` 구현 (match_2024.py)
- [x] `is_hand_clip()` 구현 (match_2024.py)

### Phase 2: 스크립트 작성 ✅
- [x] `match_2024.py` 생성 (2025 기반)
- [x] 지역별 Entry Key 생성 로직
- [x] 클립 제외 로직 (Size < 1GB)

### Phase 3: 검증 및 내보내기 ✅
- [x] 패턴 추출 검증
- [x] Google Sheets 내보내기 (2024_Catalog, 2024_Summary, 2024_Episodes)
- [x] 문서 업데이트 (v1.1)

---

## 7. 2025와의 차이점

| 항목 | 2025 | 2024 |
|------|------|------|
| **파일 유형** | 에피소드 중심 | 클립 중심 |
| **Event # 패턴** | `Event #N` | `ev-N`, `Event #N` |
| **Day 패턴** | `Day N` | `dayN`, `[Day N]` |
| **PARADISE** | 없음 | 286개 (전체 제외) |
| **NC/RAW** | EU에 존재 | 없음 |
| **전체 파일** | 134개 | 458개 |
| **서비스 대상** | 132개 | **8개** |

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2025-12-18 | 초기 전략 수립 |
| 1.1 | 2025-12-18 | 구현 완료, 실제 결과 반영 (8개 활성 파일) |
