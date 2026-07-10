// @ts-check
import { test, expect } from '@playwright/test'

// A Google OAuth return arrives as a hash fragment set by the backend's
// 302 redirect: `<origin>/#token=...&email=...&user_id=...`. The SPA must
// consume it and route straight to the dashboard without a manual refresh.
const fakeToken = [
  'eyJhbGciOiJIUzI1NiJ9',
  btoa(JSON.stringify({ sub: '1', is_admin: false, exp: 9999999999 })),
  'sig',
].join('.')

test.describe('Google OAuth return', () => {
  test('oauth return navigates to the dashboard without a manual refresh', async ({
    page,
  }) => {
    await page.route('**/api/v1/auth/me', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ profile_complete: true }),
      }),
    )

    // Simulate the backend redirecting back to the SPA with the token in the
    // URL fragment (full document load, as in a real OAuth round-trip).
    await page.goto(
      `/#token=${fakeToken}&email=google@example.com&user_id=1`,
    )

    // The app should consume the token and end on the dashboard route.
    await expect(page).toHaveURL(/\/rides($|\?|#)/, { timeout: 10000 })
    await expect(page.locator('text=Logout').first()).toBeVisible({
      timeout: 10000,
    })
  })

  test('oauth return with incomplete profile still lands on an authenticated route', async ({
    page,
  }) => {
    await page.route('**/api/v1/auth/me', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ profile_complete: false }),
      }),
    )

    await page.goto(
      `/#token=${fakeToken}&email=google@example.com&user_id=1`,
    )

    // Even without a complete profile the user must not be stranded on the
    // empty home route — they land on /athlete (or /rides as a fallback).
    await expect(page).toHaveURL(/\/(rides|athlete)($|\?|#)/, {
      timeout: 10000,
    })
  })
})
