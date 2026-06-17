// @ts-check
import { test, expect } from '@playwright/test'

test.describe('Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('mostra il form di login all\'apertura', async ({ page }) => {
    await expect(page.locator('#username')).toBeVisible()
    await expect(page.locator('#password')).toBeVisible()
    await expect(page.locator('form button[type="submit"]')).toBeVisible()
  })

  test('mostra errore con credenziali errate', async ({ page }) => {
    await page.fill('#username', 'wronguser')
    await page.fill('#password', 'wrongpassword')
    await page.click('form button[type="submit"]')

    // Attende messaggio di errore o toast
    await expect(
      page.locator('.field-error, .toast-error, [role="alert"]').first()
    ).toBeVisible({ timeout: 5000 })
  })

  test('validazione username troppo corto', async ({ page }) => {
    await page.fill('#username', 'ab')
    await page.fill('#password', 'password123')
    await page.click('form button[type="submit"]')

    await expect(page.locator('.field-error')).toContainText('Minimo 3 caratteri')
  })

  test('toggle visibilità password funziona', async ({ page }) => {
    await page.fill('#password', 'segreto123')

    const passwordInput = page.locator('#password')
    await expect(passwordInput).toHaveAttribute('type', 'password')

    await page.click('.password-toggle')
    await expect(passwordInput).toHaveAttribute('type', 'text')

    await page.click('.password-toggle')
    await expect(passwordInput).toHaveAttribute('type', 'password')
  })

  test('switch da login a registrazione', async ({ page }) => {
    const switchBtn = page.locator('button', { hasText: /registr/i })
    await switchBtn.click()

    await expect(page.locator('h2, h1')).toContainText(/registr/i)
    await expect(page.locator('#password')).toBeVisible()
  })
})
