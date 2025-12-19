# Sheet to Sheet Migration PWA

CLASP CLI 기반 Google Sheets 간 마이그레이션 PWA

## Overview

- **GAS**: Google Apps Script (TypeScript + CLASP)
- **PWA**: React 19 + Vite + Tailwind
- **인증**: Google OAuth 또는 서비스 계정

## Quick Start

### GAS 배포

```powershell
cd gas
npm install -g @google/clasp
clasp login
clasp create --type webapp --title "Sheet2Sheet Migration"
clasp push
clasp deploy
```

### PWA 개발

```powershell
cd pwa
npm install
npm run dev
```

## 디렉토리 구조

```
sheet2sheet/
├── gas/                    # Google Apps Script
│   ├── .clasp.json        # CLASP 설정 (생성 필요)
│   ├── appsscript.json    # GAS 프로젝트 설정
│   ├── Code.ts            # 메인 엔트리 (doGet/doPost)
│   ├── SheetService.ts    # 시트 조작 서비스
│   ├── MigrationEngine.ts # 마이그레이션 엔진
│   └── TriggerManager.ts  # 트리거 관리
│
├── pwa/                    # React PWA
│   ├── src/
│   │   ├── components/    # UI 컴포넌트
│   │   ├── pages/         # 페이지
│   │   ├── services/      # API 클라이언트
│   │   └── stores/        # 상태 관리
│   ├── public/
│   │   └── manifest.json  # PWA 매니페스트
│   └── vite.config.ts     # Vite 설정
│
└── docs/
    └── PRD-SHEET2SHEET.md # -> ../../docs/prds/
```

## 핵심 기능

| 기능 | 설명 |
|------|------|
| 시트 관리 | 목록 조회, 미리보기, 범위 선택 |
| 마이그레이션 | 셀/범위 복사, 컬럼 매핑, 변환 규칙 |
| 스케줄링 | 시간 기반 트리거, 실행 로그 |

## 환경 변수

```env
# PWA
VITE_GAS_URL=https://script.google.com/macros/s/.../exec
```

## 관련 문서

- [PRD-SHEET2SHEET.md](../../../docs/prds/PRD-SHEET2SHEET.md)
- [CLASP 가이드](https://github.com/google/clasp)
