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
  }, fakeToken)
}

async function mockApi(page) {
  await page.route('**/api/v1/athletes', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ athletes: [{ id: 1, name: 'Test Rider', experience_level: 'Intermediate', ftp_watts: 250 }] }),
  }))

  await page.route('**/api/v1/coach/full', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      athlete: { name: 'Test Rider', experience_level: 'Intermediate' },
      training_scores: [
        { label: 'Performance', value: 7 },
        { label: 'Endurance', value: 6 },
        { label: 'Efficiency', value: 8 },
      ],
      training_advice: 'Increase endurance rides',
      historical_analysis: 'Steady progress over last 30 days',
      recovery_advice: 'Ensure 48h rest after hard efforts',
    }),
  }))

  await page.route('**/api/v1/coach/workout', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ workout: 'Interval session: 5x5min at threshold' }),
  }))

  await page.route('**/api/v1/coach/recovery', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ recovery_advice: 'Active recovery recommended' }),
  }))
}

test.describe('AI Coach Panel E2E', () => {
  test.beforeEach(async ({ page }) => {
    await mockLogin(page)
    await mockApi(page)
    await page.goto('/coach')
    await page.waitForLoadState('networkidle')
  })

  test('loads coach page', async ({ page }) => {
    await expect(page.locator('h2')).toContainText('AI Coach')
  })

  test('has athlete ID input', async ({ page }) => {
    await expect(page.locator('#coach-athlete-id')).toBeVisible()
  })

  test('has load full coach button', async ({ page }) => {
    await expect(page.locator('button.btn-primary')).toContainText('Load Full Coach')
  })

  test('shows stat cards after data loads', async ({ page }) => {
    await page.waitForTimeout(1500)
    await expect(page.locator('.stat-card').first()).toBeVisible()
  })

  test('shows training advice after data loads', async ({ page }) => {
    await page.waitForTimeout(1500)
    await expect(page.locator('text=Increase endurance rides')).toBeVisible()
  })

  test('shows recovery advice after data loads', async ({ page }) => {
    await page.waitForTimeout(1500)
    await expect(page.locator('text=Ensure 48h rest')).toBeVisible()
  })

  test('can click load full coach button', async ({ page }) => {
    await page.locator('button:has-text("Load Full Coach")').click()
    await page.waitForTimeout(500)
    await expect(page.locator('.stat-card').first()).toBeVisible()
  })
})
