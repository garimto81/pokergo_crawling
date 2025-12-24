# NAMS 시스템 개요

NAS Asset Management System - 전체 로직 정리

**버전**: 2.1
**날짜**: 2025-12-17

---

## 1. 시스템 목적

WSOP 영상 파일을 통합 관리하고 PokerGO 메타데이터와 매칭하여 콘텐츠 카탈로그를 구축.

---

## 2. 데이터 소스

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           데이터 소스 구조                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   NAS 저장소 (물리적 파일)                       PokerGO (메타데이터)        │
│   ┌─────────────────────────────┐               ┌─────────────────────┐     │
│   │ Y: Origin (WSOP Backup)     │               │ wsop_final.json     │     │
│   │ - 원본 파일 (Backup)        │               │ - 828 비디오        │     │
│   │ - Backup role               │               │ - 타이틀, 설명      │     │
│   │ - 1,568 files (~1.8 TB)     │               │ - 재생시간, 연도    │     │
│   └─────────────────────────────┘               └─────────────────────┘     │
│                                                                             │
│   ┌─────────────────────────────┐                                           │
│   │ Z: Archive (Primary)        │                                           │
│   │ - 아카이브 (Primary)        │                                           │
│   │ - Primary role              │                                           │
│   │ - 1,405 files (~20 TB)      │                                           │
│   └─────────────────────────────┘                                           │
│                                                                             │
│   ┌─────────────────────────────┐                                           │
│   │ X: PokerGO Source           │                                           │
│   │ - GGP Footage/POKERGO       │                                           │
│   │ - pokergo_source role       │                                           │
│   │ - 828 files (~684 GB)       │                                           │
│   └─────────────────────────────┘                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 NAS 드라이브 역할

| 드라이브 | 경로 | 용도 | DB Role | 파일 수 |
|----------|------|------|---------|---------|
| **Y:** | WSOP Backup | Backup 원본 | `backup` | 1,568 |
| **Z:** | Archive | Primary 아카이브 | `primary` | 1,405 |
| **X:** | GGP Footage/POKERGO | PokerGO 원본 | `pokergo_source` | 828 |

### 2.2 PokerGO 메타데이터

| 항목 | 값 |
|------|-----|
| 총 비디오 | 828개 |
| 소스 파일 | `data/pokergo/wsop_final.json` |
| 원본 소스 | `D:\AI\claude01\Archive_Converter\data\pokergo\pokergo_video_list_20251216_155158.json` |
| 크롤링 일자 | 2025-12-16 |
| Era 분포 | CLASSIC(20), BOOM(236), HD(572) |

**Era별 상세**:
| Era | 연도 | 개수 |
|-----|------|------|
| CLASSIC | 1973-2002 | 20 |
| BOOM | 2003-2010 | 236 |
| HD | 2011-2025 | 572 |

**WSOP Europe**: 36개 (2008-2021)

### 2.3 매칭 현황 (2025-12-17, v5.0)

| 분류 | 건수 | 설명 |
|------|------|------|
| **NAS Groups** | 646 | 총 Asset Groups |
| **MATCHED** | 365 | PokerGO 매칭 완료 |
| **NAS_ONLY_HISTORIC** | 50 | 1973-2002 (PokerGO 없음) |
| **NAS_ONLY_MODERN** | 231 | 지역 데이터 없음 (APAC/PARADISE 등) |
| **DUPLICATE** | 18 | 66% 감소 (53 → 18) |

**Action Stats**:
| Action | 건수 | 설명 |
|--------|------|------|
| OK | 765 | 정상 매칭 |
| Excluded | 502 | 제외 조건 해당 |
| -> Find NAS | 614 | PokerGO만 있음 (NAS 필요) |
| DUPLICATE | 18 | 패턴 추가 필요 |

**v5.0 개선 사항**:
- Region 매칭 강화 (substring false positive 해결)
- Episode-less 그룹 제한 (2003년 이후)
- BOOM Era Bracelet Event 오매칭 방지
- 제외 파일 DUPLICATE 감지 제외

---

