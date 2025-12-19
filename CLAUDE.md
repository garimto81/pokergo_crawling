# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NAMS (NAS Asset Management System) - WSOP 영상 파일 통합 관리 및 PokerGO 메타데이터 매칭 시스템.

**Version**: 2.1.0 | **Date**: 2025-12-19

**핵심 기능:**
- NAS 파일 스캔 및 메타데이터 추출 (Y:/Z:/X: 드라이브)
- 정규식 기반 패턴 매칭 (33개 패턴)
- Era별 카탈로그 생성 (CLASSIC/BOOM/HD)
- PokerGO 에피소드 자동 매칭 (828개 비디오)
- Netflix 스타일 제목 생성
- Google Sheets 내보내기

## Quick Start

```powershell
# NAMS 시스템 실행 (터미널 2개)
cd src/nams/api && uvicorn main:app --reload --port 8001
cd src/nams/ui && npm run dev -- --port 5174

# NAS 스캔 (전체)
python scripts/scan_nas.py --mode full --folder all

# Google Sheets 내보내기
python scripts/export_4sheets.py
```

## Port Mapping

| 서비스 | 포트 | URL |
|--------|------|-----|
| NAMS API | 8001 | http://localhost:8001/docs |
| NAMS UI | 5174 | http://localhost:5174 |

## Architecture

```
src/nams/
├── api/                           # FastAPI 백엔드 (포트 8001)
│   ├── main.py                    # 앱 엔트리포인트
│   ├── database/                  # SQLAlchemy 모델, 세션, 초기화
│   ├── routers/                   # API 엔드포인트 (files, groups, patterns, process, stats)
│   └── services/                  # 비즈니스 로직
│       ├── pattern_engine.py      # ⭐ 핵심: 정규식 패턴 매칭 엔진
│       ├── scanner.py             # NAS 스캔
│       ├── grouping.py            # Primary/Backup 그룹핑
│       ├── matching_v2.py         # PokerGO 매칭 (Era별)
│       └── export.py              # Google Sheets/CSV/JSON 내보내기
│
└── ui/                            # React 프론트엔드 (포트 5174)
    └── src/pages/                 # Dashboard, Files, Groups, Patterns, Entries, Validator
```

## Data Flow

```
NAS Drives (Y:/Z:/X:)
        │
        ▼
    [Scanner] ──▶ SQLite DB (data/nams/nams.db)
        │              │
        │              ▼
        │        [Pattern Engine] ──▶ 메타데이터 추출 (year, region, event_type, episode)
        │              │
        │              ▼
        │        [Matching Service] ◀── PokerGO 데이터 (data/pokergo/wsop_final.json)
        │              │
        ▼              ▼
    [Export] ──▶ Google Sheets (5시트)
```

## Key Data Models

| 모델 | 설명 |
|------|------|
| **NasFile** | NAS 파일 메타데이터 + 패턴 매칭 결과, `is_excluded` 플래그 |
| **Pattern** | DB 기반 정규식 패턴 정의, 우선순위로 적용 |
| **FileGroup** | 동일 콘텐츠 Asset Group (Primary/Backup 역할) |
| **CatalogEntry** | Era별 카탈로그 엔트리 (Netflix 스타일 제목) |
| **Region** | 지역 (LV, EU, APAC, PARADISE, CYPRUS, LONDON, LA) |
| **EventType** | 이벤트 타입 (ME, BR, HR, GM, HU 등) |
| **Era** | 시대 구분 (CLASSIC/BOOM/HD) |

## Commands

### Backend

```powershell
# Lint
ruff check src/nams/ --fix

# API 서버 실행
cd src/nams/api && uvicorn main:app --reload --port 8001

# 테스트 (개별 파일 권장 - 전체 테스트 120초 초과 시 타임아웃)
pytest tests/test_specific.py -v
pytest tests/test_pattern_engine.py -v

# 패턴 엔진 테스트 (스크립트)
python scripts/test_pattern_engine.py

# DB 초기화 (API 서버 시작 시 자동 실행, 수동 시)
python -c "from src.nams.api.database.init_db import init_db; init_db()"
```

### Frontend

```powershell
cd src/nams/ui

# 개발 서버
npm run dev -- --port 5174

# 빌드
npm run build

# Lint
npm run lint

# E2E 테스트 (Playwright)
npm run test:e2e
npm run test:e2e:ui  # UI 모드
```

