# 매칭 전략 분석 보고서

**분석일**: 2025-12-17
**상태**: 패턴 엔진 미실행 (year/region/event_type 모두 NULL)

---

## 1. 현재 상태 요약

### 1.1 데이터 현황

| 항목 | 개수 | 비고 |
|------|------|------|
| **NAS 전체 파일** | 1,621 | |
| **제외된 파일** | 543 | clip, hand, circuit, <1GB 등 |
| **유효 파일** | 1,078 | 매칭 대상 |
| **패턴 매칭됨** | 0 | 패턴 엔진 미실행 |

### 1.2 데이터 소스

| 소스 | 개수 | 특징 |
|------|------|------|
| **wsop_final.json** | 828 | WSOP 전용, CLASSIC Era 포함 |
| **pokergo_episodes** | 1,131 | National Heads-Up 등 포함 |
| **WSOP 관련만** | 631 | DB 필터링 결과 |

---

## 2. NAS 파일 패턴 분석

### 2.1 패턴별 분포

| 우선순위 | 패턴 | 개수 | 매칭 가능성 | 예시 |
|----------|------|------|-------------|------|
| **P1** | `WSOP_YYYY_ME` | 274 | 높음 | `WSOP 2025 Bracelet Events | Event #13...` |
| **P2** | `YEAR_WSOP` | 204 | 높음 | `1987 World Series of Poker 1.mov` |
| **P3** | `WSOP_YY_TYPE` | 89 | 높음 | `WSOP13_ME01_NB.mp4` |
| **P4** | `WSOPE_YYYY` | 32 | 중간 | `WSOPE08_Episode_1_H264.mov` |
| **P5** | `WS_YY_TYPE` | 30 | 높음 | `WS11_GM01_NB.mp4` |
| **P6** | `OTHER` | 435 | 낮음 | 다양한 패턴 혼재 |
| **P7** | `DOLLAR_PREFIX` | 11 | 중간 | `$1M GTD $1K PokerOK Mystery Bounty...` |
| **P8** | `NUMERIC_PREFIX` | 3 | 중간 | `1003_WSOPE_2024_50K DIAMOND...` |

### 2.2 OTHER 카테고리 상세 분석 (435개)

| 하위 패턴 | 개수 | 예시 | 전략 |
|-----------|------|------|------|
| `other_misc` | 205 | `WSOP_1983.mov` | 연도 추출 + CLASSIC Era 매칭 |
| `WSOP_YYYY_` | 116 | `WSOP_2000_Jesus_Wins1.mxf` | 연도 추출 |
| `WSOP_YYYY_Show` | 64 | `WSOP 2005 Show 10 2k Limit...` | Show 번호 + ME 번호 추출 |
| `wsop-YYYY-me` | 18 | `wsop-1973-me-nobug.mp4` | 연도 추출 + ME 매칭 |
| `emoji_wsope` | 17 | `🏆 WSOPE 10K PLO Mystery...` | 이모지 제거 후 파싱 |
| `2025_WSOPE` | 10 | `1_2025 WSOPE #10 €10,000...` | 숫자 prefix 제거 후 파싱 |
| `wsope-yyyy` | 4 | `wsope-2021-10k-me-ft-004.mp4` | 소문자 패턴 추가 |
| `WSOP - YYYY` | 1 | `WSOP - 1973.mp4` | 연도 추출 |

---

## 3. PokerGO 에피소드 분석

### 3.1 카테고리별 분포 (WSOP 관련 631개)

| 카테고리 | 개수 | NAS 대응 패턴 |
|----------|------|---------------|
| **Main Event Episode** | 268 | `WSOP_YYYY_ME`, `WS_YY_TYPE` |
| **Bracelet Event** | 292 | `WSOP_YYYY_ME`, `WSOP_YY_TYPE` |
| **Main Event Day/Part** | 53 | `2025 WSOPE`, `emoji_wsope` |
| **Europe** | 2 | **GAP!** NAS에 32개 있음 |
| **APAC** | 0 | **GAP!** NAS에 APAC 파일 있음 |
| **Classic (pre-2003)** | 0 | **GAP!** wsop_final.json 사용 필요 |
| **Other** | 16 | 시즌 헤더 등 |

### 3.2 데이터 GAP

| 항목 | NAS | PokerGO DB | wsop_final.json |
|------|-----|-----------|-----------------|
| **CLASSIC Era (1973-2002)** | ~20개 | 0개 | 20개 |
| **WSOP Europe** | 32개 | 2개 | ? |
| **WSOP APAC** | 6개 | 0개 | 0개 |

---

## 4. 추가 매칭 전략

### 4.1 전략 1: 패턴 엔진 실행 (즉시)

**문제**: 현재 패턴 매칭이 0개 (엔진 미실행)

**해결**:
```powershell
# 패턴 재처리 실행
python scripts/migrate_and_reprocess.py
```

**예상 효과**: 기존 패턴으로 ~500개 이상 추출 가능

### 4.2 전략 2: 정규화 직접 매칭 (높은 효과)

**대상**: `WSOP_YYYY_ME` 패턴 (274개)

**방법**: NAS 파일명과 PokerGO 타이틀을 정규화 후 직접 비교

