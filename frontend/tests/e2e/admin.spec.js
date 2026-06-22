// @ts-check
import { test, expect } from '@playwright/test'

async function mockLogin(page, isAdmin = true) {
  const fakeToken = [
    'eyJhbGciOiJIUzI1NiJ9',
    btoa(JSON.stringify({ sub: 'admin', is_admin: isAdmin, exp: 9999999999 })),
    'signature',
  ].join('.')
  await page.addInitScript((token) => {
    localStorage.setItem('bikemaster_token', token)
    localStorage.setItem('bikemaster_user', JSON.stringify({ id: 1, username: 'admin', is_admin: isAdmin }))
  }, fakeToken)
}

async function mockApi(page) {
  await page.route('**/api/v1/admin/stats', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      total_rides: 42,
      total_athletes: 3,
      db_size_mb: 1.2,
      uptime_seconds: 3600,
    }),
  }))

  await page.route('**/api/v1/admin/backup', route => route.fulfill({
    status: 200,
    body: JSON.stringify({ backup_path: '/tmp/backup.db', size_mb: 1.2 }),
  }))

  await page.route('**/api/v1/admin/indexes', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ message: 'Indexes created' }),
  }))

  await page.route('**/api/v1/admin/reset-demo', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ message: 'Demo reset' }),
  }))
}

test.describe('Admin Panel E2E', () => {
  test.beforeEach(async ({ page }) => {
    await mockLogin(page, true)
    await mockApi(page)
    await page.goto('/admin')
    await page.waitForLoadState('networkidle')
  })

  test('loads admin page', async ({ page }) => {
    await expect(page.locator('h2')).toContainText('Administration')
  })

  test('has stats button', async ({ page }) => {
    await expect(page.locator('button:has-text("Stats")')).toBeVisible()
  })

  test('has backup download link', async ({ page }) => {
    await expect(page.locator('a[href*="/api/v1/admin/backup"]')).toBeVisible()
  })

  test('has indexes button', async ({ page }) => {
    await expect(page.locator('button:has-text("Indexes")')).toBeVisible()
  })

  test('clicking stats shows data', async ({ page }) => {
    await page.click('button:has-text("Stats")')
    await page.waitForTimeout(500)
    await expect(page.locator('.result-box')).toContainText('total_rides')
  })

  test('clicking indexes shows success', async ({ page }) => {
    await page.click('button:has-text("Indexes")')
    await page.waitForTimeout(500)
    await expect(page.locator('.result-box')).toContainText('Indexes created')
  })

  test('admin tab is visible for admin user', async ({ page }) => {
    await expect(page.locator('nav a:has-text("Admin")')).toBeVisible()
  })

  test('non-admin cannot access admin', async ({ page }) => {
    await mockLogin(page, false)
    await page.goto('/admin')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.error-box')).toContainText('Access denied')
  })
})
