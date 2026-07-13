import { test, expect } from "@playwright/test";

// App shell: branding, theme toggle and the unauthenticated landing chrome.
test.describe("App shell", () => {
  test("shows branding and footer on the landing screen", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator(".logo")).toHaveText(/BikeMaster/);
    await expect(page.locator(".footer")).toHaveText(/BikeMaster v2/);
    await expect(
      page.locator(".login-panel, main").first(),
    ).toBeVisible();
  });

  test("toggles the color theme via the header button", async ({ page }) => {
    await page.goto("/about");
    const app = page.locator(".app");
    // Default theme is dark.
    await expect(app).not.toHaveClass(/light-theme/);

    await page.click(".theme-toggle");
    await expect(app).toHaveClass(/light-theme/);

    await page.click(".theme-toggle");
    await expect(app).not.toHaveClass(/light-theme/);
  });

  test("renders the language switcher on public pages", async ({ page }) => {
    await page.goto("/about");
    await expect(page.locator("header .lang-switcher")).toBeVisible();
  });
});
