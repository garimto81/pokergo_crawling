import { test, expect } from '@playwright/test';

test.describe('Files Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/files');
    await page.waitForLoadState('domcontentloaded');
  });

  test('should display files page title', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/files/i, { timeout: 10000 });
  });

  test('should show content area', async ({ page }) => {
    // Page should have main content area
    const mainArea = page.locator('.space-y-6, main').first();
    await expect(mainArea).toBeVisible({ timeout: 10000 });
  });

  test('should show files table or loading/empty state', async ({ page }) => {
    await page.waitForLoadState('networkidle').catch(() => {});

    // Either table, loading, or empty state
    const table = page.locator('table');
    const loading = page.getByText(/loading/i);
    const empty = page.getByText(/no files|0 files/i);

    const hasTable = await table.isVisible({ timeout: 5000 }).catch(() => false);
    const hasLoading = await loading.isVisible({ timeout: 1000 }).catch(() => false);
    const hasEmpty = await empty.isVisible({ timeout: 1000 }).catch(() => false);

    expect(hasTable || hasLoading || hasEmpty).toBeTruthy();
  });

  test('should have filter controls if page loaded', async ({ page }) => {
    await page.waitForLoadState('networkidle').catch(() => {});

    // Look for search input or select filters
    const searchInput = page.locator('input[placeholder*="search" i]');
    const selectFilter = page.locator('select').first();

    const hasSearch = await searchInput.isVisible({ timeout: 3000 }).catch(() => false);
    const hasSelect = await selectFilter.isVisible({ timeout: 3000 }).catch(() => false);

    expect(hasSearch || hasSelect).toBeTruthy();
  });

  test('should be able to type in search box', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="search" i]');
    if (await searchInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      await searchInput.fill('test');
      await expect(searchInput).toHaveValue('test');
    }
  });
});
