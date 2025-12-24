# Archive 패턴 추출 규칙서

> 분석 일자: 2025-12-15
> 총 파일: 1,863개 (100% 분류)

---

## 1. 패턴 매칭 순서 (Priority)

패턴은 **우선순위 순서대로** 매칭합니다. 먼저 매칭되면 이후 패턴은 검사하지 않습니다.

| Priority | Pattern ID | Files | Regex |
|----------|------------|-------|-------|
| 1 | WSOP_BR_LV_2025_ME | 20 | `WSOP.*Bracelet.*LAS.?VEGAS.*2025.*MAIN.?EVENT` |
| 2 | WSOP_BR_LV_2025_SIDE | 41 | `WSOP.*Bracelet.*LAS.?VEGAS.*2025.*BRACELET.?SIDE` |
| 3 | WSOP_BR_EU_2025 | 56 | `WSOP.*Bracelet.*EUROPE.*2025` |
| 4 | WSOP_BR_EU | 97 | `WSOP.*Bracelet.*EUROPE` |
| 5 | WSOP_BR_PARADISE | 335 | `WSOP.*Bracelet.*PARADISE` |
| 6 | WSOP_BR_LV | 174 | `WSOP.*Bracelet.*LAS.?VEGAS` |
| 7 | WSOP_CIRCUIT_LA | 40 | `WSOP.*Circuit.*LA` |
| 8 | WSOP_CIRCUIT_SUPER | 8 | `WSOP.*Super.?Circuit` |
| 9 | WSOP_ARCHIVE_PRE2016 | 1000 | `WSOP.*ARCHIVE.*PRE-?2016` |
| 10 | PAD | 44 | `PAD.*(pad-s\d{2}-ep\d{2}\|PAD_S\d{2}_EP\d{2})` |
| 11 | GOG | 24 | `GOG.*E\d{2}[_\-]GOG` |
| 12 | MPP_ME | 4 | `MPP.*Main.?Event` |
| 13 | MPP | 7 | `MPP.*\$\d+[MK]?\s*GTD` |
| 14 | GGMILLIONS | 13 | `GGMillions.*Super.*High.*Roller` |

---

## 2. 패턴별 상세 추출 규칙

### 2.1 WSOP_BR_LV_2025_ME (2025 Las Vegas Main Event)

**경로 구조:**
```
WSOP/WSOP Bracelet Event/WSOP-LAS VEGAS/2025 WSOP-LAS VEGAS/WSOP 2025 MAIN EVENT/
├── WSOP 2025 Main Event _ Day 1/
│   ├── WSOP 2025 Main Event _ Day 1A/
│   │   └── WSOP 2025 Main Event _ Day 1A.mp4
│   └── ...
├── WSOP 2025 Main Event _ Day 3/
│   └── WSOP 2025 Main Event _ Day 3.mp4
└── WSOP 2025 Main Event _ Final Table/
    └── WSOP 2025 Main Event _ Final Table Day 1.mp4
```

**추출 규칙:**
| Field | Regex | Example | Extracted |
|-------|-------|---------|-----------|
| year | `(\d{4})` in path | `2025 WSOP-LAS VEGAS` | 2025 |
| region | 고정값 | - | LV |
| event_type | 고정값 | - | ME |
| stage | `Day\s*(\d+)\s*([ABCD])?` | `Day 1A` | D1A |
| stage | `Final\s*Table` | `Final Table` | FT |

**정규식 (Python):**
```python
# 패턴 매칭
PATTERN = r'WSOP.*Bracelet.*LAS.?VEGAS.*2025.*MAIN.?EVENT'

# 메타데이터 추출
YEAR = r'(\d{4})\s*WSOP'  # → 2025
STAGE_DAY = r'Day\s*(\d+)\s*([ABCD])?'  # → ('1', 'A')
STAGE_FT = r'Final\s*Table(?:\s*Day\s*(\d+))?'  # → Final Table Day 1
PART = r'Part\s*(\d+)'  # → Part 1, Part 2
```

---

### 2.2 WSOP_BR_LV_2025_SIDE (2025 Las Vegas Side Events)

