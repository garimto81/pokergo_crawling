import { test } from '@playwright/test';

test('capture dashboard screenshot', async ({ page }) => {
  await page.goto('http://localhost:5173');
  await page.waitForTimeout(3000); // Wait for data to load
  await page.screenshot({ path: 'screenshots/dashboard.png', fullPage: true });
});

test('capture matches page', async ({ page }) => {
  await page.goto('http://localhost:5173/matches');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'screenshots/matches.png', fullPage: true });
});

test('capture not-uploaded page', async ({ page }) => {
  await page.goto('http://localhost:5173/not-uploaded');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'screenshots/not-uploaded.png', fullPage: true });
});
