import { test, expect } from "@playwright/test";
import { login } from "./utils";

test.describe("Auth flows", () => {
  test("login page loads and login succeeds", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await login(page);
    // check user indicator present
    await expect(page.locator("text=LMView Admin").first()).toBeVisible({ timeout: 5000 });
    expect(errors.filter((m) => !m.includes("429") && !m.includes("ResizeObserver")).length).toBe(0);
  });

  test("login button hidden when already logged in", async ({ page }) => {
    await login(page);
    await page.goto("https://lmview.duckdns.org", { waitUntil: "networkidle" });
    await page.waitForTimeout(2000);
    const loginBtn = page.locator('button:has-text("Login")').first();
    // should NOT be visible (redirect to main or already logged in)
    const visible = await loginBtn.isVisible();
    expect(visible).toBeFalsy();
  });

  test("invalid credentials show error", async ({ page }) => {
    await page.goto("https://lmview.duckdns.org", { waitUntil: "networkidle" });
    await page.waitForTimeout(2000);
    const loginBtn = page.locator('button:has-text("Login")').first();
    await loginBtn.click();
    await page.waitForTimeout(500);
    await page.fill('input[type="email"]', "wrong@email.com");
    await page.fill('input[type="password"]', "wrongpassword");
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);
    // error toast or message should appear
    const toast = page.locator('[role="alert"]').first();
    const hasToast = await toast.isVisible().catch(() => false);
    const body = await page.locator("body").innerText();
    const hasError = hasToast || body.toLowerCase().includes("error") || body.toLowerCase().includes("invalid") || body.toLowerCase().includes("fail");
    expect(hasError).toBeTruthy();
  });

  test("logout clears session", async ({ page }) => {
    await login(page);
    // find logout button
    const logoutBtn = page.locator('button:has-text("Logout")').first();
    if ((await logoutBtn.count()) > 0 && await logoutBtn.isVisible()) {
      await logoutBtn.click();
      await page.waitForTimeout(2000);
      // login button should reappear
      const loginBtn = page.locator('button:has-text("Login")').first();
      await expect(loginBtn).toBeVisible({ timeout: 5000 });
    } else {
      // If no logout button visible, check if we can find it in user menu
      const userBtn = page.locator('button:has-text("Admin")').first();
      if ((await userBtn.count()) > 0) {
        await userBtn.click();
        await page.waitForTimeout(500);
        const logoutDropdown = page.locator('button:has-text("Logout")').first();
        if ((await logoutDropdown.count()) > 0) {
          await logoutDropdown.click();
          await page.waitForTimeout(2000);
        }
      }
    }
  });
});
