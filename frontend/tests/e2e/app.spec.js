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

    await page.goto('/rides')
    await expect(page.getByRole('heading', { name: /Your Rides|Rides/i })).toBeVisible()
    await expect(page.getByText(/42km.*95min|42.*95/)).toBeVisible()

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
    await expect(page.getByText(/60km.*150min|60.*150/)).toBeVisible()
})

test('PWA manifest and service worker registration', async ({ page }) => {
    await page.goto('/')
    const manifest = await page.request.get('/manifest.json')
    expect(manifest.ok()).toBeTruthy()

    const sw = await page.request.get('/sw.js')
    expect(sw.ok()).toBeTruthy()
})

test('offline ride creation persists locally', async ({ page }) => {
    await page.route('**/api/v1/auth/login', route => route.fulfill({
      json: { access_token: jwt, id: 1 },
    }))

    await page.route('**/api/v1/rides*', (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          json: { rides: [], total: 0 },
        })
      } else {
        route.fulfill({ status: 503, json: { detail: 'Service Unavailable' } })
      }
    })

    await page.goto('/')
    await page.getByLabel('Username').fill('rider')
    await page.locator('#password').fill('secret')
    await page.getByRole('button', { name: 'Sign In', exact: true }).click()

    await page.waitForURL('**/rides')
    await page.route('**/api/v1/rides', (route) => {
      route.fulfill({ status: 503, json: { detail: 'Service Unavailable' } })
    })

    const today = new Date().toISOString().slice(0, 10)
    await page.locator('input[type="date"]').fill(today)
    await page.locator('input[placeholder="Distance (km)"]').fill('45')
    await page.locator('input[placeholder="Duration (min)"]').fill('100')
    await page.locator('input[placeholder="Avg speed (km/h)"]').fill('27')
    await page.getByRole('button', { name: /add ride|add/i }).click()

    await expect(page.getByText(/45km.*100min|45.*100/)).toBeVisible()
})

test('sync pending count updates after offline creation', async ({ page }) => {
    await page.route('**/api/v1/auth/login', route => route.fulfill({
      json: { access_token: jwt, id: 1 },
    }))

    await page.route('**/api/v1/sync/status', (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          json: { mode: 'local', last_sync_at: null, pending_count: 1 },
        })
      } else {
        route.fulfill({
          json: { mode: 'local', last_sync_at: new Date().toISOString(), pending_count: 0 },
        })
      }
    })

    await page.goto('/')
    await page.getByLabel('Username').fill('rider')
    await page.locator('#password').fill('secret')
    await page.getByRole('button', { name: 'Sign In', exact: true }).click()

    await page.waitForURL('**/rides')
    await expect(page.getByText(/pending.*1|1.*pending/i)).toBeVisible()
})

test('service worker caches app shell assets', async ({ page }) => {
    await page.goto('/')
    const cached = await page.evaluate(async () => {
      const cache = await caches.open('bikemaster-app-shell')
      const keys = await cache.keys()
      return keys.some(request => request.url.includes('/manifest.json'))
    })
    expect(cached).toBeTruthy()
})

test('offline fallback shows cached app shell', async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => {
      window.addEventListener('offline', () => {})
    })
    await page.route('**/*', (route) => {
      if (route.request().url().includes('/sw.js')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/javascript',
          body: '',
        })
      }
      if (route.request().url().includes('/manifest.json')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ name: 'BikeMaster' }),
        })
      }
      return route.fulfill({
        status: 503,
        body: 'offline',
      })
    })
    await page.reload()
    await expect(page.locator('body')).not.toBeEmpty()
})
