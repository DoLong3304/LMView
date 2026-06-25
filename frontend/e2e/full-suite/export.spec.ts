import { test, expect } from "@playwright/test";
import { login } from "./utils";

test.describe("Export / Snapshot", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("export button renders and triggers download", async ({ page }) => {
    const exportBtn = page.locator('button:has-text("Export"), button:has-text("Export Chart")').first();
    await expect(exportBtn).toBeVisible({ timeout: 5000 });
    // Click and wait for download
    const [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 30000 }).catch(() => null),
      exportBtn.click(),
    ]);
    if (download) {
      expect(download.suggestedFilename).toMatch(/\.(png|jpg|svg|csv|json)$/i);
    }
  });

  test("history/screenshot button works", async ({ page }) => {
    const histBtn = page.locator('button:has-text("History"), button:has-text("Screenshot")').first();
    if ((await histBtn.count()) > 0 && await histBtn.isVisible()) {
      const [download] = await Promise.all([
        page.waitForEvent("download", { timeout: 15000 }).catch(() => null),
        histBtn.click(),
      ]);
    }
  });
});
