import { test, expect } from '@playwright/test';
import { clearAppState } from './fixtures';

test.describe('Top-level navigation', () => {
  test.beforeEach(async ({ page }) => {
    await clearAppState(page);
  });

  test('navigates to My Reports', async ({ page }) => {
    await page.goto('/home');
    await page.getByRole('link', { name: /My Reports/i }).first().click();
    await expect(page).toHaveURL(/\/my-reports$/);
    await expect(page.getByRole('heading', { name: 'My Reports' })).toBeVisible();
  });

  test('opens the New report screen from the more-menu', async ({ page }) => {
    await page.goto('/my-reports');
    await page.getByRole('button', { name: /New report/i }).first().click();
    await expect(page).toHaveURL(/\/new-report$/);
    await expect(page.getByRole('heading', { name: 'New Report' })).toBeVisible();
  });

  test('opens the Import report screen', async ({ page }) => {
    await page.goto('/my-reports');
    await page.getByRole('button', { name: /Import report/i }).first().click();
    await expect(page).toHaveURL(/\/import-report$/);
  });

  test('navigates to FAQ', async ({ page }) => {
    await page.goto('/home');
    await page.locator('button.nav-more-btn').click();
    await page.getByRole('menuitem', { name: /FAQ/i }).click();
    await expect(page).toHaveURL(/\/faq$/);
  });

  test('unknown route falls back to home component', async ({ page }) => {
    await page.goto('/this-route-does-not-exist');
    await expect(page.getByRole('heading', { name: /Vulnerability reports/i })).toBeVisible();
  });
});
