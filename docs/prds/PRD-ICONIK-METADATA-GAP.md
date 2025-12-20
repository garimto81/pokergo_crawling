# PRD: Iconik 메타데이터 갭 분석 및 복구 전략

**Version**: 1.0
**Date**: 2025-12-21
**Status**: Draft
**Author**: Claude Code

---

## 1. 개요

### 1.1 목적

두 Google Sheets 시트 간의 메타데이터 차이를 분석하고, 누락 데이터를 Iconik에서 가져올 수 있는지 전략을 수립한다.

### 1.2 배경

- **GGmetadata_and_timestamps**: 수동 입력된 PokerGO 영상 메타데이터 (기존)
- **Iconik_Full_Metadata**: Iconik API에서 자동 추출한 메타데이터 (신규)
- 스프레드시트 ID: `1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk`

### 1.3 범위

- 시트 비교 분석 결과 문서화
- 누락/불일치 데이터 원인 분석
- 복구 가능한 데이터 및 전략 제시

---

## 2. 현재 상태 분석

### 2.1 시트 비교 요약

| 항목 | GGmetadata | Iconik_Full | 차이 |
|------|------------|-------------|------|
| 행 수 | 2,450 | 2,840 | +390 |
| 컬럼 수 | 35 | 35 | 0 |
| 매칭 행 | - | - | 2,289 |

### 2.2 행 분포

```
┌─────────────────────────────────────────────────────────────┐
│                      전체 Asset 분포                         │
├─────────────────────────────────────────────────────────────┤
│  GGmetadata에만: 161개  │  공통: 2,289개  │  Iconik에만: 546개  │
│         (6.6%)          │     (93.4%)     │       (19.2%)       │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 컬럼 구조

35개 컬럼 **완전 동일**:

| 카테고리 | 컬럼 |
|----------|------|
| 기본 | id, title |
| 타임코드 | time_start_ms, time_end_ms, time_start_S, time_end_S |
| 기본 정보 | Description, ProjectName, ProjectNameTag, SearchTag, Year_, Location, Venue |
| 포커 관련 | EpisodeEvent, Source, Scene, GameType, PlayersTags, HandGrade, HANDTag, EPICHAND, Tournament, PokerPlayTags, Adjective, Emotion |
| 추가 필드 | AppearanceOutfit, SceneryObject, _gcvi_tags, Badbeat, Bluff, Suckout, Cooler, RUNOUTTag, PostFlop, All-in |

---

## 3. 문제 정의

### 3.1 주요 누락/불일치 항목

| 문제 유형 | 건수 | 영향 범위 | 심각도 |
|----------|------|----------|--------|
| 타임코드 누락 (Iconik 빈칸) | 1,034 | 45% | High |
| PlayersTags 불일치 | 394 | 17% | Medium |
| PokerPlayTags 불일치 | 335 | 15% | Medium |
| Scene 불일치 | 137 | 6% | Low |
| Emotion 불일치 | 85 | 4% | Low |

### 3.2 상세 분석

#### 3.2.1 타임코드 누락 (1,034건)

**현상**: Iconik_Full_Metadata 시트의 time_start_ms, time_end_ms 등이 비어있음

**원인**: Iconik Segments API에 해당 Asset의 타임코드 데이터가 존재하지 않음

**API 응답 예시**:
```json
{
  "objects": [],   // 빈 배열 = 타임코드 없음
  "total": 0
}
```

**결론**: Iconik에서 가져올 수 없음. 역방향 동기화(GGmetadata → Iconik) 필요.

#### 3.2.2 PlayersTags/PokerPlayTags 불일치 (729건)

**현상**: 값이 다름 (예: "Seth Davies,DAVIES" vs "Seth Davies")

**원인**: 현재 추출 코드가 **첫 번째 값만** 추출

**코드 위치**: `sync/full_metadata_sync.py:278-289`

```python
# 현재 코드 (문제)
first_item = field_values[0]
value = first_item.get("value")