**경로 구조:**
```
WSOP/WSOP Bracelet Event/WSOP-LAS VEGAS/2025 WSOP-LAS VEGAS/WSOP 2025 BRACELET SIDE EVENT/
├── WSOP 2025 Bracelet Events  Event #13 $1.5K No-Limit Hold'em 6-Max/
│   ├── (PokerGO) WSOP 2025 Bracelet Events _ Event #13 $1.5K No-Limit Hold'em 6-Max.mp4
│   └── (YouTube) WSOP 2025 Bracelet Events  Event #13 $1.5K No-Limit Hold'em 6-Max.mp4
└── WSOP 2025 Bracelet Events _ Event #38 $100K No-Limit Hold'em High Roller _ Final/
    └── ...
```

**추출 규칙:**
| Field | Regex | Example | Extracted |
|-------|-------|---------|-----------|
| year | 폴더에서 추출 | `2025 WSOP-LAS VEGAS` | 2025 |
| region | 고정값 | - | LV |
| event_type | 고정값 | - | BR |
| event_num | `Event\s*#?(\d+)` | `Event #13` | 13 |
| buyin | `\$(\d+[KM]?)` | `$100K` | 100K |
| stage | `Day\s*(\d+)` 또는 `Final` | `Day 2`, `Final` | D2, FT |

**정규식 (Python):**
```python
PATTERN = r'WSOP.*Bracelet.*LAS.?VEGAS.*2025.*BRACELET.?SIDE'

EVENT_NUM = r'Event\s*#?(\d+)'  # → 13, 38, 46
BUYIN = r'\$(\d+(?:,\d+)?[KM]?)'  # → 1.5K, 100K, 250K
GAME_TYPE = r'\$[\d.,]+[KM]?\s+(.+?)(?:\s*[-_]\s*(?:Day|Final)|\s*$)'  # → "No-Limit Hold'em 6-Max"
```

---

### 2.3 WSOP_BR_EU_2025 (2025 Europe)

**경로 구조:**
```
WSOP/WSOP Bracelet Event/WSOP-EUROPE/2025 WSOP-Europe/
├── 2025 WSOP-EUROPE #10 10K PLO MY.BO FINAL/
│   ├── NO COMMENTARY WITH GRAPHICS VER/
│   │   └── ...
│   └── 🏆 WSOPE 10K PLO Mystery Bounty Final Day [BRACELET #10]...mp4
└── 2025 WSOP-EUROPE #14 MAIN EVENT/
    ├── NO COMMENTARY WITH GRAPHICS VER/
    │   ├── Day 1 A/
    │   ├── Day 1 B/
    │   └── ...
    └── STREAM/
```

**추출 규칙:**
| Field | Regex | Example | Extracted |
|-------|-------|---------|-----------|
| year | 폴더에서 | `2025 WSOP-Europe` | 2025 |
| region | 고정값 | - | EU |
| event_num | `#(\d+)` | `#10`, `#14` | 10, 14 |
| event_type | `MAIN EVENT` → ME, 기타 → BR | `#14 MAIN EVENT` | ME |
| stage | 폴더명 | `Day 1 A` | D1A |
| version | 폴더명 | `NO COMMENTARY WITH GRAPHICS VER` | NC |

**정규식 (Python):**
```python
PATTERN = r'WSOP.*Bracelet.*EUROPE.*2025'

EVENT_NUM = r'#(\d+)'  # → 10, 14
IS_MAIN_EVENT = r'MAIN\s*EVENT'  # True/False
DAY_FOLDER = r'Day\s*(\d+)\s*([ABCD])?'  # 폴더명에서
NO_COMMENTARY = r'NO\s*COMMENTARY'  # NC 버전 여부
```

---

### 2.4 WSOP_BR_EU (Europe 2008-2024)

**경로 구조:**
```
WSOP/WSOP Bracelet Event/WSOP-EUROPE/
├── 2008 WSOP-Europe/
│   ├── WSOPE08_Episode_1_H264.mov
│   └── ...
├── 2013 WSOP-Europe/
│   ├── WSE13-ME01_EuroSprt_NB_TEXT.mp4
│   └── ...
└── 2024 WSOP-Europe/
    └── ...
```

