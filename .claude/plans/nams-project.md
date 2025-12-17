# NAMS Project Plan

> NAS Asset Management System - WSOP 52년 역사 카탈로그 구축

**Version**: 3.0 | **Updated**: 2025-12-17

---

## 프로젝트 목표 (재정의)

### 핵심 인사이트

```
┌─────────────────────────────────────────────────────────────────┐
│                    데이터 성격의 근본적 차이                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [PokerGO 828개]              [NAS 1,405개]                     │
│  ├─ 편집된 에피소드            ├─ 생방송 스트리밍 원본           │
│  ├─ 30-60분 단위              ├─ 수시간 Raw footage            │
│  ├─ 방송용 최종본              └─ 소스 영상                     │
│                                                                 │
│  → 1:1 매칭은 본질적으로 불가능                                  │
│  → PokerGO 매칭률은 잘못된 KPI                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 새로운 목표

**NAS 파일 기반 자체 카탈로그 구축**

```
[NAS 파일] → [패턴 추출] → [카탈로그 생성] → [수동 검증]
                                    ↑
                           [PokerGO는 참조용]
```

---

## 현재 상태 (2025-12-17)

### 보유 자산

| 항목 | 수량 | 비고 |
|------|------|------|
| NAS 전체 파일 | 1,405 | X: + Y: + Z: |
| Active 파일 | 858 | 제외 조건 미해당 |
| Excluded 파일 | 547 | 클립, 짧은 영상 등 |
| PokerGO 에피소드 | 828 | 참조용 메타데이터 |

### 드라이브별 현황

| 드라이브 | 용도 | 파일 수 | 크기 |
|----------|------|---------|------|
| X: | PokerGO Source | 247 | 684 GB |
| Y: | WSOP Backup | 371 | 1.8 TB |
| Z: | Archive (Primary) | 1,405 | 20 TB |

---

## 새로운 데이터 모델

### 핵심 개념

```
Category (카테고리)
└── CatalogEntry (카탈로그 항목)
    ├── NasFile[] (NAS 파일 - 1:N)
    └── PokerGoRef[] (PokerGO 참조 - 1:N, optional)
```

### 테이블 구조

| 테이블 | 역할 |
|--------|------|
| **Category** | 연도별 시리즈 (WSOP 2022, WSOP Europe 2022, ...) |
| **CatalogEntry** | 개별 콘텐츠 (Main Event Day 1, Bracelet #1, ...) |
| **NasFile** | 실제 파일 (기존 유지, catalog_id 추가) |
| **PokerGoRef** | PokerGO 참조 정보 (optional) |

### 상세 설계

→ [docs/PRD-CATALOG-DB.md](../../docs/PRD-CATALOG-DB.md)

---

## 신규 KPI

### 기존 vs 신규

| 기존 KPI (폐기) | 신규 KPI |
|----------------|----------|
| ~~PokerGO 매칭률 53%~~ | **카탈로그 커버리지** |
| ~~MATCHED/NAS_ONLY~~ | **VERIFIED/UNVERIFIED** |
| 패턴 추출률 97.6% | **제목 완성도** |

### 목표 지표

| 지표 | 정의 | 목표 |
|------|------|------|
| **카탈로그 커버리지** | CatalogEntry 연결된 NasFile / Active NasFile | 95%+ |
| **제목 완성도** | display_title 있는 Entry / 전체 Entry | 100% |
| **검증 완료율** | verified=true Entry / 전체 Entry | 80%+ |
| **PokerGO 참조율** | PokerGoRef 있는 Entry / 전체 Entry | 50%+ |

---

## 실행 로드맵 (5주)

### Phase 1: DB 마이그레이션 (Week 1)

**목표**: 새 스키마로 전환

| Task | 설명 |
|------|------|
| 새 테이블 생성 | categories, catalog_entries, pokergo_refs |
| NasFile 스키마 수정 | catalog_id 컬럼 추가 |
| 데이터 마이그레이션 | AssetGroup → CatalogEntry 변환 |
| 기존 테이블 백업 | asset_groups 등 보존 |

```python
# 마이그레이션 스크립트
python scripts/migrate_to_catalog.py
```

### Phase 2: 카탈로그 자동 생성 (Week 2)

**목표**: NAS 파일 → CatalogEntry 자동 생성

| Task | 설명 |
|------|------|
| 카탈로그 키 생성 로직 | year_event_sequence 조합 |
| Category 자동 생성 | 연도/지역별 카테고리 |
| CatalogEntry 생성 | 패턴 기반 자동 생성 |
| NasFile 연결 | catalog_id 할당 |

```python
# 카탈로그 생성
python scripts/generate_catalog.py
```

### Phase 3: 제목 생성 엔진 (Week 3)

**목표**: 모든 CatalogEntry에 display_title 생성

| Task | 설명 |
|------|------|
| Era별 제목 규칙 | CLASSIC (1973-2002) 특수 처리 |
| Region별 접두사 | WSOP, WSOP Europe, WSOP Paradise 등 |
| Event Type 명칭 | ME→Main Event, BR→Bracelet Event |
| Sequence 포맷 | Day 1, Episode 1, Part 1 |

```python
def generate_display_title(entry):
    # Era 처리
    if entry.year <= 2002:
        return f"WSOP Classic {entry.year} - {CHAMPIONS[entry.year]}"

    # 일반 처리
    prefix = REGION_PREFIX[entry.region]  # WSOP, WSOP Europe, ...
    event = EVENT_NAMES[entry.event_type]  # Main Event, Bracelet, ...
    seq = f" Day {entry.sequence}" if entry.sequence else ""

    return f"{prefix} {entry.year} {event}{seq}"
