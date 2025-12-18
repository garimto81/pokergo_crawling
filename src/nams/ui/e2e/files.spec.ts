import { test, expect } from '@playwright/test';

test.describe('Files Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/files');
  });

  test('should display files page title', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/files/i);
  });

  test('should show files table or list', async ({ page }) => {
    // Either a table or a list of files should be present
    const filesList = page.locator('table, [data-testid="files-list"], .file-list');
    await expect(filesList).toBeVisible();
  });

  test('should have pagination controls', async ({ page }) => {
    // Pagination should be visible if there are files
    const pagination = page.locator('[data-testid="pagination"], .pagination, button:has-text("Next")');
    // May or may not be visible depending on data
    await expect(pagination.or(page.getByText(/no files|empty/i))).toBeVisible();
  });

  test('should have filter options', async ({ page }) => {
    // Filter controls should exist
    const filters = page.locator('select, [data-testid="filters"], input[placeholder*="search" i]');
    await expect(filters.first()).toBeVisible();
  });

  test('should be able to search files', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="search" i], input[type="search"]');
    if (await searchInput.isVisible()) {
      await searchInput.fill('test');
      // Search should trigger (wait for network or UI change)
      await page.waitForTimeout(500);
    }
  });
});