## 3. 처리 파이프라인

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          데이터 처리 파이프라인                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 1: 스캔                Phase 2: 필터링             Phase 3: 매칭     │
│  ┌──────────────┐            ┌──────────────┐           ┌──────────────┐   │
│  │ NAS 스캔     │            │ 제외 조건    │           │ PokerGO      │   │
│  │ - Y: Origin  │──────────▶ │ - Size <1GB  │──────────▶│ 메타데이터   │   │
│  │ - Z: Archive │            │ - Dur <30min │           │ 매칭         │   │
│  │ - X: PokerGO │            │ - Clip/Hand  │           │              │   │
│  └──────────────┘            │ - Circuit    │           └──────────────┘   │
│         │                    └──────────────┘                  │           │
│         ▼                           │                          ▼           │
│  ┌──────────────┐                   │                   ┌──────────────┐   │
│  │ SQLite DB    │◀──────────────────┘                   │ Asset Groups │   │
│  │ nas_files    │                                       │ 연도+타입    │   │
│  │ 1,529 files  │◀──────────────────────────────────────│ +에피소드    │   │
│  └──────────────┘                                       └──────────────┘   │
│                                                                             │
│  Phase 4: 내보내기                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       Google Sheets (5 시트)                         │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐        │   │
│  │  │ Origin_Raw │ │Archive_Raw │ │PokerGO_Raw │ │PokerGO_Raw │        │   │
│  │  │  (Y:)      │ │  (Z:)      │ │  (X:)      │ │  (Meta)    │        │   │
│  │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘        │   │
│  │        └──────────────┴──────────────┴──────────────┘               │   │
│  │                               │                                      │   │
│  │                               ▼                                      │   │
│  │                    ┌───────────────────────┐                         │   │
│  │                    │ Matching_Integrated   │                         │   │
│  │                    │ - 10개 체크박스       │                         │   │
│  │                    │ - 통합 매칭 결과      │                         │   │
│  │                    └───────────────────────┘                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 스캔 서비스

### 4.1 스캔 모드

| 모드 | 설명 |
|------|------|
| `INCREMENTAL` | 신규 파일만 추가 (기존 유지) |
| `FULL` | 전체 재스캔 (기존 삭제) |

### 4.2 폴더 타입

| 타입 | 스캔 대상 |
|------|----------|
| `ORIGIN` | Y: 드라이브만 |
| `ARCHIVE` | Z: 드라이브만 |
| `POKERGO` | X: 드라이브만 |
| `BOTH` | Y: + Z: |
| `ALL` | Y: + Z: + X: |

### 4.3 제외 규칙 (is_excluded 플래그)

| 조건 | 기준 | 체크박스 |
|------|------|----------|
| Size | < 1GB | `<1GB` |
| Duration | < 30분 | `<30min` |
| Keyword | `clip` 포함 | `Clip` |
| Keyword | `hand_`, `-hs-` 등 | `Hand` |
| Keyword | `circuit` 포함 | `Circuit` |

**중요**: 제외 파일도 DB에 저장됨 (`is_excluded=True`)

---

## 5. 패턴 매칭 엔진

### 5.1 추출 메타데이터

| 필드 | 설명 | 예시 |
|------|------|------|
| `year` | 연도 | 2011, 2024 |
| `region` | 지역 | LV, EU, APAC, PARADISE |
| `event_type` | 이벤트 | ME, BR, HR, GM, HU |
| `episode` | 에피소드 | 1, 25 |
| `stage` | 스테이지 | D1A, D2, FT |

### 5.2 주요 패턴

| 패턴 | 예시 | 추출 |
|------|------|------|
| `WS{YY}_{TYPE}{EP}` | WS11_ME25 | Year=2011, Type=ME, Ep=25 |
| `WSOP{YY}_{TYPE}{EP}` | WSOP13_ME01 | Year=2013, Type=ME, Ep=01 |
| `WSOPE{YY}_Episode_{EP}` | WSOPE08_Episode_5 | Year=2008, Region=EU, Ep=5 |
| `{YYYY} WSOP ME{EP}` | 2009 WSOP ME13 | Year=2009, Type=ME, Ep=13 |

---

## 6. 매칭 전략

### 6.1 매칭 키

| 타입 | NAS 필드 | PokerGO 필드 |
|------|----------|--------------|
| Main Event Episode | year + episode | title에서 추출 |
| Main Event Day | year + stage | title에서 추출 |
| Bracelet Event | year + event_num | title에서 추출 |

### 6.2 정규화 매칭

```
NAS: WSOP 2024 Main Event _ Episode 1.mp4
     ↓ 정규화
     wsop 2024 main event episode 1
     ↓ 비교
PokerGO: WSOP 2024 Main Event | Episode 1
     ↓ 정규화
     wsop 2024 main event episode 1
     ↓
     MATCH!
```

### 6.3 CLASSIC Era 연도 매칭

1973-2002년은 연도당 Main Event 1개이므로 연도만으로 매칭:

```
wsop-1978-me-nobug.mp4 → Wsop 1978 Main Event
```

### 6.4 Region별 PokerGO 데이터 가용성

