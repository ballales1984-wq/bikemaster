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

    await page.route('/api/v1/rides', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ rides: mockRides, total: mockRides.length }),
        })
      } else if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({ id: 99, ...JSON.parse(route.request().postData() || '{}') }),
        })
      }
    })

    await page.goto('/rides')
  })

  test('mostra la lista delle ride', async ({ page }) => {
    await expect(page.locator('.ride-item').first()).toBeVisible({ timeout: 5000 })
    const items = page.locator('.ride-item')
    await expect(items).toHaveCount(3)
  })

  test('ogni ride mostra data e distanza', async ({ page }) => {
    const firstItem = page.locator('.ride-item').first()
    await expect(firstItem).toContainText('2026-06-01')
    await expect(firstItem).toContainText('42.5')
  })

  test('il form di aggiunta ride è visibile', async ({ page }) => {
    await expect(page.locator('input[type="date"]')).toBeVisible()
    await expect(page.locator('button[type="submit"], .btn-primary').first()).toBeVisible()
  })

  test('aggiunge una nuova ride tramite form', async ({ page }) => {
    let postCalled = false

    await page.route('/api/v1/rides', async (route) => {
      if (route.request().method() === 'POST') {
        postCalled = true
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({ id: 99, date: '2026-06-17', distance_km: 35 }),
        })
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ rides: mockRides, total: 3 }),
        })
      }
    })

    await page.fill('input[type="date"]', '2026-06-17')
    const numberInputs = page.locator('input[type="number"]')
    await numberInputs.nth(0).fill('35')
    await numberInputs.nth(1).fill('80')

    await page.click('button[type="submit"]')
    await page.waitForTimeout(500)

    expect(postCalled).toBe(true)
  })

  test('il bottone Elimina apre la modale di conferma', async ({ page }) => {
    await expect(page.locator('.btn-danger').first()).toBeVisible({ timeout: 5000 })
    await page.locator('.btn-danger').first().click()

    // La modale di conferma deve apparire
    await expect(
      page.locator('.modal, [role="dialog"], .confirm-modal').first()
    ).toBeVisible({ timeout: 3000 })
  })
})
