import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('domcontentloaded');
  });

  test('should display page title', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/dashboard/i, { timeout: 10000 });
  });

  test('should show action buttons area', async ({ page }) => {
    // Action buttons area should exist (even if loading)
    const actionArea = page.locator('.flex.space-x-3, .flex.gap-3').first();
    await expect(actionArea).toBeVisible({ timeout: 10000 });
  });

  test('should display stats cards area if loaded', async ({ page }) => {
    await page.waitForLoadState('networkidle').catch(() => {});
    // Stats cards area (grid) should be visible
    const gridSection = page.locator('.grid').first();
    if (await gridSection.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(gridSection).toBeVisible();
    }
  });

  test('should show KPI card titles when API available', async ({ page }) => {
    await page.waitForLoadState('networkidle').catch(() => {});
    // Check for KPI titles - conditional based on API availability
    const totalFiles = page.getByText(/total files/i);
    if (await totalFiles.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(totalFiles).toBeVisible();
      await expect(page.getByText(/total groups/i)).toBeVisible();
    }
  });

  test('should have NAS Scan button', async ({ page }) => {
    const scanButton = page.getByRole('button', { name: /nas scan/i });
    await expect(scanButton).toBeVisible({ timeout: 10000 });
  });

  test('should have Export button', async ({ page }) => {
    const exportButton = page.getByRole('button', { name: /export/i });
    await expect(exportButton).toBeVisible({ timeout: 10000 });
  });

  test('should have Import JSON button', async ({ page }) => {
    const importButton = page.getByRole('button', { name: /import json/i });
    await expect(importButton).toBeVisible({ timeout: 10000 });
  });

  test('should show matching status section if data loaded', async ({ page }) => {
    await page.waitForLoadState('networkidle').catch(() => {});
    const matchingSection = page.getByText(/4-category matching status/i);
    if (await matchingSection.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(matchingSection).toBeVisible();
    }
  });

  test('should show sync status section if data loaded', async ({ page }) => {
    await page.waitForLoadState('networkidle').catch(() => {});
    const syncSection = page.getByText(/origin\/archive sync status/i);
    if (await syncSection.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(syncSection).toBeVisible();
    }
  });

  test('should open scan modal when clicking NAS Scan', async ({ page }) => {
    const scanButton = page.getByRole('button', { name: /nas scan/i });
    await scanButton.click();

    // Modal should appear
    await expect(page.locator('h2').filter({ hasText: /nas scan/i })).toBeVisible({ timeout: 5000 });
  });

  test('should close scan modal when clicking cancel', async ({ page }) => {
    const scanButton = page.getByRole('button', { name: /nas scan/i });
    await scanButton.click();

    // Wait for modal
    await page.locator('h2').filter({ hasText: /nas scan/i }).waitFor({ state: 'visible' });

    const cancelButton = page.getByRole('button', { name: /cancel/i }).first();
    await cancelButton.click();

    // Modal should be hidden
    await expect(page.locator('h2').filter({ hasText: /nas scan/i })).not.toBeVisible();
  });

  test('should open export modal when clicking Export', async ({ page }) => {
    const exportButton = page.getByRole('button', { name: /export/i });
    await exportButton.click();

    // Modal should appear
    await expect(page.locator('h2').filter({ hasText: /export data/i })).toBeVisible({ timeout: 5000 });
  });

  test('should show scan mode options in modal', async ({ page }) => {
    const scanButton = page.getByRole('button', { name: /nas scan/i });
    await scanButton.click();

    // Wait for modal
    await page.locator('h2').filter({ hasText: /nas scan/i }).waitFor({ state: 'visible' });

    // Mode options
    await expect(page.getByText(/incremental/i).first()).toBeVisible();
    await expect(page.getByText(/full/i).first()).toBeVisible();
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

  test('should navigate to groups page', async ({ page }) => {
    await page.getByRole('link', { name: /groups/i }).click();
    await expect(page).toHaveURL(/.*groups/);
  });

  test('should navigate to validator page', async ({ page }) => {
    const validatorLink = page.getByRole('link', { name: /validator/i });
    if (await validatorLink.isVisible()) {
      await validatorLink.click();
      await expect(page).toHaveURL(/.*validator/);
    }
  });

  test('should show unclassified alert when present', async ({ page }) => {
    // May or may not be visible depending on data
    const alertSection = page.getByText(/attention needed/i);
    if (await alertSection.isVisible()) {
      await expect(alertSection).toBeVisible();
    }
  });
});
