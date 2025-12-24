# NAMS DB 데이터 현황 분석 리포트

**생성일**: 2025-12-17
**DB 경로**: `D:\AI\claude01\pokergo_crawling\src\nams\data\nams.db`

---

## 요약

| 항목 | 수량 | 상태 |
|------|------|------|
| **전체 파일** | 1,621개 | - |
| **활성 파일** | 1,078개 | 제외 파일 543개 |
| **PokerGO 에피소드** | 1,131개 | - |
| **Asset Groups** | 716개 | **NAS 파일과 연결 0개** |
| **패턴 매칭율** | 0% | **심각한 문제** |

---

## 1. NAS Files 현황

### 1.1 기본 통계

```
전체 파일 수: 1,621
제외된 파일 수: 543
활성 파일 수: 1,078
```

### 1.2 역할별 분포 (활성 파일만)

| 역할 | 파일 수 |
|------|---------|
| backup | 857 |
| pokergo_source | 221 |

### 1.3 확장자별 분포 (Top 10)

| 확장자 | 파일 수 |
|--------|---------|
| .mp4 | 695 |
| .mov | 269 |
| .mxf | 114 |

### 1.4 **심각한 문제: 패턴 매칭 실패**

```
그룹 할당 현황:
  Ungrouped: 1,078 (100%)

패턴 매칭 현황:
  No Pattern Match: 1,078 (100%)

메타데이터 추출 현황:
  패턴 매칭됨: 0 (0.0%)
  연도 추출됨: 99 (9.2%)
  지역 추출됨: 0 (0.0%)
  이벤트 타입 추출됨: 0 (0.0%)
  에피소드 추출됨: 0 (0.0%)
```

**원인**:
- 18개 패턴이 DB에 등록되어 있음
- 하지만 패턴 엔진이 실행되지 않았거나 실패함
- 전체 경로 매칭이 필요한데 파일명만 매칭 시도했을 가능성

**샘플 파일 경로**:
```
Z:\ARCHIVE\MPP\2025 MPP Cyprus\$1M GTD   $1K PokerOK Mystery Bounty\$1M GTD   $1K PokerOK Mystery Bounty – Day 1A.mp4
```

**등록된 패턴 (샘플)**:
```
[1] WSOP_BR_LV_2025_ME (ME) - 활성
[2] WSOP_BR_LV_2025_SIDE (BR) - 활성
[3] WSOP_BR_EU_2025 (N/A) - 활성
[4] WSOP_BR_EU (N/A) - 활성
[5] WSOP_BR_PARADISE (N/A) - 활성
[6] WSOP_BR_LV (N/A) - 활성
...
```

---

## 2. PokerGO Episodes 현황

```
전체 에피소드 수: 1,131
```

### 2.1 컬렉션별 분포 (Top 10)

| 컬렉션 | 에피소드 수 |
|--------|-------------|
| High Stakes Poker | 198 |
| No Gamble, No Future | 124 |
| WSOP 2024 | 110 |
| National Heads-Up Poker Championship | 99 |
| WSOP 2025 | 70 |
| WSOP 2021 | 52 |
| WSOP 2023 | 51 |
| WSOP 2022 | 51 |
| WSOP 2019 | 44 |
| WSOP | World Series of Poker | 32 |

---

## 3. Asset Groups 현황

```
전체 그룹 수: 716
```

### 3.1 PokerGO 매칭 현황

| 상태 | 그룹 수 |
|------|---------|
| Matched | 149 |
| Unmatched | 567 |

### 3.2 백업 존재 현황

| 상태 | 그룹 수 |
|------|---------|
| Has Backup | 36 |
| No Backup | 680 |

### 3.3 매치 카테고리별 분포

| 카테고리 | 그룹 수 |
|----------|---------|
| MATCHED | 409 |
| NAS_ONLY_HISTORIC | 307 |

### 3.4 매치 스코어 분포 (매칭된 그룹만)