**추출 규칙:**
| Field | Regex | Example | Extracted |
|-------|-------|---------|-----------|
| year | `(\d{4})\s*WSOP` 또는 `WSOPE?(\d{2})` | `2008`, `WSOPE08` | 2008 |
| region | 고정값 | - | EU |
| episode | `Episode[_\s]?(\d+)` 또는 `ME(\d{2})` | `Episode_1`, `ME01` | 1 |
| event_type | `ME` in filename → ME | `WSE13-ME01` | ME |

**정규식 (Python):**
```python
PATTERN = r'WSOP.*Bracelet.*EUROPE'

# 연도 추출 (우선순위)
YEAR_4DIGIT = r'(\d{4})\s*WSOP'  # → 2008
YEAR_2DIGIT = r'WSOPE?(\d{2})[_\-]'  # → 08 → 2008

# 에피소드
EPISODE_LONG = r'Episode[_\s]?(\d+)'  # → 1
EPISODE_SHORT = r'[_\-]ME(\d{2})[_\-]'  # → 01

# 버전 정보
VERSION_NB = r'_NB[_\.]'  # No Bug
VERSION_TEXT = r'_TEXT\.'  # With Text
```

---

### 2.5 WSOP_BR_PARADISE (Paradise/Bahamas)

**경로 구조:**
```
WSOP/WSOP Bracelet Event/WSOP-PARADISE/
├── 2023 WSOP-PARADISE/
│   ├── STREAM/
│   └── SUBCLIP/
└── 2024 WSOP-PARADISE SUPER MAIN EVENT/
    ├── 2024 WSOP Paradise Super Main Event - Day 1B.mp4
    ├── Hand Clip/
    │   ├── Day 1B/
    │   ├── Day 2/
    │   └── ...
    └── WSOP Paradise Main Event (Day 1A) - Sergio Aguero & Ryan Riess [$15M Prize].mp4
```

**추출 규칙:**
| Field | Regex | Example | Extracted |
|-------|-------|---------|-----------|
| year | `(\d{4})\s*WSOP` | `2024 WSOP Paradise` | 2024 |
| region | 고정값 | - | PARADISE |
| event_type | `Main Event` → ME | `Super Main Event` | ME |
| stage | `Day\s*(\d+)([ABCD])?` | `Day 1B` | D1B |
| players | `- (.+?) \[` | `Sergio Aguero & Ryan Riess` | (참고용) |
| prize | `\[\$(.+?) Prize\]` | `$15M Prize` | 15M |

**정규식 (Python):**
```python
PATTERN = r'WSOP.*Bracelet.*PARADISE'

YEAR = r'(\d{4})\s*WSOP'
STAGE = r'Day\s*(\d+)\s*([ABCD])?'
PLAYERS = r'-\s*(.+?)\s*\['  # 선수 이름
PRIZE = r'\[\$(.+?)\s*Prize\]'  # 상금
CONTENT_TYPE = r'(STREAM|SUBCLIP|Hand\s*Clip)'  # 콘텐츠 유형
```

---

### 2.6 WSOP_BR_LV (Las Vegas 2021-2024)

**경로 구조:**
```
WSOP/WSOP Bracelet Event/WSOP-LAS VEGAS/
├── 2021 WSOP - LAS Vegas/
│   └── 2021 WSOP Event #13 -$3,000 Freezeout No Limit Hold'em Final Table.mp4
├── 2022 WSOP - LAS Vegas/
│   └── 2022 WSOP Event #70 -$10,000 No-Limit Hold'em Main Event Day 3.mp4
└── 2024 WSOP-LAS VEGAS (PokerGo Clip)/
    ├── Clean/
    └── Mastered/
```

**추출 규칙:**
| Field | Regex | Example | Extracted |
|-------|-------|---------|-----------|
| year | `(\d{4})\s*WSOP` | `2021 WSOP Event` | 2021 |
| region | 고정값 | - | LV |
| event_num | `Event\s*#(\d+)` | `Event #13` | 13 |
| buyin | `-?\$(\d+,?\d*)\s` | `$3,000` | 3000 |
| event_type | `Main Event` → ME, 기타 → BR | `No-Limit Hold'em` | BR |
| stage | `(Final Table\|Day\s*\d+[ABCD]?)` | `Final Table` | FT |

