# NAS-PokerGO 매칭 규칙

NAS 파일과 PokerGO 콘텐츠 매칭 및 Asset Grouping 규칙 정의서.

**Version**: 5.11 | **Date**: 2025-12-18

> 상세 패턴 예시 및 변경 이력: [MATCHING_PATTERNS_DETAIL.md](MATCHING_PATTERNS_DETAIL.md)

---

## 절대 원칙

> **모든 규칙의 최상위 원칙. 예외 없이 반드시 준수.**

### 원칙 1: PokerGO Title 1:1 매칭

```
하나의 PokerGO Title = 하나의 NAS 그룹
```

- **금지**: 여러 NAS 그룹이 동일한 PokerGO Title에 매칭 (N:1)
- **허용**: 하나의 NAS 그룹이 하나의 PokerGO Title에 매칭 (1:1)
- **미매칭**: NAS 그룹이 PokerGO에 매칭되지 않는 것은 허용 (NAS_ONLY)

**구현**: `enforce_one_to_one()` 함수가 매칭 후 중복 제거

### 원칙 2: PokerGO 100% 매칭 목표

```
모든 PokerGO 에피소드는 NAS archive와 매칭 가능함
```

- **전제**: 모든 PokerGO 콘텐츠는 NAS archive에 존재
- **미매칭 원인**: 매칭 규칙 부족 또는 패턴 미인식
- **목표**: 규칙 추가/개선을 통해 100% 매칭 달성

---

## 1. 파일 필터링 규칙

### 제외 조건

| 조건 | 기준 | 플래그 |
|------|------|--------|
| 파일 크기 | < 1GB | `is_excluded=True` |
| 영상 길이 | < 30분 | `is_excluded=True` |
| 키워드 | `clip`, `highlight`, `circuit`, `paradise` | `is_excluded=True` |
| Hand Clip | `^\d+-wsop-`, `-hs-`, `hand_` | `is_excluded=True` |

**중요**: 제외 파일도 DB에 저장됨 (DUPLICATE 감지에서만 제외)

### 확장자 우선순위

| 순위 | 확장자 | 용도 |
|------|--------|------|
| 1 | .mp4 | 방송/배포용 |
| 2 | .mov | 편집용 |
| 3 | .mxf | 아카이브용 |
| 4+ | .avi, .mkv, .wmv, .m4v | 기타 |

---

## 2. 패턴 우선순위

| # | 패턴 | 추출 정보 | 파일 수 |
|---|------|----------|---------|
| P0 | `WSOP{YY}_APAC_*` | Year, Region=APAC, Type, Episode | 6 |
| P1 | `WS{YY}_{TYPE}{EP}` | Year, Type, Episode | 30 |
| P2 | `WSOP{YY}_{TYPE}{EP}` | Year, Type, Episode | 89 |
| P3 | `WSOP_{YYYY}_{SEQ}_{TYPE}{EP}` | Year, Type, Episode | 2 |
| P4 | `WSOPE{YY}_Episode_{EP}` | Year, Region=EU, Episode | 28 |
| P5 | `{YYYY} World Series...Main Event Show` | Year, Type=ME, Episode | 16 |
| P6 | `{YYYY} WSOP Show {##} ME {##}` | Year, Type=ME, Episode | 10 |
| P7 | `WSOP {YYYY} Show {##} ME {##}` | Year, Type=ME, Episode | 29 |
| P8 | `{YYYY} WSOP ME{##}` | Year, Type=ME, Episode | 56 |
| P9 | `wsop-{yyyy}-me-*` | Year, Type=ME | 20 |
| P10 | Folder year + filename | Year + partial | 341 |

