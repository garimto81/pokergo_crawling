# NAMS Sheets Sync (Google Apps Script)

작업자 메타데이터 시트 → NAMS 시트 자동 동기화

## 설정 방법

### 1. CLASP 설치

```bash
npm install -g @google/clasp
```

### 2. Google 로그인

```bash
clasp login
```

### 3. 프로젝트 생성

```bash
# 새 프로젝트 생성
clasp create --type sheets --title "NAMS-Sheets-Sync"

# 또는 기존 프로젝트에 연결
clasp clone <SCRIPT_ID>
```

### 4. 설정 수정

`Code.gs` 파일에서 CONFIG 수정:

```javascript
const CONFIG = {
  SOURCE_SHEET_ID: "작업자_시트_ID",
  TARGET_SHEET_ID: "NAMS_시트_ID",
  ADMIN_EMAIL: "관리자_이메일"
};
```

### 5. 배포

```bash
clasp push
clasp deploy
```

### 6. 트리거 설정

Google Apps Script 에디터에서:
1. `createDailyTrigger()` 함수 실행
2. 또는 수동으로 트리거 추가

## 파일 구조

| 파일 | 설명 |
|------|------|
| `Code.gs` | 메인 동기화 로직 |
| `appsscript.json` | GAS 프로젝트 설정 |
| `.clasp.json` | CLASP 설정 (로컬용) |

## 주요 함수

| 함수 | 설명 |
|------|------|
| `syncMetadata()` | 메인 동기화 (트리거로 실행) |
| `createDailyTrigger()` | 매일 트리거 생성 |
| `testSync()` | 수동 테스트 |
| `checkConfig()` | 설정 확인 |

## 시트 ID 찾기

Google Sheets URL:
```
https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit
```

`[SHEET_ID]` 부분이 시트 ID입니다.