### Scripts

| Script | Purpose |
|--------|---------|
| `scan_nas.py` | NAS 스캔 (`--mode full/incremental`, `--folder origin/archive/pokergo/all`) |
| `export_4sheets.py` | Google Sheets 5시트 내보내기 |
| `match_pokergo_nas.py` | PokerGO-NAS 매칭 |
| `test_pattern_engine.py` | 패턴 엔진 테스트 |
| `create_master_catalog.py` | Era별 Master 카탈로그 생성 |
| `run_title_generation.py` | Netflix 스타일 제목 생성 |
| `match_classic.py` | CLASSIC Era (1973-2002) 매칭 |
| `match_boom.py` | BOOM Era (2003-2010) 매칭 |
| `match_hd.py` | HD Era (2011-2025) 매칭 |
| `match_YYYY.py` | 연도별 개별 매칭 (2003-2025) |

## Data Storage

```
data/
├── nams/nams.db                   # SQLite 데이터베이스
└── pokergo/
    └── wsop_final.json            # PokerGO WSOP 데이터 (828개)
```

## Key Design Decisions

1. **Full-path pattern matching**: 파일명 + 전체 경로로 패턴 매칭
2. **Config-driven patterns**: DB에서 패턴 관리, 코드 수정 없이 패턴 추가/수정
3. **Primary/Backup grouping**: 확장자 우선순위로 동일 콘텐츠 그룹화 (mp4 > mov > mxf)
4. **Three-drive support**: Origin(Y:), Archive(Z:), PokerGO Source(X:)

## Pattern Matching Rules

상세 규칙: [docs/MATCHING_RULES.md](docs/MATCHING_RULES.md) (v5.11)

**패턴 추출률**: 97.6% (1,371/1,405 파일) - 파일명에서 메타데이터 추출 성공률
**PokerGO 매칭률**: 53.3% (440/826 그룹) - Asset Group과 PokerGO 에피소드 매칭률

**주요 패턴 (33개):**
- `WS{YY}_{TYPE}{EP}` → WS11_ME25 = 2011 Main Event Ep.25
- `WSOP{YY}_{TYPE}{EP}` → WSOP13_ME01 = 2013 Main Event Ep.01
- `WSOPE{YY}_Episode_{EP}` → WSOPE08_Episode_5 = 2008 Europe Ep.5
- `WSOP_YYYY-NN.mxf` → 경로 폴더에서 Event Type 추출
- `YYYY WSOP MEXX` → 2009 WSOP ME01 = 2009 Main Event Ep.1
- `ESPN YYYY WSOP SHOW N` → ESPN 2007 WSOP SHOW 1

**Era 분류 (카탈로그 생성):**

| Era | 연도 | 특징 | 카탈로그 |
|-----|------|------|----------|
| CLASSIC | 1973-2002 | Main Event Only | 연도별 1개 |
| BOOM | 2003-2010 | 포커 붐, ESPN | 다양한 이벤트 |
| HD | 2011-2025 | PokerGO 스트리밍 | 상세 매칭 |

**제외 조건:** Size < 1GB, Duration < 30min, `clip`, `hand_`, `circuit` 포함

**GOG 버전 우선순위:** 찐최종 > 수정본2 > 수정본 > 원본 (PRIMARY는 1개만)

## Matching Categories (4분류)

| 분류 | 설명 |
|------|------|
| **MATCHED** | NAS + PokerGO 매칭 완료 |
| **NAS_ONLY_HISTORIC** | 1973-2002 (PokerGO 데이터 없음) |
| **NAS_ONLY_MODERN** | APAC/PARADISE/CYPRUS/LONDON/LA (PokerGO 없음) |
| **POKERGO_ONLY** | PokerGO만 존재 |

## DUPLICATE 방지 규칙

**1. Region Mismatch**
- EU/APAC/PARADISE/CYPRUS/LONDON/LA 그룹 → LV 에피소드 매칭 금지
- LV 그룹 → Regional 에피소드 매칭 금지

**2. Event # 필수 매칭**
- Bracelet Event(BR)에서 group_event_num 있으면 반드시 일치해야 매칭