> 상세 예시: [MATCHING_PATTERNS_DETAIL.md](MATCHING_PATTERNS_DETAIL.md#패턴-상세-예시)

---

## 3. Era 분류

| Era | 연도 | 특징 |
|-----|------|------|
| **CLASSIC** | 1973-2002 | 아날로그 촬영, 연도당 Main Event 1개 |
| **BOOM** | 2003-2010 | ESPN 중계, Day/Show 구조 |
| **HD** | 2011-2025 | HD 제작, PokerGO 스트리밍 |

```python
def get_era(year: int) -> str:
    if year <= 2002: return 'CLASSIC'
    elif year <= 2010: return 'BOOM'
    else: return 'HD'
```

---

## 4. Event Type

### 타입 약어

| 약어 | 전체명 | 설명 |
|------|--------|------|
| ME | Main Event | 메인 이벤트 |
| BR | Bracelet | 브레이슬릿 이벤트 |
| HR | High Roller | 하이 롤러 |
| HU | Heads Up | 헤즈업 |
| GM | Grudge Match | 그러지 매치 |
| FT | Final Table | 파이널 테이블 |
| PPC | Players Poker Championship | 별도 대회 |

### 타입 감지 키워드

| 키워드 | 감지 타입 |
|--------|----------|
| `main event`, `_ME` | main_event |
| `grudge`, `_GM` | grudge_match |
| `heads up`, `_HU` | heads_up |
| `bracelet` | bracelet |
| `high roller` | high_roller |
| `_PPC` | ppc (별도 대회) |

### Generic Title 금지 규칙 (CRITICAL)

> **"Event" / "Bracelet Event"는 사용 금지. 모든 타이틀에 구체적 이벤트명 필수.**

| 금지 | 허용 | 설명 |
|------|------|------|
| `Event` | `Main Event` | 단독 "Event" 사용 금지 |
| `Bracelet Event` | `Event #1 $5K NLH` | 이벤트 번호 + 이름 |
| `Bracelet Event \| Day 1` | `€50K Diamond High Roller \| Day 1` | 구체적 이벤트명 |

**타이틀 생성 우선순위**:
1. `Event #{num} {event_name}` - 이벤트 번호 + 이름
2. `Event #{num}` - 이벤트 번호만 (이름 없는 경우)
3. `{event_name}` - 이름만 (번호 없는 경우)
4. `{filename[:40]}` - 최후 fallback (파일명 앞부분)

**Day 중복 방지**:
- event_name에 "Day" 포함 시 day_display 추가 스킵
- 예: `$250K Super High Roller - Day 3` → Day 3 추가 안 함 ✅
- 예: `$25K High Roller` → `| Day 2` 추가 ✅

**구현**: `generate_title()` 함수에서 generic fallback 제거, Day 중복 체크

### 바이인 없는 이벤트 처리

> **Tournament of Champions 등 초청 이벤트는 바이인($) 없이 이벤트명만 존재**

| 케이스 | 예시 파일명 | 추출 결과 |
|--------|-------------|----------|
| 바이인 있음 | `Event #44 - $10,000 H.O.R.S.E. Championship` | `$10,000 H.O.R.S.E. Championship` |
| 바이인 없음 | `Event #89 - WSOP Tournament of Champions` | `WSOP Tournament of Champions` |

**구현**: 바이인 금액(`$XXX`)을 선택적(optional) 패턴으로 처리

```python
# $ 금액은 선택적 - Tournament of Champions 등 처리
r'Event #\d+\s*-\s*((?:\$[\d,.]+[KM]?\s+)?.+?)(?:\s+Final Table|\.mp4|$)'
```

---

## 5. Region

### 지역 코드

| 약어 | 전체명 | 파일명 패턴 |
|------|--------|------------|
| LV (기본) | Las Vegas | `WSOP`, `WS` |
| EU | Europe | `WSOPE`, `wsope-` |
| APAC | Asia Pacific | `WSOP_APAC` |
| PARADISE | Bahamas | `PARADISE` |
| CYPRUS | Cyprus | `CYPRUS` |
| LONDON | London | `LONDON` |
| LA | Los Angeles Circuit | `WCLA` |

### PokerGO 지역별 데이터 가용성

| 지역 | PokerGO 데이터 | 매칭 결과 |
|------|---------------|----------|
| **LV** | ✅ 있음 (1973-2025) | MATCHED |
| **EU** | ⚠️ 일부 (2008-2012) | MATCHED / NAS_ONLY |
| **APAC** | ❌ 없음 | NAS_ONLY_MODERN |
| **PARADISE** | ❌ 없음 | NAS_ONLY_MODERN |
| **CYPRUS** | ❌ 없음 | NAS_ONLY_MODERN |
| **LONDON** | ❌ 없음 | NAS_ONLY_MODERN |
| **LA** | ❌ 없음 | NAS_ONLY_MODERN |

### WSOPE 파일명 패턴

> **wsope-{YYYY}-{buyin}-{event}-ft-{seq}.mp4**

WSOP Europe 파일은 하이픈 구분자 기반 명명 규칙 사용.

| 요소 | 예시 | 설명 |
|------|------|------|
| `wsope` | `wsope` | WSOP Europe 접두사 (고정) |
| `YYYY` | `2021` | 연도 |
| `buyin` | `10k`, `25k`, `1650` | 바이인 금액 (K 또는 숫자) |
| `event` | `me`, `nlh6max`, `platinumhighroller` | 이벤트 타입 |
| `ft` | `ft` | Final Table (고정) |
| `seq` | `001`, `004`, `009` | 시퀀스 번호 |

**파일명 예시**:
```
wsope-2021-10k-me-ft-004.mp4          → €10K Main Event
wsope-2021-10k-nlh6max-ft-009.mp4     → €10K NLH 6-Max
wsope-2021-1650-nlh6max-ft-010.mp4    → €1,650 NLH 6-Max
wsope-2021-25k-platinumhighroller-ft-001.mp4 → €25K Platinum High Roller
```

**FT 충돌 없음**: `ft`는 하이픈 구분자 내 고정 위치 (`{event}-ft-{seq}`)로 Day FT 패턴과 분리 처리.

---

## 6. Asset Grouping

### Group ID 생성

```
{연도}_{지역}_{타입}_{에피소드} (LV는 기본이므로 제외)
```

| 예시 | 설명 |
|------|------|
| `2011_ME_25` | WSOP 2011 Main Event Episode 25 (LV) |
| `2011_EU_01` | WSOP Europe 2011 Episode 1 |
| `2013_APAC_ME_01` | WSOP APAC 2013 Main Event Episode 1 |
| `1973_ME` | WSOP 1973 Main Event (CLASSIC Era) |

### Primary/Backup 결정

**Backup 조건** (아래 중 하나):
- 파일명 동일 (확장자만 다름) + 크기 동일
- 분석 결과 동일 (연도+지역+이벤트+에피소드)

**Primary 우선순위**:
1. 정제 키워드 (`nobug`, `clean`, `final`)
2. 복사 표시 없음 (`(1)` 패턴 없음)
3. 확장자 우선순위 (mp4 > mov > mxf)

### GOG (Game of Gold) 버전 우선순위

> **2023 GOG 파일 전용 규칙. 각 에피소드에서 최고 우선순위 버전 1개 = PRIMARY.**

| 우선순위 | 버전 키워드 | 설명 |
|---------|------------|------|
| 4 (최고) | `찐최종` | 최종 확정본 |
| 3 | `최종` | 최종본 |
| 2 | (표기없음) | 작업본 |
| 1 (최저) | `클린본` | 클린 버전 |

**Role 결정**:
- 각 에피소드별 최고 우선순위 1개 = **PRIMARY** (Title: `Episode X`)
- 나머지 = **BACKUP** (Title: `Episode X (버전)`)

**적용 예시**:
```
Episode 11:  (찐최종 보유)
  ★ E11_GOG_final_edit_20231203_찐최종.mp4  → PRIMARY  Title: Episode 11
    E11_GOG_final_edit_클린본_20231201.mp4  → BACKUP   Title: Episode 11 (클린본)

Episode 2:  (최종이 최고 우선순위)
  ★ E02_GOG_final_edit_20231113_최종.mp4    → PRIMARY  Title: Episode 2
    E02_GOG_final_edit_클린본_20231031.mp4  → BACKUP   Title: Episode 2 (클린본)

Episode 1:  (작업본이 최고 우선순위)
  ★ E01_GOG_final_edit_231106.mp4          → PRIMARY  Title: Episode 1
    E01_GOG_final_edit_클린본.mp4           → BACKUP   Title: Episode 1 (클린본)
```

**구현**: 에피소드별 그룹화 후 최고 우선순위 선택

### Origin/Archive 관계

| 저장소 | 드라이브 | 용도 |
|--------|----------|------|
| **Origin** | Y: | 원본 보관 (불변) |
| **Archive** | Z: | 아카이브 백업 (Origin ⊆ Archive) |

| 상태 | Origin | Archive | 의미 |
|------|--------|---------|------|
| `BOTH` | ✓ | ✓ | 정상 |
| `ARCHIVE_ONLY` | ✗ | ✓ | 정상 (추가 영상) |
| `ORIGIN_ONLY` | ✓ | ✗ | **CRITICAL** - 백업 필요 |

---

## 7. 매칭 규칙 (v5.0)

### 7.1 Region 매칭 (CRITICAL)

```python
NON_LV_REGIONS = ('EU', 'APAC', 'PARADISE', 'CYPRUS', 'LA', 'LONDON')

if region_code in NON_LV_REGIONS:
    if region_code == 'EU' and not ep_is_europe:
        continue  # EU 그룹 → Europe 에피소드만
    elif region_code == 'APAC' and not ep_is_apac:
        continue  # APAC 그룹 → APAC 에피소드만
elif region_code == 'LV' and ep_is_regional:
    continue  # LV 그룹 → 비지역 에피소드만
```

### 7.2 Episode 매칭 (CRITICAL)

```python
# Episode 불일치 스킵
if ep_episode and group.episode:
    if ep_episode != group.episode:
        continue  # Episode 25 ≠ Episode 2

# Episode-less 그룹 제한 (2003년 이후)
if not group.episode and ep_episode and group.year >= 2003:
    continue  # episode 없는 그룹 → episode 타이틀 매칭 안 함
```

### 7.3 Event Type 매칭

```python
# GM/HU → Main Event 매칭 방지
if event_type_code == 'GM' and is_main_event_title:
    continue
elif event_type_code == 'HU' and is_main_event_title:
    continue

# Event Type 없는 그룹 → Bracelet Event 매칭 방지
if not event_type_code:
    is_bracelet_event = re.search(r'wsop\s+\d{4}\s+\d{2}\s+', title_lower)
    if is_bracelet_event and not is_main_event_title:
        continue
```

### 7.4 DUPLICATE 감지

```python
def detect_duplicates(pokergo_to_files, file_to_group):
    """Group 기반 중복 감지"""
    duplicates = {}

    for title, files in pokergo_to_files.items():
        if len(files) <= 1:
            continue

        # 제외된 파일 필터링
        unique_groups = set()
        for f in files:
            if not f.is_excluded:  # v5.0: 제외 파일은 DUPLICATE 감지 제외
                group = file_to_group.get(f)
                if group:
                    unique_groups.add(group.group_id)

        if len(unique_groups) > 1:
            duplicates[title] = {'groups': list(unique_groups)}

    return duplicates
```

---

## 8. Match Category

| Category | 조건 | 의미 |
|----------|------|------|
| **MATCHED** | PokerGO 매칭 성공 | 정상 |
| **NAS_ONLY_HISTORIC** | 매칭 실패 + Era ≤ BOOM | 히스토릭 콘텐츠 |
| **NAS_ONLY_MODERN** | 매칭 실패 + Era = HD | 모던 콘텐츠 |
| **DUPLICATE** | 동일 PokerGO에 여러 그룹 매칭 | 규칙 확인 필요 |

---

## 9. CLASSIC Era 특수 규칙

**1973-2002 연도 기반 자동 매칭**:

```python
# CLASSIC Era는 연도만으로 Main Event 자동 매칭
if era == 'CLASSIC' and event_type == 'ME':
    # 에피소드 번호 없이 연도만으로 매칭
    # "Wsop 1973" ↔ NAS 1973 파일
```

**예외 처리**:
- PokerGO에 단일 타이틀만 존재 (예: "Wsop 2002 Main Event")
- NAS에 Part 1, Part 2 등 복수 콘텐츠 존재
- **해결**: Catalog Title 생성 (예: "Wsop 2002 Main Event Part 1")

### 9.1 CLASSIC Era Primary/Backup 그룹핑 (v5.8)

**BACKUP 파일 패턴**:
| 패턴 | 예시 | 설명 |
|------|------|------|
| `nobug` | `wsop-1973-me-nobug.mp4` | 버그 수정된 저용량 버전 |
| `VHS DUB` | `1995 WSOP VHS DUB.mov` | VHS 복사본 |

**그룹핑 규칙**:
```python
# 1. 그룹 내 유일한 파일 → PRIMARY
if len(group_files) == 1:
    return 'PRIMARY'

# 2. nobug/VHS DUB 패턴 → BACKUP
if 'nobug' in filename.lower() or 'vhs dub' in filename.lower():
    return 'BACKUP'

# 3. 용량 큰 파일 → PRIMARY (동일 그룹 내)
# 예: WSOP_1983.mov (72GB) = PRIMARY
#     WSOP_1983.mxf (17GB) = BACKUP
#     wsop-1983-me-nobug.mp4 (3GB) = BACKUP
```

**Part 분리**:
| 파일명 패턴 | 예시 | 그룹 |
|------------|------|------|
| `Part X` | `2002 World Series of Poker Part 1.mov` | `WSOP_2002_ME_P1` |
| `WSOP_YYYY_X` | `WSOP_2002_1.mxf` | `WSOP_2002_ME_P1` |

**2002년 예시**:
| 파일명 | Part | Role | 용량 |
|--------|------|------|------|
| `2002 World Series of Poker Part 1.mov` | 1 | PRIMARY | 92GB |
| `WSOP_2002_1.mxf` | 1 | BACKUP | 18GB |
| `2002 World Series of Poker Part 2.mov` | 2 | PRIMARY | 94GB |
| `WSOP_2002_2.mxf` | 2 | BACKUP | 18GB |

### 9.2 2004년 특수 규칙 (v5.10)

> **수작업 예정**: 메타데이터 작업 시 전면 수정 예정

**폴더별 처리:**
| 폴더 | 파일 수 | 처리 |
|------|---------|------|
| `Bracelet Event` | 6 | TOC EP01-06 (모두 PRIMARY) |
| `Generics(No Graphic)` | 26 | ME/BR/기타 분류 |
| `MXFs (master)` | 23 | 모두 BACKUP |

**분류 규칙:**
```python
# Show 13-22 + ME → Main Event Episode
if 'ME' in event_name:
    return 'WSOP_ME', episode_num

# Show 1-12 → Bracelet Event
elif show_num <= 12:
    return 'WSOP_BR', show_num

# Tournament of Champions Generic → BACKUP
elif 'generic' in filename.lower():
    return 'WSOP_TOC_GENERIC', role='BACKUP'

# 기타 → 파일명 그대로 출력
```

**특수 케이스:**
| 케이스 | 처리 |
|--------|------|
| Show 3 (이름없음) | `(noName)` 표기 |
| Show 4, 5 | mxf만 존재 → BACKUP |
| TOC Generic 3개 | BACKUP |

---

### 9.3 2003년 특수 규칙 (Moneymaker Year) (v5.9)

**파일 분류:**
| 유형 | 패턴 | 설명 |
|------|------|------|
| `WSOP_ME` | `WSOP_2003-XX.mxf` | Main Event Episode 1-7 |
| `WSOP_ME_FT` | `Final Table` 포함 | Final Table |
| `WSOP_BEST` | `Best of` 또는 `Best_Of` 포함 | 컴필레이션 |

**Best Of 주제 정규화:**
```python
TOPIC_NORMALIZE = {
    'all ins': 'All-Ins',
    'amazing all-ins': 'All-Ins',
    'bluffs': 'Bluffs',
    'best bluffs': 'Bluffs',
    'amazing bluffs': 'Bluffs',
    'moneymaker': 'Moneymaker',
    'memorable moments': 'Memorable Moments',
}
```

**그룹핑:**
| 그룹 | Entry Key | 파일 수 |
|------|-----------|---------|
| ME Episode 1-6 | `WSOP_2003_ME_EP{N}` | 각 1개 |
| ME Episode 7 | `WSOP_2003_ME_EP7` | 1개 |
| ME Episode 7 (text) | `WSOP_2003_ME_EP7_TEXT` | 1개 (별도 PRIMARY) |
| Final Table | `WSOP_2003_ME_FT` | 1개 |
| Best Of: [Topic] | `WSOP_2003_BEST_{Topic}` | 2개 (mov+mxf) |

**확장자 우선순위 적용:**
- Best Of: mov (PRIMARY) > mxf (BACKUP)
- "text" 버전: 별도 그룹으로 분리, 둘 다 PRIMARY

### 9.4 2005년 특수 규칙 (v5.11)

**파일 구조 (75개):**
| 유형 | 패턴 | 파일 수 |
|------|------|---------|
| Show mov | `WSOP 2005 Show {N} ...` | 33 |
| Show mxf | `WSOP_2005_{NN}.mxf` | 32 |
| TOC | `Tournament of Champs` | 3 |
| Circuit | Lake Tahoe, Rio, Rincon, New Orleans | 5 |
| EOE | `EOE Final Table` | 1 |
| Best Of | `Best Hand Ever Played` | 1 |

**Show 매핑:**
- **Shows 7-20**: Bracelet Events (BR)
- **Shows 21-32**: Main Event Episodes 1-12 (ME)
- **Shows 1-6**: mxf만 존재 (mov 없음)

**버전 우선순위:**
```python
VERSION_PRIORITY = {
    'master': 1,   # Master 버전 (최고 품질)
    'plain': 2,    # 일반 버전
    'generic': 3,  # Generic 버전 (그래픽 없음)
    'mxf': 4       # MXF 아카이브
}
```

**그룹핑 규칙:**
| 조건 | PRIMARY | BACKUP |
|------|---------|--------|
| Master + Generic + mxf | Master | Generic, mxf |
| Plain + mxf | Plain | mxf |
| mxf only (Show 1-6) | mxf | - |

**그룹 ID 생성:**
```python
# Show 기반 그룹핑
if ME_SHOW_START <= show_num <= ME_SHOW_END:
    group_id = f'WSOP_2005_ME_S{show_num}'
else:
    group_id = f'WSOP_2005_BR_S{show_num}'
```

**TOC 에피소드 분리:**
- 각 TOC 파일은 다른 ES 코드 → 다른 에피소드
- EP01, EP02, EP03 각각 PRIMARY

**결과:**
| 유형 | PRIMARY | BACKUP |
|------|---------|--------|
| WSOP_ME | 12 | 4 |
| WSOP_BR | 14 | 3 |
| WSOP_TOC | 3 | 0 |
| WSOP_CIRCUIT | 5 | 0 |
| WSOP_EOE | 1 | 0 |
| WSOP_BEST | 1 | 0 |
| WSOP_MXF | 6 | 26 |
| **합계** | **42** | **33** |

---

## 10. 수작업 필요 항목

| 유형 | 건수 | 이유 | 해결 방안 |
|------|------|------|----------|
| HU/GM episode-less | 4 | 대전자 이름으로만 구분 | 영상 확인 후 수동 지정 |
| Day-based (2007) | 8 | ESPN Show vs PokerGO Day 불일치 | 수동 매핑 |
| CLASSIC Era | 3 | 연도당 단일 타이틀 | 그룹 통합 |

---

## 변경 이력 (주요)

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 5.11 | 2025-12-18 | 2005년 특수 규칙 추가 (Show 기반 그룹핑, 버전 우선순위) |
| 5.10 | 2025-12-18 | 2004년 특수 규칙 추가 (폴더 기반 분류, TOC/MXF BACKUP) |
| 5.9 | 2025-12-18 | 2003년 특수 규칙 추가 (Best Of 주제 정규화, text 버전 분리) |
| 5.8 | 2025-12-18 | CLASSIC Era Primary/Backup 그룹핑 규칙 추가 (nobug, VHS DUB, Part) |
| 5.7 | 2025-12-18 | WSOPE 파일명 패턴 규칙 추가 (ft = Final Table) |
| 5.6 | 2025-12-18 | 바이인 없는 이벤트 처리 (Tournament of Champions 등) |
| 5.5 | 2025-12-18 | GOG 규칙: 에피소드별 최고 우선순위 = PRIMARY (12개 에피소드 각 1개) |
| 5.4 | 2025-12-18 | GOG 규칙 수정: 찐최종만 PRIMARY, 나머지 BACKUP + Title 버전 표기 |
| 5.3 | 2025-12-18 | GOG 버전 우선순위 규칙 추가 (찐최종 > 최종 > 클린본) |
| 5.2 | 2025-12-18 | Day 중복 방지 규칙 추가 (event_name에 Day 포함 시 스킵) |
| 5.1 | 2025-12-18 | Generic Title 금지 규칙 추가, Day 추출 버그 수정 |
| 5.0 | 2025-12-17 | Region/Episode 매칭 강화, DUPLICATE 53→18 감소 |
| 4.0 | 2025-12-17 | DUPLICATE 완전 해결 (374→0), LV 기본 지역 적용 |
| 3.0 | 2025-12-16 | Era 분류, Origin/Archive 관계 정립, 4시트 시스템 |
| 2.0 | 2025-12-15 | 11개 패턴 정의 (767개 파일 분석 기반) |

> 전체 변경 이력: [MATCHING_PATTERNS_DETAIL.md](MATCHING_PATTERNS_DETAIL.md#변경-이력)
