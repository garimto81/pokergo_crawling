# Archive 파일명 규칙 분석서

> 분석 일자: 2025-12-15
> 분석 대상: Z:/archive (총 1,863 파일, ~20TB)

---

## 1. 폴더 구조 규칙

### 1.1 최상위 카테고리

```
Z:/archive/
├── WSOP/                    # World Series of Poker (95%, 1,771 파일)
├── PAD/                     # Poker After Dark (44 파일)
├── GOG 최종/                # Game of Gold (24 파일)
├── MPP/                     # Merit Poker Premier (11 파일)
├── GGMillions/              # GGPoker High Roller (13 파일)
└── HCL/                     # Hustler Casino Live (빈 폴더)
```

### 1.2 WSOP 하위 폴더 구조

```
WSOP/
├── WSOP ARCHIVE (PRE-2016)/           # 2016년 이전 아카이브
│   └── WSOP {YYYY}/                   # 연도별 폴더
│       ├── MOVs/                      # MOV 원본
│       ├── MXFs/                      # MXF 원본
│       ├── Masters/                   # 마스터 파일
│       └── Generics/                  # 범용 버전
│
├── WSOP Bracelet Event/               # 브레이슬릿 이벤트
│   ├── WSOP-LAS VEGAS/
│   │   └── {YYYY} WSOP-LAS VEGAS/
│   │       ├── WSOP {YYYY} BRACELET SIDE EVENT/
│   │       └── WSOP {YYYY} MAIN EVENT/
│   │
│   ├── WSOP-EUROPE/
│   │   └── {YYYY} WSOP-Europe/
│   │       └── {YYYY} WSOP-EUROPE #{N} {EVENT_NAME}/
│   │           └── NO COMMENTARY WITH GRAPHICS VER/
│   │
│   └── WSOP-PARADISE/
│       └── {YYYY} WSOP-PARADISE {EVENT_NAME}/
│           ├── Hand Clip/
│           ├── STREAM/
│           └── SUBCLIP/
│
└── WSOP Circuit Event/
    ├── WSOP Super Circuit/
    └── WSOP-Circuit/
```

---

## 2. 파일명 패턴 규칙

### 2.1 WSOP 파일명 패턴

#### Pattern W1: 최신 브레이슬릿 이벤트 (2021+)

```
{YYYY} WSOP Event #{N} - ${BUYIN} {EVENT_NAME} {STAGE}.mp4

예시:
- 2021 WSOP Event #13 -$3,000 Freezeout No Limit Hold'em Final Table.mp4
- 2022 WSOP Event #70 -$10,000 No-Limit Hold'em Main Event Day 3.mp4
- 2025 WSOP Event #3 $5K No-Limit Hold'em Final Table (1080P).mp4
```

| 요소 | 규칙 |
|------|------|
| YYYY | 4자리 연도 |
| N | 이벤트 번호 (1~70+) |
| BUYIN | $1,000 ~ $250,000 |
| STAGE | Day 1A/1B/1C/1D, Day 2, Final Table 등 |

#### Pattern W2: Circuit LA 스타일 (2024)

```
{YYYY} WSOP Circuit Los Angeles - {EVENT_NAME} [{STAGE}].mp4

예시:
- 2024 WSOP Circuit Los Angeles - Main Event [Day 1A].mp4
- 2024 WSOP Circuit Los Angeles - Mystery Bounty NL Hold'em [Day 2].mp4
- 2024 WSOP Circuit Los Angeles - Tournament of Champions, $1M GTD [Final Table].mp4
```

#### Pattern W3: PokerGO 클립 스타일 (2024 BE)

```
{N}-wsop-{YYYY}-{TYPE}-ev-{EVENT_NUM}-{DESCRIPTION}-clean.mp4

예시:
- 1-wsop-2024-be-ev-01-5k-champions-reunion-ft-Conniff-hero-calls.mp4
- 54-wsop-2024-me-day6-Foxen-gets-2-better-hands-to-fold-clean.mp4
```

| 요소 | 규칙 |
|------|------|
| N | 시퀀스 번호 |
| TYPE | be (bracelet event), me (main event) |
| clean | 클린 버전 표시 |

#### Pattern W4: WS 축약형 (2011-2015)

