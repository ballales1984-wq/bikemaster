// @ts-check
import { test, expect } from '@playwright/test'

async function mockLogin(page) {
  const fakeToken = [
    'eyJhbGciOiJIUzI1NiJ9',
    btoa(JSON.stringify({ sub: 'testuser', is_admin: false, exp: 9999999999 })),
    'signature',
  ].join('.')
  await page.addInitScript((token) => {
    localStorage.setItem('bikemaster_token', token)
    localStorage.setItem('bikemaster_user', JSON.stringify({ id: 1, username: 'testuser', is_admin: false }))
  }, fakeToken)
}

async function mockApi(page) {
  await page.route('**/api/v1/knowledge', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      topics: ['VO2 Max', 'Training Plans', 'Nutrition', 'Recovery'],
      total: 4,
    }),
  }))

  await page.route('**/api/v1/knowledge/search', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      results: [
        { title: 'VO2 Max Training', snippet: 'VO2 max is the maximum rate of oxygen consumption during exercise.' },
        { title: 'Recovery Strategies', snippet: 'Active recovery helps reduce muscle soreness.' },
      ],
    }),
  }))

  await page.route('**/api/v1/knowledge/stats', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ total_documents: 4, last_reload: '2026-06-01' }),
  }))
}

test.describe('Knowledge Base Panel E2E', () => {
  test.beforeEach(async ({ page }) => {
    await mockLogin(page)
    await mockApi(page)
    await page.goto('/knowledge')
    await page.waitForLoadState('networkidle')
  })

  test('loads knowledge base page', async ({ page }) => {
    await expect(page.locator('h2')).toContainText('Knowledge Base')
  })

  test('has search input', async ({ page }) => {
    await expect(page.locator('#kb-query')).toBeVisible()
  })

  test('has search button', async ({ page }) => {
    await expect(page.locator('button:has-text("Search")')).toBeVisible()
  })

  test('has list topics button', async ({ page }) => {
    await expect(page.locator('button:has-text("List Topics")')).toBeVisible()
  })

  test('search loads results', async ({ page }) => {
    await page.fill('#kb-query', 'VO2 Max')
    await page.click('button:has-text("Search")')
    await page.waitForTimeout(500)
    await expect(page.locator('.result-box')).toContainText('VO2 max is the maximum')
  })

  test('list topics shows topic count', async ({ page }) => {
    await page.click('button:has-text("List Topics")')
    await page.waitForTimeout(500)
    await expect(page.locator('.result-box')).toContainText('VO2 Max')
  })

  test('shows error on failed search', async ({ page }) => {
    await page.route('**/api/v1/knowledge/search', route => route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Search failed' }),
    }))
    await page.fill('#kb-query', 'test')
    await page.click('button:has-text("Search")')
    await page.waitForTimeout(500)
    await expect(page.locator('.result-box')).toContainText('Error')
  })
})
