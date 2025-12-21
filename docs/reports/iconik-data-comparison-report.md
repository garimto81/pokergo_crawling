# Iconik 데이터 비교 분석 보고서

**작성일**: 2025-12-21
**작성자**: Claude Code
**버전**: 1.0

---

## Executive Summary

### 핵심 수치

| 지표 | 기존 (수동 입력) | 신규 (API 추출) | 비고 |
|------|-----------------|-----------------|------|
| **총 행수** | 2,450 | 2,840 | +390 (+15.9%) |
| **컬럼 수** | 35 | 35 | 완전 일치 |
| **ID 매칭** | - | 2,290 | 93.5% 매칭 |

### 데이터 차이 요약

| 구분 | 건수 | 설명 |
|------|------|------|
| 기존에만 존재 | 160 | Iconik에서 삭제된 Asset |
| 신규에만 존재 | 542 | 새로 추가된 Asset |
| 값 불일치 | 195 | 동일 ID, 다른 값 |
| 신규가 더 채움 | 1,919 | 기존 빈값 → 신규 채워짐 |
| 기존이 더 채움 | 4,051 | 기존 채워짐 → 신규 빈값 |

### 결론

1. **신규 데이터가 더 많은 Asset 포함** (+390개)
2. **컬럼 구조 완전 일치** (35개)
3. **timecode 필드가 주요 차이점** - 기존 수동 입력 데이터 중 1,009건이 Iconik에 없음 (수동 입력 전용)
4. **메타데이터 필드는 신규가 개선됨** - Description, Year_, ProjectName 등 신규에서 더 많이 채워짐

---

## 1. 비교 대상

### 1.1 기존 데이터: GGmetadata_and_timestamps

| 항목 | 내용 |
|------|------|
| **시트명** | GGmetadata_and_timestamps |
| **데이터 소스** | 수동 입력 |
| **총 행수** | 2,450 |
| **컬럼 수** | 35 |
| **특징** | 수동으로 입력된 메타데이터, timecode 포함 |

### 1.2 신규 데이터: Iconik_Full_Metadata

| 항목 | 내용 |
|------|------|
| **시트명** | Iconik_Full_Metadata |
| **데이터 소스** | Iconik MAM API 자동 추출 |
| **총 행수** | 2,840 |
| **컬럼 수** | 35 |
| **특징** | API 기반 자동 추출, 다중값 필드 지원, Graceful 404 처리 |

---

## 2. 컬럼 구조 비교

### 2.1 결과

| 비교 항목 | 결과 |
|-----------|------|
| 공통 컬럼 | 35개 |
| 기존에만 있는 컬럼 | 없음 |
| 신규에만 있는 컬럼 | 없음 |

**결론**: 컬럼 구조 **완전 일치**

### 2.2 컬럼 목록 (35개)

| 구분 | 컬럼명 |
|------|--------|
| 기본 정보 | id, title |
| Timecode | time_start_ms, time_end_ms, time_start_S, time_end_S |
| 프로젝트 | Description, ProjectName, ProjectNameTag, SearchTag |
| 분류 | Year_, Location, Venue, EpisodeEvent, Source, Scene |
| 포커 메타 | GameType, PlayersTags, HandGrade, HANDTag, EPICHAND, Tournament |
| 태그 | PokerPlayTags, Adjective, Emotion, AppearanceOutfit |
| 기타 | SceneryObject, _gcvi_tags, Badbeat, Bluff, Suckout, Cooler, RUNOUTTag, PostFlop, All-in |

---

## 3. 행(Asset) 비교

### 3.1 총 행수 비교

```
기존 (GGmetadata_and_timestamps):  2,450 rows
신규 (Iconik_Full_Metadata):       2,840 rows
                                   ------
차이:                              +390 rows (+15.9%)
```

### 3.2 ID 매칭 결과

| 구분 | 건수 | 비율 |
|------|------|------|
| ID 매칭 성공 | 2,290 | - |
| 기존에만 존재 | 160 | 기존의 6.5% |
| 신규에만 존재 | 542 | 신규의 19.1% |

### 3.3 누락 Asset 분석

#### 기존에만 존재하는 Asset (160건)
- **원인**: Iconik에서 삭제되었거나 이동된 Asset
- **샘플 ID**:
  - `010e67d2-6d0c-11f0-b372-867d5c2b67ce`
  - `014e7d9e-51a1-11f0-9b13-227cff1a1c5c`
  - `02f8c4c0-ef62-11ef-9d61-c2d9edbd303d`

