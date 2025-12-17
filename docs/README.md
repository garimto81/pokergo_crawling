# NAMS Documentation Index

> NAS Asset Management System - WSOP 52년 역사 DB 체계화 프로젝트

**Version**: 1.0 | **Last Updated**: 2025-12-17

---

## Project Overview

NAMS는 3개의 NAS 드라이브(X:/Y:/Z:)와 PokerGO 메타데이터를 통합하여
**1973년부터 현재까지 52년간의 WSOP 콘텐츠 카탈로그**를 구축하는 시스템입니다.

### 핵심 목표

1. **NAS 파일 통합 관리**: 3개 드라이브(X:/Y:/Z:) 비디오 파일 메타데이터 통합
2. **PokerGO 매칭**: 828개 PokerGO 에피소드와 NAS 파일 1:1 자동 매칭
3. **Asset Grouping**: 동일 콘텐츠 파일 그룹화 (Primary/Backup 구분)
4. **카탈로그 생성**: Netflix 스타일 표시 제목 및 Google Sheets 5시트 내보내기

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NAMS 데이터 흐름                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   [NAS Drives]                              [PokerGO]                       │
│   ┌─────────────┐                          ┌─────────────┐                  │
│   │ X: PokerGO  │──┐                       │ wsop_final  │                  │
│   │ (828 files) │  │                       │ .json       │                  │
│   └─────────────┘  │    ┌──────────────┐   │ (828 eps)   │                  │
│   ┌─────────────┐  ├───▶│   NAMS DB    │◀──└─────────────┘                  │
│   │ Y: Backup   │  │    │  (SQLite)    │                                    │
│   │ (1,568 files│  │    └──────┬───────┘                                    │
│   └─────────────┘  │           │                                            │
│   ┌─────────────┐  │           ▼                                            │
│   │ Z: Archive  │──┘    ┌──────────────┐    ┌──────────────┐               │
│   │ (1,405 files│       │ Pattern      │───▶│ Google       │               │
│   └─────────────┘       │ Matching     │    │ Sheets       │               │
│                         └──────────────┘    │ (5 sheets)   │               │
│                                             └──────────────┘               │
│                                                                             │
│   Total: 3,801 video files (~22.5 TB)                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Sources

### NAS Drives (Physical Files)

| Drive | Path | Role | Files | Size |
|-------|------|------|-------|------|
| **X:** | GGP Footage/POKERGO | PokerGO Source | 828 | ~684 GB |
| **Y:** | WSOP backup | Backup | 1,568 | ~1.8 TB |
| **Z:** | Archive | Primary | 1,405 | ~20 TB |

### PokerGO (Metadata)

| Item | Value |
|------|-------|
| Total Episodes | 828 |
| Source | wsop_final.json |
| Coverage | 1973-2025 |
| Era Distribution | CLASSIC(20), BOOM(236), HD(572) |

---

## Document Hierarchy

```
docs/
├── README.md              ← 현재 문서 (마스터 인덱스)
│
├── [Architecture]
│   └── SYSTEM_OVERVIEW.md      # 전체 시스템 아키텍처 (v2.1)
│
├── [PRD - Requirements]
│   ├── PRD-NAMS-MATCHING.md    # 매칭 시스템 요구사항 (v2.0)
│   ├── PRD-POKERGO-SOURCE.md   # X: 드라이브 통합 PRD (v1.0)
│   └── PRD-NAMS-REFACTORING.md # 기술 부채 로드맵
│
├── [Operations]
│   ├── AUTOMATION_PIPELINE.md  # 파이프라인 실행 가이드 (v1.0)
│   └── DASHBOARD_GUIDE.md      # UI 사용 가이드 (v2.0)
│
├── [Technical Reference]
│   ├── MATCHING_RULES.md           # 매칭 규칙 핵심 (v5.0)
│   ├── MATCHING_PATTERNS_DETAIL.md # 패턴 상세/변경이력 (v5.0)
│   └── NAS_DRIVE_STRUCTURE.md      # 드라이브 물리 구조 (v1.0)
│
├── [Status Reports]
│   └── DB_STATUS_REPORT.md     # 현황 진단 보고서
│
└── [Archive]
    ├── IMPLEMENTATION_PLAN.md      # → PRD에 통합됨
    └── MATCHING_STRATEGY_ANALYSIS.md # → MATCHING_RULES에 통합됨
```

---

## Quick Reference

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Era** | CLASSIC(1973-2002), BOOM(2003-2010), HD(2011-2025) |
| **Region** | LV(Las Vegas), EU(Europe), APAC, PARADISE, CYPRUS, LA |
| **Match Category** | MATCHED, NAS_ONLY_HISTORIC, NAS_ONLY_MODERN |
| **Asset Group** | 동일 콘텐츠 파일들의 그룹 (Primary/Backup) |

### Matching Status (2025-12-17)

```
┌─────────────────────────────────────────────┐
│           Current Matching Status            │
├─────────────────────────────────────────────┤
│  PokerGO Episodes:       828                │
│  NAS Groups:             221                │
│  ├─ MATCHED:             101 (45.7%)        │
│  ├─ NAS_ONLY_HISTORIC:    18 (8.1%)         │
│  └─ NAS_ONLY_MODERN:     102 (46.2%)        │
│  DUPLICATE:                0 (100% 해결)     │
└─────────────────────────────────────────────┘
```

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

## Document Details

### Architecture

| Document | Purpose | Version |
|----------|---------|---------|
| [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) | 전체 시스템 설계, 데이터 흐름, 매칭 전략 | v2.1 |

### PRD (Product Requirements)

| Document | Purpose | Version |
|----------|---------|---------|
| [PRD-NAMS-MATCHING.md](PRD-NAMS-MATCHING.md) | 매칭 시스템 4대 목표, DUPLICATE 해결 규칙, 카탈로그 설계 | v2.0 |
| [PRD-POKERGO-SOURCE.md](PRD-POKERGO-SOURCE.md) | X: 드라이브 통합 사양, Scanner/Export 확장 | v1.0 |
| [PRD-NAMS-REFACTORING.md](PRD-NAMS-REFACTORING.md) | 코드 품질 개선, 기술 부채 해결 로드맵 | v1.0 |

### Operations

| Document | Purpose | Version |
|----------|---------|---------|
| [AUTOMATION_PIPELINE.md](AUTOMATION_PIPELINE.md) | 파이프라인 실행, 매칭 규칙 v5.0, 트러블슈팅 | v1.0 |
| [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) | NAMS UI 사용법, KPI 카드, 워크플로우 | v2.0 |

### Technical Reference

| Document | Purpose | Version |
|----------|---------|---------|
| [MATCHING_RULES.md](MATCHING_RULES.md) | 매칭 규칙 핵심 (절대원칙, 패턴, Region, Grouping) | v5.0 |
| [MATCHING_PATTERNS_DETAIL.md](MATCHING_PATTERNS_DETAIL.md) | 패턴 상세 예시, BOOM Era 매핑, 변경 이력 | v5.0 |
| [NAS_DRIVE_STRUCTURE.md](NAS_DRIVE_STRUCTURE.md) | X:/Y:/Z: 드라이브 폴더 구조, 파일 분포 | v1.0 |

### Status Reports

| Document | Purpose | Date |
|----------|---------|------|
| [DB_STATUS_REPORT.md](DB_STATUS_REPORT.md) | 패턴 매칭 현황, 데이터 품질 진단 | 2025-12-17 |

---

## Data Flow

### 1. Scan Phase

```
NAS Drives → scanner.py → SQLite DB (nas_files table)
```

- X:/Y:/Z: 드라이브 스캔
- 비디오 파일 메타데이터 추출
- 제외 조건 플래깅 (Size < 1GB, Duration < 30min, Clip keywords)

### 2. Pattern Matching Phase

```
nas_files → pattern_engine.py → Metadata Extraction
```

- 파일명에서 Year/Region/EventType/Episode 추출
- 패턴 우선순위: DB 정의 패턴 → Fallback 패턴

### 3. PokerGO Matching Phase

```
AssetGroups + PokerGO → matching.py → Match Results
```

- 양방향 매칭 (NAS → PokerGO, PokerGO → NAS)
- Region/Episode/Event Type 제약 적용
- DUPLICATE 감지 및 해결

### 4. Export Phase

```
Match Results → export.py → Google Sheets (5 sheets)
```

- NAS_Origin_Raw, NAS_Archive_Raw, NAS_PokerGO_Raw
- PokerGO_Raw, Matching_Integrated

---

## Version Notes

| Version | Component | Notes |
|---------|-----------|-------|
| v5.0 | Matching Rules | MATCHING_RULES.md (핵심) + MATCHING_PATTERNS_DETAIL.md (상세) |
| v2.1 | System Overview | 드라이브 파일 수 업데이트 |
| v2.0 | PRD-NAMS-MATCHING | DUPLICATE 100% 해결 |

**Note**: 2025-12-17 문서 구조화 완료. MATCHING_RULES.md(v5.0)이 최신 규칙.

---

## Contributing

### Document Updates

1. 버전 번호 증가 (Major.Minor)
2. 변경 이력 섹션 업데이트
3. README.md (이 문서) 업데이트

### Archiving

더 이상 관련 없는 문서는 `docs/archive/`로 이동.

---

## Change History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-17 | 초기 문서 구조 정립, 아카이빙 체계 확립 |
