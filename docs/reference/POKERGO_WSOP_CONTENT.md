# PokerGO WSOP 콘텐츠 종합 가이드

**Version**: 1.0.0
**Last Updated**: 2025-12-17
**Data Source**: `data/pokergo/wsop_final_20251216_154021.json`

---

## 1. 개요

| 항목 | 수치 |
|------|------|
| **총 영상 수** | 828개 |
| **연도 범위** | 1973 ~ 2025 (52년) |
| **카테고리** | WSOP, WSOP Classic, WSOP Europe |
| **스크래핑 일자** | 2025-12-16 |

### 카테고리별 분포

| 카테고리 | 영상 수 | 비율 | 설명 |
|----------|---------|------|------|
| **WSOP** | 558 | 67.4% | 현대 WSOP (2011~2025) |
| **WSOP Classic** | 234 | 28.3% | 클래식 아카이브 (1973~2010) |
| **WSOP Europe** | 36 | 4.3% | 유럽 시리즈 (2008~2021) |

---

## 2. WSOP (현대)

### 2.1 개요

| 항목 | 내용 |
|------|------|
| **영상 수** | 558개 |
| **연도 범위** | 2011 ~ 2025 |
| **주요 컨텐츠** | Bracelet Events, Main Event |
| **포맷** | Episodes (편집본), Livestreams (생중계) |

### 2.2 연도별 컬렉션

#### 2025 (70개)

| 컬렉션 | 영상 수 | 설명 |
|--------|---------|------|
| WSOP 2025 Bracelet Events | 35 | 브레이슬릿 이벤트 FT |
| WSOP 2025 Main Event | 35 | 메인 이벤트 풀 커버리지 |

#### 2024 (111개)

| 컬렉션 | 영상 수 | 설명 |
|--------|---------|------|
| WSOP 2024 Bracelet Events \| Livestreams | 41 | 브레이슬릿 생중계 |
| WSOP 2024 Bracelet Events \| Episodes | 36 | 브레이슬릿 편집본 |
| WSOP 2024 Main Event \| Livestreams | 18 | ME 생중계 |
| WSOP 2024 Main Event \| Episodes | 15 | ME 편집본 |

#### 2023 (51개)

| 컬렉션 | 영상 수 |
|--------|---------|
| WSOP 2023 Bracelet Events | 36 |
| WSOP 2023 Main Event | 15 |

#### 2022 (51개)

| 컬렉션 | 영상 수 |
|--------|---------|
| WSOP 2022 Bracelet Events | 36 |
| WSOP 2022 Main Event | 15 |

#### 2021 (52개)

| 컬렉션 | 영상 수 |
|--------|---------|
| WSOP 2021 Bracelet Events | 36 |
| WSOP 2021 Main Event | 16 |

#### 2019 (44개)

| 컬렉션 | 영상 수 |
|--------|---------|
| WSOP 2019 Bracelet Events | 29 |
| WSOP 2019 Main Event | 15 |

#### 2011-2018 (179개)

| 연도 | Main Event | Bracelet Events | 합계 |
|------|------------|-----------------|------|
| 2018 | 15 | - | 15 |
| 2017 | 18 | - | 18 |
| 2016 | 16 | 2 | 18 |
| 2015 | 18 | 2 | 20 |
| 2014 | 16 | 8 | 24 |
| 2013 | 24 | 2 | 26 |
| 2012 | 24 | 4 | 28 |
| 2011 | 26 | 4 | 30 |

### 2.3 URL 패턴

```
Base: https://www.pokergo.com/videos/

Bracelet Events:
- wsop-2025-be-ev-{NN}-{buyin}-{game}-{type}
- wsop-2024-be-ev-{NN}-...
- 예: wsop-2025-be-ev-01-1k-mystery-millions-ft

Main Event:
- wsop-2025-me-day-{N}-{part}
- wsop-2024-me-episode-{N}
- 예: wsop-2025-me-day-1a-pt1
```

### 2.4 Slug 구조 분석

| 필드 | 예시 | 설명 |
|------|------|------|
| `wsop` | - | 브랜드 |
| `2025` | - | 연도 |
| `be` / `me` | - | Bracelet Event / Main Event |
| `ev-01` | - | 이벤트 번호 |
| `1k` / `25k` | - | 바이인 ($1,000 / $25,000) |
| `nlh` / `plo` | - | 게임 종류 |
| `6max` / `8h` | - | 포맷 (6-Max, 8-Handed) |
| `ft` / `day-1` | - | Final Table / Day 구분 |

---

## 3. WSOP Classic

### 3.1 개요

| 항목 | 내용 |
|------|------|
| **영상 수** | 234개 |
| **연도 범위** | 1973 ~ 2010 |
| **주요 컨텐츠** | 역대 WSOP 아카이브 영상 |
| **특징** | 계층적 컬렉션 구조 |

### 3.2 컬렉션 구조

