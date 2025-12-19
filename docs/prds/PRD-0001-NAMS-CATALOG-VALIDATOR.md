# PRD: NAMS Catalog Validator

**Version**: 1.0
**Date**: 2024-12-19
**Status**: Approved

---

## 1. 개요

NAMS(NAS Asset Management System)을 확장하여 카탈로그 검증 기능을 추가합니다.

### 1.1 핵심 기능
- **일일 자동 스캔**: Windows Task Scheduler로 매일 NAS 스캔
- **경로 변경 추적**: 파일 이동/삭제 감지 및 기록
- **검증 UI**: 영상 재생 → 제목/카테고리 확인 → 수정
- **Google Sheets 동기화**: 변경사항 자동 반영

### 1.2 요구사항 정리
| 항목 | 결정 |
|------|------|
| 플랫폼 | Web App (기존 NAMS UI 확장) |
| 영상 재생 | **시스템 기본 플레이어** (os.startfile) |
| 수정 범위 | 제목(display_title), 카테고리만 |
| 스케줄러 | Windows Task Scheduler |

> **영상 재생 설계**: VLC/PotPlayer 의존성 없이, 해당 장비에 설정된 기본 플레이어로 재생. Windows 탐색기 더블클릭과 동일한 동작.

---

## 2. 아키텍처

### 2.1 새로운 파일 구조

```
src/nams/api/
├── routers/
│   └── validator.py          [NEW] 검증 API
├── services/
│   ├── validator_service.py  [NEW] 검증 비즈니스 로직
│   └── change_tracker.py     [NEW] 경로 변경 추적
└── database/
    └── models.py             [MODIFY] ScanHistory 모델 추가

src/nams/ui/src/
├── pages/
│   └── Validator.tsx         [NEW] 검증 UI 페이지
└── components/validator/
    ├── EntryCard.tsx         [NEW] 검증 카드
    ├── VideoPlayer.tsx       [NEW] 재생 버튼 컴포넌트
    └── ChangeHistory.tsx     [NEW] 변경 이력

scripts/
├── daily_scan.py             [NEW] 일일 스캔 스크립트
└── sync_sheets.py            [NEW] Sheets 동기화
```

### 2.2 데이터 흐름

```
[Daily Scan - 매일 03:00]
Windows Task Scheduler → daily_scan.py
    ├── NAS 드라이브 스캔 (Y:/Z:/X:)
    ├── 새 파일 → DB INSERT + 패턴 매칭
    ├── 경로 변경 → path_history 기록
    └── 삭제 파일 → is_missing 플래그

[검증 워크플로우]
User → Validator UI
    ├── 미검증 항목 조회 (verified=false)
    ├── 영상 재생 버튼 → 시스템 기본 플레이어 실행
    ├── 제목/카테고리 수정 → AuditLog 기록
    └── 검증 완료 → verified=true

[Sheets 동기화]
변경 감지 → sync_sheets.py → Master_Catalog 업데이트
```

---

## 3. API 엔드포인트

### 3.1 검증 API (`/api/validator`)

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/pending` | 미검증 항목 목록 (페이지네이션) |
| GET | `/entry/{id}` | Entry 상세 (파일 목록 + 변경 이력) |
| PATCH | `/entry/{id}` | 제목/카테고리 수정 |
| POST | `/entry/{id}/verify` | 검증 완료 처리 |
| POST | `/entry/{id}/play` | 시스템 기본 플레이어로 재생 (os.startfile) |
| GET | `/stats` | 검증 진행 통계 |

### 3.2 스케줄러 API (`/api/scheduler`)

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/status` | 마지막 스캔 결과 |
| POST | `/run` | 수동 스캔 트리거 |
| GET | `/history` | 스캔 이력 |

---

## 4. 데이터 모델

### 4.1 새 모델: ScanHistory

```python
class ScanHistory(Base):
    __tablename__ = 'scan_history'

    id = Column(Integer, primary_key=True)
    scan_type = Column(String(20))  # daily, manual, full
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    status = Column(String(20))  # running, completed, failed

    new_files = Column(Integer, default=0)
    updated_files = Column(Integer, default=0)
    missing_files = Column(Integer, default=0)
    path_changes = Column(Integer, default=0)

    error_message = Column(Text)
    scanned_drives = Column(String(50))
```

### 4.2 기존 모델 활용
- `CategoryEntry`: verified, verified_at, verified_by 필드 활용
- `NasFile`: path_history, last_seen_at 필드 활용
- `AuditLog`: 변경 이력 자동 기록

---

## 5. UI 설계

### 5.1 Validator 페이지 레이아웃