**3. LA Circuit vs Ladies**
- LA = Los Angeles Circuit (PokerGO 없음)
- Ladies = LV Bracelet Event #71 (PokerGO 있음)

**4. NAS_ONLY 보호**
- NAS_ONLY_HISTORIC, NAS_ONLY_MODERN 그룹은 재매칭에서 제외

## Tech Stack

| 영역 | 기술 |
|------|------|
| **백엔드** | Python 3.11+, FastAPI, SQLAlchemy 2.0, SQLite |
| **프론트엔드** | React 19, Vite, TanStack Query, Zustand, TailwindCSS |
| **테스트** | Playwright (E2E) |
| **도구** | ruff (린터), uvicorn (ASGI) |

## Documentation

| 카테고리 | 문서 | 내용 |
|----------|------|------|
| **Architecture** | `docs/SYSTEM_OVERVIEW.md` | 시스템 아키텍처 (v2.1) |
| **PRD** | `docs/PRD-NAMS-MATCHING.md` | 매칭 시스템 PRD (v2.0) |
| | `docs/PRD-CATALOG-DB.md` | 카탈로그 DB PRD |
| **Technical** | `docs/MATCHING_RULES.md` | 매칭 규칙 핵심 (v5.11) |
| | `docs/MATCHING_PATTERNS_DETAIL.md` | 패턴 상세, 변경 이력 |
| | `docs/NAS_DRIVE_STRUCTURE.md` | X:/Y:/Z: 드라이브 폴더 구조 |
| **Operations** | `docs/AUTOMATION_PIPELINE.md` | 파이프라인 실행, 트러블슈팅 |
| | `docs/DASHBOARD_GUIDE.md` | UI 사용 가이드 |

## Troubleshooting

| 문제 | 원인 | 해결 |
|------|------|------|
| NAS 드라이브 접근 불가 | 네트워크 마운트 해제 | Y:/Z:/X: 드라이브 마운트 확인 |
| 패턴 매칭 실패 | 새 파일명 패턴 | `test_pattern_engine.py` 실행, 패턴 추가 |
| DB 손상/초기화 필요 | 스키마 변경 | `data/nams/nams.db` 삭제 후 API 재시작 |
| API 서버 시작 실패 | 포트 충돌 | `netstat -ano | findstr 8001` 확인 |
| 전체 테스트 타임아웃 | 120초 제한 | 개별 테스트 파일로 실행 권장 |
| 매칭률 저하 | Region/Event 불일치 | `docs/MATCHING_RULES.md` DUPLICATE 방지 규칙 확인 |

## 작업 관리 워크플로우

### 체크리스트 파일
- **위치**: `pokergo_crawling_checklist.yaml`
- **용도**: 모든 작업 추적 및 결과 기록
- **구조**: current_task, tasks (완료), pending_tasks (대기), stats

### 작업 처리 프로세스

```
1. 작업 시작 → yaml에서 pending_tasks 확인
2. 에이전트 할당 → 적절한 서브 에이전트 선택
3. 작업 실행 → 서브 에이전트가 처리
4. 결과 기록 → yaml 파일에 결과 업데이트
5. 상태 확인 → 완료 후 yaml 파일 검토
```

### 서브 에이전트 매핑

| 카테고리 | 에이전트 | 용도 |
|----------|----------|------|
| feature | general-purpose, backend-dev | 새 기능 개발 |
| test | test-engineer | E2E/단위 테스트 |
| refactoring | code-reviewer | 코드 개선 |
| bugfix | debugger | 버그 수정 |
| docs | docs-writer | 문서 작성 |

### yaml 파일 업데이트 규칙

**작업 시작 시:**
```yaml
current_task:
  id: "TASK-XXX"
  title: "작업 제목"
  status: "in_progress"
  started_at: "YYYY-MM-DDTHH:MM:SS"
  agent: "에이전트명"
```

**작업 완료 시:**
```yaml
# current_task를 null로 변경
current_task: null

# tasks 목록에 완료 정보 추가
tasks:
  - id: "TASK-XXX"
    status: "completed"
    completed_at: "YYYY-MM-DDTHH:MM:SS"
    result:
      success: true/false
      message: "결과 요약"
      files_changed: [...]
      commits: [...]

# stats 업데이트
stats:
  completed: N+1
```
