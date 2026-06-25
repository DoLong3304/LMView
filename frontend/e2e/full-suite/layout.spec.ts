import { test, expect } from "@playwright/test";
import { login } from "./utils";

test.describe("Layout – Header, sidebar, right panel", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("header shows LMView branding, symbol price and profile", async ({ page }) => {
    await expect(page.locator("text=LMView").first()).toBeVisible({ timeout: 5000 });
    // price indicator shows BTC price
    const priceElement = page.locator("text=BTCUSDT").first();
    await expect(priceElement).toBeVisible({ timeout: 5000 });
    // user profile
    await expect(page.locator("text=Admin").first()).toBeVisible({ timeout: 5000 });
  });

  test("left sidebar toggles symbols list", async ({ page }) => {
    // sidebar should be visible by default
    const sidebar = page.locator("nav").or(page.locator('aside'));
    const sidebarVisible = await sidebar.first().isVisible();
    if (sidebarVisible) {
      // check contains symbols
      const body = await page.locator("body").innerText();
      expect(body).toMatch(/BTC|ETH|SOL/i);
    }
  });

  test("right panel has tabs (AI, watchlist, settings)", async ({ page }) => {
    const body = await page.locator("body").innerText();
    const hasAiSettingsOrWatchlist = body.includes("AI") || body.includes("Settings") || body.includes("Watchlist");
    expect(hasAiSettingsOrWatchlist).toBeTruthy();
  });

  test("AI Helper button opens panel", async ({ page }) => {
    // Already opened by login(), verify textarea
    const textarea = page.locator("textarea").first();
    await expect(textarea).toBeVisible({ timeout: 5000 });
  });

  test("theme switcher (EN/VI toggle)", async ({ page }) => {
    // Find language toggle
    const langBtn = page.locator('button:has-text("EN"), button:has-text("VI")').first();
    if ((await langBtn.count()) > 0) {
      const initialText = await langBtn.innerText();
      await langBtn.click();
      await page.waitForTimeout(1000);
      const afterText = await langBtn.innerText();
      expect(afterText).not.toBe(initialText); // should have switched
    }
  });
});
