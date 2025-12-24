# 매칭 패턴 상세 참조

NAS-PokerGO 매칭 규칙의 상세 패턴 예시 및 변경 이력.

**Version**: 5.0 | **Date**: 2025-12-17

> 핵심 규칙: [MATCHING_RULES.md](MATCHING_RULES.md)

---

## 패턴 상세 예시

### P0: WSOP + APAC (Asia Pacific)

**중요**: APAC은 일반 WSOP와 **별도 이벤트**

```
WSOP{YY}_APAC_{EVENT}_{EP}
WSOP{YY}_APAC_{EVENT}-SHOW {##}
```

| 예시 | Year | Region | Event | Episode |
|------|------|--------|-------|---------|
| `WSOP13_APAC_ME01_NB.mp4` | 2013 | APAC | Main Event | 01 |
| `WSOP14_APAC_HIGH_ROLLER-SHOW 1.mp4` | 2014 | APAC | High Roller | 01 |
| `WSOP14_APAC_MAIN_EVENT-SHOW 2.mp4` | 2014 | APAC | Main Event | 02 |

→ Group ID: `{YYYY}_APAC-{TYPE}_{EP}` (예: `2013_APAC-ME_01`)

---

### P1: WS + 2자리 연도

```
WS{YY}_{TYPE}{EP}_*
```

| 예시 | Year | Type | Episode |
|------|------|------|---------|
| `WS11_ME01_NB.mp4` | 2011 | ME | 01 |
| `WS11_ME25_4CH.mp4` | 2011 | ME | 25 |
| `WS11_HU01_NB.mp4` | 2011 | HU | 01 |
| `WS11_GM01_NB.mp4` | 2011 | GM | 01 |

→ Group ID: `{YYYY}_{TYPE}_{EP}` (예: `2011_ME_01`)

---

### P2: WSOP + 2자리 연도

```
WSOP{YY}_{TYPE}{EP}*
```

| 예시 | Year | Type | Episode |
|------|------|------|---------|
| `WSOP11_ME01_AUDIO.mp4` | 2011 | ME | 01 |
| `WSOP13_ME01_NB.mp4` | 2013 | ME | 01 |
| `WSOP14_BR01_NB.mp4` | 2014 | BR | 01 |

---

### P3: WSOP + 4자리 연도 + 시퀀스

```
WSOP_{YYYY}_{SEQ}_{TYPE}{EP}*
```

| 예시 | Year | Seq | Type | Episode |
|------|------|-----|------|---------|
| `WSOP_2011_31_ME25.mxf` | 2011 | 31 | ME | 25 |

---

### P4: WSOPE (Europe)

```
WSOPE{YY}_Episode_{EP}*
WSOPE{YY}_{TYPE}{EP}*
wsope-{yyyy}-{type}-*
```

| 예시 | Year | Region | Episode |
|------|------|--------|---------|
| `WSOPE08_Episode_5.mov` | 2008 | EU | 5 |
| `WSOPE11_Episode_01.mov` | 2011 | EU | 01 |
| `wsope-2009-me-day1.mp4` | 2009 | EU | - |

---

### P5: World Series 전체명

```
{YYYY} World Series of Poker Main Event Show {##}
```

| 예시 | Year | Type | Episode |
|------|------|------|---------|
| `1995 World Series of Poker Main Event Show 1.mp4` | 1995 | ME | 1 |
| `1997 World Series of Poker Main Event Show 3.mp4` | 1997 | ME | 3 |

---

### P6-P8: WSOP Show 패턴 (BOOM Era)

```
P6: {YYYY} WSOP Show {##} ME {##}
P7: WSOP {YYYY} Show {##} ME {##}
P8: {YYYY} WSOP ME{##}
```

| 패턴 | 예시 | Year | Show | ME Episode |
|------|------|------|------|------------|
| P6 | `2006 WSOP Show 15 ME 01.mov` | 2006 | 15 | 01 |
| P7 | `WSOP 2005 Show 10 ME 01.mov` | 2005 | 10 | 01 |
| P8 | `2009 WSOP ME01.mov` | 2009 | - | 01 |

---

### P9: wsop-{yyyy}-me 패턴

```
wsop-{yyyy}-me-*
wsop-{yyyy}-be-*
```

| 예시 | Year | Type |
|------|------|------|
| `wsop-2024-me-day1a.mp4` | 2024 | ME |
| `wsop-2024-be-ev-71-1k-ladies-ft.mp4` | 2024 | BE (Bracelet) |

**주의**: Episode 추출 불가 (Day 정보만 포함)

---

### P10: 폴더명 기반 추출

폴더 경로에서 연도 및 Event Type 추출:

| 폴더 경로 | 추출 | 예시 파일 |
|----------|------|----------|
| `WSOP 2011/` | year=2011 | `ME25.mxf` |
| `Main Event/` | type=ME | `episode_01.mp4` |
| `Bracelet Event/` | type=BR | `event_37.mp4` |
| `WSOP-Europe/2009/` | region=EU, year=2009 | `day1.mov` |

