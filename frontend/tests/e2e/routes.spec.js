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
  }, fakeToken)
}

async function mockApi(page) {
  await page.route('**/api/v1/athletes', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ athletes: [{ id: 1, name: 'Test Rider', experience_level: 'Intermediate', ftp_watts: 250 }] }),
  }))

  await page.route('**/api/v1/rides', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ rides: [], total: 0 }),
  }))

  await page.route('**/api/v1/heatmap', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ total_points: 1000, points: [{ lat: 45.46, lon: 9.19, intensity: 0.8 }, { lat: 45.47, lon: 9.20, intensity: 0.6 }] }),
  }))

  await page.route('**/api/v1/training/granfondo/plan', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      plan: [
        { date: '2026-06-20', title: 'Endurance Ride', workout_type: 'endurance', duration_minutes: 120, target_intensity: 0.7 },
        { date: '2026-06-22', title: 'Recovery', workout_type: 'recovery', duration_minutes: 60, target_intensity: 0.5 },
      ],
    }),
  }))

  await page.route('**/api/v1/training/granfondo/save', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ message: 'Plan saved' }),
  }))

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
}

test.describe('Heatmap Route E2E', () => {
  test.beforeEach(async ({ page }) => {
    await mockLogin(page)
    await mockApi(page)
    await page.goto('/heatmap')
    await page.waitForLoadState('networkidle')
  })

  test('loads heatmap page', async ({ page }) => {
    await expect(page.locator('h2')).toContainText('Personal Heatmap')
  })

  test('has athlete ID input', async ({ page }) => {
    await expect(page.locator('#heatmap-athlete-id')).toBeVisible()
  })

  test('has load heatmap button', async ({ page }) => {
    await expect(page.locator('button.btn-primary')).toContainText('Load Heatmap')
  })

  test('loads heatmap data on button click', async ({ page }) => {
    await page.locator('button.btn-primary').click()
    await expect(page.locator('.badge')).toContainText('1000 GPS points')
  })

  test('shows heatmap map container when data loaded', async ({ page }) => {
    await page.locator('button.btn-primary').click()
    await expect(page.locator('#leaflet-heatmap')).toBeVisible()
  })
})

test.describe('Granfondo Route E2E', () => {
  test.beforeEach(async ({ page }) => {
    await mockLogin(page)
    await mockApi(page)
    await page.goto('/granfondo')
    await page.waitForLoadState('networkidle')
  })

  test('loads granfondo planner page', async ({ page }) => {
    await expect(page.locator('h2')).toContainText('Granfondo Planner')
  })

  test('has start date and weeks selectors', async ({ page }) => {
    await expect(page.locator('#gf-start-date')).toBeVisible()
    await expect(page.locator('#gf-weeks')).toBeVisible()
  })

  test('generates training plan when button clicked', async ({ page }) => {
    await page.locator('button:has-text("Generate Plan")').click()
    await expect(page.locator('.plan-container')).toBeVisible()
  })

  test('shows plan with workout items after generation', async ({ page }) => {
    await page.locator('button:has-text("Generate Plan")').click()
    await expect(page.locator('.workout-item')).toHaveCount(2)
  })

  test('shows save button after plan generated', async ({ page }) => {
    await page.locator('button:has-text("Generate Plan")').click()
    await expect(page.locator('.btn-success')).toBeVisible()
  })

  test('saves plan successfully', async ({ page }) => {
    await page.locator('button:has-text("Generate Plan")').click()
    await page.locator('.btn-success').click()
    await expect(page.locator('.save-message')).toContainText('Plan saved')
  })

  test('shows tapering badge', async ({ page }) => {
    await page.locator('button:has-text("Generate Plan")').click()
    await expect(page.locator('.badge')).toContainText('Tapering')
  })
})

test.describe('Map Route E2E', () => {
  test.beforeEach(async ({ page }) => {
    await mockLogin(page)
    await mockApi(page)
    await page.goto('/map')
    await page.waitForLoadState('networkidle')
  })

  test('loads map page', async ({ page }) => {
    await expect(page.locator('h2')).toContainText('Route Maps')
  })

  test('has update map button', async ({ page }) => {
    await expect(page.locator('button:has-text("Update map")')).toBeVisible()
  })

  test('has coloring mode select', async ({ page }) => {
    await expect(page.locator('select.form-input').first()).toBeVisible()
  })

  test('has weather toggle checkbox', async ({ page }) => {
    await expect(page.locator('input[type="checkbox"]')).toBeVisible()
  })

  test('map container renders', async ({ page }) => {
    await expect(page.locator('#route-map')).toBeVisible()
  })

  test('update map button loads routes', async ({ page }) => {
    await page.locator('button:has-text("Update map")').click()
    await page.waitForTimeout(1000)
    await expect(page.locator('#route-map')).toBeVisible()
  })
})
