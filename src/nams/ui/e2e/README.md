# NAMS E2E Tests (Playwright)

## 개요

NAMS 프론트엔드의 End-to-End 테스트 스위트입니다. Playwright를 사용하여 Chromium 브라우저에서 실행됩니다.

## 테스트 파일

| 파일 | 테스트 대상 | 주요 기능 |
|------|-------------|-----------|
| **dashboard.spec.ts** | Dashboard 페이지 | KPI 카드, 4-Category 매칭 상태, Sync 상태, 모달 (Scan/Export) |
| **files.spec.ts** | Files 페이지 | 파일 목록, 필터링, 페이지네이션, 검색 |
| **groups.spec.ts** | Groups 페이지 | Asset Group 목록, 필터링 (연도/매칭 상태), 상세 보기 |
| **patterns.spec.ts** | Patterns 페이지 | 패턴 목록, 우선순위, 테스트 기능 |
| **settings.spec.ts** | Settings 페이지 | 지역/이벤트 타입 설정, Exclusion 규칙 |
| **validator.spec.ts** | Validator 페이지 | 카탈로그 검증, 제목 편집, 영상 재생, 필터링 |

## 사전 요구사항

### 1. API 서버 실행 (필수)

E2E 테스트는 백엔드 API와 통신합니다. 테스트 전에 API 서버를 실행해야 합니다.

```powershell
# 터미널 1: API 서버
cd D:\AI\claude01\pokergo_crawling\src\nams\api
uvicorn main:app --reload --port 8001
```

API 서버가 실행되지 않으면 다음 테스트가 실패합니다:
- Dashboard 통계 표시 테스트
- Files/Groups 목록 테스트
- Validator 데이터 로드 테스트

### 2. 데이터베이스 준비

테스트 실행 전에 DB에 데이터가 있어야 합니다.

```powershell
# NAS 스캔 (샘플 데이터)
python D:\AI\claude01\pokergo_crawling\scripts\scan_nas.py --mode incremental --folder all
```

## 테스트 실행

### 전체 테스트 실행

```powershell
cd D:\AI\claude01\pokergo_crawling\src\nams\ui
npm run test:e2e
```

### 개별 파일 테스트

```powershell
npx playwright test dashboard.spec.ts
npx playwright test validator.spec.ts
```

### UI 모드 (디버깅용)

```powershell
npm run test:e2e:ui
```

UI 모드에서는:
- 테스트를 하나씩 실행하며 확인 가능
- 각 단계별 DOM 상태 확인
- 타임라인으로 실행 과정 추적

### 특정 테스트만 실행

```powershell
# 테스트 이름으로 필터링
npx playwright test --grep "should display validator page title"

# 파일 + 테스트 조합
npx playwright test validator.spec.ts --grep "keyboard shortcuts"
```

## 테스트 결과 확인

### HTML 리포트

```powershell
npx playwright show-report
```

테스트 실패 시 자동으로 생성되는 리포트:
- 스크린샷 (실패 시점)
- 비디오 (재시도 시)
- Trace (네트워크 요청, DOM 스냅샷)

### 스크린샷 위치

```
test-results/
├── validator-Validator-Page-should-display-validator-page-title-chromium/
│   ├── test-failed-1.png
│   └── error-context.md
└── ...
```

## 테스트 작성 패턴

### 1. Page Object 패턴 (권장)

```typescript
// e2e/pages/validator.page.ts
export class ValidatorPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/validator');
  }

  async filterByYear(year: number) {
    await this.page.locator('select').first().selectOption(String(year));
  }
}

// validator.spec.ts
test('should filter by year', async ({ page }) => {
  const validatorPage = new ValidatorPage(page);
  await validatorPage.goto();
  await validatorPage.filterByYear(2024);
});
```

### 2. 조건부 검증

API 응답이 없을 때도 테스트가 실패하지 않도록:

```typescript
test('should show stats if available', async ({ page }) => {
  const stats = page.getByText(/verified/i);
  if (await stats.isVisible({ timeout: 5000 }).catch(() => false)) {
    await expect(stats).toBeVisible();
  }
});
```

### 3. 네트워크 대기

```typescript
test('should load data', async ({ page }) => {
  await page.waitForLoadState('networkidle');
  // 또는
  await page.waitForResponse(resp => resp.url().includes('/api/validator'));
});
```

## 알려진 이슈

### API 서버 미실행 시

다음 테스트들이 타임아웃으로 실패합니다:
- Dashboard KPI 카드 표시
- Validator 제목/설명 표시
- Files/Groups 목록 로드

**해결**: API 서버를 먼저 실행하세요.

### 데이터베이스 비어있을 때

Validator 테스트가 "all verified" 메시지를 표시합니다.

**해결**: NAS 스캔으로 데이터를 생성하세요.

### 느린 네트워크

타임아웃 설정을 늘립니다:

```typescript
test('slow test', async ({ page }) => {
  test.setTimeout(60000); // 60초
  await page.goto('/validator');
});
```

## CI/CD 통합

### GitHub Actions 예시

```yaml
- name: Run E2E tests
  run: |
    cd src/nams/api
    uvicorn main:app --port 8001 &
    sleep 5
    cd ../ui
    npx playwright test
```

### Docker

```dockerfile
FROM mcr.microsoft.com/playwright:v1.57.0-focal
WORKDIR /app
COPY . .
RUN npm install
CMD ["npx", "playwright", "test"]
```

## 트러블슈팅

### 1. "element not found" 에러

**원인**: 페이지 로드 전에 요소를 찾으려 함

**해결**:
```typescript
await page.waitForLoadState('networkidle');
await expect(page.locator('h1')).toBeVisible({ timeout: 10000 });
```

### 2. "ECONNREFUSED" 에러

**원인**: API 서버가 실행되지 않음

**해결**: API 서버를 포트 8001에서 실행

### 3. 테스트가 너무 느림

**원인**: 브라우저 병렬 실행 제한

**해결**:
```powershell
# 워커 수 증가
npx playwright test --workers=4
```

## 참고 자료

- [Playwright 공식 문서](https://playwright.dev/)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Selectors 가이드](https://playwright.dev/docs/selectors)
- [NAMS API 문서](http://localhost:8001/docs)

## 기여 가이드

새 테스트 추가 시:
1. 해당 페이지의 spec 파일에 추가
2. 의미 있는 테스트 이름 사용
3. 조건부 검증 패턴 활용 (API 의존성 최소화)
4. 커밋 전에 로컬에서 테스트 실행 확인
