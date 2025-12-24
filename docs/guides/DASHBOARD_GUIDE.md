# NAMS Dashboard 사용 가이드

NAMS (NAS Asset Management System) 대시보드 사용 방법 및 각 지표의 의미를 설명합니다.

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [대시보드 지표](#2-대시보드-지표)
3. [액션 버튼](#3-액션-버튼)
4. [용어 정리](#4-용어-정리)
5. [워크플로우](#5-워크플로우)

---

## 1. 시스템 개요

**URL**: http://localhost:5174

NAMS는 NAS 파일을 패턴 기반으로 분류하고 PokerGO 에피소드와 매칭하는 시스템입니다.

### 실행 방법

```powershell
# API 서버 (포트 8001)
cd src/nams/api && uvicorn main:app --reload --port 8001

# UI 서버 (포트 5174)
cd src/nams/ui && npm run dev -- --port 5174
```

---

## 2. 대시보드 지표

### 2.1 KPI 카드

대시보드 상단에 4개의 핵심 지표가 표시됩니다:

```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│  Total Files    │  Total Groups   │ PokerGO Matched │   Unmatched     │
│     1,690       │      850        │      720        │       45        │
│   (125.4 GB)    │  (85.2% grouped)│ (84.7% match)   │  (no group)     │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

| 지표 | 의미 | 정상 범위 |
|------|------|----------|
| **Total Files** | NAS에서 스캔된 전체 비디오 파일 수 | - |
| **Total Groups** | 패턴 매칭으로 생성된 그룹 수 | 파일 수의 50-70% |
| **PokerGO Matched** | PokerGO 에피소드와 매칭된 그룹 수 | 그룹의 80%+ |
| **Unmatched** | 그룹에 속하지 않은 파일 수 | 5% 이하 권장 |

### 2.2 Year Distribution

연도별 파일/그룹 분포를 보여줍니다.

```
┌──────────┬──────────┬──────────┬──────────┐
│   2024   │   2023   │   2022   │   2021   │
│ 120 files│ 98 files │ 85 files │ 76 files │
│ 45 groups│ 38 groups│ 32 groups│ 28 groups│
└──────────┴──────────┴──────────┴──────────┘
```

- **파일 수**: 해당 연도 WSOP/이벤트의 NAS 파일 수
- **그룹 수**: 동일 콘텐츠를 묶은 그룹 수 (Primary + Backup)

### 2.3 Region Distribution

지역별 파일 분포입니다.

| 지역 코드 | 전체 이름 | 설명 |
|-----------|----------|------|
| **LV** | Las Vegas | 기본 WSOP (라스베가스) |
| **EU** | Europe | WSOP Europe |
| **APAC** | Asia Pacific | WSOP APAC (2013-2014) |
| **PARADISE** | Paradise (Bahamas) | WSOP Paradise (2023-) |

### 2.4 Attention Needed (주의 필요)

노란색 경고 박스로 관리자 개입이 필요한 항목을 표시합니다.

| 경고 | 의미 | 조치 |
|------|------|------|
| **files without group** | 패턴 매칭 실패 | Files 페이지에서 수동 분류 |
| **files with unknown type** | 이벤트 타입 인식 실패 | 패턴 추가 필요 |
| **files without year** | 연도 추출 실패 | 파일명/경로 확인 |

---

## 3. 액션 버튼

### 3.1 NAS Scan

NAS 폴더를 스캔하여 새 파일을 추가합니다.

```
┌─────────────────────────────────────────────┐
│  NAS Scan                                   │
├─────────────────────────────────────────────┤
│  Origin Path:  [Y:/WSOP Backup          ]   │
│  Archive Path: [Z:/archive              ]   │
│                                             │
│  Scan Mode:                                 │
│  ○ Incremental (추가분만)                   │
│  ○ Full (전체 재스캔)                       │
│                                             │
│  Folder:                                    │
│  ○ Both  ○ Origin Only  ○ Archive Only     │
└─────────────────────────────────────────────┘
```

| 옵션 | 설명 |
|------|------|
| **Incremental** | 새로 추가된 파일만 스캔 (빠름) |
| **Full** | 전체 재스캔 (정확, 느림) |
| **Origin** | 원본 소스 폴더 |
| **Archive** | 아카이브 폴더 |

### 3.2 Export

데이터를 다양한 형식으로 내보냅니다.

| 형식 | 설명 |
|------|------|
| **CSV** | 스프레드시트용 CSV 파일 |
| **JSON** | 개발/분석용 JSON 파일 |
| **Google Sheets** | Google Sheets 직접 업로드 (API 설정 필요) |

### 3.3 Import JSON

기존 JSON 데이터를 DB로 마이그레이션합니다.

---

## 4. 용어 정리

### 4.1 파일 관련

| 용어 | 설명 |
|------|------|
| **Origin** | 원본 소스 파일 경로 (변경 안 됨) |
| **Archive** | 아카이브 폴더 경로 (정리된 구조) |
| **Primary** | 그룹 내 대표 파일 (MP4 우선) |
| **Backup** | 그룹 내 백업 파일 (같은 콘텐츠) |

### 4.2 패턴 관련

| 용어 | 설명 |
|------|------|
| **Pattern** | 파일명/경로에서 메타데이터를 추출하는 정규식 |
| **Group ID** | `{YYYY}_{REGION}_{TYPE}_{EPISODE}` 형식의 식별자 |
| **Event Type** | ME (Main Event), BR (Bracelet), HR (High Roller) 등 |

### 4.3 매칭 관련

| 용어 | 설명 |
|------|------|
| **PokerGO Match** | NAS 그룹과 PokerGO 에피소드 연결 |
| **Match Rate** | 전체 그룹 중 PokerGO 매칭된 비율 |

---

## 5. 워크플로우

### 5.1 새 NAS 파일 추가 시

```
1. Dashboard → NAS Scan 버튼
2. Incremental 모드로 스캔
3. Attention Needed 확인
4. 필요시 Files 페이지에서 수동 분류
```

### 5.2 패턴 매칭 실패 시

```
1. Files 페이지에서 Unmatched 파일 확인
2. 파일명 패턴 분석
3. Patterns 페이지에서 새 패턴 추가
4. Dashboard → Import JSON으로 재처리
```

### 5.3 내보내기

```
1. Dashboard → Export 버튼
2. 형식 선택 (CSV/JSON/Google Sheets)
3. 다운로드 또는 Sheets URL 확인
```

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2025-12-16 | 2.0 | YouTube 관련 내용 제거, NAMS 전용으로 변경 |
| 2025-12-16 | 1.0 | 초기 문서 작성 |
