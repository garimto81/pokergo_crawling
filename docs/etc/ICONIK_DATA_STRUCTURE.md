# Iconik 데이터 구조 분석

> Iconik MAM 시스템의 Segment, Subclip, Metadata 구조 분석

**Version**: 1.0 | **Date**: 2025-12-22 | **Source**: [Iconik Help Documentation](https://help.iconik.backlight.co)

---

## 1. 개요

Iconik MAM에서 작업자들이 메타데이터를 입력하는 3가지 방식:

| 저장 방식 | API 엔드포인트 | 용도 |
|----------|---------------|------|
| **Segment Tags** | `/assets/v1/assets/{id}/segments/` | 타임코드 + 메타데이터 (Timed Metadata) |
| **Subclip** | `/assets/v1/assets/{id}/` (별도 Asset) | Segment에서 파생된 검색 가능한 Asset |
| **General Metadata** | `/metadata/v1/assets/{id}/views/{view_id}/` | Asset 레벨 메타데이터 |

---

## 2. Segment (Time-based Metadata)

### 2.1 정의

> **Segments are time-coded references to portions of an Asset.**
> Each segment has a timecode for it's in-point and a timecode for it's out-point.
> Typically segments are used for **Timed-metadata**, or metadata that lives at a particular point of an asset.

### 2.2 Segment Types

| Type | 용도 |
|------|------|
| **Generic** | Timed metadata 저장 (작업자가 29개 필드 입력) |
| Comments | iconik 코멘트 |
| Markers | 마커 |
| Quality Control Markers | QC 마커 |
| Transcription | 자막 |

### 2.3 API 구조

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
        "PlayersTags": {"field_values": [{"value": "Phil Ivey"}, {"value": "Daniel Negreanu"}]},
        ...
      }
    }
  ]
}
```

### 2.4 핵심 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `time_start_milliseconds` | Integer | 시작 시간 (밀리초) |
| `time_end_milliseconds` | Integer | 종료 시간 (밀리초) |
| `segment_type` | String | GENERIC, MARKER, QC, COMMENT 등 |
| `metadata_values` | Object | 29개 메타데이터 필드 (Generic 타입) |

---

## 3. Subclip (별도 Asset)

### 3.1 정의

> **Subclips are a special type of asset** that is derived from the time-based metadata segment of another asset of a particular version.

### 3.2 메타데이터 동기화

> **The metadata on Subclips are directly related to the time-based metadata and all metadata on the Subclip is cloned to the related time-based metadata segment on the parent asset.**

**핵심**: Subclip ↔ Parent Segment 간 **양방향 동기화**

### 3.3 Subclip 특징

| 항목 | 설명 |
|------|------|
| 유형 | Parent Asset의 Segment에서 파생된 **별도 Asset** |
| 파일 | 일반적으로 파일 없음 (API로 제공 가능) |
| 검색 | 독립적으로 검색 가능 (별도 인덱싱) |
| 메타데이터 | Parent Segment와 양방향 동기화 |

### 3.4 Subclip Sub-entities

Subclip에 저장 가능한 정보:
- Access Control
- Approval Status
- Formats
- History
- Posters
- Relationships (다른 Asset/Subclip과의 관계)
- Segments (단, Subclip의 Segment는 다시 Subclip 불가)
- Shares

### 3.5 Parent Asset 작업 영향

| Parent 작업 | Subclip 영향 |
|------------|-------------|
| Time-based metadata 삭제 | 관련 Subclip **삭제** |
| Asset 버전 삭제 | 해당 버전의 Subclip **삭제** |
| Asset 삭제 | 모든 Subclip **삭제** |

---

## 4. 데이터 흐름

### 4.1 구조도

```
┌─────────────────────────────────────────────────────────────────┐
│                      Parent Asset                               │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Segment (Generic Type = Timed Metadata)                  │   │
│  │                                                          │   │
│  │  • time_start_milliseconds                               │   │
│  │  • time_end_milliseconds                                 │   │
│  │  • segment_type: "GENERIC"                               │   │
│  │  • metadata_values: { 29개 필드 }                        │   │
│  │                                                          │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                         │                                       │
│                         │ 클론 (양방향 동기화)                  │
│                         ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Subclip (별도 Asset)                                     │   │
│  │                                                          │   │
│  │  • 독립적인 asset_id                                     │   │
│  │  • 검색 가능 (별도 인덱싱)                               │   │
│  │  • 파일/포맷 없음 (API로 제공 가능)                      │   │
│  │  • metadata_values: { Parent Segment와 동기화 }          │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 작업자 워크플로우

```
작업자가 Iconik UI에서:

1) Segment Panel에서 타임코드 설정 (in/out point)
      ↓
2) Generic Segment에 29개 메타데이터 필드 입력
      ↓
3) Subclip 생성 (선택적)
      ↓
4) 메타데이터 저장 위치:
   ├── Parent Asset의 Segment (metadata_values)
   └── Subclip (클론된 metadata_values)
      ↓
5) 이후 변경 시 양방향 동기화
```

---

## 5. 현재 시스템과의 Gap

### 5.1 현재 코드 동작

**파일**: `src/migrations/iconik2sheet/sync/full_metadata_sync.py:260-292`

```python
def _fetch_segments(asset_id, export_data):
    segments = iconik.get_asset_segments(asset_id)
    if segments:
        first_segment = segments[0]
        # 현재: 타임코드만 추출 ❌
        export_data["time_start_ms"] = first_segment.get("time_start_milliseconds")
        export_data["time_end_ms"] = first_segment.get("time_end_milliseconds")
        # metadata_values 추출 누락 ❌
```

### 5.2 Gap 분석

| 항목 | 현재 코드 | 실제 iconik 구조 |
|------|----------|-----------------|
| Segment 데이터 | 타임코드만 추출 | **타임코드 + metadata_values** |
| 메타데이터 위치 | Asset 레벨만 처리 | **Segment 레벨에 저장** |
| Subclip | 처리 안함 | 별도 Asset (Parent Segment와 동기화) |

### 5.3 필요한 수정

```python
def _fetch_segments(asset_id, export_data):
    segments = iconik.get_asset_segments(asset_id)
    if segments:
        first_segment = segments[0]

        # 타임코드
        export_data["time_start_ms"] = first_segment.get("time_start_milliseconds")
        export_data["time_end_ms"] = first_segment.get("time_end_milliseconds")

        # 메타데이터 (Generic Segment에서 추출) ✅
        metadata_values = first_segment.get("metadata_values", {})
        for field_name, field_data in metadata_values.items():
            export_data[field_name] = extract_field_values(field_data)
```

---

## 6. API 엔드포인트 요약

| 작업 | Method | Endpoint |
|------|--------|----------|
| Segment 조회 | GET | `/assets/v1/assets/{id}/segments/` |
| Segment 생성 | POST | `/assets/v1/assets/{id}/segments/` |
| Segment 업데이트 | PUT | `/assets/v1/assets/{id}/segments/{seg_id}/` |
| Asset 메타데이터 조회 | GET | `/metadata/v1/assets/{id}/views/{view_id}/` |
| Asset 메타데이터 업데이트 | PUT | `/metadata/v1/assets/{id}/views/{view_id}/` |
| Subclip 조회 | GET | `/assets/v1/assets/{subclip_id}/` |

---

## 7. 참고 자료

- [Subclips – iconik](https://help.iconik.backlight.co/hc/en-us/articles/25304106435863-Subclips)
- [Segments Entities – iconik](https://help.iconik.backlight.co/hc/en-us/articles/25304074513815-Segments-Entities)
- [Iconik API Documentation](https://app.iconik.io/docs/api.html)
