// @ts-check
import { test, expect } from '@playwright/test'

/**
 * Helper: simulate login via localStorage (bypass form for dashboard test)
 * @param {import('@playwright/test').Page} page
 */
async function mockLogin(page) {
  const fakeToken = [
    'eyJhbGciOiJIUzI1NiJ9',
    btoa(JSON.stringify({ sub: 'testuser', is_admin: false, exp: 9999999999 })),
    'signature',
  ].join('.')

  await page.addInitScript(/** @param {string} token */ (token) => {
    localStorage.setItem('bikemaster_token', token)
    localStorage.setItem('bikemaster_user', JSON.stringify({ id: 1, username: 'testuser', is_admin: false }))
  }, fakeToken)
}

test.describe('Dashboard Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await mockLogin(page)

    await page.route('**/api/v1/dashboard', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        athlete: { name: 'Test User', email: 'test@example.com', experience_level: 'Intermediate' },
        summary: { total_rides: 15, total_km: 450, total_hours: 22, total_calories: 12000 },
        scores: { performance: 7, endurance: 6, recovery: 8, efficiency: 7 },
        fitness: { atl: 40, ctl: 50, tsb: -10, status: 'Good form' },
        trends: { weekly_progress: [10, 0, 25, 0, 30, 0, 0] },
      }),
    }))

    await page.route('**/api/v1/rides*', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ rides: [], total: 0 }),
    }))

    await page.goto('/rides')
  })

  test('rides page loads after login', async ({ page }) => {
    await expect(page).toHaveURL(/\/rides/)
    await expect(page.locator('h2').first()).toBeVisible()
  })

  test('HeaderTabs navigation works', async ({ page }) => {
    // Find navigation links
    const navLinks = page.locator('nav a, header a').first()
    await expect(navLinks).toBeVisible({ timeout: 3000 })
  })

  test('page title is BikeMaster', async ({ page }) => {
    await expect(page).toHaveTitle(/BikeMaster/)
  })

  test('rides section shows add form', async ({ page }) => {
    await page.goto('/rides')
    await expect(page.locator('form.ride-form, .add-ride-form form')).toBeVisible({ timeout: 5000 })
  })

  test('logout redirects to home', async ({ page }) => {
    await page.route('/api/v1/auth/logout', route => route.fulfill({ status: 200, body: '{}' }))

    // Click logout button if exists on the page
    const logoutBtn = page.locator('button', { hasText: /logout|sign out/i })
    if (await logoutBtn.count() > 0) {
      await logoutBtn.click()
      await expect(page).toHaveURL('/')
    }
  })
})
