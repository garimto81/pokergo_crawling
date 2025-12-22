# PRD: Iconik 역방향 타임코드 동기화

**Version**: 1.0
**Date**: 2025-12-21
**Status**: Draft (구현 보류)
**Author**: Claude Code

---

## 1. 개요

### 1.1 목적

GGmetadata_and_timestamps 시트의 타임코드를 Iconik Segments API로 업로드하여 1,034건의 누락된 타임코드를 복구합니다.

### 1.2 배경

| 항목 | 내용 |
|------|------|
| 문제 | Iconik 2,840개 Asset 중 1,034개(36.4%)에 타임코드 부재 |
| 원인 | Iconik Segments API에 데이터 없음 |
| 해결 | GGmetadata 시트 → Iconik Segments API 역방향 동기화 |
| 선행 문서 | `PRD-ICONIK-METADATA-GAP.md` (Phase 2) |

### 1.3 범위

- iconik2sheet 모듈에 역방향 동기화 기능 추가
- Iconik Segments API POST/PUT 구현
- GGmetadata 시트 읽기 기능 추가

---

## 2. 아키텍처

```
┌─────────────────────────┐       ┌─────────────────────────┐
│  GGmetadata_and_        │       │  Iconik MAM System      │
│  timestamps 시트        │       │  Segments API           │
│  (Source of Truth)      │       │  (Target)               │
│                         │       │                         │
│  - id (Asset ID)        │ ────► │  POST /assets/v1/       │
│  - time_start_ms        │       │  assets/{id}/segments   │
│  - time_end_ms          │       │                         │
└─────────────────────────┘       └─────────────────────────┘
            │                               ▲
            │     ┌─────────────────────┐   │
            └────►│ ReverseTimecodeSync │───┘
                  │ (신규 모듈)         │
                  └─────────────────────┘
```

---

## 3. 구현 단계

### Phase 1: IconikClient 확장 (POST/PUT 메서드)

**파일**: `src/migrations/iconik2sheet/iconik/client.py`

추가할 메서드:
- `_post(endpoint, json)` - POST 요청 + 에러 처리
- `_put(endpoint, json)` - PUT 요청 + 에러 처리
- `create_segment(asset_id, time_base, time_end)` - 세그먼트 생성
- `update_segment(asset_id, segment_id, ...)` - 세그먼트 업데이트
- `upsert_segment(asset_id, time_base, time_end)` - 멱등성 보장

**참고 패턴**: `src/migrations/sheet2iconik/clients/iconik_client.py`
- tenacity 재시도 로직 (3회, 지수 백오프)

### Phase 2: SheetsReader 추가

**파일**: `src/migrations/iconik2sheet/sheets/reader.py` (신규)

- Google Sheets 읽기 클라이언트
- `read_ggmetadata(spreadsheet_id)` - GGmetadata 시트 읽기
- 기존 writer.py 패턴 활용

### Phase 3: 역방향 동기화 로직

**파일**: `src/migrations/iconik2sheet/sync/reverse_timecode_sync.py` (신규)

```python
class ReverseTimecodeSync:
    """GGmetadata → Iconik 역방향 타임코드 동기화"""

    def run(self, dry_run: bool = True) -> dict:
        # 1. GGmetadata 시트 읽기
        # 2. 타임코드 있는 행 필터링
        # 3. Iconik에 세그먼트 없는 Asset 식별
        # 4. 세그먼트 생성/업데이트 (upsert)
        # 5. 결과 보고서 반환
```

### Phase 4: CLI 스크립트

**파일**: `src/migrations/iconik2sheet/scripts/run_reverse_sync.py` (신규)

```powershell
# Dry run (기본)
python -m scripts.run_reverse_sync

# Live 실행
python -m scripts.run_reverse_sync --live
```

### Phase 5: 예외 클래스 추가

**파일**: `src/migrations/iconik2sheet/iconik/exceptions.py`

추가: `IconikConflictError` (409 Conflict)

---

## 4. 핵심 파일 목록

| 파일 | 작업 | 변경 내용 |
|------|------|----------|
| `iconik/client.py` | 수정 | `_post`, `_put`, `upsert_segment` 추가 |
| `iconik/exceptions.py` | 수정 | `IconikConflictError` 추가 |
| `sheets/reader.py` | 신규 | Google Sheets 읽기 클라이언트 |
| `sync/reverse_timecode_sync.py` | 신규 | 역방향 동기화 로직 |
| `scripts/run_reverse_sync.py` | 신규 | CLI 엔트리포인트 |
| `tests/unit/test_reverse_sync.py` | 신규 | 단위 테스트 |

