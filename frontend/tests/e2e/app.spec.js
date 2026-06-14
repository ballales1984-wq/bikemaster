import { test, expect } from '@playwright/test'

const jwt = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJyaWRlciIsImlzX2FkbWluIjpmYWxzZX0.signature'

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
  await page.getByLabel('Password').fill('secret')
  await page.getByRole('button', { name: 'Entra' }).click()

  await expect(page.getByRole('heading', { name: '📋 Le tue Ride' })).toBeVisible()
  await expect(page.getByText('42km • 95min • 26.5 km/h')).toBeVisible()

  const today = new Date().toISOString().slice(0, 10)
  const postPromise = page.waitForResponse(response =>
    response.url().includes('/api/v1/rides') && response.request().method() === 'POST'
  )

  await page.locator('input[type="date"]').fill(today)
  await page.locator('input[placeholder="Distanza (km)"]').fill('60')
  await page.locator('input[placeholder="Durata (min)"]').fill('150')
  await page.locator('input[placeholder="Velocità media (km/h)"]').fill('24')
  await page.getByRole('button', { name: 'Aggiungi Ride' }).click()

  await expect(postPromise).resolves.toBeTruthy()
  await expect(page.getByText('60km • 150min • 24 km/h')).toBeVisible()
})
