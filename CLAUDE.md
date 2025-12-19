# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

NAMS - NAS 영상 파일 관리 및 PokerGO 메타데이터 매칭 시스템 (Y:/Z:/X: 드라이브)

## Quick Start

```powershell
# API (8001) + UI (5174)
cd src/nams/api && uvicorn main:app --reload --port 8001
cd src/nams/ui && npm run dev -- --port 5174

# 스캔 & 내보내기
python scripts/scan_nas.py --mode full --folder all
python scripts/export_4sheets.py
```

## Commands

```powershell
# Backend
ruff check src/nams/ --fix
pytest tests/test_pattern_engine.py -v    # 개별 테스트 권장 (전체 120초 타임아웃)

# Frontend (src/nams/ui)
npm run lint && npm run build
npm run test:e2e                          # Playwright E2E
```

## Architecture

- **API**: `src/nams/api/` - FastAPI + SQLAlchemy (SQLite: `data/nams/nams.db`)
  - `services/pattern_engine.py` - 핵심 패턴 매칭 엔진
  - `services/matching_v2.py` - PokerGO 매칭 (Era별: CLASSIC/BOOM/HD)
- **UI**: `src/nams/ui/` - React 19 + Vite + TanStack Query

## Key Docs

| 문서 | 내용 |
|------|------|
| `docs/MATCHING_RULES.md` | 매칭 규칙 (v5.11) |
| `docs/SYSTEM_OVERVIEW.md` | 시스템 아키텍처 |
| `docs/NAS_DRIVE_STRUCTURE.md` | 드라이브 폴더 구조 |
