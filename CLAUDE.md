# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

NAMS - NAS 영상 파일 관리 및 PokerGO 메타데이터 매칭 시스템

| 드라이브 | 역할 | 용도 |
|----------|------|------|
| Y: | Origin (Backup) | 원본 백업 (~1.8TB, 1,568 files) |
| Z: | Archive (Primary) | 아카이브 (~20TB, 1,405 files) |
| X: | PokerGO Source | PokerGO 원본 (~684GB, 828 files) |

## Quick Start

```powershell
# API (8001) + UI (5174)
cd src/nams/api && uvicorn main:app --reload --port 8001
cd src/nams/ui && npm run dev -- --port 5174

# NAS 스캔 & Google Sheets 내보내기
python scripts/scan_nas.py --mode full --folder all
python scripts/create_master_catalog.py

# 일일 자동화 (매일 08:00 실행)
python scripts/scheduler/run_all_tasks.py
```

## Commands

```powershell
# Backend 린트
ruff check src/nams/ --fix

# Frontend (src/nams/ui)
cd src/nams/ui
npm run lint && npm run build
npm run test:e2e                           # Playwright E2E

# 주요 스크립트 (모듈 실행 권장)
python -m scripts.scan_nas --mode incremental --folder origin
python -m scripts.daily_scan --mode daily --sync-sheets
python -m scripts.match_pokergo_nas
python -m scripts.create_master_catalog

# 패턴 엔진 테스트
python scripts/test_pattern_engine.py
python scripts/test_title_generation.py
```

## Architecture

```
src/nams/
├── api/                        # FastAPI Backend (port 8001)
│   ├── services/
│   │   ├── pattern_engine.py   # 핵심: 파일명 → 메타데이터 추출 (P0-P10 패턴)
│   │   ├── matching_v2.py      # 핵심: Era별 PokerGO 매칭 (Region/Episode 키)
│   │   ├── title_generation.py # Catalog Title 생성
│   │   ├── scanner.py          # NAS 스캔 서비스
│   │   └── grouping.py         # Asset Grouping (Primary/Backup 결정)
│   ├── routers/                # API 엔드포인트 (files, groups, patterns, stats)
│   └── database/models.py      # SQLAlchemy (SQLite: data/nams/nams.db)
├── ui/                         # React 19 + Vite + TanStack Query (port 5174)
│   └── src/pages/              # Dashboard, Files, Groups, Patterns, Validator
└── migrations/                 # 마이그레이션 서브 프로젝트 (별도 세션 개발 권장)
    ├── iconik2sheet/           # Iconik → Google Sheets
    └── sheet2sheet/            # Sheets 간 마이그레이션 (GAS + PWA)
```

## Core Matching Logic

### Era 분류 (매칭 핵심)

| Era | 연도 | 특징 |
|-----|------|------|
| CLASSIC | 1973-2002 | 연도당 Main Event 1개 → 연도만으로 매칭 |
| BOOM | 2003-2010 | ESPN Day/Show 구조 |
| HD | 2011-2025 | PokerGO Episode 기반 |

### 규칙

- **PokerGO Title 1:1 매칭**: 하나의 NAS 그룹 = 하나의 PokerGO Title
- **Generic Title 금지**: "WSOP 2024 Main Event"와 같은 시즌 헤더는 실제 에피소드가 아님
- **Region 매칭**: LV(기본), EU(Europe), APAC, PARADISE, CYPRUS, LONDON, LA

## Data Flow

```
NAS 스캔 → 패턴 추출 → Asset Grouping → PokerGO 매칭 → Google Sheets 내보내기
              ↓              ↓                ↓
         year/region    group_id 생성    MATCHED / NAS_ONLY
         event_type     (2011_ME_25)     / DUPLICATE 분류
```

**Scheduler** (매일 08:00-09:00):
- Task1 (08:00): NAS 스캔 → NAMS 시트
- Task2 (08:30): Iconik API → Iconik_Full_Metadata 시트
- Task3 (09:00): Iconik_Full_Metadata 시트 → Iconik API

## Google Sheets

| 시트명 | ID | 용도 |
|--------|-----|------|
| **UDM metadata** | `1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4` | Master_Catalog (메인) |
| **Iconik metadata** | `1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk` | Iconik 메타데이터 + 타임코드 |

**상세 구조**: `docs/reference/GOOGLE_SHEETS_STRUCTURE.md`

## Key Docs

| 문서 | 내용 |
|------|------|
| `docs/core/MATCHING_RULES.md` | 매칭 규칙 (Era 분류, 패턴 P0-P10) |
| `docs/core/SYSTEM_OVERVIEW.md` | 시스템 아키텍처 (데이터 모델, API 라우터) |
| `docs/core/NAS_DRIVE_STRUCTURE.md` | 드라이브 폴더 구조 (CLASSIC/BOOM/HD) |
| `docs/guides/SCHEDULER_SETUP.md` | 일일 스케줄러 설정 (Windows Task Scheduler) |
| `src/migrations/CLAUDE.md` | 마이그레이션 서브 프로젝트 (별도 세션 개발 권장)