```

### Phase 4: UI 및 검증 워크플로우 (Week 4)

**목표**: 수동 검증 가능한 UI 구축

| Task | 설명 |
|------|------|
| 대시보드 수정 | 신규 KPI 표시 |
| 카탈로그 목록 | 필터, 정렬, 인라인 편집 |
| 검증 워크플로우 | 일괄 검증, 검증 이력 |
| 미할당 파일 관리 | 수동 카탈로그 할당 |

### Phase 5: 내보내기 및 완성 (Week 5)

**목표**: 최종 카탈로그 내보내기

| Task | 설명 |
|------|------|
| Google Sheets 수정 | 신규 스키마 반영 |
| 카탈로그 시트 추가 | Category/Entry 전용 시트 |
| 최종 검증 | 데이터 품질 검토 |
| 문서 업데이트 | 완료 보고서 |

---

## 카테고리 구조 (예상)

### 연도별 분포

```
WSOP (LV)
├── WSOP Classic 1973-2002 (30개 카테고리)
├── WSOP 2003-2010 Boom Era (8개)
├── WSOP 2011-2025 HD Era (15개)
└── 총 ~53개 LV 카테고리

WSOP Europe
├── WSOPE 2007-2021 (15개)
└── 총 ~15개 EU 카테고리

기타
├── WSOP APAC (2013-2014) ~2개
├── WSOP Paradise (2023-2024) ~2개
├── WSOP Cyprus (2025) ~1개
├── WSOP Circuit LA ~1개
└── 총 ~6개 기타 카테고리

전체: ~74개 카테고리, ~800개 카탈로그 항목
```

### 예상 카탈로그 항목

| 카테고리 | 예상 항목 수 |
|----------|-------------|
| WSOP LV (1973-2025) | ~550 |
| WSOP Europe | ~120 |
| WSOP APAC | ~20 |
| WSOP Paradise | ~60 |
| WSOP Cyprus | ~20 |
| 기타 | ~30 |
| **합계** | **~800** |

---

## 기술적 결정

### 1. NAS 파일이 Truth

- NAS 파일 = 실제 보유 자산
- 카탈로그는 NAS 파일 기반으로 생성
- PokerGO는 보조 참조 정보

### 2. 자동 + 수동 하이브리드

- 자동: 패턴 기반 카탈로그/제목 생성
- 수동: 검증, 제목 수정, 예외 처리
- 목표: 자동 90%, 수동 10%

### 3. 1:N 관계 허용

- 하나의 NAS 스트림 = 여러 PokerGO 에피소드
- 하나의 카탈로그 = 여러 NAS 파일 (품질/백업)

### 4. 검증 상태 추적

- 자동 생성 → UNVERIFIED
- 사람 확인 → VERIFIED
- 검증 이력 보존

---

## 성공 정의

### Week 5 완료 시점

| 지표 | 목표 |
|------|------|
| 카탈로그 항목 | 800+ entries |
| 카탈로그 커버리지 | 95%+ |
| 제목 완성도 | 100% |
| 검증 완료율 | 80%+ |

### 산출물

- [ ] SQLite DB (신규 스키마)
- [ ] 카탈로그 생성 스크립트
- [ ] 제목 생성 엔진
- [ ] 검증 UI
- [ ] Google Sheets 내보내기

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 3.0 | 2025-12-17 | **패러다임 전환**: PokerGO 매칭 → NAS 중심 카탈로그 |
| 2.0 | 2025-12-17 | 현실적 목표 재설정 (80%→65%) |
| 1.0 | 2025-12-17 | 초기 계획 수립 |
