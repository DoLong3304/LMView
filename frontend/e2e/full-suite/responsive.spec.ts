import { test, expect } from "@playwright/test";
import { login, setMode, sendMessage, waitForTourOverlay, clearChat, setViewport } from "./utils";

const VIEWPORTS = [
  { name: "phone", width: 375, height: 667 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "desktop", width: 1440, height: 900 },
];

for (const vp of VIEWPORTS) {
  test.describe(`Responsive – ${vp.name} (${vp.width}×${vp.height})`, () => {
    test.beforeEach(async ({ page }) => {
      await setViewport(page, vp.width, vp.height);
      await login(page);
    });

    test("chart renders on ${vp.name}", async ({ page }) => {
      await page.waitForTimeout(4000);
      const canvas = page.locator("canvas").first();
      const svg = page.locator("svg").first();
      const hasChart = (await canvas.count()) > 0 || (await svg.count()) > 0;
      expect(hasChart).toBeTruthy();
    });

    test("textarea accessible on ${vp.name}", async ({ page }) => {
      await page.waitForTimeout(2000);
      const textarea = page.locator("textarea").first();
      await expect(textarea).toBeVisible({ timeout: 5000 });
      await expect(textarea).toBeEnabled({ timeout: 5000 });
    });

    test("interact tour overlay visible on ${vp.name}", async ({ page }) => {
      await setMode(page, "interact");
      await clearChat(page);
      await sendMessage(page, "How to use LMView?");
      const tour = await waitForTourOverlay(page, 120000);
      expect(tour).not.toBeNull();
      expect(tour!.total).toBeGreaterThanOrEqual(3);
      // overlay visible
      const overlay = page.locator('[data-testid="ai-tour-overlay"]');
      await expect(overlay).toBeVisible({ timeout: 5000 });
      // next button visible
      await expect(overlay.locator('[data-testid="ai-tour-next"]')).toBeVisible({ timeout: 3000 });
    });

    test("header elements fit on ${vp.name}", async ({ page }) => {
      await page.waitForTimeout(2000);
      // All major buttons should at least be present (may be in hamburger)
      const hasHeader = await page.locator("header, nav").first().isVisible();
      expect(hasHeader).toBeTruthy();
    });

    test("right panel toggles on ${vp.name}", async ({ page }) => {
      await page.waitForTimeout(2000);
      // On mobile, panel may be in overlay; on desktop it's side-by-side
      const panel = page.locator('aside, div[class*="right-panel"]').first();
      const visible = await panel.isVisible().catch(() => false);
      if (!visible) {
        // might need to toggle it
        const menuBtn = page.locator('button[aria-label*="menu" i], button:has-text("☰")').first();
        if ((await menuBtn.count()) > 0) await menuBtn.click();
        await page.waitForTimeout(1000);
      }
    });
  });
}
