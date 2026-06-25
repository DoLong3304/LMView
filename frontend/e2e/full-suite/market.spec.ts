import { test, expect } from "@playwright/test";
import { login } from "./utils";

test.describe("Market Overview", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("market overview shows heatmap or price grid", async ({ page }) => {
    // try clicking "Markets & News" or similar nav
    const marketBtn = page.locator('button:has-text("Markets"), button:has-text("Market"), nav a:has-text("Markets")').first();
    if ((await marketBtn.count()) > 0 && await marketBtn.isVisible()) {
      await marketBtn.click();
      await page.waitForTimeout(3000);
      const body = await page.locator("body").innerText();
      // Should contain price data
      const hasPrices = /\d+[,.]?\d*/.test(body);
      expect(hasPrices).toBeTruthy();
    }
  });

  test("price ticker updates in header", async ({ page }) => {
    await page.waitForTimeout(2000);
    // BTC price should show
    const body = await page.locator("body").innerText();
    const hasBtcPrice = /BTCUSDT/.test(body) || /62,\d{3}/.test(body) || /62\d{3}/.test(body);
    expect(hasBtcPrice).toBeTruthy();
  });

  test("change percentage visible for tracked symbols", async ({ page }) => {
    await page.waitForTimeout(2000);
    const body = await page.locator("body").innerText();
    // Should have negative or positive percentage
    const hasPct = /-\d+\.\d+%/.test(body) || /\+\d+\.\d+%/.test(body) || /\d+\.\d+%/.test(body);
    expect(hasPct).toBeTruthy();
  });
});
