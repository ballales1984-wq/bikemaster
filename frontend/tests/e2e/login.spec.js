// @ts-check
import { test, expect } from '@playwright/test'

test.describe('Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('shows login form on open', async ({ page }) => {
    await expect(page.locator('#username')).toBeVisible()
    await expect(page.locator('#password')).toBeVisible()
    await expect(page.locator('form button[type="submit"]')).toBeVisible()
  })

  test('shows error with wrong credentials', async ({ page }) => {
    await page.fill('#username', 'wronguser')
    await page.fill('#password', 'wrongpassword')
    await page.click('form button[type="submit"]')

    // Wait for error message or toast
    await expect(
      page.locator('.field-error, .toast-error, [role="alert"]').first()
    ).toBeVisible({ timeout: 5000 })
  })

  test('validation username too short', async ({ page }) => {
    await page.fill('#username', 'ab')
    await page.fill('#password', 'password123')
    await page.click('form button[type="submit"]')

    await expect(page.locator('.field-error')).toContainText('Min 3 characters')
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
    const switchBtn = page.locator('button', { hasText: /sign up/i })
    await switchBtn.click()

    await expect(page.locator('h2, h1')).toContainText(/sign up/i)
    await expect(page.locator('#password')).toBeVisible()
  })
})