**정규식 (Python):**
```python
PATTERN = r'WSOP.*Bracelet.*LAS.?VEGAS'

# 파일명 파싱: "2021 WSOP Event #13 -$3,000 Freezeout No Limit Hold'em Final Table.mp4"
FULL_PARSE = r'(\d{4})\s*WSOP\s*Event\s*#(\d+)\s*-?\$?([\d,]+)\s+(.+?)\s+(Day\s*\d+[ABCD]?|Final\s*Table)'
# Groups: (year, event_num, buyin, game_type, stage)

IS_MAIN_EVENT = r'Main\s*Event'  # event_type = ME if matches
```

---

### 2.7 WSOP_CIRCUIT_LA (Circuit Los Angeles)

**경로 구조:**
```
WSOP/WSOP Circuit Event/WSOP-Circuit/2024 WSOP Circuit LA/
├── 2024 WSOP-C LA STREAM/
│   └── 2024 WSOP Circuit Los Angeles - Main Event [Day 1A].mp4
└── 2024 WSOP-C LA SUBCLIP/
    └── WCLA24-01.mp4
```

**추출 규칙:**
| Field | Regex | Example | Extracted |
|-------|-------|---------|-----------|
| year | `(\d{4})\s*WSOP` | `2024 WSOP Circuit` | 2024 |
| region | 고정값 | - | LA |
| event_name | `- (.+?) \[` | `Main Event` | Main Event |
| event_type | `Main Event` → ME | - | ME |
| stage | `\[(.+?)\]` | `[Day 1A]` | D1A |
| episode | `WCLA\d{2}-(\d+)` | `WCLA24-01` | 1 |

**정규식 (Python):**
```python
PATTERN = r'WSOP.*Circuit.*LA'

# 풀 타이틀: "2024 WSOP Circuit Los Angeles - Main Event [Day 1A].mp4"
FULL_TITLE = r'(\d{4})\s*WSOP\s*Circuit\s*Los\s*Angeles\s*-\s*(.+?)\s*\[(.+?)\]'
# Groups: (year, event_name, stage)

# 숏 코드: "WCLA24-01.mp4"
SHORT_CODE = r'WCLA(\d{2})-(\d+)'  # → (24, 01)
```

---

### 2.8 WSOP_CIRCUIT_SUPER (Super Circuit)

**경로 구조:**
```
WSOP/WSOP Circuit Event/WSOP Super Ciruit/
├── 2023 WSOP International Super Circuit - London/
│   └── 2023 WSOP International Super Circuit - London Main Event Day 3.mp4
└── 2025 WSOP Super Circuit Cyprus/
    └── $5M GTD   WSOP Super Circuit Cyprus Main Event - Day 1A-006.mp4
```

**추출 규칙:**
| Field | Regex | Example | Extracted |
|-------|-------|---------|-----------|
| year | `(\d{4})\s*WSOP` | `2023 WSOP` | 2023 |
| region | `London` → LONDON, `Cyprus` → CYPRUS | - | LONDON/CYPRUS |
| event_type | `Main Event` → ME | - | ME |
| stage | `Day\s*(\d+)([ABCD])?` | `Day 3` | D3 |
| gtd | `\$(\d+[MK]?)\s*GTD` | `$5M GTD` | 5M |

**정규식 (Python):**
```python
PATTERN = r'WSOP.*Super.?Circuit'

GTD = r'\$(\d+[MK]?)\s*GTD'
LOCATION = r'Circuit\s*[-\s]?\s*(\w+)'  # London, Cyprus
```

---

### 2.9 WSOP_ARCHIVE_PRE2016 (Archive 1973-2016)

**경로 구조:**
```
WSOP/WSOP ARCHIVE (PRE-2016)/
├── WSOP 1973/
│   ├── WSOP - 1973.avi
│   └── wsop-1973-me-nobug.mp4
├── WSOP 2004/
│   ├── Generics/
│   ├── MOVs/
│   │   └── 2004 WSOP Show 1 2k NLTH_ESM000100722.mov
│   └── MXFs/
│       └── WSOP_2004_1.mxf
└── WSOP 2016/
    └── 2016 World Series of Poker - Main Event Show 01 - GMPO 2074.mxf
```

