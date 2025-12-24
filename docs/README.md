# NAMS Documentation Index

> NAS Asset Management System - WSOP 52년 역사 카테고리 구축

**Version**: 4.0 | **Last Updated**: 2025-12-23

---

## Project Overview

NAMS는 3개의 NAS 드라이브(X:/Y:/Z:)에 보유한 WSOP 영상을 기반으로
**1973년부터 현재까지 52년간의 WSOP 콘텐츠 카테고리**를 구축하는 시스템입니다.

### 하이브리드 접근

```
NAS 파일 858개
    │
    ├─[매칭 가능]──▶ PokerGO 카테고리/제목 활용
    │
    └─[매칭 불가]──▶ 자체 카테고리/제목 생성
```

---

## Document Structure

```
docs/
├── README.md              ← 현재 문서 (마스터 인덱스)
│
├── core/                  # 핵심 시스템 문서
│   ├── SYSTEM_OVERVIEW.md      # 전체 시스템 아키텍처 (v2.1)
│   ├── MATCHING_RULES.md       # 매칭 규칙 핵심 (v5.11)
│   ├── MATCHING_PATTERNS_DETAIL.md  # 패턴 상세/변경이력 (v5.0)
│   └── NAS_DRIVE_STRUCTURE.md  # 드라이브 물리 구조 (v1.0)
│
├── prds/                  # PRD (요구사항)
│   ├── PRD-CATALOG-DB.md       # NAS 중심 카탈로그 DB 설계
│   ├── PRD-NAMS-MATCHING.md    # 매칭 시스템 (deprecated)
│   ├── PRD-NAMS-REFACTORING.md # 기술 부채 로드맵
│   ├── PRD-POKERGO-SOURCE.md   # X: 드라이브 통합 PRD
│   ├── PRD-0001-NAMS-CATALOG-VALIDATOR.md  # 카탈로그 검증
│   ├── PRD-0010-DAILY-SCHEDULER.md  # 일일 스케줄러
│   ├── PRD-ICONIK-*.md (3개)   # Iconik 연동
│   └── PRD-SHEET2*.md (2개)    # Sheets 연동
│
├── guides/                # 운영 가이드
│   ├── DASHBOARD_GUIDE.md      # UI 사용 가이드 (v2.0)
│   ├── SCHEDULER_SETUP.md      # 스케줄러 설정
│   └── AUTOMATION_PIPELINE.md  # 파이프라인 실행 가이드
│
├── reference/             # 참조 데이터
│   ├── GOOGLE_SHEETS_STRUCTURE.md  # Google Sheets 구조 (v1.0)
│   ├── POKERGO_WSOP_FULL_LIST.md   # 828개 에피소드 전체 목록
│   ├── POKERGO_WSOP_CONTENT.md     # 카테고리별 콘텐츠 가이드
│   └── ICONIK_DATA_STRUCTURE.md    # Iconik 메타데이터 구조
│
├── reports/               # 리포트
│   └── iconik-data-comparison-report.md
│
└── archive/               # 과거 버전 보관
    ├── matching/          # 매칭 전략 아카이브
    ├── analysis/          # 분석 문서 아카이브
    └── [기타 아카이브]
```

---

## Core Documents

| Document | Purpose | Version |
|----------|---------|---------|
| [SYSTEM_OVERVIEW.md](core/SYSTEM_OVERVIEW.md) | 전체 시스템 설계, 데이터 흐름 | v2.1 |
| [MATCHING_RULES.md](core/MATCHING_RULES.md) | 매칭 규칙 핵심 (절대원칙, 패턴) | v5.11 |
| [MATCHING_PATTERNS_DETAIL.md](core/MATCHING_PATTERNS_DETAIL.md) | 패턴 상세, BOOM Era 매핑 | v5.0 |
| [NAS_DRIVE_STRUCTURE.md](core/NAS_DRIVE_STRUCTURE.md) | X:/Y:/Z: 드라이브 폴더 구조 | v1.0 |

