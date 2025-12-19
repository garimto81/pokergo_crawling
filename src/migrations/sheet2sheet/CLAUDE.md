# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Google Sheets 간 데이터 마이그레이션 PWA - CLASP 기반 GAS 백엔드 + React 프론트엔드

## Commands

### GAS 개발 및 배포

```powershell
cd gas

# 초기 설정 (최초 1회)
npm install -g @google/clasp
clasp login
clasp create --type webapp --title "Sheet2Sheet Migration"

# 개발
clasp push              # 코드 푸시
clasp deploy            # 배포
clasp open              # Apps Script 에디터 열기
clasp pull              # 원격 코드 가져오기
```

### PWA 개발

```powershell
cd pwa
npm install
npm run dev             # 개발 서버 (port 5175)
npm run build           # 프로덕션 빌드
npm run preview         # 빌드 미리보기
npm run lint            # ESLint
```

### 루트에서 실행

```powershell
npm run dev             # PWA 개발 서버
npm run gas:push        # GAS 푸시
npm run gas:deploy      # GAS 배포
```

## Architecture

### GAS (Google Apps Script)

```
gas/
├── Code.ts             # 엔트리 (doGet/doPost)
├── appsscript.json     # GAS 프로젝트 설정
└── .clasp.json         # CLASP 설정 (생성 필요)
```

**API 엔드포인트**:

| Method | Action | 용도 |
|--------|--------|------|
| GET | `status` | 상태 확인 |
| GET | `sheets` | 시트 목록 조회 |
| GET | `preview` | 시트 데이터 미리보기 |
| GET | `triggers` | 트리거 목록 |
| GET | `logs` | 실행 로그 |
| POST | `migrate` | 마이그레이션 실행 |
| POST | `createTrigger` | 트리거 생성 |
| POST | `deleteTrigger` | 트리거 삭제 |
| POST | `testRun` | 테스트 실행 |

**주요 인터페이스**:
- `MigrationConfig`: 소스/타겟 시트, 범위, 컬럼 매핑, 변환 규칙
- `TransformRule`: upper/lower/trim/date/number/regex 변환

### PWA (React)

```
pwa/
├── src/
│   ├── App.tsx         # 라우터 설정
│   ├── components/     # UI 컴포넌트
│   ├── pages/          # 페이지 (Dashboard, Migration, Scheduler, History)
│   ├── services/       # GAS API 클라이언트
│   └── stores/         # Zustand 상태
└── vite.config.ts
```

**기술 스택**: React 19 + Vite 7 + TanStack Query 5 + Zustand 5 + Tailwind 4

**라우트**:
- `/` - Dashboard
- `/migration` - 마이그레이션 설정
- `/scheduler` - 트리거 관리
- `/history` - 실행 이력

## Environment

```env
# PWA (.env)
VITE_GAS_URL=https://script.google.com/macros/s/.../exec
```

## Key Files

| 파일 | 역할 |
|------|------|
| `gas/Code.ts` | GAS 엔트리포인트, API 라우팅 |
| `pwa/src/App.tsx` | React 앱 레이아웃, 라우팅 |
| `pwa/src/services/` | GAS API 통신 |
