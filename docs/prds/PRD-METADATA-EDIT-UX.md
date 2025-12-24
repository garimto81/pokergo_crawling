# PRD: 메타데이터 편집 UX 최적화

> NAMS 시스템의 메타데이터 편집 기능 확장 및 마이그레이션 친화적 설계

**Version**: 1.0 | **Date**: 2025-12-19 | **Status**: Draft

---

## 1. 개요

### 1.1 프로젝트 배경

현재 NAMS 시스템에서 작업자가 메타데이터를 편집할 때 다음과 같은 문제점이 있습니다:

```
┌─────────────────────────────────────────────────────────────────┐
│                    현재 워크플로우 (Pain Points)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [작업자]                                                        │
│  ├─ MAM 솔루션 또는 구글 시트에서 파일 확인                       │
│  ├─ MAM 내장 플레이어 / 외부 플레이어로 영상 확인                 │
│  ├─ 메타데이터 수정 (카테고리, 제목)                              │
│  └─ ❌ 수정사항이 DB에 반영되지 않음                             │
│                                                                 │
│  [문제점]                                                        │
│  ├─ Google Sheets 편집 → DB 역동기화 없음                        │
│  ├─ NAMS UI에서 Catalog Title만 편집 가능                        │
│  ├─ Year, Region, EventType 수정 불가                           │
│  ├─ 변경 이력 추적 없음                                          │
│  └─ 마이그레이션 시 수정사항 반영 불가                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 핵심 목표

1. **편집 범위 확장**: Catalog Title 외에 Year, Region, EventType, Episode 편집 가능
2. **변경 추적**: 모든 메타데이터 변경을 Audit Log로 기록
3. **Google Sheets 연동**: 하이브리드 방식으로 양방향 동기화
4. **마이그레이션 친화적**: 변경사항이 마이그레이션에 반영 가능한 구조

### 1.3 성공 메트릭

| 지표 | 목표 |
|------|------|
| 메타데이터 편집 시간 | < 5초 (저장까지) |
| Sheets → DB 동기화 성공률 | > 99% |
| 변경 이력 추적 정확도 | 100% |
| 일괄 편집 지원 항목 수 | 최대 100개/배치 |

---

## 2. 현황 분석

### 2.1 현재 시스템 상태

| 항목 | 현재 상태 |
|------|----------|
| **Backend** | FastAPI + SQLAlchemy (SQLite) |
| **Frontend** | React 19 + Vite + TailwindCSS + Zustand |
| **편집 가능 필드** | Catalog Title (inline edit) |
| **Google Sheets** | DB → Sheets 단방향 (export_4sheets.py) |
| **변경 추적** | path_change만 (메타데이터 X) |

### 2.2 주요 문제점 (6개 Pain Points)

| # | 문제점 | 영향 |
|---|--------|------|
| 1 | Catalog Title만 편집 가능 | Year/Region/EventType 오류 수정 불가 |
| 2 | Google Sheets → DB 역동기화 없음 | Sheets 편집이 DB에 반영 안됨 |
| 3 | 변경 이력 추적 없음 | 누가/언제/무엇을 수정했는지 모름 |
| 4 | 일괄 편집 불가 | 100개 수정 시 100번 클릭 필요 |
| 5 | 승인 워크플로우 없음 | 잘못된 수정 방지 어려움 |
| 6 | CSV/JSON 내보내기 없음 | 마이그레이션 데이터 준비 어려움 |

### 2.3 권장 솔루션: 하이브리드 방식

```
┌─────────────────────────────────────────────────────────────────┐
│                    하이브리드 연동 방식                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [배치 동기화] (일일)                                            │
│  ├─ DB → Sheets                                                 │
│  ├─ 전체 파일 목록 + 메타데이터                                  │
│  └─ scripts/export_4sheets.py                                   │
│                                                                 │
│  [API 실시간] (메타데이터)                                       │
│  ├─ Sheets → DB (PATCH /groups/{id})                           │
│  ├─ Catalog Title, Year, Region, EventType                     │
│  └─ Google Apps Script 연동 (향후)                              │
│                                                                 │
│  [장점]                                                         │
│  ├─ 현재 구현 최소 변경                                          │
│  ├─ 개발 비용: 15-25시간 (vs 실시간 40-60시간)                  │
│  └─ 점진적 확장 가능                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 세부 요구사항

### 3.1 UI 편집 패턴 (4계층)

