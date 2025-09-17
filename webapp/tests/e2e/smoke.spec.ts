import { test, expect } from '@playwright/test';

test('loads dashboard', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/MCP|Console|Dashboard/i);
});

test('settings page renders', async ({ page }) => {
  await page.goto('/settings');
  await expect(page.getByText(/Settings|Platform/i)).toBeVisible();
});