---

## PRDs

| Document | Purpose | Status |
|----------|---------|--------|
| [PRD-CATALOG-DB.md](prds/PRD-CATALOG-DB.md) | NAS 중심 카탈로그 DB 설계 | Active |
| [PRD-0010-DAILY-SCHEDULER.md](prds/PRD-0010-DAILY-SCHEDULER.md) | 일일 스케줄러 | Active |
| [PRD-0001-NAMS-CATALOG-VALIDATOR.md](prds/PRD-0001-NAMS-CATALOG-VALIDATOR.md) | 카탈로그 검증 | Active |
| [PRD-ICONIK-MASTER-MAPPING.md](prds/PRD-ICONIK-MASTER-MAPPING.md) | Iconik 마스터 매핑 | Active |
| [PRD-SHEET2SHEET.md](prds/PRD-SHEET2SHEET.md) | Sheets 간 마이그레이션 | Active |

[전체 PRD 목록 →](prds/)

---

## Guides

| Document | Purpose |
|----------|---------|
| [DASHBOARD_GUIDE.md](guides/DASHBOARD_GUIDE.md) | NAMS UI 사용법, KPI 카드 |
| [SCHEDULER_SETUP.md](guides/SCHEDULER_SETUP.md) | Windows Task Scheduler 설정 |
| [AUTOMATION_PIPELINE.md](guides/AUTOMATION_PIPELINE.md) | 파이프라인 실행 가이드 |

---

## Reference

| Document | Purpose |
|----------|---------|
| [GOOGLE_SHEETS_STRUCTURE.md](reference/GOOGLE_SHEETS_STRUCTURE.md) | Google Sheets 구조 (UDM/Iconik) |
| [POKERGO_WSOP_FULL_LIST.md](reference/POKERGO_WSOP_FULL_LIST.md) | 828개 에피소드 전체 목록 |
| [POKERGO_WSOP_CONTENT.md](reference/POKERGO_WSOP_CONTENT.md) | 카테고리별 콘텐츠 가이드 |
| [ICONIK_DATA_STRUCTURE.md](reference/ICONIK_DATA_STRUCTURE.md) | Iconik 메타데이터 구조 |

---

## Quick Reference

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Era** | CLASSIC(1973-2002), BOOM(2003-2010), HD(2011-2025) |
| **Region** | LV(Las Vegas), EU(Europe), APAC, PARADISE, CYPRUS, LA |
| **Match Category** | MATCHED, NAS_ONLY_HISTORIC, NAS_ONLY_MODERN |
| **Asset Group** | 동일 콘텐츠 파일들의 그룹 (Primary/Backup) |

### Execution Commands

```powershell
# Full Pipeline (Scan → Match → Export)
python scripts/run_pipeline.py --mode full

# Incremental Update
python scripts/run_pipeline.py --mode incremental

# Individual Steps
python scripts/scan_nas.py --mode full --folder all
python scripts/export_4sheets.py
```

---

## Data Sources

| Drive | Path | Role | Files | Size |
|-------|------|------|-------|------|
| **X:** | GGP Footage/POKERGO | PokerGO Source | 828 | ~684 GB |
| **Y:** | WSOP backup | Backup | 1,568 | ~1.8 TB |
| **Z:** | Archive | Primary | 1,405 | ~20 TB |

---

## Archive

과거 버전 및 분석 문서는 [archive/](archive/) 폴더에 보관됩니다.

- [archive/matching/](archive/matching/) - 매칭 전략 히스토리
- [archive/analysis/](archive/analysis/) - 분석 문서

---

## Change History

| Version | Date | Changes |
|---------|------|---------|
| 4.0 | 2025-12-23 | 문서 구조 재편 (core/guides/reference/prds/archive) |
| 3.0 | 2025-12-17 | 초기 문서 구조 정립 |