```
WSOP Classic
├── WSOP Classic | Pre-2003 (20개)
│   └── 1973, 1978, 1979, 1981, 1983, 1987-2002
│
└── WSOP Classic | 2003-2010
    ├── WSOP Classic 2003 (8개)
    │
    ├── WSOP Classic 2004 (26개)
    │   ├── WSOP Classic 2004 Main Event (11개)
    │   └── WSOP Classic 2004 Bracelet Events (15개)
    │
    ├── WSOP Classic 2005 (31개)
    │   ├── WSOP Classic 2005 Main Event (13개)
    │   └── WSOP Classic 2005 Bracelet Events (18개)
    │
    ├── WSOP Classic 2006 (23개)
    │   ├── WSOP Classic 2006 Main Event (12개)
    │   └── WSOP Classic 2006 Bracelet Events (11개)
    │
    ├── WSOP Classic 2007 (32개)
    │   ├── WSOP Classic 2007 Main Event (16개)
    │   └── WSOP Classic 2007 Bracelet Events (16개)
    │
    ├── WSOP Classic 2008 (31개)
    │   ├── WSOP Classic 2008 Main Event (19개)
    │   └── WSOP Classic 2008 Bracelet Events (12개)
    │
    ├── WSOP Classic 2009 (31개)
    │   ├── WSOP Classic 2009 Main Event (25개)
    │   └── WSOP Classic 2009 Bracelet Events (6개)
    │
    └── WSOP Classic 2010 (32개)
        ├── WSOP Classic 2010 Main Event (28개)
        └── WSOP Classic 2010 Bracelet Events (4개)
```

### 3.3 연도별 상세

| 연도 | Main Event | Bracelet | 합계 | 주요 챔피언 |
|------|------------|----------|------|------------|
| 2010 | 28 | 4 | 32 | Jonathan Duhamel |
| 2009 | 25 | 6 | 31 | Joe Cada |
| 2008 | 19 | 12 | 31 | Peter Eastgate |
| 2007 | 16 | 16 | 32 | Jerry Yang |
| 2006 | 12 | 11 | 23 | Jamie Gold |
| 2005 | 13 | 18 | 31 | Joe Hachem |
| 2004 | 11 | 15 | 26 | Greg Raymer |
| 2003 | 8 | - | 8 | Chris Moneymaker |
| Pre-2003 | 20 | - | 20 | 레전드 시대 |

### 3.4 Pre-2003 아카이브

| 연도 | 영상 수 | 챔피언 |
|------|---------|--------|
| 2002 | 1 | Robert Varkonyi |
| 2001 | 1 | Carlos Mortensen |
| 2000 | 1 | Chris Ferguson |
| 1999 | 1 | Noel Furlong |
| 1998 | 1 | Scotty Nguyen |
| 1997 | 1 | Stu Ungar |
| 1995 | 1 | Dan Harrington |
| 1994 | 1 | Russ Hamilton |
| 1993 | 1 | Jim Bechtel |
| 1992 | 1 | Hamid Dastmalchi |
| 1991 | 1 | Brad Daugherty |
| 1990 | 1 | Mansour Matloubi |
| 1989 | 1 | Phil Hellmuth |
| 1988 | 1 | Johnny Chan |
| 1987 | 1 | Johnny Chan |
| 1983 | 1 | Tom McEvoy |
| 1981 | 1 | Stu Ungar |
| 1979 | 1 | Hal Fowler |
| 1978 | 1 | Bobby Baldwin |
| 1973 | 1 | Puggy Pearson |

---

## 4. WSOP Europe

### 4.1 개요

| 항목 | 내용 |
|------|------|
| **영상 수** | 36개 |
| **연도 범위** | 2008 ~ 2021 |
| **개최지** | Rozvadov (체코), Cannes (프랑스), London (영국) |
| **특징** | 유럽 전용 브레이슬릿 이벤트 |

### 4.2 연도별 상세

| 연도 | 영상 수 | 주요 콘텐츠 |
|------|---------|------------|
| 2021 | 4 | Main Event FT, 25K Platinum HR, 10K NLH 6-Max, 1650 NLH 6-Max |
| 2013 | 2 | Main Event Episode 1-2 |
| 2012 | 4 | Main Event Episode 1-4 |
| 2011 | 4 | Main Event Episode 1-4 |
| 2010 | 4 | Main Event Episode 1-4 |
| 2009 | 10 | 다양한 이벤트 커버리지 |
| 2008 | 8 | 첫 WSOP Europe 시리즈 |

### 4.3 컬렉션 구조

```
WSOP Europe
├── WSOP Europe 2021 (4개)
├── WSOP Europe 2013 (2개)
├── WSOP Europe 2012 (4개)
├── WSOP Europe 2011 (4개)
├── WSOP Europe 2010 (4개)
├── WSOP Europe 2009 (10개)
└── WSOP Europe 2008 (8개)
```

---

## 5. 데이터 스키마

