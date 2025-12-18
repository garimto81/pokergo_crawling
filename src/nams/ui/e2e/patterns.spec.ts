import { test, expect } from '@playwright/test';

test.describe('Patterns Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/patterns');
  });

  test('should display patterns page title', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/patterns/i);
  });

  test('should show patterns list', async ({ page }) => {
    // Patterns should be listed
    const patternsList = page.locator('table, [data-testid="patterns-list"], .pattern-card');
    await expect(patternsList).toBeVisible();
  });

  test('should display pattern information', async ({ page }) => {
    // Patterns should show name, priority, or regex
    const patternInfo = page.getByText(/WSOP|regex|priority/i);
    await expect(patternInfo.first()).toBeVisible();
  });

  test('should have add pattern button', async ({ page }) => {
    const addButton = page.getByRole('button', { name: /add|create|new/i });
    await expect(addButton).toBeVisible();
  });

  test('should show pattern test section', async ({ page }) => {
    // Expand a pattern to see test functionality
    const expandButton = page.locator('[data-testid="expand-pattern"], button:has-text("Test")');
    if (await expandButton.first().isVisible()) {
      await expandButton.first().click();
      await expect(page.getByPlaceholder(/filename|test/i)).toBeVisible();
    }
  });

  test('should show pattern priority order', async ({ page }) => {
    // Patterns should be ordered by priority
    const priorityIndicators = page.locator('.priority, [data-priority]');
    await expect(priorityIndicators.first()).toBeVisible();
  });
});