**추출 규칙:**
| Field | Regex | Example | Extracted |
|-------|-------|---------|-----------|
| year | 폴더명 `WSOP (\d{4})` | `WSOP 2004` | 2004 |
| region | 고정값 | - | LV |
| event_type | `me` 또는 `Main Event` → ME | `wsop-1973-me-nobug` | ME |
| episode | `Show\s*(\d+)` 또는 `_(\d+)\.` | `Show 1`, `_01.mxf` | 1 |
| format | 확장자 | `.mxf`, `.mov` | MXF/MOV |

**정규식 (Python):**
```python
PATTERN = r'WSOP.*ARCHIVE.*PRE-?2016'

# 폴더에서 연도
YEAR_FOLDER = r'WSOP\s+(\d{4})'

# 파일명 패턴들
HISTORIC_ME = r'wsop-(\d{4})-me'  # wsop-1973-me-nobug.mp4
ESPN_SHOW = r'(\d{4})\s*WSOP\s*Show\s*(\d+)'  # 2004 WSOP Show 1
SEASON_SHOW = r'ESPN\s*(\d{4})\s*WSOP\s*SEASON\s*(\d+)\s*SHOW\s*(\d+)'  # ESPN 2007 WSOP SEASON 5 SHOW 1
MXF_CODE = r'WSOP[_-](\d{4})[_-]?(\d+)?\.mxf'  # WSOP_2004_1.mxf
GMPO_CODE = r'GMPO\s*(\d+)'  # GMPO 2074
ESM_CODE = r'ESM?(\d+)'  # ESM000100722
```

---

### 2.10 PAD (Poker After Dark)

**경로 구조:**
```
PAD/
├── PAD S12/
│   └── pad-s12-ep01-002.mp4
└── PAD S13/
    └── PAD_S13_EP01_GGPoker-001.mp4
```

**추출 규칙:**
| Field | Regex | Example | Extracted |
|-------|-------|---------|-----------|
| season | `[Ss](\d{2})` | `S12`, `s12` | 12 |
| episode | `[Ee][Pp]?(\d{2})` | `ep01`, `EP01` | 1 |
| sequence | `-(\d{3})` | `-002` | 2 |
| sponsor | `_(\w+)-\d{3}` | `_GGPoker-001` | GGPoker |

**정규식 (Python):**
```python
PATTERN = r'PAD.*(pad-s\d{2}-ep\d{2}|PAD_S\d{2}_EP\d{2})'

# 소문자 형식: pad-s12-ep01-002.mp4
LOWERCASE = r'pad-s(\d{2})-ep(\d{2})-(\d{3})'
# Groups: (season, episode, sequence)

# 대문자 형식: PAD_S13_EP01_GGPoker-001.mp4
UPPERCASE = r'PAD_S(\d{2})_EP(\d{2})_(\w+)-(\d{3})'
# Groups: (season, episode, sponsor, sequence)
```

---

### 2.11 GOG (Game of Gold)

**경로 구조:**
```
GOG 최종/
├── e01/
│   ├── E01_GOG_final_edit_231106.mp4
│   └── E01_GOG_final_edit_클린본.mp4
└── e12/
    └── E12_GOG_final_edit_클린본_20240703.mp4
```

**추출 규칙:**
| Field | Regex | Example | Extracted |
|-------|-------|---------|-----------|
| episode | `E(\d{2})` | `E01` | 1 |
| edit_date | `(\d{6,8})` | `231106`, `20240703` | 2023-11-06 |
| version | `클린본\|최종\|찐최종` | `클린본` | CLEAN |

**정규식 (Python):**
```python
PATTERN = r'GOG.*E\d{2}[_\-]GOG'

# 파일명: E01_GOG_final_edit_231106.mp4
PARSE = r'E(\d{2})_GOG_final_edit_(.+)\.mp4'
# Groups: (episode, suffix)

# 날짜 추출 (6자리 또는 8자리)
DATE_6 = r'(\d{2})(\d{2})(\d{2})'  # YY MM DD → 23 11 06
DATE_8 = r'(\d{4})(\d{2})(\d{2})'  # YYYY MM DD → 2024 07 03

# 버전 키워드
VERSION_CLEAN = r'클린본'
VERSION_FINAL = r'최종|찐최종'
```