| 스코어 범위 | 그룹 수 | 평균 |
|-------------|---------|------|
| Bad (<60) | 149 | 1.0 |

**문제점**:
- 매치 스코어가 1점으로 거의 의미 없는 수준
- PokerGO 에피소드와 정확한 매칭이 이루어지지 않음

### 3.5 **심각한 문제: NAS 파일과 연결 0개**

```
asset_group_id로 연결된 파일 수: 0
미연결 파일 수: 1,078
```

**Asset Groups 샘플**:
```
[1973 N/A ME EPN/A] WSOP 1973 Main Event - 1개 파일, 미매칭
[1973 N/A UNK EPN/A] WSOP 1973 Unknown - 1개 파일, 미매칭
[1978 N/A ME EPN/A] WSOP 1978 Main Event - 1개 파일, 미매칭
[1979 N/A ME EPN/A] WSOP 1979 Main Event - 1개 파일, 미매칭
[1981 N/A ME EPN/A] WSOP 1981 Main Event - 1개 파일, 미매칭
```

**PokerGO 매칭 샘플** (스코어 1점):
```
[1점] WSOP 2011 Bracelet Events | Heads-Up Grudge Match
  컬렉션: WSOP 2011
  그룹 제목: WSOP 2011 Grudge Match | Episode 1

[1점] WSOP 2011 Main Event | Episode 1
  컬렉션: WSOP 2011
  그룹 제목: WSOP 2011 Main Event | Episode 1
```

---

## 4. 미그룹화 파일 패턴 분석

```
미그룹화 파일 수: 1,078 (100%)
```

### 4.1 패턴별 분포

| 패턴 | 파일 수 | 샘플 |
|------|---------|------|
| WSOP Other - .mp4 | 359 | `WSOP - 1973.mp4` |
| WSOP Other - .mov | 222 | `WSOP_1983.mov` |
| Video (Unknown) - .mp4 | 179 | `$1M GTD $1K PokerOK Mystery Bounty – Day 1A.mp4` |
| WSOP ME - .mp4 | 149 | `WSOP 2006 Show 17 ME 7_GMPO 743-FULL EPISODE.mp4` |
| WSOP Other - .mxf | 98 | `WSOP_1981_-_Stu_Unger_Video.mxf` |
| WSOP ME - .mov | 38 | `2004 WSOP Show 13 ME 01_ESM000100900.mov` |
| Other - .mxf | 16 | `2016 World Series of Poker - Main Event Show 01 - GMPO 2074.mxf` |
| Video (Unknown) - .mov | 9 | `1987 World Series of Poker 1.mov` |
| WSOP APAC - .mp4 | 6 | `WSOP13_APAC_ME01_NB.mp4` |
| WSOP EU - .mp4 | 2 | `WSOP Europe 2009 Bracelet Events...` |

---

## 5. 미매칭 그룹 분석 (샘플 20개)

```
[2025 N/A N/A EPN/A] WSOP 2025 (0개 파일)
[2025 N/A FT EPN/A] WSOP 2025 Final Table (0개 파일)
[2025 EU N/A EPN/A] WSOP Europe 2025 (10개 파일)
[2024 N/A HR EPN/A] WSOP 2024 High Roller (0개 파일)
[2024 N/A FT EPN/A] WSOP 2024 Final Table (0개 파일)
[2024 N/A N/A EPN/A] WSOP 2024 (0개 파일)
[2024 EU N/A EPN/A] WSOP Europe 2024 (4개 파일)
[2024 EU FT EP1] WSOP Europe 2024 Final Table | Episode 1 (0개 파일)
[2024 PARADISE N/A EP1] WSOP Paradise 2024 Main Event | Episode 1 (3개 파일)
[2024 PARADISE N/A EP2] WSOP Paradise 2024 Main Event | Episode 2 (1개 파일)
```

---

## 6. 진단 요약

### 6.1 주요 문제점

