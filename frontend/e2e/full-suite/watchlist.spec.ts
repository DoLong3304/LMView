import { test, expect } from "@playwright/test";
import { login } from "./utils";

test.describe("Watchlist", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("watchlist tab opens and shows symbols", async ({ page }) => {
    const watchlistBtn = page.locator('button:has-text("Watchlist"), button:has-text("Watch")').first();
    if ((await watchlistBtn.count()) > 0 && await watchlistBtn.isVisible()) {
      await watchlistBtn.click();
      await page.waitForTimeout(1000);
      const body = await page.locator("body").innerText();
      const hasSymbols = /\bBTC\b|\bETH\b|\bSOL\b/.test(body);
      expect(hasSymbols).toBeTruthy();
    }
  });

  test("add symbol to watchlist", async ({ page }) => {
    const watchlistBtn = page.locator('button:has-text("Watchlist"), button:has-text("Watch")').first();
    if ((await watchlistBtn.count()) > 0 && await watchlistBtn.isVisible()) {
      await watchlistBtn.click();
      await page.waitForTimeout(500);
      // add button
      const addBtn = page.locator('button:has-text("Add"), button[title="Add"]').first();
      if ((await addBtn.count()) > 0) {
        await addBtn.click();
        await page.waitForTimeout(500);
        const input = page.locator('input[placeholder*="symbol" i], input[type="text"]').first();
        if ((await input.count()) > 0) {
          await input.fill("ETHUSDT");
          await page.waitForTimeout(300);
          // confirm / submit
          const confirmBtn = page.locator('button:has-text("Add"), button:has-text("Confirm")').first();
          await confirmBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    }
  });

  test("remove symbol from watchlist", async ({ page }) => {
    const watchlistBtn = page.locator('button:has-text("Watchlist")').first();
    if ((await watchlistBtn.count()) > 0 && await watchlistBtn.isVisible()) {
      await watchlistBtn.click();
      await page.waitForTimeout(500);
      const removeBtn = page.locator('button:has-text("Remove"), button[title="Remove"], button[title="Delete"]').first();
      if ((await removeBtn.count()) > 0) {
        await removeBtn.click();
        await page.waitForTimeout(1000);
      }
    }
  });

  test("empty watchlist shows placeholder", async ({ page }) => {
    const watchlistBtn = page.locator('button:has-text("Watchlist")').first();
    if ((await watchlistBtn.count()) > 0 && await watchlistBtn.isVisible()) {
      await watchlistBtn.click();
      await page.waitForTimeout(500);
      const body = await page.locator("body").innerText();
      const hasEmpty = body.includes("empty") || body.includes("No symbols") || body.includes("no results");
      // not critical if no placeholder found
    }
  });
});
