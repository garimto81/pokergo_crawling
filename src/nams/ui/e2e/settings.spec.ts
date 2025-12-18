import { test, expect } from '@playwright/test';

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
  });

  test('should display settings page title', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/settings/i);
  });

  test('should show regions section', async ({ page }) => {
    const regionsSection = page.getByText(/regions/i);
    await expect(regionsSection.first()).toBeVisible();
  });

  test('should show event types section', async ({ page }) => {
    const eventTypesSection = page.getByText(/event.*types/i);
    await expect(eventTypesSection.first()).toBeVisible();
  });

  test('should display region codes', async ({ page }) => {
    // Should show region codes like LV, EU, APAC
    const regionCodes = page.getByText(/LV|EU|APAC|PARADISE/);
    await expect(regionCodes.first()).toBeVisible();
  });

  test('should display event type codes', async ({ page }) => {
    // Should show event type codes like ME, BR, HR
    const eventTypeCodes = page.getByText(/ME|BR|HR|Main Event|Bracelet/i);
    await expect(eventTypeCodes.first()).toBeVisible();
  });

  test('should have exclusion rules section', async ({ page }) => {
    const exclusionSection = page.getByText(/exclusion|rules/i);
    await expect(exclusionSection.first()).toBeVisible();
  });

  test('should be able to toggle exclusion rule', async ({ page }) => {
    // Find toggle switches for exclusion rules
    const toggleSwitch = page.locator('input[type="checkbox"], [role="switch"]');
    if (await toggleSwitch.first().isVisible()) {
      await toggleSwitch.first().click();
      await page.waitForTimeout(300);
    }
  });
});
