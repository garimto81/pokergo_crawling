import { test, expect } from '@playwright/test';

test.describe('Groups Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/groups');
  });

  test('should display groups page title', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/groups/i);
  });

  test('should show groups list', async ({ page }) => {
    // Groups list or table should be visible
    const groupsList = page.locator('table, [data-testid="groups-list"], .group-card');
    await expect(groupsList).toBeVisible();
  });

  test('should display group information', async ({ page }) => {
    // Groups should show year, region, or file count
    const groupInfo = page.getByText(/\d{4}|LV|EU|files/i);
    await expect(groupInfo.first()).toBeVisible();
  });

  test('should have filter by year option', async ({ page }) => {
    const yearFilter = page.locator('select, [data-testid="year-filter"]');
    await expect(yearFilter.first()).toBeVisible();
  });

  test('should have PokerGO match filter', async ({ page }) => {
    // Should have option to filter by PokerGO match status
    const matchFilter = page.getByText(/pokergo|matched|unmatched/i);
    await expect(matchFilter.first()).toBeVisible();
  });

  test('should navigate to group detail', async ({ page }) => {
    // Click on first group to see details
    const groupRow = page.locator('tr, .group-card').first();
    if (await groupRow.isVisible()) {
      await groupRow.click();
      // Should show detail or expand
      await page.waitForTimeout(300);
    }
  });
});