# API 응답 구조
"PlayersTags": {
    "field_values": [
        {"value": "Seth Davies"},    # 첫 번째만 추출됨
        {"value": "DAVIES"}          # 누락됨
    ]
}
```

**결론**: 다중 값 추출 코드 수정으로 해결 가능.

---

## 4. Iconik API 데이터 가용성

### 4.1 가져올 수 있는 데이터

| 데이터 | API | 조건 |
|--------|-----|------|
| 메타데이터 29개 필드 | `/metadata/v1/assets/{id}/views/{view_id}/` | View ID 올바른 경우 |
| 타임코드 | `/assets/v1/assets/{id}/segments/` | Segments 데이터 존재 시 |
| 다중 값 필드 | Metadata API | 코드 수정 필요 |

### 4.2 가져올 수 없는 데이터

| 데이터 | 원인 | 대안 |
|--------|------|------|
| 타임코드 1,034건 | Iconik에 데이터 없음 | 역방향 동기화 필요 |
| GGmetadata 전용 데이터 | 수동 입력 데이터 | 병합 필요 |

### 4.3 API 제한사항

| 제한 | 설명 | 대응 |
|------|------|------|
| Rate Limit | 429 Too Many Requests | 지수 백오프 재시도 |
| 404 Not Found | 메타데이터 없는 Asset | Graceful 처리 (구현됨) |
| View ID 필수 | 잘못된 View ID → 빈 응답 | 진단 스크립트로 확인 |

---

## 5. 복구 전략

### 5.1 Phase 1: 다중 값 추출 개선 (최우선)

**목표**: PlayersTags, PokerPlayTags 등에서 모든 값 추출

**수정 파일**: `src/migrations/iconik2sheet/sync/full_metadata_sync.py`

**변경 내용**:
```python
# 현재 (첫 번째 값만)
value = field_values[0].get("value")

# 개선 (모든 값 연결)
values = [item.get("value") for item in field_values if item.get("value")]
value = ",".join(values)
```

**예상 효과**:
- PlayersTags 불일치 394건 해결
- PokerPlayTags 불일치 335건 해결
- 총 729건 (32% 불일치) 해소

### 5.2 Phase 2: 역방향 동기화 (향후)

**목표**: GGmetadata의 타임코드를 Iconik에 업로드

**필요 사항**:
- Iconik Segments API (POST) 권한
- 타임코드 데이터 형식 변환 (ms → Iconik 형식)

**영향**: 1,034건 타임코드 복구

**별도 PRD**: `PRD-ICONIK-REVERSE-SYNC.md`

### 5.3 Phase 3: 데이터 병합 (향후)

**목표**: 두 시트의 최신/완전한 데이터를 병합

**필요 사항**:
- 충돌 해결 규칙 정의
- 우선순위 시트 결정 (GGmetadata vs Iconik)

**별도 PRD**: `PRD-METADATA-MERGE.md`

---

## 6. Phase 1 구현 계획

### 6.1 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `sync/full_metadata_sync.py` | `_fetch_metadata()` 메서드에서 다중 값 처리 |

### 6.2 테스트

| 테스트 | 검증 내용 |
|--------|----------|
| 단위 테스트 | 다중 값 추출 로직 검증 |
| 통합 테스트 | 실제 API 응답으로 검증 |
| 비교 테스트 | 수정 후 불일치 건수 감소 확인 |

### 6.3 검증 방법

```bash
# 1. 수정 후 동기화 실행
python -m scripts.run_full_metadata

# 2. 비교 스크립트 재실행
python scripts/compare_sheets.py

# 3. PlayersTags/PokerPlayTags 불일치 감소 확인
```

---

## 7. 제약사항 및 리스크

### 7.1 제약사항

| 제약 | 설명 |
|------|------|
| Iconik 데이터 부재 | API에 없는 데이터는 가져올 수 없음 |
| 수동 입력 데이터 | 자동화 불가, 병합 정책 필요 |
| API 권한 | 역방향 동기화에 POST 권한 필요 |

### 7.2 리스크

| 리스크 | 영향 | 완화 방안 |
|--------|------|----------|
| 다중 값 구분자 불일치 | 쉼표(,) vs 다른 구분자 | 기존 데이터 패턴 분석 후 결정 |
| 데이터 덮어쓰기 | 수동 입력 데이터 손실 | 병합 전 백업 필수 |

---

## 8. 다음 단계

| 순서 | 작업 | 담당 |
|------|------|------|
| 1 | Phase 1 다중 값 추출 구현 | 개발 |
| 2 | 비교 분석 재실행 및 검증 | 개발 |
| 3 | Phase 2 PRD 작성 (역방향 동기화) | 기획 |
| 4 | Phase 3 PRD 작성 (데이터 병합) | 기획 |

---

## 9. 참조

| 문서 | 위치 |
|------|------|
| 비교 분석 스크립트 | `scripts/compare_sheets.py` |
| 동기화 모듈 | `src/migrations/iconik2sheet/` |
| Iconik API 클라이언트 | `src/migrations/iconik2sheet/iconik/client.py` |
| 기존 PRD | `docs/prds/PRD-ICONIK-MASTER-MAPPING.md` |