| 번호 | 문제 | 심각도 |
|------|------|--------|
| 1 | **패턴 매칭 0%** | 🔴 Critical |
| 2 | **NAS 파일 그룹핑 전무** | 🔴 Critical |
| 3 | **메타데이터 추출 전무** | 🔴 Critical |
| 4 | PokerGO 매칭 스코어 1점 | 🟡 Major |
| 5 | 567개 그룹 미매칭 | 🟡 Major |

### 6.2 근본 원인

1. **패턴 엔진 미실행**
   - 18개 패턴이 DB에 등록되어 있음
   - 하지만 `pattern_engine.py`가 NAS 파일에 적용되지 않음
   - `matched_pattern_id`가 모두 NULL

2. **그룹핑 미실행**
   - 716개 Asset Groups는 PokerGO 에피소드만 기준으로 생성됨
   - NAS 파일 기준 그룹핑이 실행되지 않음
   - `create_asset_groups.py` 미실행

3. **매칭 로직 문제**
   - PokerGO 매칭 스코어가 1점으로 의미 없음
   - 메타데이터 없이 매칭 시도했을 가능성

### 6.3 데이터 흐름 문제

```
[현재 상태]
NAS 스캔 (1,078 파일) → [패턴 엔진 미실행] → 메타데이터 0개
                                              ↓
                                          그룹핑 불가능
                                              ↓
                                          매칭 불가능

[정상 상태]
NAS 스캔 → 패턴 엔진 실행 → 메타데이터 추출 → 그룹핑 → PokerGO 매칭
```

---

## 7. 권장 조치

### 7.1 즉시 조치 (필수)

1. **패턴 엔진 재실행**
   ```bash
   cd D:/AI/claude01/pokergo_crawling
   python scripts/migrate_and_reprocess.py
   ```
   - 모든 NAS 파일에 패턴 매칭 적용
   - 메타데이터 추출 (year, region, episode 등)

2. **NAS 파일 그룹핑**
   ```bash
   python scripts/create_asset_groups.py
   ```
   - 메타데이터 기반으로 파일 그룹핑
   - Primary/Backup 역할 할당

3. **PokerGO 매칭**
   ```bash
   python scripts/match_pokergo_nas.py
   ```
   - 그룹과 PokerGO 에피소드 매칭
   - 매치 스코어 계산

### 7.2 장기 조치

1. **패턴 개선**
   - 현재 샘플 파일 경로와 패턴 불일치
   - MPP Cyprus, PokerOK Mystery Bounty 등 새 패턴 추가

2. **자동화**
   - NAS 스캔 시 자동으로 패턴 엔진 실행
   - 그룹핑 및 매칭 자동화

3. **모니터링**
   - 패턴 매칭율 추적
   - 미매칭 파일 주기적 검토

---

## 8. 실행 로그

### 8.1 분석 스크립트

- `scripts/analyze_db_status.py`: 기본 현황 분석
- `scripts/analyze_db_detailed.py`: 상세 진단

### 8.2 다음 단계

```bash
# 1. 패턴 엔진 재실행
python scripts/migrate_and_reprocess.py

# 2. 결과 확인
python scripts/analyze_db_status.py

# 3. 그룹핑 실행
python scripts/create_asset_groups.py

# 4. 매칭 실행
python scripts/match_pokergo_nas.py

# 5. 최종 확인
python scripts/analyze_db_detailed.py
```

---

## 9. 기대 결과

조치 후 예상되는 상태:

| 지표 | 현재 | 목표 |
|------|------|------|
| 패턴 매칭율 | 0% | 80%+ |
| 그룹 할당율 | 0% | 95%+ |
| 메타데이터 추출율 | 9.2% | 80%+ |
| PokerGO 매칭 스코어 | 1.0 | 70+ |
| NAS-Group 연결 | 0개 | 1,000+ |

---

**작성자**: Claude (NAMS DB Specialist)
**검토 필요**: 패턴 정규식, 매칭 로직
