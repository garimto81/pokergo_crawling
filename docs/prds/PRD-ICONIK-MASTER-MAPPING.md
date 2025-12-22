# PRD: Iconik to Master Catalog Mapping

> Iconik 메타데이터를 UDM Master_Catalog에 통합

**Version**: 2.0 | **Date**: 2025-12-20 | **Status**: In Progress

---

## 용어 정의

| 약칭 | 스프레드시트 ID | 설명 |
|------|----------------|------|
| **아이코닉 시트** | `1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk` | 아이코닉 메타 데이터 |
| **UDM 시트** | `1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4` | UDM 메타 데이터 (Master_Catalog) |

### 아이코닉 시트 구성

| 시트명 | 설명 | 상태 |
|--------|------|------|
| GGmetadata_and_timestamps | 이전 메타데이터 (35개 컬럼) | 기존 |
| Iconik_Assets | 기본 Asset 정보 (7개 컬럼) | 추출됨 |
| Iconik_Collections | 컬렉션 정보 | 추출됨 |
| **Iconik_Full_Metadata** | 전체 메타데이터 (35개 컬럼) | **추출 필요** |

---

## 1. 개요

### 1.1 목표

1. **Phase A**: Iconik API에서 전체 메타데이터 추출 (GGmetadata_and_timestamps와 동일)
2. **Phase B**: 추출된 메타데이터를 UDM 시트 Master_Catalog에 매핑

### 1.2 현재 문제

| 항목 | 현재 상태 | 필요한 상태 |
|------|-----------|-------------|
| Iconik_Assets | 7개 컬럼 (기본 정보) | 35개 컬럼 (전체 메타데이터) |
| 메타데이터 | 미추출 | Segment + Metadata API 조회 필요 |

---

## 2. Phase A: Iconik 전체 메타데이터 추출

### 2.1 추출 대상 컬럼 (35개)

GGmetadata_and_timestamps와 동일한 컬럼 구조:

| # | 컬럼 | 소스 | 설명 |
|---|------|------|------|
| 1 | id | Asset | Iconik Asset ID |
| 2 | title | Asset | 클립 제목 |
| 3 | time_start_ms | Segment | 시작 시간 (ms) |
| 4 | time_end_ms | Segment | 종료 시간 (ms) |
| 5 | time_start_S | 계산 | ms / 1000 |
| 6 | time_end_S | 계산 | ms / 1000 |
| 7 | Description | Metadata | 핸드 설명 |
| 8 | ProjectName | Metadata | 프로젝트명 (WSOP) |
| 9 | ProjectNameTag | Metadata | 프로젝트 태그 |
| 10 | SearchTag | Metadata | 검색 태그 |
| 11 | Year_ | Metadata | 연도 |
| 12 | Location | Metadata | 위치 |
| 13 | Venue | Metadata | 장소 |
| 14 | EpisodeEvent | Metadata | 에피소드/이벤트 |
| 15 | Source | Metadata | 소스 |
| 16 | Scene | Metadata | 장면 |
| 17 | GameType | Metadata | 게임 유형 |
| 18 | PlayersTags | Metadata | 플레이어 태그 |
| 19 | HandGrade | Metadata | 핸드 등급 |
| 20 | HANDTag | Metadata | 핸드 태그 |
| 21 | EPICHAND | Metadata | 에픽 핸드 여부 |
| 22 | Tournament | Metadata | 토너먼트 |
| 23 | PokerPlayTags | Metadata | 포커 플레이 태그 |
| 24 | Adjective | Metadata | 형용사 |
| 25 | Emotion | Metadata | 감정 |
| 26 | AppearanceOutfit | Metadata | 외모/복장 |
| 27 | SceneryObject | Metadata | 배경/오브젝트 |
| 28 | _gcvi_tags | Metadata | GCVI 태그 |
| 29 | Badbeat | Metadata | 배드빗 |
| 30 | Bluff | Metadata | 블러프 |
| 31 | Suckout | Metadata | 석아웃 |
| 32 | Cooler | Metadata | 쿨러 |
| 33 | RUNOUTTag | Metadata | 런아웃 태그 |
| 34 | PostFlop | Metadata | 포스트플랍 |
| 35 | All-in | Metadata | 올인 |