```
┌─────────────────────────────────────────────────────────┐
│ Catalog Validator                    [Stats: 50/1056]   │
├─────────────────────────────────────────────────────────┤
│ [Year ▼] [Category ▼] [Status ▼] [Search] [Refresh]    │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐ │
│ │ WSOP_2024_ME_D1                              [1/50] │ │
│ │                                                     │ │
│ │ Display Title: [________________________]          │ │
│ │ PokerGO Title: 2024 WSOP Main Event Day 1          │ │
│ │ Category: [WSOP 2024 ▼]                            │ │
│ │                                                     │ │
│ │ Files:                                             │ │
│ │ ├─ [▶ 재생] Y:/2024_ME_D1.mp4 (45.2 GB)           │ │
│ │ └─ [▶ 재생] Z:/2024_ME_D1.mov (48.1 GB)           │ │
│ │                                                     │ │
│ │ [< Prev] [Skip] [Save] [Verify & Next >]           │ │
│ └─────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│ Recent Changes                                          │
│ - 2024-12-19 14:30 Title changed...                    │
└─────────────────────────────────────────────────────────┘
```

### 5.2 키보드 단축키
- `N`: 다음 항목
- `P`: 이전 항목
- `Enter`: 검증 완료
- `Ctrl+S`: 저장

---

## 6. 스케줄러 구성

### 6.1 daily_scan.py

```python
"""
Windows Task Scheduler로 매일 03:00에 실행

Usage:
    python scripts/daily_scan.py --mode daily
    python scripts/daily_scan.py --mode full --drives Y:,Z:,X:
"""

def main():
    # 1. 로그 설정
    # 2. NAS 스캔 (기존 scanner.py 활용)
    # 3. 새 파일 감지 → DB INSERT
    # 4. 경로 변경 감지 → path_history 업데이트
    # 5. 삭제 파일 감지 → is_missing 플래그
    # 6. ScanHistory 기록
    # 7. 변경사항 있으면 Sheets 동기화 트리거
```

### 6.2 Task Scheduler 설정

```
Trigger: Daily 03:00 AM
Action: python D:\AI\claude01\pokergo_crawling\scripts\daily_scan.py --mode daily
Working Dir: D:\AI\claude01\pokergo_crawling
```

---

## 7. 구현 계획

### Phase 1: 핵심 기능 (2일)
1. `ScanHistory` 모델 추가
2. `validator.py` 라우터 (pending, update, verify)
3. `Validator.tsx` 기본 UI

### Phase 2: 영상 재생 연동 (0.5일)
1. `/play` 엔드포인트 (`os.startfile()` - 시스템 기본 플레이어)
2. `VideoPlayer.tsx` 컴포넌트 (재생 버튼만)
3. VLC/PotPlayer 설정 불필요 - 각 장비 기본 프로그램 사용

### Phase 3: 스케줄러 (1일)
1. `daily_scan.py` 스크립트
2. 경로 변경 추적 로직
3. Task Scheduler 등록

### Phase 4: Sheets 동기화 (1일)
1. `sync_sheets.py` 스크립트
2. 변경사항만 부분 업데이트

---

## 8. 수정할 파일 목록

### 백엔드
| 파일 | 작업 |
|------|------|
| `src/nams/api/database/models.py` | ScanHistory 모델 추가 |
| `src/nams/api/routers/validator.py` | [NEW] 검증 API |
| `src/nams/api/services/validator_service.py` | [NEW] 검증 로직 |
| `src/nams/api/main.py` | validator 라우터 등록 |

### 프론트엔드
| 파일 | 작업 |
|------|------|
| `src/nams/ui/src/pages/Validator.tsx` | [NEW] 검증 페이지 |
| `src/nams/ui/src/components/validator/*.tsx` | [NEW] 컴포넌트들 |
| `src/nams/ui/src/api/client.ts` | validator API 추가 |
| `src/nams/ui/src/App.tsx` | 라우트 추가 |

### 스크립트
| 파일 | 작업 |
|------|------|
| `scripts/daily_scan.py` | [NEW] 일일 스캔 |
| `scripts/sync_sheets.py` | [NEW] Sheets 동기화 |

---

## 9. 성공 지표

| 지표 | 목표 |
|------|------|
| 일일 스캔 성공률 | 99% |
| 검증 처리량 | 50건/시간 |
| Sheets 동기화 지연 | < 5분 |
| UI 응답 시간 | < 500ms |

---

## 10. 다음 단계

1. ~~PRD 승인~~ ✅
2. Phase 1 구현 시작
3. `/work` 명령으로 이슈 생성 및 개발 진행
