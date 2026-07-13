import { test, expect } from "@playwright/test";

// Public (unauthenticated) routes must always render their legal/info pages
// and expose navigation between them via the header links.
const PUBLIC_PAGES = [
  { path: "/privacy", title: "Privacy Policy", heading: "Privacy Policy" },
  {
    path: "/terms",
    title: "Termini di servizio",
    heading: "Termini di Servizio",
  },
  { path: "/cookies", title: "Cookie Policy", heading: "Cookie Policy" },
  { path: "/about", title: "Chi siamo", heading: "BikeMaster" },
  { path: "/contact", title: "Contatti", heading: "Contattaci" },
];

test.describe("Public routing", () => {
  for (const page of PUBLIC_PAGES) {
    test(`renders ${page.path} with the correct title and content`, async ({
      browser,
    }) => {
      const ctx = await browser.newContext();
      const tab = await ctx.newPage();
      await tab.goto(page.path);

      await expect(tab).toHaveTitle(page.title);
      await expect(
        tab.locator("main").getByText(page.heading, { exact: false }).first(),
      ).toBeVisible();
      await expect(tab.locator(".public-links")).toBeVisible();

      await ctx.close();
    });
  }

  test("navigates between public pages via header links", async ({ page }) => {
    await page.goto("/privacy");
    await page.click(".public-links a:has-text('Chi Siamo')");
    await expect(page).toHaveURL(/\/about$/);
    await expect(page).toHaveTitle("Chi siamo");
  });

  test("an authenticated-only route redirects anonymous users to home", async ({
    page,
  }) => {
    // /rides requires auth; without a token the router guard bounces to "/".
    await page.goto("/rides");
    await expect(page).toHaveURL(/\/$/);
    await expect(page.locator(".login-panel")).toBeVisible();
  });
});