```
WS{YY}_{TYPE}{EP}_NB.mp4

예시:
- WS11_ME01_NB.mp4       # 2011 Main Event Episode 1
- WS11_GM02_NB.mp4       # 2011 Grudge Match Episode 2
- WS11_HU01_NB.mp4       # 2011 Heads Up Episode 1
- WS12_Show_17_FINAL_NB.mp4
```

| 코드 | 의미 |
|------|------|
| ME | Main Event |
| GM | Grudge Match |
| HU | Heads Up |
| PPC | Poker Players Championship |
| NB | No Bug (버그 없음) |

#### Pattern W5: WSOP Europe 스타일

```
WSOPE{YY}_Episode_{N}_H264.mov
WSE{YY}-ME{EP}_EuroSprt_NB_TEXT.mp4

예시:
- WSOPE08_Episode_1_H264.mov
- WSE13-ME01_EuroSprt_NB_TEXT.mp4
```

#### Pattern W6: WSOP APAC 스타일

```
WSOP{YY}_APAC_{TYPE}{EP}_NB.mp4

예시:
- WSOP13_APAC_ME01_NB.mp4
- WSOP14_APAC_HIGH_ROLLER-SHOW 1.mp4
- WSOP14_APAC_MAIN_EVENT-SHOW 2.mp4
```

#### Pattern W7: 아카이브 MXF 스타일 (PRE-2016)

```
WSOP_{YYYY}_{N}.mxf
WSOP_{YYYY}.mxf

예시:
- WSOP_2004_1.mxf
- WSOP_2005_01.mxf
- WSOP_2011_31_ME25.mxf
```

#### Pattern W8: ESPN 방송 스타일 (2004-2010)

```
ESPN {YYYY} WSOP SEASON {N} SHOW {M}.mov
{YYYY} WSOP Show {N} {EVENT_NAME}_ESM{ID}.mov

예시:
- ESPN 2007 WSOP SEASON 5 SHOW 1.mov
- 2004 WSOP Show 1 2k NLTH_ESM000100722.mov
- WSOP 2006 Show 10_ES0600163242_GMPO 736.mov
```

#### Pattern W9: 역사적 ME 스타일 (1973-2001)

```
wsop-{YYYY}-me-nobug.mp4
WSOP - {YYYY}.mp4
{YYYY} World Series of Poker.mov

예시:
- wsop-1973-me-nobug.mp4
- WSOP - 1973.avi
- 1997 World Series of Poker.mov
```

#### Pattern W10: WSOP Paradise 스타일 (2023-2024)

```
{YYYY} WSOP Paradise {EVENT} - {STAGE}.mp4
WSOP Paradise {EVENT} ({STAGE}) - {PLAYERS} [$PRIZE].mp4

예시:
- 2024 WSOP Paradise Super Main Event - Day 1B.mp4
- WSOP Paradise Main Event (Day 1A) - Sergio Aguero & Ryan Riess [$15M Prize].mp4
```

#### Pattern W11: 2025 브레이슬릿 스타일

```
WSOP {YYYY} Bracelet Events _ Event #{N} ${BUYIN} {EVENT_NAME}.mp4
(PokerGO) WSOP {YYYY} Bracelet Events _ Event #{N} ...
(YouTube) WSOP {YYYY} Bracelet Events  Event #{N} ...

예시:
- WSOP 2025 Bracelet Events _ Event #13 $1.5K No-Limit Hold'em 6-Max.mp4
- WSOP 2025 Bracelet Events _ Event #38 $100K No-Limit Hold'em High Roller _ Final.mp4
```

---

### 2.2 PAD (Poker After Dark) 패턴

```
pad-s{SS}-ep{EE}-{NNN}.mp4

예시:
- pad-s12-ep01-002.mp4
- pad-s13-ep05-004.mp4
```

| 요소 | 규칙 |
|------|------|
| SS | 시즌 번호 (2자리) |
| EE | 에피소드 번호 (2자리) |
| NNN | 파일 시퀀스 (3자리) |

**폴더 구조:**
```
PAD/
├── PAD S12/    # 시즌 12
└── PAD S13/    # 시즌 13
```

---

### 2.3 GOG (Game of Gold) 패턴

```
E{NN}_GOG_final_edit_{YYYYMMDD|DESC}.mp4

예시:
- E01_GOG_final_edit_231106.mp4
- E01_GOG_final_edit_클린본.mp4
- E02_GOG_final_edit_20231113_최종.mp4
- E11_GOG_final_edit_20231203_찐최종.mp4
```