### 2.2 추출 프로세스

```
┌─────────────────────────────────────────────────────────────┐
│  Iconik API                                                  │
│                                                              │
│  1. GET /assets/v1/assets/ (페이지네이션)                   │
│     └─ 모든 Asset 목록 조회                                 │
│                                                              │
│  2. 각 Asset에 대해:                                        │
│     ├─ GET /metadata/v1/assets/{id}/views/{view_id}/        │
│     │   └─ 메타데이터 필드 조회 (26개)                      │
│     │                                                        │
│     └─ GET /assets/v1/assets/{id}/segments/                 │
│         └─ 타임코드 조회 (time_start, time_end)             │
│                                                              │
│  3. 결합하여 35개 컬럼 생성                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  아이코닉 시트                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Iconik_Full_Metadata (35개 컬럼, 2,621+ 행)         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 구현 파일

```
src/migrations/iconik2sheet/
├── sync/
│   ├── full_sync.py           # 기존 (기본 정보만)
│   └── full_metadata_sync.py  # 신규: 전체 메타데이터 추출
└── scripts/
    └── run_full_metadata.py   # 신규: 실행 스크립트
```

---

## 3. Phase B: UDM 시트 매핑

### 3.1 매핑 관계

```
아이코닉 시트                    UDM 시트
Iconik_Full_Metadata    ─────▶   Master_Catalog
  (35개 컬럼)                      (18개 + 추가 컬럼)
  2,621+ 행                        1,057 행

관계: N:1 (여러 클립 → 1개 파일)
```

### 3.2 매칭 로직

| Iconik title 패턴 | → | Master Entry Key |
|-------------------|---|------------------|
| `7-wsop-2024-be-ev-12-...` | → | `WSOP_2024_BR_E12_*` |
| `53-wsop-2024-me-day5-...` | → | `WSOP_2024_ME_D5_*` |

### 3.3 추가 컬럼

Master_Catalog에 추가:

| 컬럼 | 설명 |
|------|------|
| Iconik_Clip_Count | 매칭된 클립 수 |
| Iconik_Clip_IDs | 클립 ID 목록 (쉼표 구분) |
| + 35개 메타데이터 | 병합된 메타데이터 |

---

## 4. 구현 순서

### Step 1: Iconik 전체 메타데이터 추출 (Phase A)

```powershell
cd src/migrations/iconik2sheet
python -m scripts.run_full_metadata
```

**산출물**: 아이코닉 시트에 `Iconik_Full_Metadata` 시트 생성

### Step 2: 데이터 검증

- GGmetadata_and_timestamps와 Iconik_Full_Metadata 비교
- 컬럼 구조 일치 확인
- 데이터 정합성 검증

### Step 3: UDM 매핑 (Phase B)

```powershell
cd src/migrations/iconik2master
python -m scripts.run_mapping --write
```

**산출물**: UDM 시트 Master_Catalog에 메타데이터 컬럼 추가

---

## 5. 관련 파일

| 프로젝트 | 파일 | 용도 |
|----------|------|------|
| iconik2sheet | `sync/full_metadata_sync.py` | 전체 메타데이터 추출 |
| iconik2sheet | `scripts/run_full_metadata.py` | 추출 실행 |
| iconik2master | `parsers/title_parser.py` | 제목 파싱 |
| iconik2master | `matchers/entry_key_matcher.py` | Entry Key 매칭 |
| iconik2master | `scripts/run_mapping.py` | 매핑 실행 |

---

## 6. 스프레드시트 URL

| 시트 | URL |
|------|-----|
| 아이코닉 시트 | https://docs.google.com/spreadsheets/d/1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk |
| UDM 시트 | https://docs.google.com/spreadsheets/d/1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4 |
