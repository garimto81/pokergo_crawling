# NAMS - NAS Asset Management System

NAS 파일 패턴 매칭 및 PokerGO 콘텐츠 매칭 시스템.

## 기능

- NAS 파일 스캔 및 메타데이터 추출
- 정규식 기반 패턴 매칭 (WSOP, Europe, APAC, Paradise 등)
- PokerGO 에피소드 자동 매칭
- Primary/Backup 그룹핑
- Google Sheets/CSV/JSON 내보내기

## 설치

```bash
pip install -e .
cd src/nams/ui && npm install
```

## 실행

```bash
# API 서버 (포트 8001)
cd src/nams/api && uvicorn main:app --reload --port 8001

# UI 서버 (포트 5174)
cd src/nams/ui && npm run dev -- --port 5174
```

## 데이터베이스

- 위치: `data/nams/nams.db` (SQLite)
- 테이블: nas_files, patterns, file_groups, regions, event_types

## 기술 스택

- Python 3.11+
- FastAPI
- SQLAlchemy 2.0
- React 19 + Vite
- TailwindCSS
