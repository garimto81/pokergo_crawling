# PRD: Google Sheets 동기화 (CLASP + GAS)

> 작업자 메타데이터 시트 → NAMS 시트 자동 동기화

**Version**: 1.0 | **Date**: 2025-12-19 | **Status**: Draft

---

## 1. 개요

### 1.1 배경

작업자들이 MAM 솔루션이나 구글 시트에서 메타데이터를 작업하고 있습니다. 이 데이터에서 **카테고리**와 **제목** 정보를 추출하여 NAMS 시스템으로 마이그레이션해야 합니다.

### 1.2 핵심 원칙

- **별도 앱 불필요**: Google Apps Script로 처리
- **자동 동기화**: 매일 스케줄 실행
- **단방향 흐름**: 작업자 시트 → NAMS 시트

### 1.3 목표

| 항목 | 목표 |
|------|------|
| 동기화 주기 | 매일 1회 (오전 6시) |
| 추출 필드 | 카테고리, 제목 |
| 실패 알림 | 이메일 알림 |

---

## 2. 아키텍처

```
┌──────────────────────────┐          ┌──────────────────────────┐
│     작업자 시트 (소스)     │          │     NAMS 시트 (타겟)      │
│   (별도 스프레드시트)      │          │   (별도 스프레드시트)      │
├──────────────────────────┤          ├──────────────────────────┤
│                          │          │                          │
│  파일명 | 카테고리 | 제목  │          │  Metadata_Import 시트    │
│                          │          │                          │
└────────────┬─────────────┘          └────────────▲─────────────┘
             │                                      │
             │                                      │
             │      Google Apps Script              │
             │      (CLASP으로 관리)                 │
             │      매일 06:00 AM 실행              │
             │                                      │
             └──────────────────────────────────────┘
```

---

## 3. 요구사항

### 3.1 기능 요구사항

| # | 요구사항 | 설명 |
|---|----------|------|
| FR-1 | 시트 간 데이터 복사 | 소스 시트의 카테고리/제목을 타겟 시트로 복사 |
| FR-2 | 매일 자동 실행 | 시간 기반 트리거로 매일 06:00 AM 실행 |
| FR-3 | 실행 로그 | 동기화 결과를 로그 시트에 기록 |
| FR-4 | 에러 알림 | 실패 시 이메일 알림 발송 |

### 3.2 비기능 요구사항

| # | 요구사항 | 설명 |
|---|----------|------|
| NFR-1 | 실행 시간 | 1000행 기준 10초 이내 |
| NFR-2 | 신뢰성 | 실패 시 재시도 로직 |

---

## 4. 데이터 구조

### 4.1 소스 시트 형식 (작업자 시트)

| 열 | 필드명 | 예시 |
|----|--------|------|
| A | 파일명 | wsop_2024_me_d1.mp4 |
| B | 카테고리 | WSOP 2024 |
| C | 제목 | 2024 WSOP Main Event Day 1 |

### 4.2 타겟 시트 형식 (NAMS 시트)

| 열 | 필드명 | 설명 |
|----|--------|------|
| A | 파일명 | 소스에서 복사 |
| B | 카테고리 | 소스에서 복사 |
| C | 제목 | 소스에서 복사 |
| D | 동기화일시 | 자동 기록 |

---

## 5. 기술 스택

### 5.1 Google Apps Script (GAS)

- **런타임**: V8 엔진
- **API**: SpreadsheetApp, ScriptApp
- **트리거**: 시간 기반 트리거

### 5.2 CLASP CLI

- **용도**: 로컬에서 GAS 개발 및 배포
- **버전 관리**: Git과 연동 가능

```bash
# 설치
npm install -g @google/clasp

# 프로젝트 설정
clasp login
clasp create --type sheets --title "NAMS-Sheets-Sync"
clasp push
clasp deploy
```

---

## 6. 구현 계획

### 6.1 파일 구조

```
gas/
├── Code.gs              # 메인 동기화 로직
├── Config.gs            # 설정 (시트 ID 등)
├── Logger.gs            # 로그 기록
├── appsscript.json      # GAS 프로젝트 설정
└── .clasp.json          # CLASP 설정
```

### 6.2 핵심 함수

| 함수 | 설명 |
|------|------|
| `syncMetadata()` | 메인 동기화 함수 |
| `createDailyTrigger()` | 매일 트리거 생성 |
| `logSync()` | 동기화 결과 기록 |
| `sendErrorEmail()` | 에러 알림 발송 |

### 6.3 트리거 설정

```javascript
function createDailyTrigger() {
  // 기존 트리거 삭제
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => ScriptApp.deleteTrigger(trigger));

  // 새 트리거 생성 (매일 오전 6시)
  ScriptApp.newTrigger('syncMetadata')
    .timeBased()
    .everyDays(1)
    .atHour(6)
    .create();
}
```

---

## 7. 기존 시스템과의 관계

### 7.1 export_4sheets.py

| 항목 | export_4sheets.py | GAS 동기화 |
|------|-------------------|-----------|
| 방향 | DB → Sheets | Sheets → Sheets |
| 실행 | Python 스크립트 | GAS 트리거 |
| 용도 | NAMS DB 내보내기 | 외부 메타 가져오기 |

### 7.2 통합 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                    전체 데이터 흐름                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [NAS 드라이브]                                                  │
│       │                                                         │
│       ▼ (daily_scan.py - 매일 03:00)                           │
│  [NAMS DB]                                                      │
│       │                                                         │
│       ▼ (export_4sheets.py - 매일 04:00)                       │
│  [NAMS Sheets] ◀─── [작업자 시트]                               │
│                    (GAS 동기화 - 매일 06:00)                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. 배포 가이드

### 8.1 초기 설정

```bash
# 1. CLASP 설치
npm install -g @google/clasp

# 2. 로그인
clasp login

# 3. 프로젝트 클론 (기존 시트에 연결 시)
clasp clone <SCRIPT_ID>

# 또는 새 프로젝트 생성
clasp create --type sheets --title "NAMS-Sheets-Sync"
```

### 8.2 배포

```bash
# 코드 푸시
clasp push

# 배포
clasp deploy --description "v1.0"

# 웹 에디터 열기
clasp open
```

### 8.3 트리거 활성화

1. Google Apps Script 에디터 열기
2. `createDailyTrigger()` 함수 실행
3. 트리거 목록에서 확인

---

## 9. 성공 기준

| 지표 | 목표 |
|------|------|
| 동기화 성공률 | > 99% |
| 실행 시간 | < 30초 |
| 데이터 정확성 | 100% |

---

## 10. 참고 자료

### 관련 문서

| 문서 | 설명 |
|------|------|
| [SCHEDULER_SETUP.md](./SCHEDULER_SETUP.md) | Windows 스케줄러 설정 |
| [AUTOMATION_PIPELINE.md](./AUTOMATION_PIPELINE.md) | 자동화 파이프라인 |

### 관련 스크립트

| 파일 | 용도 |
|------|------|
| `scripts/export_4sheets.py` | DB → Sheets 내보내기 |
| `scripts/daily_scan.py` | NAS 일일 스캔 |

---

## 변경 이력

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-19 | 초기 작성 |
