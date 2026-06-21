// @ts-check
import { test, expect } from '@playwright/test'

/**
 * @param {import('@playwright/test').Page} page
 */
async function mockLogin(page) {
  const fakeToken = [
    'eyJhbGciOiJIUzI1NiJ9',
    btoa(JSON.stringify({ sub: 'rider', is_admin: false, exp: 9999999999 })),
    'sig',
  ].join('.')
  await page.addInitScript(/** @param {string} token */ (token) => {
    localStorage.setItem('bikemaster_token', token)
    localStorage.setItem('bikemaster_user', JSON.stringify({ id: 1, username: 'rider', is_admin: false }))
  }, fakeToken)
}

const mockRides = [
  { id: 1, date: '2026-06-01', distance_km: 42.5, duration_minutes: 90, avg_speed_kmh: 28.3, calories: 950 },
  { id: 2, date: '2026-06-08', distance_km: 25.0, duration_minutes: 60, avg_speed_kmh: 25.0, calories: 600 },
  { id: 3, date: '2026-06-15', distance_km: 60.0, duration_minutes: 130, avg_speed_kmh: 27.7, calories: 1400 },
]

test.describe('Rides Management', () => {
  test.beforeEach(async ({ page }) => {
    await mockLogin(page)

    await page.route('/api/v1/rides', (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ rides: mockRides, total: mockRides.length }),
        })
      } else {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ rides: mockRides, total: mockRides.length }),
        })
      }
    })

    await page.goto('/rides')
    await expect(page.locator('.ride-item').first()).toBeVisible({ timeout: 10000 })
  })

  test('shows rides list', async ({ page }) => {
    const items = page.locator('.ride-item')
    await expect(items).toHaveCount(3)
  })

  test('each ride shows date and distance', async ({ page }) => {
    const firstItem = page.locator('.ride-item').first()
    await expect(firstItem).toContainText('2026-06-01')
    await expect(firstItem).toContainText('42.5')
  })

  test('add ride form is visible', async ({ page }) => {
    await expect(page.locator('input[type="date"]')).toBeVisible()
    await expect(page.locator('button[type="submit"], .btn-primary').first()).toBeVisible()
  })

  test('adds a new ride via form', async ({ page }) => {
    const postPromise = page.waitForResponse('/api/v1/rides')
    await page.fill('input[type="date"]', '2026-06-17')
    const numberInputs = page.locator('input[type="number"]')
    await numberInputs.nth(0).fill('35')
    await numberInputs.nth(1).fill('80')
    await page.click('button[type="submit"]')

    await expect(postPromise).resolves.toBeTruthy()
  })

  test('Delete button opens confirm modal', async ({ page }) => {
    const deleteBtn = page.locator('.btn-danger').first()
    await expect(deleteBtn).toBeVisible()
    await deleteBtn.click()

    await expect(
      page.locator('.modal, [role="dialog"], .confirm-modal').first()
    ).toBeVisible({ timeout: 3000 })
  })
})
