# PRD: Sheet to Sheet Migration PWA

> CLASP CLI 기반 Google Sheets 간 마이그레이션 PWA

**Version**: 1.0 | **Date**: 2025-12-19 | **Status**: Draft

---

## 1. 개요

### 1.1 배경

현재 NAMS 시스템에서 Google Sheets를 통한 데이터 관리가 이루어지고 있습니다:
- 5개 시트: NAS_Origin_Raw, NAS_Archive_Raw, NAS_PokerGO_Raw, PokerGO_Raw, Matching_Integrated
- GAS 기반 자동 동기화 (`gas/Code.gs`)
- CLASP으로 로컬 개발 환경 구축됨

시트 간 데이터 마이그레이션/변환 작업을 위한 전용 도구가 필요합니다.

### 1.2 목표

1. **시트 관리**: 여러 스프레드시트의 시트 목록 조회 및 미리보기
2. **마이그레이션**: 셀/범위 단위 복사, 컬럼 매핑, 데이터 변환
3. **스케줄링**: 자동 실행 트리거 관리 및 실행 이력 조회
4. **PWA**: 오프라인 지원, 설치 가능한 웹 앱

### 1.3 핵심 원칙

- **GAS 기반**: Google Apps Script로 핵심 로직 구현 (실행 시간 제한 고려)
- **PWA UI**: React 기반 사용자 인터페이스
- **완전 독립**: 기존 NAMS 코드와 분리된 독립 프로젝트

---

## 2. 아키텍처

### 2.1 시스템 구성도

