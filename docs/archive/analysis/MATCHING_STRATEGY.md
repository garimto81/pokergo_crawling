# NAS ↔ PokerGO 매칭 전략

> 작성일: 2025-12-16

## 1. 데이터 개요

### NAS 파일 (1,690개)
- 패턴 분류 완료 (100% 매칭)
- 추출 메타데이터: year, region, event_type, episode, stage, event_num, season, buyin, gtd, version

### PokerGO 에피소드 (1,095개)
- WSOP 관련: 589개
- 상세 매칭 가능: 537개 (Episode/Day/Event# 포함)

---

## 2. 매칭 키 정의

### 2.1 Primary Keys (정확 매칭)

| 매칭 타입 | NAS 필드 | PokerGO 필드 | 예시 |
|-----------|----------|--------------|------|
| **Main Event Episode** | year + episode | title에서 추출 | 2012 + Ep5 |
| **Main Event Day** | year + stage | title에서 추출 | 2025 + D1A |
| **Bracelet Event** | year + event_num | title에서 추출 | 2025 + #13 |

### 2.2 Secondary Keys (퍼지 매칭)

| 매칭 타입 | NAS 필드 | PokerGO 필드 | 유사도 기준 |
|-----------|----------|--------------|-------------|
| **Title Similarity** | filename | title | Levenshtein ≥ 0.7 |
| **Duration Match** | - | duration_sec | ±10% |

---

## 3. 매칭 알고리즘

```
┌─────────────────────────────────────────────────────────────┐
│                    매칭 프로세스                              │
└─────────────────────────────────────────────────────────────┘

[NAS File]
    │
    ▼
┌─────────────────┐
│ 1. Pattern 확인  │ → WSOP_BR_LV_2025_ME, WSOP_ARCHIVE_PRE2016 등
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. 매칭 타입 결정│
└────────┬────────┘
         │
    ┌────┴────┬────────────┬────────────┐
    ▼         ▼            ▼            ▼
[Type A]  [Type B]     [Type C]    [Type D]
ME+Episode ME+Day    Bracelet    Non-WSOP
    │         │            │            │
    ▼         ▼            ▼            ▼
┌─────────────────────────────────────────┐
│ 3. PokerGO 검색                          │
│    - Primary Key 매칭 시도               │
│    - 실패 시 Secondary Key (퍼지)        │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 4. 매칭 결과                             │
│    - EXACT: Primary Key 일치            │
│    - FUZZY: Secondary Key 유사 (≥0.7)   │
│    - NONE: 매칭 없음                     │
└─────────────────────────────────────────┘
```

---

## 4. 패턴별 매칭 전략

### 4.1 WSOP_BR_LV_2025_ME (2025 Main Event)

```python
# NAS 예시
filename: "WSOP 2025 Main Event _ Day 1A.mp4"
year: 2025, stage: "D1A", event_type: "ME"

# PokerGO 매칭
search: title LIKE "WSOP 2025 Main Event%Day 1A%"
match: "WSOP 2025 Main Event | Day 1A"
```

**매칭 키**: `year=2025 AND stage=D1A AND event_type=ME`

### 4.2 WSOP_BR_LV_2025_SIDE (2025 Bracelet Events)

```python
# NAS 예시
filename: "WSOP 2025 Bracelet Events _ Event #13 $1.5K...mp4"
year: 2025, event_num: 13, buyin: "1.5K"

# PokerGO 매칭
search: title LIKE "WSOP 2025%Event #13%"
match: "WSOP 2025 Bracelet Events | Event #13 $1K Mystery Millions"
```

**매칭 키**: `year=2025 AND event_num=13`

### 4.3 WSOP_ARCHIVE_PRE2016 (2011-2016)

```python
# NAS 예시
filename: "WS12_Show_10_ME06_NB.mp4"
year: 2012, episode: 6, event_type: "ME"

# PokerGO 매칭
search: title LIKE "WSOP 2012 Main Event%Episode 6%"
match: "WSOP 2012 Main Event | Episode 6"
```

**매칭 키**: `year=2012 AND episode=6`

### 4.4 WSOP_BR_EU (Europe)

```python
# NAS 예시
filename: "WSOPE08_Episode_1_H264.mov"
year: 2008, region: "EU", episode: 1

# PokerGO 매칭
# Europe는 PokerGO에 없을 수 있음 → NONE 반환
```

**매칭 키**: `year AND region=EU AND episode` (PokerGO 데이터 확인 필요)

### 4.5 PAD (Poker After Dark)

```python
# NAS 예시
filename: "pad-s12-ep17-013.mp4"
season: 12, episode: 17

# PokerGO 매칭 (별도 컬렉션)
# PokerGO에 Poker After Dark 컬렉션 확인 필요
```

---

## 5. 매칭 우선순위

```
Priority 1: EXACT Match (Primary Key)
    year + episode (Main Event 2011-2024)
    year + stage (Main Event 2025)
    year + event_num (Bracelet Events)

Priority 2: FUZZY Match (Secondary Key)
    Title similarity ≥ 0.7
    + Duration match ±10%

Priority 3: MANUAL Review
    매칭 실패 → UI에서 수동 매칭
```

---

## 6. 매칭 대상 분류

### PokerGO에 있을 가능성 높음 (High)
| NAS Pattern | 예상 PokerGO 매칭 |
|-------------|-------------------|
| WSOP_BR_LV_2025_ME | WSOP 2025 Main Event |
| WSOP_BR_LV_2025_SIDE | WSOP 2025 Bracelet Events |
| WSOP_ARCHIVE_PRE2016 (2011-2016) | WSOP 20XX Main Event |
| WSOP_BR_LV (2021-2024) | WSOP 20XX Main Event/Bracelet |

### PokerGO에 있을 가능성 낮음 (Low)
| NAS Pattern | 이유 |
|-------------|------|
| WSOP_BR_EU | PokerGO는 주로 LV 이벤트 |
| WSOP_BR_PARADISE | 별도 확인 필요 |
| WSOP_HISTORIC (Pre-2011) | PokerGO 콘텐츠 범위 외 |
| PAD, GOG, MPP, GGMILLIONS | 별도 컬렉션 확인 |

---

## 7. 구현 계획

### Phase 1: PokerGO 데이터 정규화
1. episodes.json에서 매칭 키 추출
2. 별도 테이블 생성: `pokergo_matching_keys`
   - id, pokergo_episode_id, year, episode, stage, event_num, title

### Phase 2: 자동 매칭 실행
1. NAS 파일별 매칭 키 생성
2. Primary Key 매칭 (EXACT)
3. Secondary Key 매칭 (FUZZY)
4. 결과 저장: `nas_files.pokergo_episode_id`, `match_score`, `match_type`

### Phase 3: UI에서 확인/수정
1. 매칭 결과 리스트 뷰
2. 미매칭 파일 수동 매칭 UI
3. 매칭 오류 수정 기능

---

## 8. 예상 매칭률

| Pattern | NAS 파일 수 | 예상 매칭률 |
|---------|------------|-------------|
| WSOP_BR_LV_2025_ME | 20 | 90%+ |
| WSOP_BR_LV_2025_SIDE | 41 | 80%+ |
| WSOP_BR_LV | 174 | 70%+ |
| WSOP_ARCHIVE_PRE2016 | 544 | 50%+ (2011-2016만) |
| WSOP_BR_EU | 64 | 10%- |
| WSOP_BR_PARADISE | 335 | 30%? |
| Others | 512 | 10%- |

**전체 예상**: 약 40-50% 자동 매칭

---

## 9. 매칭 키 추출 함수 (Python)

```python
import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class MatchingKey:
    year: Optional[int] = None
    episode: Optional[int] = None
    stage: Optional[str] = None
    event_num: Optional[int] = None
    event_type: Optional[str] = None  # ME, BR, HR

def extract_pokergo_key(title: str) -> MatchingKey:
    """PokerGO 타이틀에서 매칭 키 추출"""
    key = MatchingKey()

    # Year
    year_match = re.search(r'WSOP\s*(\d{4})', title)
    if year_match:
        key.year = int(year_match.group(1))

    # Episode
    ep_match = re.search(r'Episode\s*(\d+)', title)
    if ep_match:
        key.episode = int(ep_match.group(1))

    # Stage (Day)
    day_match = re.search(r'Day\s*(\d+)([ABCD])?', title)
    if day_match:
        key.stage = f"D{day_match.group(1)}{day_match.group(2) or ''}"

    # Event#
    event_match = re.search(r'Event\s*#(\d+)', title)
    if event_match:
        key.event_num = int(event_match.group(1))

    # Event Type
    if 'Main Event' in title:
        key.event_type = 'ME'
    elif 'Bracelet' in title:
        key.event_type = 'BR'
    elif 'High Roller' in title:
        key.event_type = 'HR'

    return key

def match_nas_to_pokergo(nas_file, pokergo_episodes) -> Optional[dict]:
    """NAS 파일을 PokerGO 에피소드와 매칭"""

    # 1. Primary Key 매칭
    for ep in pokergo_episodes:
        pg_key = extract_pokergo_key(ep['title'])

        # Main Event Episode 매칭
        if nas_file.year == pg_key.year and nas_file.episode == pg_key.episode:
            if nas_file.event_type == 'ME' and pg_key.event_type == 'ME':
                return {'episode': ep, 'match_type': 'EXACT', 'score': 1.0}

        # Main Event Day 매칭
        if nas_file.year == pg_key.year and nas_file.stage == pg_key.stage:
            if nas_file.event_type == 'ME' and pg_key.event_type == 'ME':
                return {'episode': ep, 'match_type': 'EXACT', 'score': 1.0}

        # Bracelet Event 매칭
        if nas_file.year == pg_key.year and nas_file.event_num == pg_key.event_num:
            return {'episode': ep, 'match_type': 'EXACT', 'score': 1.0}

    # 2. Fuzzy 매칭 (생략)

    return None
```

---

*문서 생성: 2025-12-16*
