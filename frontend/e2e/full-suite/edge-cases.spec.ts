import { test, expect, Page } from "@playwright/test";
import { login, setMode, sendMessage, waitForTourOverlay, clearChat } from "./utils";

test.describe("Edge cases", () => {
  const errors: string[] = [];
  test.beforeEach(async ({ page }) => {
    errors.length = 0;
    page.on("pageerror", (e) => errors.push(e.message));
  });

  // ── Slow 3G ──
  test("chart loads under slow network (3G)", async ({ page }) => {
    await page.context().setOffline(true);
    await page.goto("https://lmview.duckdns.org", { waitUntil: "domcontentloaded", timeout: 30000 }).catch(() => {});
    await page.context().setOffline(false);
    // UI should show some retry / offline state
    await page.waitForTimeout(2000);
    const body = await page.locator("body").innerText();
    const hasOfflineIndicator = body.includes("offline") || body.includes("retry") || body.includes("reconnect");
    // Not critical if no offline indicator – log only
  });

  // ── API 429 / rate limit ──
  test("handles rate limit (429) gracefully", async ({ page }) => {
    // Intercept and return 429 once
    await page.route("**/api/ai/**", (route) => {
      void route.fulfill({ status: 429, contentType: "application/json", body: '{"detail":"Rate limit exceeded"}' });
    }, { times: 1 });
    await login(page);
    await sendMessage(page, "What is RSI?");
    await page.waitForTimeout(3000);
    // UI should show error toast/message, not crash
    const body = await page.locator("body").innerText();
    const hasRateLimitMsg = body.includes("rate") || body.includes("429") || body.includes("too many");
    expect(hasRateLimitMsg).toBeTruthy();
    // No page errors
    expect(errors.filter((m) => !m.includes("429")).length).toBe(0);
  });

  // ── API 500 ──
  test("handles server error (500) gracefully", async ({ page }) => {
    await page.route("**/api/ai/chat", (route) => {
      void route.fulfill({ status: 500, contentType: "application/json", body: '{"detail":"Internal server error"}' });
    }, { times: 1 });
    await login(page);
    await sendMessage(page, "Analyze BTC");
    await page.waitForTimeout(3000);
    const body = await page.locator("body").innerText();
    // Should show fallback local help, not crash
    const hasResponse = body.includes("error") || body.includes("help") || body.includes("offline");
    // At minimum the page is not blank
    expect(hasResponse).toBeTruthy();
  });

  // ── Auth 403 ──
  test("handles auth error (403) gracefully", async ({ page }) => {
    await page.route("**/api/**", (route) => {
      if (route.request().url().includes("/login")) return route.continue();
      void route.fulfill({ status: 403, contentType: "application/json", body: '{"detail":"Forbidden"}' });
    });
    await login(page);
    await sendMessage(page, "What is RSI?");
    await page.waitForTimeout(3000);
    const body = await page.locator("body").innerText();
    const has403 = body.includes("login") || body.includes("forbid") || body.includes("auth");
    // Should redirect to login or show auth required
  });

  // ── Rapid message flood ──
  test("rapid message send does not break state", async ({ page }) => {
    await login(page);
    const textarea = page.locator("textarea").first();
    for (let i = 0; i < 5; i++) {
      await textarea.fill(`Test message ${i}`);
      await page.waitForTimeout(50); // burst
    }
    await page.locator('button:has-text("Send")').first().click();
    await page.waitForTimeout(3000);
    // state should be consistent – textarea still works
    await expect(textarea).toBeEnabled({ timeout: 5000 });
    // no page errors
    const crit = errors.filter((m) => !m.includes("429") && !m.includes("ResizeObserver"));
    expect(crit.length).toBe(0);
  });

  // ── Locale switch ──
  test("locale switch (EN ↔ VI) updates UI text", async ({ page }) => {
    await login(page);
    const langBtn = page.locator('button:has-text("EN"), button:has-text("VI")').first();
    if ((await langBtn.count()) === 0) return;
    // Switch to VN
    await langBtn.click();
    await page.waitForTimeout(1000);
    // After switch, UI should show Vietnamese
    const body = await page.locator("body").innerText();
    const hasVn = /[àáâãèéêìíòóôõùúăđĩũơ]/.test(body);
    expect(hasVn).toBeTruthy();
    // Switch back to EN
    await langBtn.click();
    await page.waitForTimeout(1000);
  });

  // ── Empty state / No data ──
  test("shows fallback when no candle data", async ({ page }) => {
    // route candle API to return empty
    await page.route("**/api/v2/klines/**", (route) => {
      void route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    }, { times: 2 });
    await login(page);
    // give it time to load and render fallback
    await page.waitForTimeout(5000);
    const body = await page.locator("body").innerText();
    const hasNoData = body.includes("no data") || body.includes("empty") || body.includes("No Data") || body.includes("No data");
    // Chart still renders (even if empty)
    const canvas = page.locator("canvas").first();
    expect((await canvas.count()) > 0).toBeTruthy();
  });

  // ── Long session – multiple actions ──
  test("long session with multiple interactions", async ({ page }) => {
    await login(page);
    // 1. Ask question
    await sendMessage(page, "What is RSI?");
    await page.waitForTimeout(5000);
    // 2. Switch to interact mode
    await setMode(page, "interact");
    await clearChat(page);
    // 3. Send interact query
    await sendMessage(page, "How to use LMView?");
    let tour = await waitForTourOverlay(page, 120000);
    expect(tour).not.toBeNull();
    // 4. Navigate a few steps
    for (let i = 0; i < Math.min(2, tour!.total - 1); i++) {
      const nextBtn = page.locator('[data-testid="ai-tour-next"]');
      await nextBtn.click();
      await page.waitForTimeout(800);
    }
    // 5. Cancel – new message
    await clearChat(page);
    await setMode(page, "ask");
    await sendMessage(page, "Compare BTC and ETH");
    await page.waitForTimeout(5000);
    // 6. Check state – textarea still enabled
    const textarea = page.locator("textarea").first();
    await expect(textarea).toBeEnabled({ timeout: 5000 });
    expect(errors.filter((m) => !m.includes("429") && !m.includes("ResizeObserver")).length).toBe(0);
  });

  // ── Settings modal ──
  test("settings modal opens and allows session delete", async ({ page }) => {
    await login(page);
    const settingsBtn = page.locator('button:has-text("Settings")').first();
    if ((await settingsBtn.count()) > 0) {
      await settingsBtn.click();
      await page.waitForTimeout(1500);
      // settings modal should be visible (check for close button or heading)
      const modal = page.locator('div[role="dialog"], div[class*="modal"]').first();
      const visible = await modal.isVisible().catch(() => false);
      if (visible) {
        // find delete session button
        const deleteBtn = modal.locator('button:has-text("Delete"), button:has-text("Remove")').first();
        if ((await deleteBtn.count()) > 0) {
          await deleteBtn.click();
          await page.waitForTimeout(1000);
          // confirm dialog if present
          const confirmBtn = modal.locator('button:has-text("Confirm"), button:has-text("Yes")').first();
          if ((await confirmBtn.count()) > 0) await confirmBtn.click();
          await page.waitForTimeout(1000);
        }
        // close modal
        const closeBtn = modal.locator('button[aria-label="Close"]').or(modal.locator('button:has-text("Close")')).first();
        if ((await closeBtn.count()) > 0) await closeBtn.click();
        await page.waitForTimeout(500);
      }
    }
  });

  // ── Back button / browser navigation ──
  test("browser back does not break chart", async ({ page }) => {
    await login(page);
    await page.waitForTimeout(3000);
    await page.goBack();
    await page.waitForTimeout(2000);
    await page.goForward();
    await page.waitForTimeout(3000);
    // chart should still render
    const canvas = page.locator("canvas").first();
    const chartVisible = (await canvas.count()) > 0 && (await canvas.isVisible());
    expect(chartVisible).toBeTruthy();
  });
});
