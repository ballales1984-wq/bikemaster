// @ts-check
import { test, expect } from '@playwright/test'

async function mockLogin(page, isAdmin = false) {
  const fakeToken = [
    'eyJhbGciOiJIUzI1NiJ9',
    btoa(JSON.stringify({ sub: 'testuser', is_admin: isAdmin, exp: 9999999999 })),
    'signature',
  ].join('.')
  await page.addInitScript((token) => {
    localStorage.setItem('bikemaster_token', token)
    localStorage.setItem('bikemaster_user', JSON.stringify({ id: 1, username: 'testuser', is_admin: isAdmin }))
    localStorage.setItem('bikemaster_tracking_state', JSON.stringify({
      isTracking: false,
      isPaused: false,
      points: [],
      metrics: { distance: 0, duration: 0, avgSpeed: 0 },
    }))
  }, fakeToken)
}

async function mockApi(page) {
  await page.route('**/api/v1/athletes', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ athletes: [{ id: 1, name: 'Test Rider', experience_level: 'Intermediate' }] }),
  }))

  await page.route('**/api/v1/rides*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ rides: [], total: 0 }),
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

  await page.route('**/api/v1/coach/full', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      training_scores: [
        { label: 'Performance', value: 7 },
        { label: 'Endurance', value: 6 },
        { label: 'Efficiency', value: 8 },
      ],
      training_advice: 'Increase endurance rides',
      recovery_advice: 'Ensure 48h rest',
    }),
  }))

  await page.route('**/api/v1/knowledge/search', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ results: [{ title: 'VO2 Max', snippet: 'VO2 max info' }] }),
  }))

  await page.route('**/api/v1/knowledge', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ topics: ['VO2 Max', 'Training'] }),
  }))

  await page.route('**/api/v1/admin/stats', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ total_rides: 42, total_athletes: 3 }),
  }))

  await page.route('**/api/v1/heatmap', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ total_points: 100, points: [] }),
  }))

  await page.route('**/api/v1/training/granfondo/plan', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ plan: [{ date: '2026-06-20', title: 'Endurance Ride' }] }),
  }))

  await page.route('**/api/v1/weather', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ temperature: 22, score: 7, advice: 'Good weather' }),
  }))

  await page.route('**/api/v1/import/gpx', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ id: 1, message: 'Imported' }),
  }))

  await page.route('**/api/v1/badges', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ badges: [] }),
  }))

  await page.route('**/api/v1/training/load', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ status: 'balanced', load: 50 }),
  }))

  await page.route('**/api/v1/auth/logout', route => route.fulfill({ status: 200, body: '{}' }))
}

test.describe('Multi-Page Smoke Flow E2E', () => {
  test.beforeEach(async ({ page }) => {
    await mockLogin(page)
    await mockApi(page)
  })

  test('full user journey: login -> rides -> coach -> knowledge -> logout', async ({ page }) => {
    await page.goto('/rides')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('h2')).toBeVisible()

    await page.goto('/coach')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('h2')).toContainText('AI Coach')

    await page.goto('/knowledge')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('h2')).toContainText('Knowledge Base')

    await page.goto('/heatmap')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('h2')).toContainText('Personal Heatmap')

    await page.goto('/map')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('h2')).toContainText('Route Maps')

    const logoutBtn = page.locator('button:has-text("Logout")')
    if (await logoutBtn.count() > 0) {
      await logoutBtn.click()
      await expect(page).toHaveURL('/')
    }
  })

  test('navigation tabs are accessible from any page', async ({ page }) => {
    await page.goto('/rides')
    await expect(page.locator('nav .tab:has-text("Rides")')).toBeVisible()

    await page.goto('/coach')
    await expect(page.locator('nav .tab:has-text("AI Coach")')).toBeVisible()

    await page.goto('/knowledge')
    await expect(page.locator('nav .tab:has-text("Knowledge")')).toBeVisible()
  })

  test('page titles are consistent across navigation', async ({ page }) => {
    await page.goto('/rides')
    await expect(page).toHaveTitle(/BikeMaster/)

    await page.goto('/coach')
    await expect(page).toHaveTitle(/BikeMaster/)

    await page.goto('/map')
    await expect(page).toHaveTitle(/BikeMaster/)
  })

  test('all major sections load without errors', async ({ page }) => {
    const sections = ['/rides', '/track', '/import', '/coach', '/knowledge', '/calendar', '/granfondo', '/map', '/heatmap', '/badges', '/weather']
    for (const section of sections) {
      await page.goto(section)
      await page.waitForLoadState('networkidle', { timeout: 10000 })
      await expect(page.locator('h2').first()).toBeVisible({ timeout: 5000 })
    }
  })
})
