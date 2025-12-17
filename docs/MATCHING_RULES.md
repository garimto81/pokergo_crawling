# NAS-PokerGO 매칭 규칙

NAS 파일과 PokerGO 콘텐츠 매칭 및 Asset Grouping 규칙 정의서.

**Version**: 5.0 | **Date**: 2025-12-17

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
| 5.0 | 2025-12-17 | Region/Episode 매칭 강화, DUPLICATE 53→18 감소 |
| 4.0 | 2025-12-17 | DUPLICATE 완전 해결 (374→0), LV 기본 지역 적용 |
| 3.0 | 2025-12-16 | Era 분류, Origin/Archive 관계 정립, 4시트 시스템 |
| 2.0 | 2025-12-15 | 11개 패턴 정의 (767개 파일 분석 기반) |

> 전체 변경 이력: [MATCHING_PATTERNS_DETAIL.md](MATCHING_PATTERNS_DETAIL.md#변경-이력)