#### 신규에만 존재하는 Asset (542건)
- **원인**: 최근 Iconik에 추가된 신규 Asset
- **샘플 ID**:
  - `00490002-d5ce-11f0-8b6b-ba32cfebb41a`
  - `005c9a28-dd7a-11f0-bce8-e232a4f98933`
  - `00a17fbe-dbed-11f0-8e5a-163bc42afaea`

---

## 4. 필드별 상세 비교

### 4.1 개선된 필드 (신규 > 기존)

기존에는 빈값이었으나 신규에서 채워진 필드:

| 필드명 | 개선 건수 | 비고 |
|--------|----------|------|
| time_start_ms | 434 | 세그먼트 timecode |
| time_end_ms | 434 | 세그먼트 timecode |
| time_start_S | 434 | 초 단위 변환 |
| time_end_S | 434 | 초 단위 변환 |
| Description | 45 | 설명 필드 |
| Year_ | 31 | 연도 |
| ProjectName | 29 | 프로젝트명 |
| Location | 28 | 위치 |
| Source | 24 | 소스 |
| EpisodeEvent | 12 | 에피소드/이벤트 |

**분석**: timecode 필드가 434건 추가 추출됨. 이는 세그먼트 필드명 수정(#12)의 결과.

### 4.2 저하된 필드 (기존 > 신규)

기존에는 채워져 있으나 신규에서 빈값인 필드:

| 필드명 | 누락 건수 | 원인 |
|--------|----------|------|
| time_start_ms | 1,009 | Iconik에 세그먼트 없음 |
| time_end_ms | 1,009 | Iconik에 세그먼트 없음 |
| time_start_S | 1,009 | Iconik에 세그먼트 없음 |
| time_end_S | 1,009 | Iconik에 세그먼트 없음 |
| _gcvi_tags | 10 | API에서 미지원 |

**분석**:
- timecode 1,009건은 **수동 입력 전용 데이터**로, Iconik API에서 가져올 수 없음
- 이는 기존 GG시트에서 수동으로 입력한 세그먼트 정보

### 4.3 값 불일치 필드

동일 Asset ID에서 값이 다른 필드:

| 필드명 | 불일치 건수 | 원인 |
|--------|------------|------|
| Source | 52 | 수동 입력 vs API 추출 차이 |
| title | 45 | Iconik에서 제목 업데이트됨 |
| time_start_S | 25 | 형식 차이 (초 vs 분:초) |
| time_end_S | 25 | 형식 차이 |
| time_end_ms | 14 | 밀리초 값 차이 |
| Description | 11 | 내용 업데이트 |
| PlayersTags | 10 | 다중값 처리 방식 차이 |
| time_start_ms | 9 | 밀리초 값 차이 |
| Scene | 4 | 씬 분류 차이 |

---

## 5. 결론 및 권장사항

### 5.1 데이터 품질 평가

| 항목 | 기존 | 신규 | 평가 |
|------|------|------|------|
| **커버리지** | 2,450 | 2,840 | 신규 우수 (+15.9%) |
| **자동화** | 수동 | 자동 | 신규 우수 |
| **최신성** | - | API 동기화 | 신규 우수 |
| **timecode** | 수동 입력 포함 | 일부 누락 | 기존 우수 (수동 데이터) |

### 5.2 권장사항

1. **신규 데이터를 기본으로 사용**
   - 더 많은 Asset 포함 (2,840개)
   - API 기반 자동 동기화로 최신 상태 유지

2. **timecode 데이터 보존**
   - 기존 수동 입력 timecode 1,009건은 별도 보존 필요
   - 추후 Iconik에 세그먼트 등록 시 자동 반영됨

3. **정기 동기화 권장**
   - 신규 Asset 추가 대응
   - 메타데이터 업데이트 반영

### 5.3 다음 단계

- [ ] 기존 전용 timecode 데이터 마이그레이션 계획 수립
- [ ] 정기 동기화 스케줄러 설정
- [ ] 160건 누락 Asset 확인 (Iconik에서 삭제 여부)

---

## 부록

### A. 스프레드시트 정보

| 항목 | 값 |
|------|-----|
| Spreadsheet ID | `1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk` |
| 기존 시트 | GGmetadata_and_timestamps |
| 신규 시트 | Iconik_Full_Metadata |

### B. 관련 코드

| 파일 | 역할 |
|------|------|
| `scripts/compare_sheets.py` | 비교 분석 스크립트 |
| `src/migrations/iconik2sheet/sync/full_metadata_sync.py` | 메타데이터 추출 |
| `src/migrations/iconik2sheet/iconik/client.py` | Iconik API 클라이언트 |

### C. 변경 이력

| 날짜 | 버전 | 내용 |
|------|------|------|
| 2025-12-21 | 1.0 | 최초 작성 |