```
┌─────────────────────────────────────────────────────────────┐
│                        PWA (React)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Dashboard  │  │  Migration  │  │  Scheduler  │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         └────────────────┼────────────────┘                  │
│                          ▼                                   │
│              ┌───────────────────────┐                       │
│              │     GAS API Client    │                       │
│              └───────────┬───────────┘                       │
└──────────────────────────┼───────────────────────────────────┘
                           │ HTTPS (doGet/doPost)
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                 Google Apps Script Web App                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │ │
│  │  │ SheetService│  │MigrationSvc │  │ TriggerManager  │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   Google Spreadsheets                         │
│  ┌────────────────┐     ┌────────────────┐                   │
│  │  Source Sheet  │ ──▶ │  Target Sheet  │                   │
│  └────────────────┘     └────────────────┘                   │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 GAS + PWA 연동

| 구성 요소 | 역할 | 호스팅 |
|-----------|------|--------|
| GAS Web App | 데이터 처리, 시트 조작 | Google Apps Script |
| PWA | 사용자 인터페이스 | GitHub Pages / Vercel |

### 2.3 데이터 흐름

```
[마이그레이션 실행]
1. PWA → 마이그레이션 설정 입력
2. PWA → GAS doPost() 호출
3. GAS → 소스 시트 데이터 읽기
4. GAS → 변환 규칙 적용
5. GAS → 타겟 시트에 쓰기
6. GAS → 결과 반환
7. PWA → 결과 표시
```

---

## 3. 기능 요구사항

### 3.1 시트 관리 (FR-1xx)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| FR-101 | 시트 목록 조회 | 스프레드시트 내 모든 시트 목록 | P0 |
| FR-102 | 시트 미리보기 | 헤더 + 샘플 행 (최대 10행) | P0 |
| FR-103 | 범위 선택 | A1:Z100 형식 또는 GUI 선택 | P0 |
| FR-104 | 멀티 스프레드시트 | 여러 스프레드시트 연동 | P1 |
| FR-105 | 시트 생성/삭제 | 타겟 시트 관리 | P2 |

### 3.2 마이그레이션 (FR-2xx)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| FR-201 | 셀 단위 복사 | 개별 셀 또는 범위 복사 | P0 |
| FR-202 | 컬럼 매핑 | 소스 → 타겟 컬럼 매핑 | P0 |
| FR-203 | 데이터 변환 | 대소문자, 포맷 변환 | P1 |
| FR-204 | 필터링 | 조건에 맞는 행만 복사 | P1 |
| FR-205 | 중복 처리 | 중복 행 감지/스킵/병합 | P1 |
| FR-206 | Dry Run | 실제 실행 전 시뮬레이션 | P1 |
| FR-207 | 롤백 | 실패 시 원복 | P2 |

### 3.3 스케줄링 (FR-3xx)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| FR-301 | 시간 기반 트리거 | 매일/매주/매월 자동 실행 | P0 |
| FR-302 | 수동 실행 | 버튼 클릭으로 즉시 실행 | P0 |
| FR-303 | 트리거 목록 | 등록된 트리거 조회/삭제 | P0 |
| FR-304 | 실행 로그 | 실행 이력 조회 | P1 |
| FR-305 | 알림 설정 | 실패 시 이메일 알림 | P1 |

### 3.4 변환 규칙 (FR-4xx)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| FR-401 | 텍스트 변환 | UPPER/LOWER/TRIM/CONCAT | P0 |
| FR-402 | 날짜 포맷 | 날짜 형식 변환 | P1 |
| FR-403 | 숫자 포맷 | 통화, 소수점 등 | P1 |
| FR-404 | 정규식 치환 | REGEX 기반 값 치환 | P1 |
| FR-405 | 룩업 변환 | 다른 시트 참조 변환 | P2 |

---

## 4. 비기능 요구사항

### 4.1 성능 (NFR-1xx)

| ID | 요구사항 | 목표 |
|----|----------|------|
| NFR-101 | GAS 실행 시간 | 6분 제한 내 완료 |
| NFR-102 | 배치 처리 | 1000행 단위 처리 |
| NFR-103 | PWA 로딩 | 3초 이내 |

### 4.2 보안 (NFR-2xx)

| ID | 요구사항 | 목표 |
|----|----------|------|
| NFR-201 | 인증 | Google OAuth 또는 서비스 계정 |
| NFR-202 | 권한 | 스프레드시트 접근 권한만 |

### 4.3 PWA 요구사항 (NFR-3xx)

| ID | 요구사항 | 목표 |
|----|----------|------|
| NFR-301 | 설치 가능 | Add to Home Screen 지원 |
| NFR-302 | 오프라인 | 설정 화면 오프라인 접근 |
| NFR-303 | 반응형 | 모바일/데스크톱 지원 |

---

## 5. 기술 스택

### 5.1 GAS (Google Apps Script)

| 구성 요소 | 선택 |
|-----------|------|
| 런타임 | V8 |
| 개발 언어 | TypeScript |
| CLI | CLASP |
| API | SpreadsheetApp, ScriptApp |

### 5.2 PWA (Progressive Web App)

| 구성 요소 | 선택 |
|-----------|------|
| 프레임워크 | React 19 |
| 빌드 | Vite 7 |
| 상태 관리 | Zustand |
| 데이터 페칭 | TanStack Query v5 |
| 스타일링 | Tailwind CSS v4 |
| PWA 플러그인 | vite-plugin-pwa |
| 라우팅 | React Router v7 |

---

## 6. API 설계

### 6.1 GAS Web App 엔드포인트

#### GET 요청

| Action | 설명 | 파라미터 |
|--------|------|----------|
| `sheets` | 시트 목록 | spreadsheetId |
| `preview` | 시트 미리보기 | spreadsheetId, sheetName, range |
| `triggers` | 트리거 목록 | - |
| `logs` | 실행 로그 | limit, offset |

#### POST 요청

| Action | 설명 | Body |
|--------|------|------|
| `migrate` | 마이그레이션 실행 | source, target, mappings, transforms |
| `createTrigger` | 트리거 생성 | schedule, migrationConfig |
| `deleteTrigger` | 트리거 삭제 | triggerId |
| `testRun` | Dry Run | source, target, mappings |

### 6.2 응답 형식

```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
  };
  timestamp: string;
}
```

---

## 7. 구현 계획

### Phase 1: GAS 기반 구축

| 작업 | 파일 |
|------|------|
| CLASP 프로젝트 설정 | gas/.clasp.json |
| SheetService 구현 | gas/SheetService.ts |
| MigrationEngine 구현 | gas/MigrationEngine.ts |
| TriggerManager 구현 | gas/TriggerManager.ts |

### Phase 2: PWA UI 개발

| 작업 | 파일 |
|------|------|
| Vite PWA 설정 | vite.config.ts, manifest.json |
| 레이아웃 컴포넌트 | components/layout/* |
| 시트 선택 컴포넌트 | components/sheets/* |
| 마이그레이션 위자드 | components/migration/* |
| 스케줄러 UI | components/scheduler/* |

### Phase 3: 고급 기능

| 작업 | 파일 |
|------|------|
| 변환 규칙 엔진 | gas/TransformEngine.ts |
| 실행 로그 UI | pages/History.tsx |
| E2E 테스트 | e2e/*.spec.ts |

---

## 8. 성공 기준

| 지표 | 목표 |
|------|------|
| 시트 미리보기 응답 시간 | < 2초 |
| 1000행 마이그레이션 | < 30초 |
| PWA Lighthouse 점수 | > 90 |
| GAS 실행 성공률 | > 99% |

---

## 9. 참고 자료

- [CLASP 문서](https://github.com/google/clasp)
- [Google Apps Script 참조](https://developers.google.com/apps-script/reference)
- [Vite PWA 플러그인](https://vite-pwa-org.netlify.app/)
- 기존 GAS 코드: `gas/Code.gs`
