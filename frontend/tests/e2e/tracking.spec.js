// @ts-check
import { test, expect } from '@playwright/test'

async function mockLogin(page) {
  const fakeToken = [
    'eyJhbGciOiJIUzI1NiJ9',
    btoa(JSON.stringify({ sub: 'rider', is_admin: false, exp: 9999999999 })),
    'signature',
  ].join('.')
  await page.addInitScript((token) => {
    localStorage.setItem('bikemaster_token', token)
    localStorage.setItem('bikemaster_user', JSON.stringify({ id: 1, username: 'rider', is_admin: false }))
    localStorage.setItem('bikemaster_tracking_state', JSON.stringify({
      isTracking: false,
      isPaused: false,
      points: [],
      metrics: { distance: 0, duration: 0, avgSpeed: 0 },
    }))
  }, fakeToken)
}

async function mockApi(page) {
  await page.route('**/api/v1/rides', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ rides: [], total: 0 }),
  }))

  await page.route('**/api/v1/athletes', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ athletes: [{ id: 1, name: 'Test Rider' }] }),
  }))
}

test.describe('Ride Tracking Page E2E', () => {
  test.beforeEach(async ({ page }) => {
    await mockLogin(page)
    await mockApi(page)
    await page.goto('/track')
    await page.waitForLoadState('networkidle')
  })

  test('loads tracking page', async ({ page }) => {
    await expect(page.locator('h2')).toContainText('GPS Tracking')
  })

  test('shows ready state with start button', async ({ page }) => {
    await expect(page.locator('button:has-text("Start Tracking")')).toBeVisible()
  })

  test('shows empty state description', async ({ page }) => {
    await expect(page.locator('.empty-title')).toContainText('Ready to track')
  })

  test('start tracking button is visible', async ({ page }) => {
    await expect(page.locator('.btn-primary.btn-large')).toBeVisible()
  })

  test('start tracking button is not disabled', async ({ page }) => {
    await expect(page.locator('.btn-primary.btn-large')).not.toBeDisabled()
  })

  test('has tracking header', async ({ page }) => {
    await expect(page.locator('.tracking-header')).toBeVisible()
  })
})