---

### 2.12 MPP / MPP_ME (Merit Poker Premier)

**경로 구조:**
```
MPP/
└── 2025 MPP Cyprus/
    ├── $1M GTD   $1K PokerOK Mystery Bounty/
    │   └── $1M GTD   $1K PokerOK Mystery Bounty – Day 1A.mp4
    └── $5M GTD   $5K MPP Main Event/
        └── $5M GTD   $5K MPP Main Event – Day 2.mp4
```

**추출 규칙:**
| Field | Regex | Example | Extracted |
|-------|-------|---------|-----------|
| year | 폴더명 `(\d{4})` | `2025 MPP Cyprus` | 2025 |
| region | 폴더명 | `Cyprus` | CYPRUS |
| gtd | `\$(\d+[MK]?)\s*GTD` | `$5M GTD` | 5M |
| buyin | `\$(\d+[MK]?)` (두 번째) | `$5K` | 5K |
| event_name | GTD 뒤 | `MPP Main Event` | Main Event |
| event_type | `Main Event` → ME | - | ME |
| stage | `Day\s*(\d+)([ABCD])?` | `Day 2` | D2 |
| session | `Session\s*(\d+)` | `Session 1` | S1 |

**정규식 (Python):**
```python
PATTERN_ME = r'MPP.*Main.?Event'
PATTERN = r'MPP.*\$\d+[MK]?\s*GTD'

# 파일명: "$5M GTD   $5K MPP Main Event – Day 2.mp4"
PARSE = r'\$(\d+[MK]?)\s*GTD\s+\$(\d+[MK]?)\s+(.+?)\s*[–-]\s*(.+?)\.mp4'
# Groups: (gtd, buyin, event_name, stage)

STAGE = r'Day\s*(\d+)\s*(?:Session\s*(\d+))?'
FINAL = r'Final\s*(Day|Table)'
```

---

### 2.13 GGMILLIONS

**경로 구조:**
```
GGMillions/
├── 250507_Super High Roller Poker FINAL TABLE with Joey ingram.mp4
└── Super High Roller Poker FINAL TABLE with Benjamin Rolle (1).mp4
```

**추출 규칙:**
| Field | Regex | Example | Extracted |
|-------|-------|---------|-----------|
| date | `(\d{6})_` | `250507_` | 2025-05-07 |
| players | `with (.+?)(?:\s*\(\d+\))?\.mp4` | `with Joey ingram` | Joey ingram |
| duplicate | `\((\d+)\)` | `(1)` | 1 |

**정규식 (Python):**
```python
PATTERN = r'GGMillions.*Super.*High.*Roller'

# 파일명: "250507_Super High Roller Poker FINAL TABLE with Joey ingram.mp4"
WITH_DATE = r'(\d{2})(\d{2})(\d{2})_.*with\s+(.+?)(?:\s*\(\d+\))?\.mp4'
# Groups: (YY, MM, DD, players)

WITHOUT_DATE = r'Super High Roller.*with\s+(.+?)(?:\s*\(\d+\))?\.mp4'
# Groups: (players)

DUPLICATE_NUM = r'\((\d+)\)\.mp4'
```

---

## 3. 메타데이터 추출 종합 함수 (Python)

