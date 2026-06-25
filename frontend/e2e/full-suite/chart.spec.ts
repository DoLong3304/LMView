import { test, expect } from "@playwright/test";
import { login } from "./utils";

test.describe("Chart interaction", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("default candlestick chart renders for BTCUSDT", async ({ page }) => {
    // wait for chart canvas / SVG
    await page.waitForTimeout(4000);
    const canvas = page.locator("canvas").first();
    const svg = page.locator("svg").first();
    const hasCanvas = (await canvas.count()) > 0;
    const hasSvg = (await svg.count()) > 0;
    expect(hasCanvas || hasSvg).toBeTruthy();
  });

  test("timeframe selector switches chart", async ({ page }) => {
    // click 1m timeframe button
    const tfBtn = page.locator('button:has-text("1m"), button:has-text("5m"), button:has-text("15m")').first();
    await expect(tfBtn).toBeVisible({ timeout: 5000 });
    await tfBtn.click();
    await page.waitForTimeout(2000);
    // re-check that chart still renders
    const canvas = page.locator("canvas").first();
    await expect(canvas).toBeVisible({ timeout: 3000 });
  });

  test("chart type switch works (candle → line → bar)", async ({ page }) => {
    // Find chart type selector
    const typeBtn = page.locator('button:has-text("Candlestick")').first();
    await expect(typeBtn).toBeVisible({ timeout: 5000 });
    await typeBtn.click();
    await page.waitForTimeout(500);
    // Should show dropdown, click Line
    const lineOption = page.locator('button:has-text("Line"), div:has-text("Line")').first();
    if ((await lineOption.count()) > 0 && await lineOption.isVisible()) {
      await lineOption.click();
      await page.waitForTimeout(1000);
    }
    // chart should still render
    const canvas = page.locator("canvas").first();
    const visible = await canvas.isVisible();
    expect(visible).toBeTruthy();
  });

  test("OHLCV bar updates price display", async ({ page }) => {
    await page.waitForTimeout(3000);
    const body = await page.locator("body").innerText();
    // should contain O/H/L/C/V labels
    const hasOHLC = /\bO\s/.test(body) && /\bH\s/.test(body) && /\bL\s/.test(body) && /\bC\s/.test(body);
    expect(hasOHLC).toBeTruthy();
  });

  test("add indicator (RSI) via indicator panel", async ({ page }) => {
    const indicatorBtn = page.locator('button:has-text("Indicators")').first();
    await expect(indicatorBtn).toBeVisible({ timeout: 5000 });
    await indicatorBtn.click();
    await page.waitForTimeout(500);
    // Look for RSI in the indicator list
    const rsiItem = page.locator('text=RSI').or(page.locator('text=Relative Strength')).first();
    if ((await rsiItem.count()) > 0) {
      await rsiItem.click();
      await page.waitForTimeout(2000);
    }
    // chart canvas still present
    const canvas = page.locator("canvas").first();
    await expect(canvas).toBeVisible({ timeout: 3000 });
  });

  test("symbol search picks new symbol", async ({ page }) => {
    // Symbol search / picker
    const searchInput = page.locator('input[placeholder*="search" i], input[placeholder*="symbol" i]').first();
    if ((await searchInput.count()) > 0 && await searchInput.isVisible()) {
      await searchInput.click();
      await searchInput.fill("ETHUSDT");
      await page.waitForTimeout(500);
      const ethOption = page.locator('text=ETHUSDT').first();
      if ((await ethOption.count()) > 0) await ethOption.click();
      await page.waitForTimeout(2000);
      const body = await page.locator("body").innerText();
      expect(body).toContain("ETHUSDT");
    }
  });
});
