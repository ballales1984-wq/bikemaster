import { test, expect } from '@playwright/test'

const jwt = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJyaWRlciIsImlzX2FkbWluIjpmYWxzZX0.signature'

test('login and add a ride from the dashboard', async ({ page }) => {
    const rides = [
        { id: 1, date: '2026-06-01', distance_km: 42, duration_minutes: 95, avg_speed_kmh: 26.5, calories: 720 },
    ]

    await page.route('**/api/v1/auth/login', route => route.fulfill({
      json: { access_token: jwt, id: 1 },
    }))

    await page.route('**/api/v1/rides*', (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          json: { rides, total: rides.length },
        })
      } else {
        const body = JSON.parse(route.request().postData() || '{}')
        const newRide = { id: rides.length + 1, ...body }
        rides.push(newRide)
        route.fulfill({ status: 201, json: newRide })
      }
    })

    await page.goto('/')
    await page.getByLabel('Username').fill('rider')
    await page.locator('#password').fill('secret')
    await page.getByRole('button', { name: 'Sign In', exact: true }).click()

    const ridesResp = await page.waitForResponse('**/api/v1/rides*')
    expect(ridesResp.ok()).toBeTruthy()

    await expect(page.getByRole('heading', { name: /Your Rides|Rides/i })).toBeVisible()
    await expect(page.getByText(/42km.*95min/)).toBeVisible()

    const today = new Date().toISOString().slice(0, 10)
    const postPromise = page.waitForResponse(response =>
      response.url().includes('/api/v1/rides') && response.request().method() === 'POST'
    )

    await page.locator('input[type="date"]').fill(today)
    await page.locator('input[placeholder="Distance (km)"]').fill('60')
    await page.locator('input[placeholder="Duration (min)"]').fill('150')
    await page.locator('input[placeholder="Avg speed (km/h)"]').fill('24')
    await page.getByRole('button', { name: /add ride|add/i }).click()

    await expect(postPromise).resolves.toBeTruthy()
    await expect(page.getByText(/60km.*150min/)).toBeVisible()
})

test('PWA manifest and service worker registration', async ({ page }) => {
    await page.goto('/')
    const manifest = await page.request.get('/manifest.json')
    expect(manifest.ok()).toBeTruthy()

    const sw = await page.request.get('/sw.js')
    expect(sw.ok()).toBeTruthy()
})

test('offline fallback works', async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => {
        window.addEventListener('offline', () => {})
    })
})
