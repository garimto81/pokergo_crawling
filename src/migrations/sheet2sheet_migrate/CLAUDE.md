# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

외부 Google Sheets 데이터를 Iconik_Full_Metadata 시트로 마이그레이션하는 Python CLI 도구

| 소스 시트 | Archive Metadata | 8개 탭, 339+ 행 |
|-----------|------------------|-----------------|
| 타겟 시트 | Iconik_Full_Metadata | 35컬럼 |

## Commands

```powershell
# 분석 스크립트 (프로젝트 루트에서 실행)
python scripts/analyze_source_sheet.py

# Dry Run
python scripts/run_sheet_migration.py

# 매핑 미리보기
python scripts/run_sheet_migration.py --show-mapping

# 실행 (append 모드)
python scripts/run_sheet_migration.py --execute

# 실행 (overwrite 모드)
python scripts/run_sheet_migration.py --execute --mode overwrite

# 프로젝트 디렉토리에서 직접 실행
cd src/migrations/sheet2sheet_migrate
python -m scripts.dry_run
python -m scripts.migrate --execute
```

## Architecture

```
sheet2sheet_migrate/
├── config/
│   └── settings.py           # Pydantic Settings
├── sheets/
│   ├── reader.py             # SheetsReader (multi-tab 지원)
│   └── writer.py             # SheetsWriter
├── mapping/
│   └── column_mapper.py      # 커스텀 컬럼 매핑 로직
├── migration/
│   └── migrator.py           # 마이그레이션 오케스트레이터
└── scripts/
    ├── dry_run.py            # Dry run 스크립트
    └── migrate.py            # 실행 스크립트
```

### 컬럼 매핑

**직접 매핑**:
- File No. → id
- File Name → title
- In → time_start_S (타임코드 파싱)
- Out → time_end_S (타임코드 파싱)
- Hand Grade → HandGrade (★→숫자 변환)
- Nas Folder Link → Source
- Hands → HANDTag

**패턴 매핑**:
- Tag (Player) x3 → PlayersTags (쉼표 병합)
- Tag (Poker Play) x7 → PokerPlayTags (쉼표 병합)
- Tag (Emotion) x2 → Emotion (쉼표 병합)

**탭 유래 필드**:
- 탭 이름에서 Year_, Location, Tournament 추출

## Environment

```env
GOOGLE_SERVICE_ACCOUNT_PATH=path/to/service_account.json
SOURCE_SPREADSHEET_ID=1_RN_W_ZQclSZA0Iez6XniCXVtjkkd5HNZwiT6l-z6d4
TARGET_SPREADSHEET_ID=1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk
TARGET_SHEET_NAME=Iconik_Full_Metadata
```

## Key Points

- **Header Row**: 소스 시트의 헤더가 Row 3에 있음 (Row 1-2는 빈 행)
- **Dry Run 필수**: Google Sheets API 롤백 불가, 실행 전 반드시 dry run
- **Append 모드 기본**: 기존 데이터 보존

## Iconik API 연동

Archive_Metadata → Iconik MAM 직접 마이그레이션 지원

### Iconik 마이그레이션 명령어

```powershell
# Dry Run
python scripts/test_iconik_migration.py

# 실행 (1번 행)
python scripts/test_iconik_migration.py --execute --row 1

# 특정 Asset ID 지정
python scripts/test_iconik_migration.py --execute --row 5 --asset-id <UUID>
```

### Iconik 필드 호환성

Iconik 메타데이터 뷰의 **19개 필드가 dropdown 타입** → 사전 정의된 값만 허용

**마이그레이션 가능 필드** (자유 텍스트):
- Description, Year_, Location, PlayersTags, PokerPlayTags

**마이그레이션 제외 필드** (dropdown):
- HandGrade, HANDTag, Tournament, Source, Emotion
- Venue, GameType, Scene, Adjective, EPICHAND 등

### 관련 이슈

- [#19](https://github.com/garimto81/pokergo_crawling/issues/19) - Iconik dropdown 필드 오류

## Key Docs

| 문서 | 내용 |
|------|------|
| `docs/prds/PRD-SHEET2SHEET-MIGRATE.md` | PRD 문서 |
| `scripts/analyze_source_sheet.py` | 소스 시트 구조 분석 |
| `scripts/run_sheet_migration.py` | 래퍼 스크립트 |
| `scripts/test_iconik_migration.py` | Iconik 마이그레이션 테스트 |
