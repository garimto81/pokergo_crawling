# Migrations Module

마이그레이션 서브 프로젝트 모음

## 프로젝트 목록

| 프로젝트 | 설명 | 기술 스택 |
|----------|------|-----------|
| [sheet2sheet](./sheet2sheet/) | Google Sheets 간 마이그레이션 PWA | CLASP + React |
| [sheet2iconik](./sheet2iconik/) | Sheets → Iconik MAM 동기화 | Python + httpx |
| [iconik2sheet](./iconik2sheet/) | Iconik MAM → Sheets 내보내기 | Python + httpx |

## 디렉토리 구조

```
migrations/
├── sheet2sheet/     # 프로젝트 1: Sheet to Sheet PWA
│   ├── gas/         # Google Apps Script (CLASP)
│   ├── pwa/         # React PWA
│   └── docs/        # 프로젝트 문서
│
├── sheet2iconik/    # 프로젝트 2: Sheet to Iconik
│   ├── config/      # 설정
│   ├── clients/     # API 클라이언트
│   ├── services/    # 비즈니스 로직
│   └── scripts/     # CLI 스크립트
│
├── iconik2sheet/    # 프로젝트 3: Iconik to Sheet
│   ├── iconik/      # Iconik API 래퍼
│   ├── sheets/      # Sheets 출력
│   ├── sync/        # 동기화 로직
│   └── scripts/     # CLI 스크립트
│
└── README.md        # 이 파일
```

## 독립 프로젝트 운영

각 서브 프로젝트는 **완전 독립적**으로 운영됩니다:

- 자체 의존성 관리 (package.json / pyproject.toml)
- 자체 설정 파일
- 별도의 Claude Code 세션에서 개발 권장

## 시작하기

```powershell
# Sheet to Sheet PWA 개발
cd src/migrations/sheet2sheet
# 새 Claude Code 세션 시작

# Sheet to Iconik 개발
cd src/migrations/sheet2iconik
# 새 Claude Code 세션 시작

# Iconik to Sheet 개발
cd src/migrations/iconik2sheet
# 새 Claude Code 세션 시작
```

## 관련 문서

- [PRD-SHEET2SHEET.md](../../docs/prds/PRD-SHEET2SHEET.md)
- [PRD-SHEET2ICONIK.md](../../docs/prds/PRD-SHEET2ICONIK.md)
- [PRD-ICONIK2SHEET.md](../../docs/prds/PRD-ICONIK2SHEET.md)
