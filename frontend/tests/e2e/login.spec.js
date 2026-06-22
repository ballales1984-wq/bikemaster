// @ts-check
import { test, expect } from '@playwright/test'

test.describe('Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('shows login form on open', async ({ page }) => {
    await expect(page.locator('#username')).toBeVisible()
    await expect(page.locator('#password')).toBeVisible()
    await expect(page.locator('form button[type="submit"]')).toBeVisible()
  })

  test('shows error with wrong credentials', async ({ page }) => {
    await page.route('**/api/v1/auth/login', route => route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Invalid credentials' }),
    }))

    await page.fill('#username', 'wronguser')
    await page.fill('#password', 'wrongpassword')
    await page.click('form button[type="submit"]')

    await expect(page.locator('.login-error, .field-error, [role="alert"]').first()).toBeVisible({ timeout: 5000 })
  })

  test('validation username too short', async ({ page }) => {
    await page.fill('#username', 'ab')
    await page.fill('#password', 'password123')
    await page.evaluate(() => {
      const form = document.querySelector('.login-form')
      form?.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    })

    await expect(page.locator('#username-error')).toContainText('Min 3 characters')
  })

  test('toggle password visibility works', async ({ page }) => {
    await page.fill('#password', 'segreto123')

    const passwordInput = page.locator('#password')
    await expect(passwordInput).toHaveAttribute('type', 'password')

    await page.click('.password-toggle')
    await expect(passwordInput).toHaveAttribute('type', 'text')

    await page.click('.password-toggle')
    await expect(passwordInput).toHaveAttribute('type', 'password')
  })

  test('switch from login to registration', async ({ page }) => {
    await page.getByRole('tab', { name: /sign up/i }).click()

    await expect(page.locator('.tab-btn.register, .tab-btn.active')).toContainText(/sign up/i)
    await expect(page.locator('#password')).toBeVisible()
  })
})