```
┌─────────────────────────────────────────────────────────────────┐
│                    4계층 UI 편집 패턴                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: 인라인 편집                                            │
│  ├─ 대상: Catalog Title, Notes                                  │
│  ├─ UX: Edit 아이콘 클릭 → 입력 → Save/Cancel                   │
│  └─ 위치: Groups 페이지 (기존 구현)                              │
│                                                                 │
│  Layer 2: 편집 모달 (EditEntryModal)                            │
│  ├─ 대상: Year, Region, EventType, Episode, Sequence           │
│  ├─ UX: 상세 버튼 → 모달 폼 → 유효성 검사 → Save               │
│  └─ 신규 컴포넌트 개발 필요                                      │
│                                                                 │
│  Layer 3: 슬라이드 패널                                          │
│  ├─ 대상: 카테고리 재할당                                        │
│  ├─ UX: 검색 + 미리보기 + 변경 전후 비교                        │
│  └─ 향후 구현 (Phase 3+)                                        │
│                                                                 │
│  Layer 4: 일괄 편집 (Batch Edit)                                │
│  ├─ 대상: 다중 entries 상태 변경                                 │
│  ├─ UX: 체크박스 선택 → 액션 → Preview → Apply                 │
│  └─ 최대 100개 항목 지원                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### EditEntryModal 필드 구성

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| display_title | 텍스트 | O | 표시 제목 (5-300자) |
| year | 숫자 | O | 연도 (1973-2099) |
| event_type | 드롭다운 | - | ME, BR, HR, HU, GM, FT, PPC |
| sequence | 숫자 | - | Day/Episode/Part 번호 |
| sequence_type | 드롭다운 | - | DAY, EPISODE, PART |
| notes | 텍스트 | - | 메모 (최대 1000자) |

### 3.2 Audit Log 설계

#### 테이블 스키마

```sql
CREATE TABLE entry_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL,          -- CategoryEntry FK
    field_name TEXT NOT NULL,           -- 변경된 필드명
    old_value TEXT,                     -- 이전 값
    new_value TEXT,                     -- 새 값
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by TEXT,                    -- 변경자 (user@example.com)
    change_reason TEXT,                 -- 변경 사유 (선택)
    source TEXT NOT NULL,               -- 'UI' | 'API' | 'SHEETS' | 'BATCH'

    FOREIGN KEY (entry_id) REFERENCES category_entries(id)
);

CREATE INDEX idx_audit_entry_id ON entry_audit_log(entry_id);
CREATE INDEX idx_audit_changed_at ON entry_audit_log(changed_at DESC);
```

#### 자동 기록 규칙

```python
def log_audit(entry_id: int, field: str, old: str, new: str,
              source: str, user: str = None):
    """모든 메타데이터 변경 시 자동 호출"""
    db.add(EntryAuditLog(
        entry_id=entry_id,
        field_name=field,
        old_value=str(old) if old else None,
        new_value=str(new) if new else None,
        source=source,
        changed_by=user or "system"
    ))
```

### 3.3 변경 승인 워크플로우

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   DRAFT     │───▶│   PENDING   │───▶│  APPROVED   │
│ (편집 중)   │    │  (검토 대기) │    │ (승인 완료)  │
└─────────────┘    └─────────────┘    └─────────────┘
       │                                     │
       │         ┌─────────────┐             │
       └────────▶│  REJECTED   │◀────────────┘
                 │ (반려, 재편집)│
                 └─────────────┘
```

| 상태 | 설명 | 전환 조건 |
|------|------|----------|
| DRAFT | 편집 중 (임시 저장) | Save Draft 클릭 |
| PENDING | 검토 대기 | Submit for Review 클릭 |
| APPROVED | 승인 완료 | 관리자 Approve 클릭 |
| REJECTED | 반려 | 관리자 Reject + 사유 입력 |

### 3.4 유효성 검사 규칙

| 필드 | 규칙 | 에러 메시지 |
|------|------|------------|
| display_title | required | "제목을 입력해주세요" |
| display_title | 5 ≤ length ≤ 300 | "5-300자로 입력해주세요" |
| display_title | `/\*?:<>\|` 금지 | "특수문자를 제거해주세요" |
| year | required | "연도를 입력해주세요" |
| year | 1973 ≤ value ≤ 2099 | "1973-2099 범위로 입력해주세요" |
| event_type | enum 값만 허용 | "올바른 이벤트 유형을 선택해주세요" |

### 3.5 Google Sheets 역동기화

#### 현재 구현 (단방향)

```
DB ──export_4sheets.py──▶ Google Sheets (5개 시트)
```