| 요소 | 규칙 |
|------|------|
| NN | 에피소드 번호 (2자리) |
| YYYYMMDD | 편집 날짜 (6자리 또는 8자리) |
| DESC | 클린본, 최종, 찐최종 등 |

**폴더 구조:**
```
GOG 최종/
├── e01/
├── e02/
...
└── e12/
```

---

### 2.4 MPP (Merit Poker Premier) 패턴

```
${GTD} GTD   ${BUYIN} {EVENT_NAME} – {STAGE}.mp4

예시:
- $1M GTD   $1K PokerOK Mystery Bounty – Day 1A.mp4
- $5M GTD   $5K MPP Main Event – Final Day.mp4
```

| 요소 | 규칙 |
|------|------|
| GTD | 보장 상금 ($1M, $2M, $5M) |
| BUYIN | 바이인 ($1K, $2K, $5K) |
| STAGE | Day 1A/1C, Day 2, Day 3 Session 1/2, Final Day/Table |

**폴더 구조:**
```
MPP/
└── 2025 MPP Cyprus/
    ├── $1M GTD   $1K PokerOK Mystery Bounty/
    ├── $2M GTD   $2K Luxon Pay Grand Final/
    └── $5M GTD   $5K MPP Main Event/
```

---

### 2.5 GGMillions 패턴

```
{YYMMDD}_Super High Roller Poker FINAL TABLE with {PLAYER}.mp4
Super High Roller Poker FINAL TABLE with {PLAYER}.mp4

예시:
- 250507_Super High Roller Poker FINAL TABLE with Joey ingram.mp4
- 250618_Super High Roller Poker FINAL TABLE with Kevin Martin & Dan Cates.mp4
- Super High Roller Poker FINAL TABLE with Benjamin Rolle (1).mp4
```

| 요소 | 규칙 |
|------|------|
| YYMMDD | 6자리 날짜 (25년 5월 7일 = 250507) |
| PLAYER | 출연 선수 이름 |
| (1) | 중복 파일 번호 |

---

## 3. 공통 규칙 요약

### 3.1 연도 표기

| 형식 | 예시 | 사용 위치 |
|------|------|----------|
| YYYY | 2024 | 대부분의 최신 파일 |
| YY | 24, 11 | WS{YY}, WCLA{YY} 축약형 |
| YYYYMMDD | 20231113 | GOG 편집 날짜 |
| YYMMDD | 231106, 250507 | GOG, GGMillions 날짜 |

### 3.2 이벤트 타입 코드

| 코드 | 전체명 | 설명 |
|------|--------|------|
| ME | Main Event | 메인 이벤트 |
| GM | Grudge Match | 그러지 매치 |
| HU | Heads Up | 헤즈업 |
| BR | Bracelet | 브레이슬릿 이벤트 |
| HR | High Roller | 하이롤러 |
| FT | Final Table | 파이널 테이블 |
| PPC | Poker Players Championship | 포커 플레이어스 챔피언십 |

### 3.3 지역 코드

| 코드 | 지역 |
|------|------|
| APAC | Asia Pacific (아시아 태평양) |
| EU / EUROPE | Europe (유럽) |
| PARADISE | Bahamas (바하마) |
| LA | Los Angeles |
| LAS VEGAS | Las Vegas |

### 3.4 스테이지 표기

| 표기 | 의미 |
|------|------|
| Day 1A, Day 1B, Day 1C, Day 1D | 1일차 플라이트 |
| Day 2, Day 2ABC, Day 2D | 2일차 |
| Day 3, Day 4, ... | 이후 일차 |
| Final Day | 최종일 |
| Final Table | 파이널 테이블 |
| Part 1, Part 2 | 분할 파트 |
| Session 1, Session 2 | 세션 분할 |

### 3.5 파일 확장자

| 확장자 | 용도 | 비율 |
|--------|------|------|
| .mp4 | 편집/배포용 | 55.7% |
| .mov | 원본/중간본 | 28.4% |
| .mxf | 방송용 원본 | 10.9% |
| .avi | 레거시 | 0.05% |

### 3.6 구분자 규칙

