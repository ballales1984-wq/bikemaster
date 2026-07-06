// @ts-check
import { test, expect } from '@playwright/test'

async function mockLogin(page) {
  const fakeToken = [
    'eyJhbGciOiJIUzI1NiJ9',
    btoa(JSON.stringify({ sub: 'rider', is_admin: false, exp: 9999999999 })),
    'sig',
  ].join('.')
  await page.addInitScript((token) => {
    localStorage.setItem('bikemaster_token', token)
    localStorage.setItem('bikemaster_user', JSON.stringify({ id: 1, username: 'rider', is_admin: false }))
  }, fakeToken)
}

const mockRides = [
  { id: 1, date: '2026-06-01', distance_km: 42.5, duration_minutes: 90, avg_speed_kmh: 28.3, calories: 950 },
]

test.describe('Registration and login', () => {
  test('guest registers, logs in and reaches dashboard', async ({ page }) => {
    await page.route('**/api/v1/auth/register', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 1, username: 'newrider' }) })
    )
    await page.route('**/api/v1/auth/login', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ access_token: 'fake.jwt.token', id: 1 }) })
    )
    await page.route('**/api/v1/auth/me', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ profile_complete: true }) })
    )

    await page.goto('/')
    await expect(page.locator('#username')).toBeVisible()
    await page.locator('#tab-register').click()
    await page.fill('#username', 'newrider')
    await page.fill('#password', 'password123')
    await page.click('form button[type="submit"]')

    // Dashboard is shown (login form gone, nav present)
    await expect(page.locator('#username')).toBeHidden({ timeout: 10000 })
    await expect(page.locator('text=Logout').first()).toBeVisible({ timeout: 10000 })
  })
})

test.describe('Logged-in rides operations', () => {
  test.beforeEach(async ({ page }) => {
    await mockLogin(page)
    await page.route('/api/v1/rides', (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ rides: mockRides, total: mockRides.length }) })
      } else if (route.request().method() === 'POST') {
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 2, date: '2026-06-20', distance_km: 30, duration_minutes: 70 }) })
      } else if (route.request().method() === 'DELETE') {
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) })
      }
    })
  })

  test('logged-in user adds and deletes a ride', async ({ page }) => {
    await page.goto('/rides')
    await expect(page.locator('.ride-item').first()).toBeVisible({ timeout: 10000 })

    // Add a ride
    const postPromise = page.waitForResponse('**/api/v1/rides')
    await page.fill('input[type="date"]', '2026-06-20')
    const numberInputs = page.locator('input[type="number"]')
    await numberInputs.nth(0).fill('30')
    await numberInputs.nth(1).fill('70')
    await page.click('button[type="submit"]')
    await expect(postPromise).resolves.toBeTruthy()

    // Delete a ride
    await page.locator('.delete-btn').first().click()
    await expect(page.locator('.modal, [role="dialog"], .confirm-modal').first()).toBeVisible({ timeout: 3000 })
    await page.getByRole('button', { name: /elimina|delete/i }).click()
  })
})
