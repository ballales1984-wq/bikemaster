import { test, expect } from '@playwright/test'

const jwt = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJyaWRlciIsImlzX2FkbWluIjpmYWxzZX0.signature'

async function mockLogin(page) {
  await page.addInitScript((token) => {
    localStorage.setItem('bikemaster_token', token)
    localStorage.setItem('bikemaster_user', JSON.stringify({ id: 1, username: 'testuser', is_admin: false }))
  }, jwt)
}

test.beforeEach(async ({ page }) => {
  await mockLogin(page)
})

test('login and add a ride from the dashboard', async ({ page }) => {
    const rides = [
        { id: 1, date: '2026-06-01', distance_km: 42, duration_minutes: 95, avg_speed_kmh: 26.5, calories: 720 },
    ]

    await page.route('**/api/v1/auth/login', route => route.fulfill({
        json: { access_token: jwt, id: 1 },
    }))

    await page.route('**/api/v1/rides', async route => {
        if (route.request().method() === 'GET') {
            await route.fulfill({ json: { rides, total: rides.length } })
            return
        }

        const body = JSON.parse(route.request().postData())
        const newRide = { id: rides.length + 1, ...body }
        rides.push(newRide)
        await route.fulfill({ status: 201, json: newRide })
    })

    await page.goto('/')
    await page.getByLabel('Username').fill('rider')
    await page.locator('#password').fill('secret')
    await page.getByRole('button', { name: /sign in|login/i }).click()

    await expect(page.getByRole('heading', { name: /Your Rides|Rides/i })).toBeVisible()
    await expect(page.getByText('42km · 95min · 26.5 km/h')).toBeVisible()

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
    await expect(page.getByText('60km · 150min · 24 km/h')).toBeVisible()
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
    await page.route('**/*', route => route.abort('failed'))
    await page.reload({ waitUntil: 'domcontentloaded' })
})