| 구분자 | 사용 패턴 | 예시 |
|--------|----------|------|
| `_` (언더스코어) | 주요 요소 분리 | `WS11_ME01_NB` |
| `-` (하이픈) | 세부 요소 분리 | `pad-s12-ep01-002` |
| ` ` (공백) | 자연어 스타일 | `2024 WSOP Circuit Los Angeles` |
| `#` | 이벤트 번호 | `Event #13` |
| `$` | 금액 | `$5K`, `$1M GTD` |
| `[]` | 스테이지 | `[Day 1A]`, `[Final Table]` |
| `()` | 보조 정보 | `(Part 1)`, `[$15M Prize]` |

---

## 4. 정규식 패턴 (NAMS 적용용)

```python
PATTERNS = [
    # W1: 최신 브레이슬릿 (2021+)
    (r'^(\d{4}) WSOP Event #(\d+)', 'W1_BRACELET_EVENT'),

    # W2: Circuit LA
    (r'^(\d{4}) WSOP Circuit', 'W2_CIRCUIT'),

    # W3: PokerGO 클립
    (r'^(\d+)-wsop-(\d{4})-(be|me)-', 'W3_POKERGO_CLIP'),

    # W4: WS 축약형
    (r'^WS(\d{2})[_-]([A-Z]+)(\d+)', 'W4_WS_SHORT'),

    # W5: WSOP Europe
    (r'^WSOPE?(\d{2})[_-]', 'W5_EUROPE'),

    # W6: WSOP APAC
    (r'WSOP\d{2}[_-]APAC', 'W6_APAC'),

    # W7: 아카이브 MXF
    (r'^WSOP[_-](\d{4})[_-]?(\d+)?\.mxf', 'W7_ARCHIVE_MXF'),

    # W8: ESPN 방송
    (r'^ESPN \d{4} WSOP|^\d{4} WSOP Show', 'W8_ESPN'),

    # W9: 역사적 ME
    (r'^wsop-(\d{4})-me|^WSOP - \d{4}', 'W9_HISTORIC'),

    # W10: Paradise
    (r'WSOP Paradise|WSOP-PARADISE', 'W10_PARADISE'),

    # W11: 2025 브레이슬릿
    (r'^WSOP \d{4} (Bracelet|Main) Event', 'W11_BRACELET_2025'),

    # PAD
    (r'^pad-s(\d{2})-ep(\d{2})', 'PAD'),

    # GOG
    (r'^E(\d{2})_GOG', 'GOG'),

    # MPP
    (r'\$\d+[MK] GTD.*MPP', 'MPP'),

    # GGMillions
    (r'^(\d{6})?_?Super High Roller', 'GGMILLIONS'),
]
```

---

## 5. 미분류 파일 (새 패턴 필요)

| 카테고리 | 수량 | 샘플 | 제안 패턴 |
|----------|------|------|----------|
| WSOP | 35 | `HyperDeck_0010-001.mp4` | 장비 캡처 파일 |
| WSOP | - | `A9o vs Kqo ho.mp4` | 핸드 클립 |
| GGMillions | 13 | 날짜 없는 파일 | 날짜 추가 필요 |
| MPP | 7 | Mystery Bounty, Grand Final | MPP 패턴 확장 |

---

## 6. 권장사항

### 6.1 표준화 제안

1. **연도 표기 통일**: 4자리 YYYY 권장
2. **이벤트 타입 코드 표준화**: ME, BR, HR, HU 사용
3. **스테이지 표기 통일**: `[Day N]`, `[Final Table]` 형식
4. **구분자 통일**: 언더스코어 `_` 기본, 자연어는 공백

### 6.2 NAMS 패턴 DB 등록 우선순위

| 우선순위 | 패턴 | 파일 수 | 비고 |
|----------|------|---------|------|
| P1 | W1 (Bracelet 2021+) | ~200 | 현재 활성 |
| P2 | W11 (Bracelet 2025) | ~60 | 최신 |
| P3 | W4 (WS 축약형) | ~150 | 2011-2015 |
| P4 | W3 (PokerGO 클립) | ~70 | 클립 |
| P5 | PAD | 44 | 완전 매칭 |
| P6 | GOG | 24 | 완전 매칭 |
| P7 | W7 (Archive MXF) | ~200 | PRE-2016 |
| P8 | W8 (ESPN) | ~150 | PRE-2016 |

---

*문서 생성: analyze_archive_patterns.py*
