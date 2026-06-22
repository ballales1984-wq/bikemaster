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
  await page.route('**/api/v1/rides', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ rides: [], total: 0 }),
  }))

  await page.route('**/api/v1/athletes', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ athletes: [{ id: 1, name: 'Test Rider' }] }),
  }))
}

test.describe('Import Panel E2E', () => {
  test.beforeEach(async ({ page }) => {
    await mockLogin(page)
    await mockApi(page)
    await page.goto('/import')
    await page.waitForLoadState('networkidle')
  })

  test('loads import page', async ({ page }) => {
    await expect(page.locator('h2')).toContainText('Import Routes')
  })

  test('has file upload input', async ({ page }) => {
    await expect(page.locator('#import-file')).toBeVisible()
  })

  test('has upload placeholder text', async ({ page }) => {
    await expect(page.locator('.upload-placeholder')).toContainText('Drag files here')
  })

  test('has import button', async ({ page }) => {
    await expect(page.locator('button:has-text("Import selected files")')).toBeVisible()
  })

  test('import button is disabled without files', async ({ page }) => {
    await expect(page.locator('button:has-text("Import selected files")')).toBeDisabled()
  })

  test('has Google Fit import button', async ({ page }) => {
    await expect(page.locator('button:has-text("Import from Google Fit")')).toBeVisible()
  })

  test('shows file count when files selected', async ({ page }) => {
    const fileInput = page.locator('#import-file')
    await fileInput.setInputFiles({
      name: 'test_ride.gpx',
      mimeType: 'application/gpx+xml',
      buffer: Buffer.from('<?xml version="1.0"?><gpx></gpx>'),
    })
    await expect(page.locator('.upload-placeholder')).toContainText('1 files selected')
  })

  test('enables import button after file selection', async ({ page }) => {
    const fileInput = page.locator('#import-file')
    await fileInput.setInputFiles({
      name: 'test_ride.gpx',
      mimeType: 'application/gpx+xml',
      buffer: Buffer.from('<?xml version="1.0"?><gpx></gpx>'),
    })
    await expect(page.locator('button:has-text("Import selected files")')).not.toBeDisabled()
  })
})
