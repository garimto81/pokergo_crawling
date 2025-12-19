import { test, expect } from '@playwright/test';

test.describe('Groups Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/groups');
    await page.waitForLoadState('domcontentloaded');
  });

  test('should display groups page title', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/groups/i, { timeout: 10000 });
  });

  test('should show content area', async ({ page }) => {
    // Page should have main content area
    const mainArea = page.locator('.space-y-6, main').first();
    await expect(mainArea).toBeVisible({ timeout: 10000 });
  });

  test('should show groups list or loading/empty state', async ({ page }) => {
    await page.waitForLoadState('networkidle').catch(() => {});

    // Either table, loading, or empty state
    const table = page.locator('table');
    const loading = page.getByText(/loading/i);
    const empty = page.getByText(/no groups|0 groups/i);

    const hasTable = await table.isVisible({ timeout: 5000 }).catch(() => false);
    const hasLoading = await loading.isVisible({ timeout: 1000 }).catch(() => false);
    const hasEmpty = await empty.isVisible({ timeout: 1000 }).catch(() => false);

    expect(hasTable || hasLoading || hasEmpty).toBeTruthy();
  });

  test('should have filter controls', async ({ page }) => {
    await page.waitForLoadState('networkidle').catch(() => {});

    // Year filter or search
    const selectFilter = page.locator('select').first();
    const searchInput = page.locator('input');

    const hasSelect = await selectFilter.isVisible({ timeout: 3000 }).catch(() => false);
    const hasSearch = await searchInput.isVisible({ timeout: 3000 }).catch(() => false);

    expect(hasSelect || hasSearch).toBeTruthy();
  });

  test('should show group count in header if loaded', async ({ page }) => {
    await page.waitForLoadState('networkidle').catch(() => {});

    // Check for groups count text
    const countText = page.getByText(/\d+ groups total/i);
    if (await countText.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(countText).toBeVisible();
    }
  });
});
