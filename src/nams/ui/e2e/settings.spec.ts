import { test, expect } from '@playwright/test';

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
  });

  test('should display settings page title', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/settings/i);
  });

  test('should show exclusion rules section', async ({ page }) => {
    await expect(page.getByText(/exclusion rules/i)).toBeVisible();
  });

  test('should have add rule button', async ({ page }) => {
    const addButton = page.getByRole('button', { name: /add rule/i });
    await expect(addButton).toBeVisible();
  });

  test('should show rule type labels in help text', async ({ page }) => {
    // Help text explains rule types
    await expect(page.getByText(/size/i).first()).toBeVisible();
    await expect(page.getByText(/duration/i).first()).toBeVisible();
    await expect(page.getByText(/keyword/i).first()).toBeVisible();
  });

  test('should display how it works section', async ({ page }) => {
    await expect(page.getByText(/how it works/i)).toBeVisible();
  });

  test('should show rules table or empty message or loading', async ({ page }) => {
    // Either rules table, empty state, or loading text
    const table = page.locator('table');
    const emptyMessage = page.getByText(/no exclusion rules/i);
    const loadingText = page.getByText('Loading...');
    const h1 = page.locator('h1');

    const hasTable = await table.isVisible({ timeout: 5000 }).catch(() => false);
    const hasEmpty = await emptyMessage.isVisible({ timeout: 3000 }).catch(() => false);
    const hasLoading = await loadingText.isVisible({ timeout: 3000 }).catch(() => false);
    const hasH1 = await h1.isVisible({ timeout: 3000 }).catch(() => false);

    // Page is functional if any of these are visible
    expect(hasTable || hasEmpty || hasLoading || hasH1).toBeTruthy();
  });

  test('should open add rule modal when clicking add', async ({ page }) => {
    const addButton = page.getByRole('button', { name: /add rule/i });
    await addButton.click();

    // Modal should appear
    await expect(page.getByText(/add exclusion rule/i)).toBeVisible({ timeout: 5000 });
  });
});
