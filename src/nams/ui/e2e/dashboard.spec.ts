import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display page title', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/dashboard/i);
  });

  test('should show statistics cards', async ({ page }) => {
    // Stats cards should be visible
    const statsSection = page.locator('[data-testid="stats-cards"], .grid');
    await expect(statsSection).toBeVisible();
  });

  test('should display total files count', async ({ page }) => {
    // Look for stats display
    await expect(page.getByText(/total|files|groups/i).first()).toBeVisible();
  });

  test('should have navigation links', async ({ page }) => {
    // Navigation should have main links
    await expect(page.getByRole('link', { name: /files/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /groups/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /patterns/i })).toBeVisible();
  });

  test('should navigate to files page', async ({ page }) => {
    await page.getByRole('link', { name: /files/i }).click();
    await expect(page).toHaveURL(/.*files/);
  });
});
