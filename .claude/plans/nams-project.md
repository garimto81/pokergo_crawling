# NAMS Project Plan

> NAS Asset Management System - WSOP 52년 역사 DB 체계화 프로젝트

**Version**: 2.0 | **Updated**: 2025-12-17

---

## 프로젝트 목표

3개의 NAS 드라이브(X:/Y:/Z:)와 PokerGO 메타데이터를 통합하여
**1973년부터 현재까지 52년간의 WSOP 콘텐츠 카탈로그**를 구축

---

## 현재 상태 (2025-12-17)

| 지표 | 값 | 목표 |
|------|-----|------|
| **패턴 추출률** | 97.6% | 99%+ |
| **PokerGO 매칭률** | 53.3% (440/826) | 65%+ (현실적) |
| Total Asset Groups | 826 | - |
| MATCHED Groups | 440 | 540+ |
| NAS_ONLY Groups | 386 | 286- |
| Active Files | 858 | - |
| Excluded Files | 547 | - |

---

## 핵심 발견사항

### 매칭률 53.3%의 원인 분석

```
┌─────────────────────────────────────────────────────────────────┐
│                    미매칭 386개 그룹 분석                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [PokerGO 데이터 부재] ─────────────────────── 74% (286개)      │
│     ├─ Paradise (2023-2024)      : ~120개 (PokerGO 범위 밖)    │
│     ├─ Cyprus (2025)             : ~48개  (PokerGO 범위 밖)    │
│     ├─ APAC (2013-2014)          : ~6개   (PokerGO 범위 밖)    │
│     ├─ LA Circuit                : ~50개  (PokerGO 범위 밖)    │
│     └─ London/Other              : ~62개  (PokerGO 범위 밖)    │
│                                                                 │
│  [CLASSIC Era] ─────────────────────────────── 13% (50개)       │
│     └─ 1973-2002 연도당 단일 타이틀                             │
│        → 자체 카탈로그 제목 생성으로 해결 가능                  │
│                                                                 │
│  [패턴 매칭 실패] ──────────────────────────── 13% (50개)       │
│     └─ 비표준 파일명, 메타데이터 추출 실패                      │
│        → 패턴 엔진 개선으로 해결 가능                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 현실적 목표 재설정

**기존 목표**: 매칭률 80%+
**현실적 목표**: 매칭률 **65%** (LV+EU 범위 내 최대)

| 영역 | 현재 | 개선 후 | 비고 |
|------|------|---------|------|
| LV (Las Vegas) | 41% | 60%+ | 패턴 개선으로 달성 가능 |
| EU (Europe) | 16% | 40%+ | 제한된 PokerGO 커버리지 |
| Paradise/Cyprus | 0% | 0% | **PokerGO 범위 밖 - 불가** |
| APAC/LA/Other | 0% | 0% | **PokerGO 범위 밖 - 불가** |

---

## 4대 핵심 목표 상태

### 1. NAS 파일 통합 관리 ✅ 완료 (95%)
- [x] X: 드라이브 (PokerGO Source) 스캔 - 247 files
- [x] Y: 드라이브 (WSOP Backup) 스캔 - 371 files
- [x] Z: 드라이브 (Archive) 스캔 - 1,405 files
- [x] 메타데이터 추출 97.6%
- [ ] X: 드라이브 전체 재매칭 (즉시 실행 필요)

### 2. PokerGO 매칭 ⚠️ 진행 중 (53.3%)
- [x] 828개 PokerGO 에피소드 로드
- [x] NAS 파일과 1:1 자동 매칭
- [ ] 매칭률 53.3% → 65% 목표
- [x] DUPLICATE 18건으로 감소 (v5.0)

### 3. Asset Grouping ✅ 완료 (100%)
- [x] 동일 콘텐츠 파일 그룹화
- [x] Primary/Backup 구분
- [x] Origin(Y:) ⊆ Archive(Z:) 관계 정립

### 4. 카탈로그 생성 🟡 진행 중 (70%)
- [x] Google Sheets 5시트 내보내기
- [ ] Netflix 스타일 표시 제목 생성
- [ ] Block F/G 카탈로그 포맷

---

## 실행 로드맵 (7주)

### Phase 1: 즉시 개선 (Week 1)

**목표**: 매칭률 53% → 58%

| Task | 예상 시간 | 영향 |
|------|----------|------|
| X: 드라이브 전체 재매칭 | 30분 | 최신 파일 반영 |
| 패턴 엔진 개선 (비표준 파일명) | 2일 | +3% 매칭률 |
| ESPN Show ↔ PokerGO Episode 매핑 | 1일 | +2% 매칭률 |
| DB 정합성 검증 | 1일 | 데이터 품질 |

```powershell
# 즉시 실행
python scripts/scan_nas.py --mode full --folder pokergo
python scripts/run_pipeline.py --mode full
```

### Phase 2: CLASSIC Era 해결 (Week 2)

**목표**: 1973-2002 카탈로그 완성

| Task | 예상 시간 | 영향 |
|------|----------|------|
| 연도별 Part 번호 자동 할당 | 2일 | 50개 그룹 정리 |
| Catalog Title 생성 함수 구현 | 2일 | UX 개선 |
| 챔피언 메타데이터 추가 | 1일 | 풍부한 정보 |

### Phase 3: 카탈로그 포맷 완성 (Week 3-4)

**목표**: Netflix 스타일 + Block F/G

| Task | 예상 시간 | 영향 |
|------|----------|------|
| generate_catalog_title() 완성 | 3일 | 표준화된 제목 |
| Block F 포맷 정의 (콘텐츠 메타) | 2일 | 납품 포맷 |
| Block G 포맷 정의 (기술 메타) | 2일 | 납품 포맷 |
| Google Sheets Catalog_Title 컬럼 | 1일 | 내보내기 |

### Phase 4: 자동화 파이프라인 (Week 5)

**목표**: 완전 자동화

| Task | 예상 시간 | 영향 |
|------|----------|------|
| run_pipeline.py 완성 | 3일 | 원클릭 실행 |
| 증분 스캔 최적화 | 2일 | 성능 개선 |
| 변경 감지 및 알림 | 2일 | 모니터링 |

### Phase 5: NAS_ONLY 처리 (Week 6)

**목표**: 미매칭 콘텐츠 정리

| Task | 예상 시간 | 영향 |
|------|----------|------|
| Paradise/Cyprus 자체 카탈로그 | 3일 | 168개 그룹 정리 |
| APAC/LA/London 자체 카탈로그 | 2일 | 118개 그룹 정리 |
| NAS_ONLY 전용 시트 생성 | 1일 | 관리 용이 |

### Phase 6: 최종 검증 (Week 7)

**목표**: 프로덕션 준비

| Task | 예상 시간 | 영향 |
|------|----------|------|
| 전체 데이터 검증 | 2일 | 품질 보증 |
| UI/UX 최종 테스트 | 2일 | 사용성 |
| 문서 최종 업데이트 | 1일 | 완성도 |
| 프로덕션 배포 | 1일 | 완료 |

---

## 기술적 해결 방안

### 1. 패턴 엔진 개선 (50개 그룹 추가 매칭)

```python
# 새 패턴 추가 필요
patterns_to_add = [
    r'MPP.*Cyprus.*(\d{4})',           # Cyprus 파일명
    r'PokerOK.*Mystery.*Bounty',       # 특수 이벤트
    r'GGMillion.*(\d{4})',             # GGMillion 이벤트
    r'wsop-(\d{4})-paradise',          # Paradise 형식
]
```

### 2. CLASSIC Era 카탈로그 제목 생성

```python
def generate_classic_catalog_title(year: int, part: int = None) -> str:
    """CLASSIC Era (1973-2002) 카탈로그 제목 생성"""
    champion = WSOP_CHAMPIONS.get(year)
    if part:
        return f"WSOP {year} Main Event Part {part} - {champion}"
    return f"WSOP {year} Main Event - {champion}"
