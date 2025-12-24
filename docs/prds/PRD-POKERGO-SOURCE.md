# PRD: PokerGO Source 추가 (X: 드라이브)

> **버전**: 1.0
> **날짜**: 2025-12-17
> **상태**: Active

---

## 1. 개요

### 1.1 목적

새 NAS 경로 `X:\GGP Footage\POKERGO`를 NAMS 시스템에 추가하여 PokerGO 원본 파일을 통합 관리.

### 1.2 데이터 소스 현황

| 드라이브 | 경로 | 용도 | 상태 |
|----------|------|------|------|
| Y: | WSOP Backup | Origin (원본) | 기존 |
| Z: | Archive | Archive (아카이브) | 기존 |
| **X:** | **GGP Footage/POKERGO** | **PokerGO 원본** | **신규** |

---

## 2. 신규 데이터 분석

### 2.1 스캔 결과 (2025-12-17)

```
Source: X:\GGP Footage\POKERGO
Total Files: 247
Total Size: 684.3 GB
Extension: .mp4 (100%)
```

### 2.2 폴더 구조

| 폴더 | 파일 수 | 용량 | 연도 |
|------|---------|------|------|
| WSOP 2024 | 110 | 528.0 GB | 2024 |
| WSOP 2023 | 51 | 58.6 GB | 2023 |
| WSOP 2019 | 44 | 52.1 GB | 2019 |
| WSOP 2017 | 18 | 25.8 GB | 2017 |
| WSOP 2018 | 15 | 10.5 GB | 2018 |
| WSOPE 2009 | 5 | 7.4 GB | 2009 |
| WSOP 2020 | 4 | 1.9 GB | 2020 |

### 2.3 파일 패턴

**특징**: 파일명이 PokerGO 타이틀과 **거의 동일**

| 타입 | 파일명 패턴 | 예시 |
|------|------------|------|
| Main Event | `WSOP {YYYY} Main Event _ Episode {N}.mp4` | WSOP 2017 Main Event _ Episode 1.mp4 |
| Bracelet | `WSOP {YYYY} Bracelet Events - Episodes - Event #{N} ...` | WSOP 2024 Bracelet Events - Episodes - Event #1 $5K Champions Reunion (Part 1).mp4 |
| Europe | `WSOP Europe {YYYY} ... Episode {N}.mp4` | Wsop Europe 2009 Main Event Episode 2.mp4 |

---

## 3. 시스템 변경사항

### 3.1 Scanner 확장

```python
class FolderType(str, Enum):
    ORIGIN = "origin"       # Y: 드라이브
    ARCHIVE = "archive"     # Z: 드라이브
    POKERGO = "pokergo"     # X: 드라이브 (신규)
    BOTH = "both"           # 기존 (Origin + Archive)
    ALL = "all"             # 전체 (Origin + Archive + PokerGO)

@dataclass
class ScanConfig:
    origin_path: str = "Y:/WSOP Backup"
    archive_path: str = "Z:/archive"
    pokergo_path: str = "X:/GGP Footage/POKERGO"  # 신규
```

### 3.2 Google Sheets 확장

| 시트명 | 용도 | 상태 |
|--------|------|------|
| NAS_Origin_Raw | Y: 드라이브 파일 | 기존 |
| NAS_Archive_Raw | Z: 드라이브 파일 | 기존 |
| **NAS_PokerGO_Raw** | **X: 드라이브 파일** | **신규** |
| PokerGO_Raw | PokerGO 메타데이터 | 기존 |
| Matching_Integrated | 통합 매칭 | 확장 |

### 3.3 Matching_Integrated 컬럼 확장

| 컬럼 | 설명 | 변경 |
|------|------|------|
| Origin | Y: 존재 여부 | 기존 |
| Archive | Z: 존재 여부 | 기존 |
| **PokerGO_Src** | **X: 존재 여부** | **신규** |
| PKG | PokerGO 매칭 여부 | 기존 |

---

## 4. 매칭 전략

### 4.1 직접 매칭 (높은 정확도)