---

## 5. 데이터 매핑

| GGmetadata 컬럼 | Iconik Segment 필드 | 비고 |
|-----------------|---------------------|------|
| id | asset_id (URL param) | Asset UUID |
| time_start_ms | time_base | 밀리초 정수 |
| time_end_ms | time_end | 밀리초 정수 |
| (없음) | segment_type | "GENERIC" 고정 |

---

## 6. 멱등성 전략

```
upsert_segment(asset_id, time_base, time_end):
    1. GET /assets/{id}/segments/
       ├─ 404 또는 빈 리스트 → POST (생성)
       └─ 세그먼트 존재 → PUT (업데이트)
    2. 결과 반환: (segment, created: bool)
```

| 시나리오 | 동작 | 결과 |
|----------|------|------|
| 첫 실행 | POST 생성 | created = True |
| 재실행 (동일 값) | PUT 업데이트 | updated = True |
| Asset 삭제됨 | 404 에러 | failed += 1 |

---

## 7. 에러 처리

| 에러 유형 | HTTP 코드 | 처리 |
|-----------|-----------|------|
| 인증 실패 | 401/403 | 즉시 중단 |
| Asset 없음 | 404 | 스킵, 로깅 후 계속 |
| 충돌 | 409 | GET 재조회 → PUT 시도 |
| Rate Limit | 429 | tenacity 재시도 (3회) |
| 서버 에러 | 5xx | 재시도 후 스킵 |

**전략**: "Fail Forward" - 실패한 Asset은 로깅 후 계속 진행

---

## 8. 테스트 계획

### 단위 테스트 (`tests/unit/test_reverse_sync.py`)

- `test_has_timecode_with_both_values` - 타임코드 존재 여부
- `test_upsert_creates_when_no_existing` - 생성 로직
- `test_upsert_updates_when_exists` - 업데이트 로직

### 통합 테스트

```powershell
# 1. Dry run 테스트
python -m scripts.run_reverse_sync

# 2. Live 실행 후 검증
python -m scripts.run_reverse_sync --live
python -m scripts.run_full_metadata  # 타임코드 다시 추출
```

---

## 9. 실행 순서

```powershell
# 작업 디렉토리
cd D:\AI\claude01\pokergo_crawling\src\migrations\iconik2sheet

# 1. Phase 1: IconikClient 확장
#    - client.py에 _post, _put, upsert_segment 추가

# 2. Phase 2: SheetsReader 추가
#    - sheets/reader.py 생성

# 3. Phase 3: ReverseTimecodeSync 구현
#    - sync/reverse_timecode_sync.py 생성

# 4. Phase 4: CLI 스크립트
#    - scripts/run_reverse_sync.py 생성

# 5. TDD 테스트
pytest tests/unit/test_reverse_sync.py -v

# 6. Dry Run
python -m scripts.run_reverse_sync

# 7. Live 실행 (확인 후)
python -m scripts.run_reverse_sync --live

# 8. 결과 검증
python -m scripts.run_full_metadata
```

---

## 10. 성공 지표

| 지표 | 목표값 |
|------|--------|
| 생성 성공률 | >= 95% |
| 처리 시간 | < 30분 |
| 에러율 | < 5% |
| 멱등성 | 재실행 시 동일 결과 |

---

## 11. 리스크

| 리스크 | 대응 |
|--------|------|
| Iconik API Rate Limit | tenacity 재시도 + 배치 간 sleep |
| Asset ID 불일치 | 사전 검증 단계 추가 |
| 잘못된 타임코드 값 | 정수 변환 검증, 음수/0 체크 |
| API 인증 만료 | 실행 전 health_check |

---

## 12. 전제 조건 (구현 전 확인 필요)

| 항목 | 상태 | 비고 |
|------|------|------|
| Iconik API POST 권한 | 미확인 | App-ID/Auth-Token 쓰기 권한 필요 |
| GGmetadata 시트 접근 | 확인됨 | 스프레드시트 ID: 1pUMPKe... |
| 서비스 계정 권한 | 확인됨 | 읽기/쓰기 권한 있음 |

---

## 13. 관련 문서

| 문서 | 내용 |
|------|------|
| `PRD-ICONIK-METADATA-GAP.md` | 메타데이터 갭 분석 (Phase 2가 역방향 동기화) |
| `src/migrations/iconik2sheet/CLAUDE.md` | iconik2sheet 모듈 가이드 |
| `src/migrations/sheet2iconik/CLAUDE.md` | sheet2iconik 모듈 가이드 (참고 패턴) |

---

## 14. 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2025-12-21 | 초안 작성 (구현 보류) |