```

### 3. NAS_ONLY 자체 카탈로그

```python
def generate_nas_only_catalog_title(group: AssetGroup) -> str:
    """PokerGO 범위 밖 콘텐츠 카탈로그 제목 생성"""
    region_names = {
        'PARADISE': 'WSOP Paradise',
        'CYPRUS': 'WSOP Cyprus',
        'APAC': 'WSOP Asia Pacific',
        'LA': 'WSOP Circuit Los Angeles',
    }
    base = region_names.get(group.region_code, 'WSOP')
    return f"{base} {group.year} {group.event_type} Episode {group.episode}"
```

---

## 성공 지표

### 최종 목표 (Week 7)

| 지표 | 현재 | 목표 | 비고 |
|------|------|------|------|
| PokerGO 매칭률 | 53.3% | **65%** | LV+EU 최대치 |
| 패턴 추출률 | 97.6% | **99%** | 패턴 개선 |
| 카탈로그 제목 | 0% | **100%** | 모든 그룹 |
| NAS_ONLY 정리 | 0% | **100%** | 자체 카탈로그 |
| 자동화 | 50% | **100%** | 파이프라인 |

### 산출물

- [x] SQLite DB (통합 매칭 결과)
- [x] Google Sheets 5시트
- [ ] Catalog Titles (Netflix 스타일) - **Week 3-4**
- [ ] Block F/G 포맷 - **Week 3-4**
- [ ] 완전 자동화 파이프라인 - **Week 5**

---

## 리스크 관리

| 리스크 | 확률 | 영향 | 대응 |
|--------|------|------|------|
| PokerGO 지역 데이터 미확보 | 높음 | 높음 | 자체 카탈로그로 대체 |
| 패턴 매칭 한계 | 중간 | 중간 | 수작업 분류 병행 |
| NAS 드라이브 접근 불가 | 낮음 | 높음 | 캐시 활용 |

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 2.0 | 2025-12-17 | 현실적 목표 재설정 (80%→65%), 7주 로드맵 수립, 미매칭 원인 분석 |
| 1.0 | 2025-12-17 | 초기 계획 수립 |
