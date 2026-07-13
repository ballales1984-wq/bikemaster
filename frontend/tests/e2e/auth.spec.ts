import { test, expect } from "@playwright/test";

// Auth screen E2E: the login/register form is the public landing UI.
test.describe("Auth screen", () => {
  test("renders the login form on the public home route", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator(".login-panel")).toBeVisible();
    await expect(page.locator("#username")).toBeVisible();
    await expect(page.locator("#password")).toBeVisible();
    await expect(page.locator("#login-form button[type='submit']")).toBeVisible();
  });

  test("register mode validates a too-short username client-side", async ({
    page,
  }) => {
    await page.goto("/");
    await page.click("#tab-register");
    await expect(page.locator("#tab-register")).toHaveAttribute(
      "aria-selected",
      "true",
    );

    const username = page.locator("#username");
    await username.fill("ab");
    await username.blur();

    await expect(page.locator("#username-error")).toHaveText("Min 3 characters");
    await expect(page.locator("#login-form button[type='submit']")).toBeDisabled();
  });

  test("valid credentials clear the field errors and enable submit", async ({
    page,
  }) => {
    await page.goto("/");
    await page.click("#tab-register");
    await page.fill("#username", "testuser");
    await page.fill("#password", "secret1");

    await expect(page.locator("#username-error")).toHaveCount(0);
    await expect(page.locator("#password-error")).toHaveCount(0);
    await expect(
      page.locator("#login-form button[type='submit']"),
    ).toBeEnabled();
  });

  test("password visibility toggle switches input type", async ({ page }) => {
    await page.goto("/");
    const password = page.locator("#password");
    await password.fill("hunter2");

    expect(await password.getAttribute("type")).toBe("password");
    await page.click(".password-toggle");
    expect(await password.getAttribute("type")).toBe("text");
    await page.click(".password-toggle");
    expect(await password.getAttribute("type")).toBe("password");
  });
});