```python
def normalize(text: str) -> str:
    text = re.sub(r'\.(mp4|mov|mxf)$', '', text, re.I)
    text = text.replace('|', ' ').replace('_', ' ')
    text = re.sub(r'[$€£]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip().lower()
```

**예시**:
```
NAS: "WSOP 2017 Main Event _ Episode 10.mp4"
 ↓ normalize
"wsop 2017 main event episode 10"
 ↓ match
PokerGO: "WSOP 2017 Main Event | Episode 10"
```

**예상 효과**: ~200개 추가 매칭

### 4.3 전략 3: CLASSIC Era 연도 매칭 (20개)

**대상**: 1973-2002년 파일

**방법**: wsop_final.json에서 연도만으로 Main Event 매칭

```python
# CLASSIC Era (연도당 ME 1개이므로 연도만으로 매칭)
if year <= 2002:
    pokergo_match = wsop_final_by_year.get(year)
```

**매칭 예**:
| NAS | PokerGO |
|-----|---------|
| `wsop-1978-me-nobug.mp4` | `Wsop 1978 Main Event` |
| `WSOP_1983.mov` | `Wsop 1983 Main Event` |

**예상 효과**: 20개 완전 매칭

### 4.4 전략 4: 신규 패턴 추가 (필수)

#### 4.4.1 이모지 패턴 (17개)
```regex
🏆\s*(?:€?\d+[,\d]*\s+)?WSOPE?\s+(.+)
```
- 이모지 및 통화 기호 제거
- WSOPE 이벤트명 추출

#### 4.4.2 숫자 prefix 패턴 (10개)
```regex
^\d+_(\d{4})\s+WSOPE?\s+#?(\d+)\s+(.+)
```
- `1_2025 WSOPE #10...` → Year=2025, Event#10

#### 4.4.3 소문자 wsope 패턴 (4개)
```regex
wsope-(\d{4})-(\d+k?)-([a-z0-9]+)-ft-(\d+)
```
- `wsope-2021-10k-me-ft-004.mp4` → Year=2021, Type=ME, Episode=4

#### 4.4.4 WSOP Show 패턴 (64개)
```regex
WSOP\s+(\d{4})\s+Show\s+\d+\s+(.+?)_
```
- `WSOP 2005 Show 10 2k Limit Holdem...` → Year=2005, Type=2k Limit

### 4.5 전략 5: Fuzzy Matching (중간 효과)

**대상**: 정규화 후에도 매칭되지 않는 파일

**방법**: Levenshtein 거리 기반 유사도 매칭

```python
from rapidfuzz import fuzz

def fuzzy_match(nas_title: str, pokergo_titles: list) -> str:
    best = max(pokergo_titles, key=lambda t: fuzz.ratio(nas_title, t))
    score = fuzz.ratio(nas_title, best)
    return best if score > 70 else None
```

**임계값**: 70% 이상

### 4.6 전략 6: 수동 매칭 테이블 (마지막 수단)

**대상**: 자동 매칭 불가능한 특수 케이스

**예시**:
| NAS | PokerGO | 이유 |
|-----|---------|------|
| `WS11_GM01_NB.mp4` | Moneymaker vs Farha | Grudge Match 대전자 식별 필요 |
| `WS11_GM02_NB.mp4` | Chan vs Hellmuth | 영상 확인 필요 |

---

## 5. 구현 우선순위

| 순위 | 전략 | 예상 효과 | 구현 난이도 | 대상 파일 수 |
|------|------|----------|-------------|-------------|
| **1** | 패턴 엔진 실행 | +500 | 낮음 | 1,078 |
| **2** | 정규화 직접 매칭 | +200 | 낮음 | 274 |
| **3** | CLASSIC Era 연도 | +20 | 낮음 | 20 |
| **4** | 신규 패턴 추가 | +100 | 중간 | 95 |
| **5** | Fuzzy Matching | +50 | 중간 | 200 |
| **6** | 수동 매칭 | +20 | 높음 | 20 |

---

## 6. 예상 최종 매칭률

| 단계 | 누적 매칭 | 매칭률 |
|------|----------|--------|
| 현재 | 0 | 0% |
| 패턴 엔진 실행 후 | 500 | 46% |
| 정규화 매칭 후 | 700 | 65% |
| CLASSIC Era 후 | 720 | 67% |
| 신규 패턴 후 | 820 | 76% |
| Fuzzy Matching 후 | 870 | 81% |
| 수동 매칭 후 | 890 | **83%** |

**최종 미매칭 예상**: ~188개 (주로 PokerGO에 없는 콘텐츠)

---

## 7. 다음 단계

1. **즉시**: `python scripts/migrate_and_reprocess.py` 실행
2. **단기**: 정규화 매칭 로직 구현 (`matching_v2.py`)
3. **중기**: 신규 패턴 DB 추가 (`init_db.py`)
4. **장기**: Fuzzy Matching 및 수동 매칭 테이블 구축

---

## 부록: 미매칭 예상 콘텐츠

PokerGO에 메타데이터가 없을 것으로 예상되는 콘텐츠:

1. **WSOP APAC** (6개) - PokerGO DB에 없음
2. **WSOP Paradise** (일부) - 2023-2024 신규 이벤트
3. **Best Of 시리즈** - 컴필레이션 영상
4. **Raw Recording** - 방송 전 원본
5. **Regional variants** - 특정 지역 방송판