#### 목표 구현 (하이브리드)

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  [배치] (일일 오전 6시)                                       │
│  DB ──export_4sheets.py──▶ Sheets                           │
│                                                              │
│  [API] (실시간)                                              │
│  Sheets ──Google Apps Script──▶ PATCH /groups/{id}──▶ DB   │
│                           │                                  │
│                           └── 메타데이터 필드만               │
│                               (Catalog Title, Year 등)       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### 신규 API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| PATCH | `/api/groups/{id}` | 그룹 메타데이터 업데이트 |
| PATCH | `/api/groups/{id}/catalog-title` | 제목만 업데이트 |
| POST | `/api/groups/batch-update` | 일괄 업데이트 |
| GET | `/api/entries/{id}/audit-log` | 변경 이력 조회 |

---

## 4. 구현 계획

### 4.1 Phase 1: 기초 (1주)

| 작업 | 상세 | 산출물 |
|------|------|--------|
| Audit Log 테이블 | 스키마 생성 + SQLAlchemy 모델 | `models/audit_log.py` |
| EditEntryModal | React 컴포넌트 개발 | `components/EditEntryModal.tsx` |
| 유효성 검사 | Pydantic 스키마 확장 | `schemas/entry.py` |
| PATCH API | 메타데이터 업데이트 엔드포인트 | `routers/entries.py` |

### 4.2 Phase 2: 확장 (2주)

| 작업 | 상세 | 산출물 |
|------|------|--------|
| Batch Edit UI | 체크박스 선택 + 일괄 액션 | `components/BatchEditPanel.tsx` |
| Sheets → DB Import | 스크립트 개발 | `scripts/import_sheets_changes.py` |
| 충돌 감지 | Timestamp 기반 비교 | `services/sync_conflict.py` |
| 변경 이력 UI | Entry 상세 페이지 History 탭 | `pages/EntryDetail.tsx` |

### 4.3 Phase 3: 마이그레이션 (1주)

| 작업 | 상세 | 산출물 |
|------|------|--------|
| 승인 워크플로우 | 상태 관리 + UI | `components/ApprovalWorkflow.tsx` |
| CSV 내보내기 | 필터 + 다운로드 | `api/export.py` |
| JSON 내보내기 | 전체 데이터 + Audit Log | `api/export.py` |
| 마이그레이션 문서 | 가이드 작성 | `docs/MIGRATION_GUIDE.md` |

### 4.4 Phase 4: 최적화 (검증)

| 작업 | 상세 |
|------|------|
| Google Apps Script | Sheets 편집 → API 호출 자동화 |
| 성능 최적화 | 대량 데이터 처리 |
| 테스트 | E2E + 단위 테스트 |
| 배포 | 프로덕션 적용 |

---

## 5. 성공 기준

### 5.1 정량적 목표

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| 편집 시간 | < 5초 | UI 응답 시간 |
| 동기화 성공률 | > 99% | Sheets → DB 성공/실패 로그 |
| 변경 추적 정확도 | 100% | Audit Log 누락 없음 |
| 일괄 편집 처리량 | 100개/배치 | API 처리 성공률 |

### 5.2 품질 기준

| 항목 | 기준 |
|------|------|
| 유효성 검사 | 모든 필드에 적용 |
| 에러 처리 | 사용자 친화적 메시지 |
| 롤백 기능 | Audit Log 기반 복원 가능 |
| 테스트 커버리지 | > 80% |

---

## 6. 참고 자료

### 관련 문서

| 문서 | 설명 |
|------|------|
| [PRD-CATALOG-DB.md](./PRD-CATALOG-DB.md) | NAS 중심 카테고리 DB 설계 |
| [MATCHING_RULES.md](./MATCHING_RULES.md) | PokerGO 매칭 규칙 v5.11 |
| [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md) | 시스템 아키텍처 |

### 관련 파일

| 파일 | 용도 |
|------|------|
| `scripts/export_4sheets.py` | 현재 Sheets 내보내기 |
| `src/nams/api/routers/groups.py` | Groups API |
| `src/nams/ui/src/pages/Groups.tsx` | Groups 페이지 |

### 리서치 결과

| 파일 | 내용 |
|------|------|
| `.agent/results/result-001.yaml` | 시스템 구조 분석 |
| `.agent/results/result-002.yaml` | Sheets 연동 비교 |
| `.agent/results/result-003.yaml` | UI 패턴 설계 |

---

## 변경 이력

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-19 | 초기 작성 - 리서치 결과 기반 PRD |