---

## BOOM Era 매핑 (2003-2010)

### Day → Episode 매핑

PokerGO는 "Episode" 대신 **"Day"** 구조 사용:

| PokerGO Title | 구조 | NAS 매핑 |
|---------------|------|----------|
| `Wsop Main Event 2003 Day 1` | Day 1 | Episode 1 |
| `Wsop Main Event 2003 Day 3 Part 1` | Day 3, Part 1 | Episode 3 |
| `Wsop Main Event 2003 Final Table Part 1` | Final Table | Episode 99 |
| `Wsop Main Event 2004 Day 1A` | Day 1A | Episode 1 |

**매핑 규칙**:
```
Day 1, Day 1A, Day 1B → Episode 1
Day 2, Day 2A, Day 2B → Episode 2
Day 3 Part 1, Part 2 → Episode 3
Final Table → Episode 99
```

### Bracelet Event 이벤트 번호 매핑

PokerGO는 **이벤트 번호 + 바이인 + 게임명** 구조:

| PokerGO Title | 이벤트# | NAS Show# |
|---------------|---------|-----------|
| `Wsop 2004 01 2K Nlh` | 01 | Show 1 |
| `Wsop 2004 05 1500 Nlh` | 05 | Show 5 |
| `Wsop 2004 10 1500 Razz` | 10 | Show 10 |

**추출 패턴**:
```python
# PokerGO: "Wsop 2004 05 1500 Nlh"
pattern = r'Wsop\s+(\d{4})\s+(\d{2})\s+(\d+[kK]?)\s+(.+)'
# group(1)=year, group(2)=event_num, group(3)=buyin, group(4)=game
```

---

## Hand Clip 감지 패턴

포커 핸드 하이라이트 클립 파일 감지:

| 패턴 | 설명 | 예시 |
|------|------|------|
| `^\d+-wsop-` | 숫자로 시작 + wsop | `43-wsop-2024-me-day1b-Koury...` |
| `-hs-` 또는 `_hs_` | Hand Segment 약어 | `51-wsop-2024-me-day4-hs-Eisenberg...` |
| `hand_` | Hand 키워드 | `1213_Hand_09_Hynes_KJc_vs_Tony...` |

```python
def is_hand_clip(filename: str) -> bool:
    fname_lower = filename.lower()
    if re.match(r'^\d+-wsop-', fname_lower):
        return True
    if '-hs-' in fname_lower or '_hs_' in fname_lower:
        return True
    if 'hand_' in fname_lower:
        return True
    return False
```

---

## LA vs Ladies 구분

**중요**: WCLA와 Ladies Championship 혼동 방지

```
WCLA = WSOP Circuit Los Angeles (지역 이벤트, Region=LA)
Ladies Championship = $1K Ladies Championship (LV Bracelet Event #71)

파일 예시:
- WCLA24-17.mp4 → LA Circuit (Region=LA)
- 39-wsop-2024-be-ev-71-1k-ladies-ft... → Ladies (Region=LV)

⚠️ LA Circuit 파일을 Ladies Championship에 매칭하면 안 됨!
```

---

## Heads-Up Championship 규칙

$25K Heads-Up Championship은 Semifinals와 Final 두 에피소드:

| PokerGO Title | NAS Episode | 파일 예시 |
|---------------|-------------|-----------|
| "... Heads-Up Championship Semifinals" | 1 (HU01) | `WS11_HU01_NB.mp4` |
| "... Heads-Up Championship Final ..." | 2 (HU02) | `WS11_HU02_NB.mp4` |

```python
if 'semifinals' in title.lower():
    episode = 1
elif 'final' in title.lower():
    episode = 2
```

---

## Grudge Match 규칙

**수작업 필요**: 대전자 이름으로만 구분

```
WSOP 2011 Bracelet Events | Heads-Up Grudge Match | Chris Moneymaker vs. Sammy Farha
WSOP 2011 Bracelet Events | Heads-Up Grudge Match | Johnny Chan vs. Phil Hellmuth
```

→ 영상 내용 확인 후 수동 매칭 필요

---

## Primary/Backup 파일명 패턴

### Primary 우선순위 점수

```python
def get_primary_score(filename: str) -> int:
    score = 0
    fname_lower = filename.lower()

    # 정제 키워드 = 높은 점수
    if 'nobug' in fname_lower or 'clean' in fname_lower or 'final' in fname_lower:
        score += 100

    # 복사 표시 = 낮은 점수
    if re.search(r'\(\d+\)', filename):
        score -= 50

    # 확장자 우선순위
    ext_priority = {'.mp4': 10, '.mov': 8, '.mxf': 6, '.avi': 4, '.mkv': 2, '.wmv': 1}
    ext = Path(filename).suffix.lower()
    score += ext_priority.get(ext, 0)

    return score
```

### Backup 감지 패턴