```python
import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class FileMetadata:
    pattern_id: str
    year: Optional[int] = None
    region: Optional[str] = None
    event_type: Optional[str] = None  # ME, BR, HR, HU, GM, PPC
    event_num: Optional[int] = None
    episode: Optional[int] = None
    season: Optional[int] = None
    stage: Optional[str] = None  # D1A, D2, FT, FINAL, S1
    buyin: Optional[str] = None
    gtd: Optional[str] = None
    version: Optional[str] = None  # NC, NB, CLEAN
    confidence: float = 0.0


def extract_metadata(full_path: str) -> FileMetadata:
    """전체 경로에서 메타데이터 추출"""

    # 1. 패턴 매칭 (우선순위 순서)
    patterns = [
        ("WSOP_BR_LV_2025_ME", r'WSOP.*Bracelet.*LAS.?VEGAS.*2025.*MAIN.?EVENT'),
        ("WSOP_BR_LV_2025_SIDE", r'WSOP.*Bracelet.*LAS.?VEGAS.*2025.*BRACELET.?SIDE'),
        ("WSOP_BR_EU_2025", r'WSOP.*Bracelet.*EUROPE.*2025'),
        # ... (나머지 패턴)
    ]

    pattern_id = "UNKNOWN"
    for pid, regex in patterns:
        if re.search(regex, full_path, re.I):
            pattern_id = pid
            break

    # 2. 패턴별 메타데이터 추출
    meta = FileMetadata(pattern_id=pattern_id)

    if pattern_id == "WSOP_BR_LV_2025_ME":
        meta.year = 2025
        meta.region = "LV"
        meta.event_type = "ME"
        # stage 추출
        stage_match = re.search(r'Day\s*(\d+)\s*([ABCD])?', full_path, re.I)
        if stage_match:
            meta.stage = f"D{stage_match.group(1)}{stage_match.group(2) or ''}"
        elif re.search(r'Final\s*Table', full_path, re.I):
            meta.stage = "FT"
        meta.confidence = 1.0

    elif pattern_id == "PAD":
        # season, episode 추출
        match = re.search(r'[Ss](\d{2}).*[Ee][Pp]?(\d{2})', full_path)
        if match:
            meta.season = int(match.group(1))
            meta.episode = int(match.group(2))
        meta.confidence = 1.0

    # ... (나머지 패턴 처리)

    return meta
```

---

## 4. NAMS 패턴 테이블 초기 데이터

```sql
INSERT INTO patterns (name, priority, regex, extract_year, extract_region, extract_type, description, is_active) VALUES
('WSOP_BR_LV_2025_ME', 1, 'WSOP.*Bracelet.*LAS.?VEGAS.*2025.*MAIN.?EVENT', 2025, 'LV', 'ME', '2025 Las Vegas Main Event', 1),
('WSOP_BR_LV_2025_SIDE', 2, 'WSOP.*Bracelet.*LAS.?VEGAS.*2025.*BRACELET.?SIDE', 2025, 'LV', 'BR', '2025 Las Vegas Side Events', 1),
('WSOP_BR_EU_2025', 3, 'WSOP.*Bracelet.*EUROPE.*2025', 2025, 'EU', NULL, '2025 WSOP Europe', 1),
('WSOP_BR_EU', 4, 'WSOP.*Bracelet.*EUROPE', NULL, 'EU', NULL, 'WSOP Europe', 1),
('WSOP_BR_PARADISE', 5, 'WSOP.*Bracelet.*PARADISE', NULL, 'PARADISE', NULL, 'WSOP Paradise', 1),
('WSOP_BR_LV', 6, 'WSOP.*Bracelet.*LAS.?VEGAS', NULL, 'LV', NULL, 'WSOP Las Vegas', 1),
('WSOP_CIRCUIT_LA', 7, 'WSOP.*Circuit.*LA', NULL, 'LA', NULL, 'WSOP Circuit LA', 1),
('WSOP_CIRCUIT_SUPER', 8, 'WSOP.*Super.?Circuit', NULL, NULL, NULL, 'WSOP Super Circuit', 1),
('WSOP_ARCHIVE_PRE2016', 9, 'WSOP.*ARCHIVE.*PRE-?2016', NULL, 'LV', NULL, 'WSOP Archive Pre-2016', 1),
('PAD', 10, 'PAD.*(pad-s\\d{2}-ep\\d{2}|PAD_S\\d{2}_EP\\d{2})', NULL, NULL, NULL, 'Poker After Dark', 1),
('GOG', 11, 'GOG.*E\\d{2}[_-]GOG', NULL, NULL, NULL, 'Game of Gold', 1),
('MPP_ME', 12, 'MPP.*Main.?Event', NULL, 'CYPRUS', 'ME', 'MPP Main Event', 1),
('MPP', 13, 'MPP.*\\$\\d+[MK]?\\s*GTD', NULL, 'CYPRUS', NULL, 'Merit Poker Premier', 1),
('GGMILLIONS', 14, 'GGMillions.*Super.*High.*Roller', NULL, NULL, NULL, 'GGMillions High Roller', 1);
```

---

*문서 생성: 2025-12-15*
