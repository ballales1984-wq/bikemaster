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
    localStorage.setItem('VITE_AETHERMAP_ENABLED', 'true')
  }, fakeToken)
}

const mockRides = [
  {
    id: 1,
    date: '2026-06-01',
    distance_km: 42.5,
    duration_minutes: 90,
    avg_speed_kmh: 28.3,
    calories: 950,
    gps_points: [
      { lat: 45.0, lon: 9.0, timestamp: '2026-06-01T10:00:00Z', speed: 20.0 },
      { lat: 45.01, lon: 9.02, timestamp: '2026-06-01T10:01:00Z', speed: 25.0 },
      { lat: 45.02, lon: 9.04, timestamp: '2026-06-01T10:02:00Z', speed: 30.0 },
    ],
  },
]

test.describe('AetherMap E2E', () => {
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
  })

  test('toggles between 2D map and AetherMap 3D viewer', async ({ page }) => {
    test.setTimeout(300000)
    await page.goto('/map')
    await page.waitForLoadState('networkidle')

    const toggleBtn = page.locator('button:has-text("3D Globe")')
    await expect(toggleBtn).toBeVisible({ timeout: 10000 })

    await toggleBtn.click()
    await expect(page.locator('canvas.aethermap-canvas')).toBeVisible({ timeout: 10000 })

    const backBtn = page.locator('button:has-text("2D Map")')
    await expect(backBtn).toBeVisible()
    await backBtn.click()
    await expect(page.locator('canvas.aethermap-canvas')).not.toBeVisible()
  })

  test('AetherMap viewer renders WebGL canvas when active', async ({ page }) => {
    test.setTimeout(300000)
    await page.goto('/map')
    await page.waitForLoadState('networkidle')

    const toggleBtn = page.locator('button:has-text("3D Globe")')
    await toggleBtn.click()

    const canvas = page.locator('canvas.aethermap-canvas')
    await expect(canvas).toBeVisible({ timeout: 10000 })
  })
})
