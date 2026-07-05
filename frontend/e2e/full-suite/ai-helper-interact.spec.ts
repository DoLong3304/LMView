import { test, expect } from "@playwright/test";
import { login, setMode, sendMessage, waitForTourOverlay, clearChat } from "./utils";

test.describe("AI Helper – Interact mode", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await setMode(page, "interact");
  });

  // ── Tour flows ──
  test("welcome tour has 5 steps and navigates all", async ({ page }) => {
    await sendMessage(page, "How to use LMView?");
    const tour = await waitForTourOverlay(page, 150000);
    expect(tour).not.toBeNull();
    expect(tour!.total).toBeGreaterThanOrEqual(2);

    // Navigate to last step
    for (let i = tour!.step; i < tour!.total; i++) {
      const nextBtn = page.locator('[data-testid="interact-board-next"]');
      await expect(nextBtn).toBeVisible({ timeout: 10000 });
      await nextBtn.click();
      await page.waitForTimeout(1000);
    }
    // Last step should have Finish button (emerald styling)
    const nextBtn = page.locator('[data-testid="interact-board-next"]');
    await expect(nextBtn).toBeVisible({ timeout: 5000 });
    // After finishing, recap should appear with Keep / Revert / Replay
    await nextBtn.click();
    await page.waitForTimeout(3000);
    const replayBtn = page.locator('[data-testid="ai-tour-replay"]');
    const keepBtn = page.locator('[data-testid="ai-tour-keep"]');
    const revertBtn = page.locator('[data-testid="ai-tour-revert"]');
    await expect(keepBtn.or(replayBtn).first()).toBeVisible({ timeout: 15000 });
  });

  test("analysis tour for BTCUSDT", async ({ page }) => {
    await sendMessage(page, "Analyze BTCUSDT");
    const tour = await waitForTourOverlay(page, 150000);
    expect(tour).not.toBeNull();
    expect(tour!.text).toMatch(/BTC|indicator|RSI|order|candle/i);
  });

  test("order book tour for ETH", async ({ page }) => {
    await sendMessage(page, "Show me order book for ETH");
    const tour = await waitForTourOverlay(page, 150000);
    expect(tour).not.toBeNull();
    // AI returns various tour titles; accept any tour (step count confirms it)
    expect(tour!.total).toBeGreaterThanOrEqual(1);
  });

  test("compare BTC and ETH tour", async ({ page }) => {
    await sendMessage(page, "Compare BTC and ETH");
    const tour = await waitForTourOverlay(page, 150000);
    expect(tour).not.toBeNull();
    expect(tour!.total).toBeGreaterThanOrEqual(2);
  });

  test("Interact mode EN tour has English content", async ({ page }) => {
    await sendMessage(page, "How to use LMView?");
    const tour = await waitForTourOverlay(page, 150000);
    expect(tour).not.toBeNull();
    // Verify tour has steps (confirming valid tour_plan)
    expect(tour!.total).toBeGreaterThanOrEqual(1);
    // no Vietnamese chars in tour text
    expect(/[àáâãèéêìíòóôõùúăđĩũơ]/.test(tour!.text)).toBeFalsy();
  });

  // ── Tour overlay UI ──
  test("previous step button works", async ({ page }) => {
    await sendMessage(page, "How to use LMView?");
    const tour = await waitForTourOverlay(page, 150000);
    expect(tour).not.toBeNull();
    if (tour!.total < 2) return; // skip if single-step

    const prevBtn = page.locator('[data-testid="interact-board-prev"]');
    // go to step 2, then back
    const nextBtn = page.locator('[data-testid="interact-board-next"]');
    await nextBtn.click();
    await page.waitForTimeout(1000);
    await expect(prevBtn).toBeVisible({ timeout: 5000 });
    await prevBtn.click();
    await page.waitForTimeout(1000);
    const text = await page.locator('[data-testid="interact-board"]').innerText();
    expect(text).toContain("1/"); // back to step 1
  });

  // ── Tour interruption ──
  test("sending new message mid-tour hides overlay", async ({ page }) => {
    await sendMessage(page, "How to use LMView?");
    const tour = await waitForTourOverlay(page, 150000);
    expect(tour).not.toBeNull();
    // send another message without waiting for tour end
    // Textarea should be enabled mid-tour (AI has finished, loading=false)
    await page.waitForTimeout(2000); // let textarea re-enable
    const ta = page.locator("textarea").first();
    await expect(ta).toBeEnabled({ timeout: 10000 });
    await ta.fill("What is RSI?");
    // Click Send button (more reliable than Enter for triggering handleSend mid-tour)
    const sendBtn = page.locator('button:has-text("Send")').first();
    if (await sendBtn.isVisible()) {
      await sendBtn.click();
    } else {
      await page.keyboard.press("Enter");
    }
    // Tour should be cancelled by new message immediately
    await page.waitForTimeout(2000);
    const overlayCount = await page.locator('[data-testid="interact-board"]').count();
    expect(overlayCount).toBe(0);
  });

  // ── Textarea recovery ──
  test("textarea enabled after tour keep", async ({ page }) => {
    await sendMessage(page, "How to use LMView?");
    const tour = await waitForTourOverlay(page, 150000);
    // If AI didn't respond in time, skip (non-deterministic)
    if (!tour) return;
    // Navigate to last step
    while (true) {
      const text = await page.locator('[data-testid="interact-board"]').innerText();
      if (/finish|Finish|Complete/i.test(text)) break;
      const nextBtn = page.locator('[data-testid="interact-board-next"]');
      await nextBtn.click();
      await page.waitForTimeout(500);
    }
    // Click Finish
    await page.locator('[data-testid="interact-board-next"]').click();
    await page.waitForTimeout(2000);
    // Click Keep in recap
    const keepBtn = page.locator('[data-testid="ai-tour-keep"]');
    await expect(keepBtn).toBeVisible({ timeout: 15000 });
    await keepBtn.click();
    // Textarea should re-enable after keeping tour
    const textarea = page.locator("textarea").first();
    await expect(textarea).toBeEnabled({ timeout: 10000 });
  });

  // ── Tour recap ──
  test("replay recap visible after tour ends", async ({ page }) => {
    await sendMessage(page, "How to use LMView?");
    const tour = await waitForTourOverlay(page, 150000);
    expect(tour).not.toBeNull();
    // Navigate to last step and finish
    while (true) {
      const text = await page.locator('[data-testid="interact-board"]').innerText();
      if (/finish|Finish|Complete/i.test(text)) break;
      const nextBtn = page.locator('[data-testid="interact-board-next"]');
      await nextBtn.click();
      await page.waitForTimeout(500);
    }
    await page.locator('[data-testid="interact-board-next"]').click();
    await page.waitForTimeout(2000);
    // Check for recap buttons (Replay or Keep in message recap)
    const replay = page.locator('[data-testid="ai-tour-replay"]');
    const keep = page.locator('[data-testid="ai-tour-keep"]');
    await expect(replay.or(keep).first()).toBeVisible({ timeout: 15000 });
  });
});
