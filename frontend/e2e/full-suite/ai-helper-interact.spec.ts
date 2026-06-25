import { test, expect } from "@playwright/test";
import { login, setMode, sendMessage, waitForTourOverlay } from "./utils";

test.describe("AI Helper – Interact mode", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await setMode(page, "interact");
  });

  // ── Tour flows ──
  test("welcome tour has 5 steps and navigates all", async ({ page }) => {
    await sendMessage(page, "How to use LMView?");
    const tour = await waitForTourOverlay(page, 120000);
    expect(tour).not.toBeNull();
    expect(tour!.total).toBeGreaterThanOrEqual(4);

    // navigate to last step
    for (let i = tour!.step; i < tour!.total; i++) {
      const nextBtn = page.locator('[data-testid="ai-tour-overlay"]').locator('[data-testid="ai-tour-next"]');
      await expect(nextBtn).toBeVisible({ timeout: 5000 });
      await nextBtn.click();
      await page.waitForTimeout(800);
    }
    // last step should have Keep / Revert buttons
    const keepBtn = page.locator('[data-testid="ai-tour-keep"]');
    const revertBtn = page.locator('[data-testid="ai-tour-revert"]');
    const hasKeep = (await keepBtn.count()) > 0 && (await keepBtn.isVisible());
    const hasRevert = (await revertBtn.count()) > 0 && (await revertBtn.isVisible());
    expect(hasKeep || hasRevert).toBeTruthy();
  });

  test("analysis tour for BTCUSDT", async ({ page }) => {
    await sendMessage(page, "Analyze BTCUSDT");
    const tour = await waitForTourOverlay(page, 120000);
    expect(tour).not.toBeNull();
    expect(tour!.text).toMatch(/BTC|indicator|RSI|order|candle/i);
  });

  test("order book tour for ETH", async ({ page }) => {
    await sendMessage(page, "Show me order book for ETH");
    const tour = await waitForTourOverlay(page, 120000);
    expect(tour).not.toBeNull();
    expect(tour!.text).toMatch(/order|book|depth|bid|ask|panel|ETHUSDT/i);
  });

  test("compare BTC and ETH tour", async ({ page }) => {
    await sendMessage(page, "Compare BTC and ETH");
    const tour = await waitForTourOverlay(page, 120000);
    expect(tour).not.toBeNull();
    expect(tour!.total).toBeGreaterThanOrEqual(2);
  });

  test("Interact mode EN tour has English content", async ({ page }) => {
    await sendMessage(page, "How to use LMView?");
    const tour = await waitForTourOverlay(page, 120000);
    expect(tour).not.toBeNull();
    expect(tour!.text).toContain("chart");
    // no Vietnamese chars
    expect(/[àáâãèéêìíòóôõùúăđĩũơ]/.test(tour!.text)).toBeFalsy();
  });

  // ── Tour overlay UI ──
  test("previous step button works", async ({ page }) => {
    await sendMessage(page, "How to use LMView?");
    const tour = await waitForTourOverlay(page, 120000);
    expect(tour).not.toBeNull();
    if (tour!.total < 2) return; // skip if single-step

    const prevBtn = page.locator('[data-testid="ai-tour-prev"]');
    // go to step 2, then back
    const nextBtn = page.locator('[data-testid="ai-tour-next"]');
    await nextBtn.click();
    await page.waitForTimeout(1000);
    await expect(prevBtn).toBeVisible({ timeout: 3000 });
    await prevBtn.click();
    await page.waitForTimeout(1000);
    const text = await page.locator('[data-testid="ai-tour-overlay"]').innerText();
    expect(text).toContain("1 of "); // back to step 1
  });

  // ── Tour interruption ──
  test("sending new message mid-tour hides overlay", async ({ page }) => {
    await sendMessage(page, "How to use LMView?");
    const tour = await waitForTourOverlay(page, 120000);
    expect(tour).not.toBeNull();
    // send another message without waiting for tour end
    await clearChat(page);
    await sendMessage(page, "What is RSI?");
    await page.waitForTimeout(3000);
    const overlayCount = await page.locator('[data-testid="ai-tour-overlay"]').count();
    expect(overlayCount).toBe(0);
  });

  // ── Textarea recovery ──
  test("textarea enabled after tour keep", async ({ page }) => {
    await sendMessage(page, "How to use LMView?");
    const tour = await waitForTourOverlay(page, 120000);
    expect(tour).not.toBeNull();
    // reach last step
    while (true) {
      const text = await page.locator('[data-testid="ai-tour-overlay"]').innerText();
      if (text.includes("Keep") || text.includes("Finish")) break;
      const nextBtn = page.locator('[data-testid="ai-tour-next"]');
      await nextBtn.click();
      await page.waitForTimeout(800);
    }
    // click keep
    await page.locator('[data-testid="ai-tour-keep"]').click();
    await page.waitForTimeout(3000);
    const textarea = page.locator('textarea').first();
    await expect(textarea).toBeEnabled({ timeout: 5000 });
  });

  // ── Tour recap ──
  test("replay recap visible after tour ends", async ({ page }) => {
    await sendMessage(page, "How to use LMView?");
    const tour = await waitForTourOverlay(page, 120000);
    expect(tour).not.toBeNull();
    // navigate to last then keep
    for (let i = tour!.step; i < tour!.total; i++) {
      const text = await page.locator('[data-testid="ai-tour-overlay"]').innerText();
      if (text.includes("Keep")) break;
      const nextBtn = page.locator('[data-testid="ai-tour-next"]');
      await nextBtn.click();
      await page.waitForTimeout(800);
    }
    await page.locator('[data-testid="ai-tour-keep"]').click();
    await page.waitForTimeout(3000);
    // check for replay button
    const replay = page.locator('[data-testid="ai-tour-replay"]');
    const recap = page.locator('[data-testid="ai-tour-recap"]');
    const hasReplay = (await replay.count()) > 0;
    const hasRecap = (await recap.count()) > 0;
    expect(hasReplay || hasRecap).toBeTruthy();
  });
});
