# Iconik 데이터 구조 분석

> Iconik MAM 시스템의 Asset, Segment, Subclip 구조 및 타임코드 저장 위치 분석

**Version**: 2.0 | **Date**: 2025-12-22 | **Source**: [Iconik Help Documentation](https://help.iconik.backlight.co)

---

## 1. 개요

Iconik MAM에서 데이터를 저장하는 3가지 방식:

| 저장 방식 | API 엔드포인트 | 용도 |
|----------|---------------|------|
| **Asset** | `/assets/v1/assets/{id}/` | 미디어 파일 또는 Subclip |
| **Segment** | `/assets/v1/assets/{id}/segments/` | 타임코드 마커 + 메타데이터 |
| **General Metadata** | `/metadata/v1/assets/{id}/views/{view_id}/` | Asset 레벨 메타데이터 |

---

## 2. 핵심 개념: 타임코드 저장 위치 ★

> **가장 중요한 발견**: Asset 타임코드와 Segment 타임코드는 **다른 데이터**입니다!

### 2.1 타임코드 저장 위치 비교

| 데이터 소스 | 저장 위치 | 용도 | API |
|------------|----------|------|-----|
| **Asset 타임코드** | `asset.time_start_milliseconds` | Subclip의 **실제 구간** (in/out point) | `GET /assets/v1/assets/{id}/` |
| **Segment 타임코드** | `segment.time_start_milliseconds` | 마커/코멘트 **위치** | `GET /assets/v1/assets/{id}/segments/` |

### 2.2 실제 검증 사례

| Title | Asset 타임코드 | Segment 타임코드 | GG 시트 | 결과 |
|-------|---------------|-----------------|---------|------|
| serock vs griff start from flop | 136600~513088 | 347300~347300 (COMMENT) | 136600~513088 | Asset ✓ |
| Phil Hellmuth Set over Set | 1241725~1446513 | 1241725~1241725 (COMMENT) | 1241725~1446513 | Asset ✓ |
| hellmuth tilted | 1986920~2230030 | 2038555~2038555 (COMMENT) | 1986920~2230030 | Asset ✓ |
| Amarillo Slim | 267567~299833 | 267567~267567 (GENERIC) | 267567~299833 | Asset ✓ |

**결론**: GG 시트의 타임코드는 **Asset 필드**와 일치. Segment는 마커/코멘트 위치일 뿐!

### 2.3 올바른 타임코드 조회 로직

```python
def get_timecode(asset):
    """Asset 타입에 따른 올바른 타임코드 조회"""

    if asset.type == "SUBCLIP":
        # Subclip: Asset 자체에서 타임코드 조회
        return {
            "start": asset.time_start_milliseconds,
            "end": asset.time_end_milliseconds
        }
    else:
        # 일반 Asset: Segment API에서 GENERIC 타입 조회
        segments = client.get_asset_segments(asset.id)
        generic_segments = [s for s in segments if s["segment_type"] == "GENERIC"]
        if generic_segments:
            return {
                "start": generic_segments[0]["time_start_milliseconds"],
                "end": generic_segments[0]["time_end_milliseconds"]
            }
        return None
```

---

## 3. Asset Types

### 3.1 타입별 특징

| Asset Type | 설명 | 타임코드 위치 | 파일 |
|------------|------|--------------|------|
| **ASSET** | 일반 미디어 파일 | Segment API | 있음 |
| **SUBCLIP** | Parent Asset에서 파생 | **Asset 자체** | 없음 (참조만) |

### 3.2 SUBCLIP 구조

```
GET /assets/v1/assets/{subclip_id}/

Response:
{
  "id": "8ddb35e6-007e-11f0-8c20-aad6eb65bf32",
  "type": "SUBCLIP",
  "title": "serock vs griff start from flop",
  "time_start_milliseconds": 136600,    // ← 실제 구간 시작
  "time_end_milliseconds": 513088,      // ← 실제 구간 종료
  "original_asset_id": "parent-uuid",   // ← Parent Asset
  "original_segment_id": "segment-uuid" // ← 원본 Segment
}
```

### 3.3 주의사항

```python
# ❌ 잘못된 방법 (Subclip에서 Segment API 호출)
segments = client.get_asset_segments(subclip_id)
# → 빈 리스트 또는 COMMENT/MARKER만 반환!

# ✅ 올바른 방법 (Asset 필드에서 직접 조회)
asset = client.get_asset(subclip_id)
if asset.type == "SUBCLIP":
    time_start = asset.time_start_milliseconds
    time_end = asset.time_end_milliseconds
```

---

## 4. Segment (Time-based Metadata)

### 4.1 정의

> **Segments are time-coded references to portions of an Asset.**
> Each segment has a timecode for its in-point and out-point.

### 4.2 Segment Types

| Type | 용도 | 타임코드 특징 | 생성 주체 |
|------|------|--------------|----------|
| **GENERIC** | Iconik 기본 템플릿 | 구간 또는 지점 | **시스템 자동** |
| **COMMENT** | 코멘트/마커 | 특정 지점 (start = end) | 작업자 |
| **MARKER** | 시각적 마커 | 특정 지점 (start = end) | 작업자 |
| **QC** | Quality Control 마커 | 특정 지점 | 작업자 |
| **TRANSCRIPTION** | 자막 | 구간 | 시스템/작업자 |

> **주의**: GENERIC Segment는 **Iconik 기본 템플릿**입니다!
> - 시스템에서 자동 생성
> - `metadata_values`가 **항상 비어있음** (검증됨)
> - 작업자가 직접 만든 것이 아님

### 4.2.1 작업자 메타데이터 저장 위치 ★★

> **핵심 발견**: 작업자 메타데이터는 **Segment가 아닌 Asset Metadata API**에 저장됩니다!

```
작업자 메타데이터 저장 위치:
  ❌ Segment.metadata_values (항상 비어있음)
  ✅ Asset Metadata API: GET /metadata/v1/assets/{id}/views/{view_id}/
```

| 조회 대상 | API | 메타데이터 |
|----------|-----|-----------|
| Subclip | `/metadata/v1/assets/{subclip_id}/views/{view_id}/` | ✅ 있음 |
| Parent Asset | `/metadata/v1/assets/{parent_id}/views/{view_id}/` | ✅ 있음 |
| Segment | `segment.metadata_values` | ❌ 비어있음 |

**검증 결과** (serock vs griff):
```
Subclip Asset Metadata API:
  Description: "Serock's amazing hero fold of flop nut straight..."
  PlayersTags: ["serock", "joseph serock"]
  EPICHAND: "Quads"
  HandGrade: "★★★"

Parent Segment (GENERIC):
  metadata_values: {} (비어있음)
```

**무작위 10개 샘플 검증** (2025-12-22):

| Type | 샘플 수 | Segment | Segment metadata_values | Asset Metadata |
|------|--------|---------|------------------------|----------------|
| SUBCLIP | 8개 | 없음 | - | ✅ 4~11개 필드 |
| ASSET | 2개 | GENERIC 있음 | **항상 0** | ✅ 또는 None |

→ **100% 검증**: GENERIC Segment의 metadata_values는 항상 비어있음

### 4.3 API 구조

```
GET /assets/v1/assets/{asset_id}/segments/

Response:
{
  "objects": [
    {
      "id": "segment-uuid",
      "time_start_milliseconds": 125000,
      "time_end_milliseconds": 180000,
      "segment_type": "GENERIC",
      "metadata_values": {
        "Description": {"field_values": [{"value": "Phil Ivey bluffs"}]},
        "PlayersTags": {"field_values": [{"value": "Phil Ivey"}]},
        ...
      }
    },
    {
      "id": "comment-uuid",
      "time_start_milliseconds": 347300,
      "time_end_milliseconds": 347300,      // ← 동일 (point marker)
      "segment_type": "COMMENT",            // ← COMMENT 타입
      "metadata_values": {}
    }
  ]
}
```

### 4.4 핵심 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `time_start_milliseconds` | Integer | 시작 시간 (밀리초) |
| `time_end_milliseconds` | Integer | 종료 시간 (밀리초) |
| `segment_type` | String | GENERIC, MARKER, COMMENT 등 |
| `metadata_values` | Object | 메타데이터 필드 (GENERIC 타입) |

---

## 5. Subclip (별도 Asset)

### 5.1 정의

> **Subclips are a special type of asset** derived from a time-based metadata segment of another asset.

### 5.2 Subclip ↔ Parent Segment 관계

> **The metadata on Subclips are directly related to the time-based metadata and all metadata on the Subclip is cloned to the related segment on the parent asset.**

- Subclip 메타데이터 변경 → Parent Segment에 반영
- Parent Segment 메타데이터 변경 → Subclip에 반영
- **양방향 동기화**

### 5.3 Subclip 특징

| 항목 | 설명 |
|------|------|
| 유형 | Parent Asset의 Segment에서 파생된 **별도 Asset** |
| 파일 | 없음 (Parent Asset 참조) |
| 검색 | 독립적으로 검색 가능 (별도 인덱싱) |
| 타임코드 | **Asset 필드**에 저장 (Segment API 아님!) |

### 5.4 Parent Asset 삭제 시 영향

| Parent 작업 | Subclip 영향 |
|------------|-------------|
| Segment 삭제 | 관련 Subclip **삭제** |
| Asset 버전 삭제 | 해당 버전의 Subclip **삭제** |
| Asset 삭제 | 모든 Subclip **삭제** |

---

## 6. 데이터 흐름도

### 6.1 구조도

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Parent Asset (ASSET)                         │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Segment (GENERIC) - Timed Metadata                              │ │
│  │                                                                 │ │
│  │  • time_start_milliseconds: 136600                              │ │
│  │  • time_end_milliseconds: 513088                                │ │
│  │  • segment_type: "GENERIC"                                      │ │
│  │  • metadata_values: { Description, PlayersTags, ... }           │ │
│  └───────────────────────────┬────────────────────────────────────┘ │
│                              │                                       │
│                              │ 파생 (양방향 동기화)                  │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Subclip (SUBCLIP) - 별도 Asset                                  │ │
│  │                                                                 │ │
│  │  • id: "8ddb35e6-007e-11f0-8c20-aad6eb65bf32"                   │ │
│  │  • type: "SUBCLIP"                                              │ │
│  │  • time_start_milliseconds: 136600  ← Asset 필드!               │ │
│  │  • time_end_milliseconds: 513088    ← Asset 필드!               │ │
│  │  • 검색 가능 (별도 인덱싱)                                      │ │
│  │                                                                 │ │
│  │  ┌──────────────────────────────────────────────────────────┐  │ │
│  │  │ Segment (COMMENT) - 마커/코멘트                           │  │ │
│  │  │                                                          │  │ │
│  │  │  • time_start_milliseconds: 347300  ← 마커 위치!         │  │ │
│  │  │  • time_end_milliseconds: 347300                         │  │ │
│  │  │  • segment_type: "COMMENT"                               │  │ │
│  │  └──────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 작업자 워크플로우

```
1) Parent Asset에서 타임코드 구간 설정 (in/out point)
      ↓
2) Generic Segment 생성 + 메타데이터 입력
      ↓
3) Subclip 생성 (선택적)
      ↓
4) 결과:
   ├── Parent Asset: Segment에 타임코드 + 메타데이터
   └── Subclip: Asset 필드에 타임코드, 메타데이터는 Segment와 동기화
      ↓
5) Subclip에 코멘트/마커 추가 가능 (COMMENT Segment)
```

---

## 7. API 엔드포인트 요약

| 작업 | Method | Endpoint |
|------|--------|----------|
| **Asset 조회** | GET | `/assets/v1/assets/{id}/` |
| **Segment 목록** | GET | `/assets/v1/assets/{id}/segments/` |
| **Segment 생성** | POST | `/assets/v1/assets/{id}/segments/` |
| **Segment 수정** | PUT | `/assets/v1/assets/{id}/segments/{seg_id}/` |
| **메타데이터 조회** | GET | `/metadata/v1/assets/{id}/views/{view_id}/` |
| **메타데이터 수정** | PUT | `/metadata/v1/assets/{id}/views/{view_id}/` |

---

## 8. 검증된 Asset ID 목록

| Title | Iconik Asset ID | Type |
|-------|----------------|------|
| serock vs griff start from flop | `8ddb35e6-007e-11f0-8c20-aad6eb65bf32` | SUBCLIP |
| Phil Hellmuth Set over Set | `712e6a98-5ca5-11f0-bc74-aa6aabd2c9a2` | SUBCLIP |
| hellmuth tilted | `32725c7e-5caa-11f0-8166-ce6143467bb9` | SUBCLIP |
| Amarillo Slim | `b88deba2-63a3-11f0-967e-820d87a649a9` | SUBCLIP |

**Iconik 직접 링크**: `https://app.iconik.io/asset/{asset_id}`

---

## 9. 버그 수정 이력

### 9.1 v2.1 수정 완료 (2025-12-23)

**수정된 버그**:

| 버그 | 이전 | 수정 후 |
|------|------|---------|
| 타임코드 조회 | `segments[0]` (타입 무관) | GENERIC 타입만 필터링 |
| 메타데이터 조회 | `segment.metadata_values` (항상 비어있음) | Asset Metadata API 사용 |

**수정된 파일**:
- `sync/full_metadata_sync.py`: `_fetch_segments()`, `_fetch_metadata()` 수정
- `tests/unit/test_metadata_sync.py`: GENERIC Segment 필터링 테스트 추가

**검증 결과** (2,847 Assets):
- 메타데이터 성공: 2,434개 (85.5%)
- Segment 타임코드: 461개
- Subclip 타임코드: 1,171개
- GG 시트 대비 누락: 0건 ✅

---

## 10. 참고 자료

- [Subclips – iconik](https://help.iconik.backlight.co/hc/en-us/articles/25304106435863-Subclips)
- [Segments Entities – iconik](https://help.iconik.backlight.co/hc/en-us/articles/25304074513815-Segments-Entities)
- [Iconik API Documentation](https://app.iconik.io/docs/api.html)