X: 드라이브 파일명이 PokerGO 타이틀과 거의 동일하므로 **직접 매칭** 가능

```python
# X: 파일명 정규화
def normalize_pokergo_filename(filename: str) -> str:
    # 언더스코어/하이픈 → 파이프
    # "WSOP 2017 Main Event _ Episode 1.mp4"
    # → "WSOP 2017 Main Event | Episode 1"
    name = filename.rsplit('.', 1)[0]
    name = name.replace(' _ ', ' | ')
    name = name.replace(' - ', ' | ')
    return name
```

### 4.2 예상 매칭률

| 소스 | 파일 수 | 예상 매칭률 | 이유 |
|------|---------|-------------|------|
| X: PokerGO | 247 | **95%+** | 파일명 = PokerGO 타이틀 |
| Z: Archive | 1,282 | 50% | 다양한 파일명 패턴 |
| Y: Origin | 0 | - | 현재 없음 |

---

## 5. 구현 계획

### 5.1 Phase 1: Scanner 확장

| 작업 | 설명 |
|------|------|
| FolderType 확장 | POKERGO, ALL 추가 |
| ScanConfig 확장 | pokergo_path 추가 |
| run_scan() 수정 | X: 드라이브 스캔 로직 |
| role 설정 | pokergo → "pokergo_source" |

### 5.2 Phase 2: Export 확장

| 작업 | 설명 |
|------|------|
| NAS_PokerGO_Raw 시트 | 새 시트 생성 |
| Matching_Integrated | PokerGO_Src 컬럼 추가 |
| 체크박스 | PokerGO_Src 체크박스 추가 |

### 5.3 Phase 3: 매칭 개선

| 작업 | 설명 |
|------|------|
| 직접 매칭 | X: 파일 → PokerGO 타이틀 |
| 크로스 체크 | X: 파일 ↔ Z: 파일 중복 확인 |

---

## 6. 데이터 모델

### 6.1 NasFile.role 확장

| role | 드라이브 | 설명 |
|------|----------|------|
| primary | Y: | Origin 원본 |
| backup | Z: | Archive 백업 |
| **pokergo_source** | **X:** | **PokerGO 원본** |

### 6.2 Storage Status 확장

```
┌──────────┬──────────┬──────────────┬───────┐
│  Origin  │  Archive │ PokerGO_Src  │  PKG  │
├──────────┼──────────┼──────────────┼───────┤
│   [V]    │   [V]    │     [V]      │  [V]  │  ← 완전 매칭
│   [ ]    │   [V]    │     [ ]      │  [V]  │  ← Archive + PKG
│   [ ]    │   [ ]    │     [V]      │  [V]  │  ← PokerGO Source Only
│   [ ]    │   [V]    │     [V]      │  [V]  │  ← Archive + PokerGO Src
└──────────┴──────────┴──────────────┴───────┘
```

---

## 7. 예상 결과

### 7.1 통합 후 데이터

| 항목 | 현재 | 추가 후 |
|------|------|---------|
| 총 NAS 파일 | 1,282 | 1,529 (+247) |
| PokerGO 매칭 | 872 | ~1,100 (+~228) |
| 매칭률 | 50.7% | ~72% |

### 7.2 연도별 커버리지

| 연도 | Archive | PokerGO Src | 합계 |
|------|---------|-------------|------|
| 2024 | 많음 | +110 | 확대 |
| 2023 | 많음 | +51 | 확대 |
| 2019 | 적음 | +44 | 신규 |
| 2017-2018 | 적음 | +33 | 신규 |
| 2009 (EU) | 있음 | +5 | 보완 |

---

## 8. 검증 기준

| 항목 | 기준 |
|------|------|
| X: 스캔 완료 | 247개 파일 DB 저장 |
| NAS_PokerGO_Raw 시트 | 247 rows |
| PokerGO 직접 매칭 | 95%+ (234+ 파일) |
| Matching_Integrated | PokerGO_Src 컬럼 정상 |

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2025-12-17 | 초기 PRD 작성 |
