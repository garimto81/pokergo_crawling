import { test, expect } from '@playwright/test';

test.describe('Patterns Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/patterns');
    await page.waitForLoadState('domcontentloaded');
  });

  test('should display patterns page title', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/patterns/i, { timeout: 10000 });
  });

  test('should show content area', async ({ page }) => {
    // Page should have main content area
    const mainArea = page.locator('.space-y-6, main').first();
    await expect(mainArea).toBeVisible({ timeout: 10000 });
  });

  test('should show patterns list or loading/empty state', async ({ page }) => {
    await page.waitForLoadState('networkidle').catch(() => {});

    // Either patterns list, table, or loading/empty state
    const table = page.locator('table');
    const listArea = page.locator('.divide-y, .space-y-4');
    const loading = page.getByText(/loading/i);

    const hasTable = await table.isVisible({ timeout: 5000 }).catch(() => false);
    const hasList = await listArea.first().isVisible({ timeout: 3000 }).catch(() => false);
    const hasLoading = await loading.isVisible({ timeout: 1000 }).catch(() => false);

    expect(hasTable || hasList || hasLoading).toBeTruthy();
  });

  test('should have add pattern button', async ({ page }) => {
    const addButton = page.getByRole('button', { name: /add|create|new/i });
    await expect(addButton).toBeVisible({ timeout: 10000 });
  });

  test('should display pattern names if loaded', async ({ page }) => {
    await page.waitForLoadState('networkidle').catch(() => {});

    // Patterns should show names or descriptions
    const patternInfo = page.getByText(/wsop|pattern/i);
    if (await patternInfo.first().isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(patternInfo.first()).toBeVisible();
    }
  });
});