| 패턴 | 설명 | 예시 |
|------|------|------|
| `(1)`, `(2)` | 복사본 표시 | `WSOP - 1973 (1).mp4` |
| `_copy` | 복사 키워드 | `file_copy.mp4` |
| `_v1`, `_v2` | 버전 표시 | `file_v1.mp4` (v2가 Primary) |

---

## PokerGO 제외 대상 (헤더)

실제 에피소드가 아닌 **컬렉션/시즌 헤더** 제외:

| 제외 패턴 | 예시 |
|-----------|------|
| `{Year} Main Event` (단독) | "WSOP 2011 Main Event" |
| `| Episodes` 로 끝남 | "WSOP 2024 Main Event \| Episodes" |
| `| Livestreams` 로 끝남 | "WSOP 2024 Bracelet Events \| Livestreams" |

**실제 에피소드 키워드**:
- `Episode` + 숫자
- `Event #` + 숫자
- `Day` + 숫자
- `Final Table`
- `vs.`

---

## v5.0 상세 변경 내용

### 1. Region 매칭 강화

**문제**: Substring false positive (`'eu' in 'reunion' = True`)

```python
# 기존 (문제)
if region_code.lower() in title_lower:
    score += 0.2

# 개선 (v5.0)
if region_code in ('EU', 'APAC', 'PARADISE', 'CYPRUS', 'LA', 'LONDON'):
    if region_code == 'EU' and not ep_is_europe:
        continue
```

### 2. Episode-less 그룹 제한

```python
# Episode-less 그룹 (2016_ME)이 "Episode 1" 매칭 방지
if not group.episode and ep_episode and group.year >= 2003:
    continue
```

### 3. BOOM Era Bracelet Event 오매칭 방지

```python
# Event type 없는 그룹이 Bracelet Event와 매칭되는 것 방지
is_bracelet_event = re.search(r'wsop\s+\d{4}\s+\d{2}\s+', title_lower)
if is_bracelet_event and not is_main_event_title:
    continue
```

### 4. 개선 결과

| 지표 | v4.2 | v5.0 | 변화 |
|------|------|------|------|
| DUPLICATE | 53 | 18 | -35 (66% 감소) |
| OK | 730 | 765 | +35 |
| MATCHED | 429 | 365 | -64 (엄격한 매칭) |

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2025-12-17 | 5.0 | Region/Episode 매칭 강화, DUPLICATE 53→18 감소, 제외 파일 DUPLICATE 제외 |
| 2025-12-17 | 4.3 | X: 드라이브 통합, 2017-2020년 NAS 공백 해결 (81개) |
| 2025-12-17 | 4.2 | BOOM Era 패턴 10개 추가, 매칭률 81%→97.6% |
| 2025-12-17 | 4.1 | 경로 기반 패턴 추가, `WSOP_2003-01.mxf` 형식 지원 |
| 2025-12-17 | 4.0 | DUPLICATE 완전 해결 (374→0), LV 기본 지역 적용 |
| 2025-12-16 | 3.8 | PokerGO Source (X:) 추가, 5개 시트 시스템 확장 |
| 2025-12-16 | 3.7 | 정규화 기반 매칭, 49개 추가 매칭 |
| 2025-12-16 | 3.6 | Full Path 기준 변경 |
| 2025-12-16 | 3.5 | 1:1 매칭 규칙, DUPLICATE Action |
| 2025-12-16 | 3.4 | CLASSIC Era 연도 기반 매칭 |
| 2025-12-16 | 3.3 | WSOP Classic 데이터 추가 (828개) |
| 2025-12-16 | 3.2 | 제외 파일 매칭 제외 |
| 2025-12-16 | 3.1 | Hand Clip 감지 패턴 추가 |
| 2025-12-16 | 3.0 | Era 분류, Origin/Archive 관계 정립, 4시트 시스템 |
| 2025-12-16 | 2.6 | NAS Origin/Archive 규칙 |
| 2025-12-16 | 2.5 | Google Sheets 규칙 확장 |
| 2025-12-16 | 2.4 | WSOP PPC 별도 대회 |
| 2025-12-16 | 2.3 | Heads-Up Championship 규칙 |
| 2025-12-16 | 2.2 | 제외 조건 추가 |
| 2025-12-15 | 2.1 | PARADISE 지역 추가 |
| 2025-12-15 | 2.0 | 전체 패턴 재분석 (11개 패턴 정의) |
| 2025-12-15 | 1.7 | APAC 패턴 추가 |
| 2025-12-15 | 1.6 | 백업 조건 B 추가 |
| 2025-12-15 | 1.5 | 백업 파일 조건 명확화 |
| 2025-12-15 | 1.4 | Pattern 5에 WSOP 패턴 추가 |
| 2025-12-15 | 1.3 | Pattern 5 추가 |
| 2025-12-15 | 1.2 | Episode 정규식 개선 |
| 2025-12-15 | 1.1 | WSOPE (Europe) 패턴 추가 |
| 2025-12-15 | 1.0 | 초기 문서 작성 |