| Region | PokerGO | 매칭 결과 |
|--------|---------|----------|
| **LV** (Las Vegas) | 있음 | MATCHED |
| **EU** (Europe) | 있음 (2008-2021) | MATCHED |
| **APAC** | 없음 | NAS_ONLY_MODERN |
| **PARADISE** | 없음 | NAS_ONLY_MODERN |
| **CYPRUS** | 없음 | NAS_ONLY_MODERN |
| **LONDON** | 없음 | NAS_ONLY_MODERN |
| **LA** (Circuit) | 없음 | NAS_ONLY_MODERN |

### 6.5 DUPLICATE 방지 규칙

**1. Region Mismatch 스킵**
```python
# EU/APAC 그룹 → LV 에피소드 매칭 방지
if region_code in ('EU', 'APAC', 'PARADISE', 'CYPRUS', 'LONDON', 'LA'):
    if not ep_is_regional:
        continue  # SKIP
```

**2. Event # 필수 매칭**
```python
# Bracelet Event에서 Event # 불일치 방지
if group_event_num:
    if not event_num_in_title:
        continue  # SKIP
```

**3. LA Circuit vs Ladies 구분**
- LA = Los Angeles Circuit (PokerGO 없음)
- Ladies = LV Bracelet Event #71 (PokerGO 있음)
- `WCLA`, `Los Angeles` → NAS_ONLY_MODERN

---

## 7. Google Sheets 출력

### 7.1 시트 구조

| # | 시트명 | 용도 | 행 수 |
|---|--------|------|-------|
| 1 | NAS_Origin_Raw | Y: 드라이브 파일 | 1,568 |
| 2 | NAS_Archive_Raw | Z: 드라이브 파일 | 1,405 |
| 3 | NAS_PokerGO_Raw | X: 드라이브 파일 | 828 |
| 4 | PokerGO_Raw | PokerGO 메타데이터 | 828 |
| 5 | Matching_Integrated | 통합 매칭 결과 | 1,721+ |

### 7.2 Matching_Integrated 컬럼

```
Year | NAS Filename | Full_Path | PokerGO Title |
Origin | Archive | PokerGO_Src | PKG |  ← Storage Status (4개 체크박스)
<1GB | <30min | Clip | Hand | Circuit |  ← Exclude Conditions (5개 체크박스)
Backup | Group ID | Action                ← Duplicate & Action
```

### 7.3 Action 판정 로직

```
1. 제외 조건 해당 시
   → Action = "Excluded"

2. Origin 있고 Archive 없음
   → Action = "→ Archive"

3. NAS 없고 PKG만 있음
   → Action = "→ Find NAS"

4. 그 외
   → Action = (빈칸)
```

---

## 8. 스크립트 실행 순서

### 8.1 초기 설정

```powershell
# 1. DB 초기화
python scripts/scan_nas.py --mode full --folder all

# 2. PokerGO 데이터 로드
# data/pokergo/wsop_final.json 준비

# 3. Google Sheets 내보내기
python scripts/export_4sheets.py
```

### 8.2 증분 업데이트

```powershell
# 신규 파일만 추가
python scripts/scan_nas.py --mode incremental --folder all

# 시트 재내보내기
python scripts/export_4sheets.py
```

---

## 9. 주요 코드 파일

### 9.1 Backend (API)

| 파일 | 역할 |
|------|------|
| `src/nams/api/services/scanner.py` | NAS 스캔 서비스 |
| `src/nams/api/services/matching.py` | PokerGO 매칭 서비스 |
| `src/nams/api/services/export.py` | 내보내기 서비스 |
| `src/nams/api/database/models.py` | SQLAlchemy 모델 |

### 9.2 Scripts

| 파일 | 역할 |
|------|------|
| `scripts/scan_nas.py` | NAS 스캔 CLI |
| `scripts/export_4sheets.py` | Google Sheets 5시트 내보내기 |
| `scripts/match_pokergo_nas.py` | PokerGO-NAS 매칭 |

---

## 10. 문서 참조

| 문서 | 내용 |
|------|------|
| `MATCHING_RULES.md` | 매칭 규칙 상세 (v4.0) |
| `PRD-NAMS-MATCHING.md` | 매칭 시스템 PRD (v2.0) |
| `PRD-POKERGO-SOURCE.md` | X: 드라이브 통합 PRD |
| `CLAUDE.md` | 프로젝트 가이드 |
| `NAS_DRIVE_STRUCTURE.md` | 드라이브 폴더 구조 상세 |

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2025-12-17 | 초기 문서 작성 |
| 2.0 | 2025-12-17 | 매칭 현황 추가, DUPLICATE 방지 규칙 추가 |
| 2.1 | 2025-12-17 | 드라이브 파일 수 업데이트, NAS_DRIVE_STRUCTURE.md 참조 추가 |
| 2.1 | 2025-12-17 | 드라이브 파일 수 업데이트, NAS_DRIVE_STRUCTURE.md 참조 추가 |