### 5.1 Video Object

```json
{
  "url": "https://www.pokergo.com/videos/{slug}",
  "slug": "wsop-2025-be-ev-01-1k-mystery-millions-ft",
  "title": "WSOP 2025 Bracelet Events | Event #1 $1K Mystery Millions",
  "year": "2025",
  "source": "WSOP 2025 Bracelet Events",
  "category": "WSOP",
  "thumbnail": "https://storage.googleapis.com/gxm-video-platform-images/..."
}
```

### 5.2 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `url` | string | 영상 페이지 전체 URL |
| `slug` | string | URL 슬러그 (고유 식별자) |
| `title` | string | 영상 제목 |
| `year` | string/int | 연도 (1973~2025) |
| `source` | string | 소속 컬렉션 경로 |
| `category` | string | 카테고리 (WSOP/WSOP Classic/WSOP Europe) |
| `thumbnail` | string | 썸네일 이미지 URL |

### 5.3 Source 필드 형식

| 카테고리 | 형식 | 예시 |
|----------|------|------|
| WSOP | `WSOP {year} {type}` | `WSOP 2025 Bracelet Events` |
| WSOP Classic | `WSOP Classic > ... > ...` | `WSOP Classic > WSOP Classic \| 2003-2010 > WSOP Classic 2010 > WSOP Classic 2010 Main Event` |
| WSOP Europe | `WSOP Europe > WSOP Europe {year}` | `WSOP Europe > WSOP Europe 2021` |

---

## 6. 연도별 전체 분포

```
2025: ████████████████████████████████████████ 70
2024: ██████████████████████████████████████████████████████████████████ 111
2023: ████████████████████████████ 51
2022: ████████████████████████████ 51
2021: ████████████████████████████████ 56
2019: ████████████████████████ 44
2018: ████████ 15
2017: ██████████ 18
2016: ██████████ 18
2015: ███████████ 20
2014: █████████████ 24
2013: █ 2 (+2 WSOPE)
2012: ██ 4 (+4 WSOPE)
2011: ██ 4 (+4 WSOPE)
2010: ████████████████████ 36 (+4 WSOPE)
2009: ██████████████████████ 41 (+10 WSOPE)
2008: █████████████████████ 39 (+8 WSOPE)
2007: █████████████████ 32
2006: ████████████ 23
2005: █████████████████ 31
2004: ██████████████ 26
2003: ████ 8
Pre-2003: ███████████ 20
```

---

## 7. 활용 가이드

### 7.1 NAS 파일 매칭

PokerGO 콘텐츠와 NAS 파일 매칭 시 사용할 키:

| PokerGO 필드 | NAS 파일명 패턴 | 매칭 방법 |
|--------------|-----------------|-----------|
| `year` | `wsop-{year}-*` | 연도 매칭 |
| `slug` → `ev-{NN}` | `ev-{NN}` | 이벤트 번호 매칭 |
| `title` → `Episode N` | `episode-{N}` | 에피소드 매칭 |
| `category` | 폴더 경로 | 브랜드 추론 |

### 7.2 UDM 변환 매핑

```python
# PokerGO → UDM Asset
Asset(
    file_name = slug + ".mp4",
    event_context = EventContext(
        year = year,
        brand = Brand.WSOP,  # category에서 추론
        event_type = EventType.BRACELET if "be" in slug else EventType.SUPER_MAIN,
        location = Location.LAS_VEGAS,  # WSOP Europe는 EUROPE
    ),
    source_origin = SourceOrigin(
        source_id = slug,
        source_type = "pokergo",
        original_url = url,
    )
)
```

### 7.3 다운로드 우선순위

| 우선순위 | 카테고리 | 연도 | 이유 |
|----------|----------|------|------|
| 1 | WSOP | 2023-2025 | 최신 고화질 |
| 2 | WSOP | 2019-2022 | 최근 아카이브 |
| 3 | WSOP Classic | 2008-2010 | HD 전환기 |
| 4 | WSOP Classic | 2003-2007 | Moneymaker 붐 시대 |
| 5 | WSOP Europe | All | 유럽 시리즈 |
| 6 | WSOP Classic | Pre-2003 | 레전드 아카이브 |

---

## 8. 관련 파일

| 파일 | 설명 |
|------|------|
| `data/pokergo/wsop_final_20251216_154021.json` | WSOP 전체 데이터 (828개) |
| `data/pokergo/pokergo_merged_20251212_215037.json` | 상세 메타데이터 포함 (206개) |
| `scripts/pokergo_*.py` | 스크래핑 스크립트 |
| `prds/PRD-0012-POKERGO-DOWNLOADER-GUI.md` | 다운로더 GUI PRD |
| `prds/PRD-0013-POKERGO-WEB-APP.md` | 다운로더 Web App PRD |

---

## 9. 업데이트 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2025-12-17 | 1.0.0 | 초기 문서 작성 |
