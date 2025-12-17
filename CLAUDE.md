# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NAMS (NAS Asset Management System) - WSOP 영상 파일 통합 관리 및 PokerGO 메타데이터 매칭 시스템.

**핵심 기능:**
- NAS 파일 스캔 및 메타데이터 추출 (Y:/Z:/X: 드라이브)
- 정규식 기반 패턴 매칭 (WSOP, Europe, APAC, Paradise)
- PokerGO 에피소드 자동 매칭 (828개 비디오)
- Google Sheets 5시트 내보내기

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
├── api/                           # FastAPI 백엔드
│   ├── main.py                    # FastAPI 앱 엔트리포인트
│   ├── database/
│   │   ├── models.py              # SQLAlchemy 모델 (NasFile, Pattern, FileGroup)
│   │   ├── session.py             # DB 세션 관리
│   │   └── init_db.py             # 초기 데이터 (패턴, 지역, 이벤트 타입)
│   ├── routers/                   # API 엔드포인트
│   │   ├── files.py               # 파일 CRUD
│   │   ├── groups.py              # Asset Group 관리
│   │   ├── patterns.py            # 패턴 관리
│   │   ├── process.py             # 스캔/내보내기
│   │   └── stats.py               # 통계
│   └── services/                  # 비즈니스 로직
│       ├── pattern_engine.py      # 핵심: 정규식 패턴 매칭 엔진
│       ├── scanner.py             # NAS 스캔 서비스
│       ├── grouping.py            # Asset Grouping (Primary/Backup)
│       ├── matching.py            # PokerGO 매칭 서비스
│       └── export.py              # Google Sheets/CSV/JSON 내보내기
│
└── ui/                            # React 프론트엔드
    └── src/
        ├── pages/                 # Dashboard, Files, Groups, Patterns
        └── components/
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
| **Region** | 지역 (LV, EU, APAC, PARADISE, CYPRUS, LONDON, LA) |
| **EventType** | 이벤트 타입 (ME, BR, HR, GM, HU 등) |

## Commands

### Backend

```powershell
# Lint
ruff check src/nams/ --fix

# API 서버 실행
cd src/nams/api && uvicorn main:app --reload --port 8001

# 패턴 엔진 테스트
python scripts/test_pattern_engine.py
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

상세 규칙: [docs/MATCHING_RULES.md](docs/MATCHING_RULES.md) (v5.0)

**매칭률: 97.6%** (1,371/1,405 파일)

**주요 패턴 (33개):**
- `WS{YY}_{TYPE}{EP}` → WS11_ME25 = 2011 Main Event Ep.25
- `WSOP{YY}_{TYPE}{EP}` → WSOP13_ME01 = 2013 Main Event Ep.01
- `WSOPE{YY}_Episode_{EP}` → WSOPE08_Episode_5 = 2008 Europe Ep.5
- `WSOP_YYYY-NN.mxf` → 경로 폴더에서 Event Type 추출
- `YYYY WSOP MEXX` → 2009 WSOP ME01 = 2009 Main Event Ep.1
- `ESPN YYYY WSOP SHOW N` → ESPN 2007 WSOP SHOW 1

**Era 분류:**
- CLASSIC (1973-2002): 연도만으로 Main Event 자동 매칭
- BOOM (2003-2010): 포커 붐 시대
- HD (2011-2025): PokerGO 스트리밍

**제외 조건:** Size < 1GB, Duration < 30min, `clip`, `hand_`, `circuit` 포함

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

```
docs/
├── README.md                      # 문서 인덱스
├── [Architecture]
│   └── SYSTEM_OVERVIEW.md         # 시스템 아키텍처 (v2.1)
├── [PRD]
│   ├── PRD-NAMS-MATCHING.md       # 매칭 시스템 PRD (v2.0)
│   ├── PRD-POKERGO-SOURCE.md      # X: 드라이브 통합 PRD
│   └── PRD-NAMS-REFACTORING.md    # 기술 부채 로드맵
├── [Operations]
│   ├── AUTOMATION_PIPELINE.md     # 파이프라인 실행 가이드
│   └── DASHBOARD_GUIDE.md         # UI 사용 가이드
├── [Technical Reference]
│   ├── MATCHING_RULES.md          # 매칭 규칙 핵심 (v5.0)
│   ├── MATCHING_PATTERNS_DETAIL.md # 패턴 상세/변경이력 (v5.0)
│   └── NAS_DRIVE_STRUCTURE.md     # 드라이브 물리 구조
└── [Archive]
    └── (레거시 문서)
```

## References

| 문서 | 내용 |
|------|------|
| `docs/MATCHING_RULES.md` | 매칭 규칙 핵심 (v5.0) |
| `docs/MATCHING_PATTERNS_DETAIL.md` | 패턴 상세 예시, 변경 이력 (v5.0) |
| `docs/AUTOMATION_PIPELINE.md` | 파이프라인 실행, 트러블슈팅 |
| `docs/SYSTEM_OVERVIEW.md` | 시스템 아키텍처 (v2.1) |
| `docs/NAS_DRIVE_STRUCTURE.md` | X:/Y:/Z: 드라이브 폴더 구조 |
