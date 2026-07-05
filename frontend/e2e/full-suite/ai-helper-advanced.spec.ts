/**
 * AI Helper advanced UI tests — session memory, settings, debug mode.
 *
 * G1: Comprehensive Playwright UI tests for all AI features.
 * G3+G4: Uses session chaining to test multiple features per login.
 */
import { test, expect } from "@playwright/test";
import { login, setMode, sendMessage, waitForTourOverlay, clearChat } from "./utils";

test.describe("AI Helper – Settings & Debug", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  // ── Settings: AI Helper tab visibility ──
  test("settings AI Helper tab appears for authenticated user", async ({ page }) => {
    // Open settings
    const settingsBtn = page.locator('button[title="Settings"]').first();
    await expect(settingsBtn).toBeVisible({ timeout: 10000 });
    await settingsBtn.click();
    await page.waitForTimeout(1500);

    // Click AI Helper tab
    const aiTab = page.locator('button:has-text("AI Helper")').first();
    await expect(aiTab).toBeVisible({ timeout: 5000 });
    await aiTab.click();
    await page.waitForTimeout(1000);

    // Verify AI settings are visible
    const responseStyle = page.locator('text=Response Style').first();
    const riskReminders = page.locator('text=Risk Reminders').first();
    expect((await responseStyle.count()) > 0 || (await riskReminders.count()) > 0).toBeTruthy();
  });

  // ── Settings: Model selector ──
  test("model selector shows available models", async ({ page }) => {
    const settingsBtn = page.locator('button[title="Settings"]').first();
    await settingsBtn.click();
    await page.waitForTimeout(2000);

    const aiTab = page.locator('button:has-text("AI Helper")').first();
    await aiTab.click();
    await page.waitForTimeout(3000); // Wait for models to load

    // Check for model dropdown with available models
    const select = page.locator('select').filter({ hasText: /qwen|Auto|model/i }).first();
    if (await select.isVisible()) {
      const options = await select.locator('option').allTextContents();
      expect(options.length).toBeGreaterThan(0);
      // Should have "Auto (Default)" option
      expect(options.some(o => o.includes('Auto'))).toBeTruthy();
    }
  });

  // ── Debug tab (admin only) ──
  test("debug tab visible and functional for admin", async ({ page }) => {
    const settingsBtn = page.locator('button[title="Settings"]').first();
    await settingsBtn.click();
    await page.waitForTimeout(1500);

    // Click Debug tab
    const debugTab = page.locator('button:has-text("Debug")').first();
    await expect(debugTab).toBeVisible({ timeout: 5000 });
    await debugTab.click();
    await page.waitForTimeout(1000);

    // Run health check
    const healthBtn = page.locator('button:has-text("Run Health Check")').first();
    await expect(healthBtn).toBeVisible({ timeout: 5000 });
    await healthBtn.click();
    await page.waitForTimeout(5000);

    // Check health result appeared
    const resultPre = page.locator('pre').first();
    const text = await resultPre.innerText();
    expect(text.length).toBeGreaterThan(10);
  });

  // ── Debug: AI health check ──
  test("AI health check shows model tiers", async ({ page }) => {
    const settingsBtn = page.locator('button[title="Settings"]').first();
    await settingsBtn.click();
    await page.waitForTimeout(1500);

    const debugTab = page.locator('button:has-text("Debug")').first();
    await debugTab.click();
    await page.waitForTimeout(1000);

    const aiHealthBtn = page.locator('button:has-text("AI Health")').first();
    await expect(aiHealthBtn).toBeVisible({ timeout: 5000 });
    await aiHealthBtn.click();
    await page.waitForTimeout(5000);

    const resultPre = page.locator('pre').first();
    const text = await resultPre.innerText();
    // Should contain model tier info
    expect(text.includes('standard') || text.includes('benchmark') || text.includes('reserved')).toBeTruthy();
  });
});

test.describe("AI Helper – Session Memory & Cross-turn", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await setMode(page, "ask");
    await clearChat(page);
  });

  // ── Session memory: cross-turn context ──
  test("cross-turn context persists within session", async ({ page }) => {
    // First message: ask about BTC
    await sendMessage(page, "What is the RSI level on BTC?");
    await page.waitForTimeout(15000); // Wait for response

    // Second message: reference prior context
    await sendMessage(page, "What does that RSI value indicate?");
    await page.waitForTimeout(20000); // Wait for response

    // Check last response references RSI context
    const lastMsg = page.locator('[data-testid^="ai-message-"]').last();
    const text = await lastMsg.innerText();
    // Should mention the RSI value or at least RSI concept
    const hasRSI = text.includes('RSI') || text.includes('rsi') || text.includes('Relative Strength');
    expect(hasRSI).toBeTruthy();
  });

  // ── Session memory: preference persistence ──
  test("user preference persisted across turns", async ({ page }) => {
    // State preference
    await sendMessage(page, "I prefer analyzing on the 4H timeframe");
    await page.waitForTimeout(12000);

    // Follow-up
    await sendMessage(page, "What do you see on the chart?");
    await page.waitForTimeout(20000);

    const lastMsg = page.locator('[data-testid^="ai-message-"]').last();
    const text = await lastMsg.innerText();
    // Should reference 4H timeframe
    const has4H = text.includes('4H') || text.includes('4h') || text.includes('4 hour');
    expect(has4H).toBeTruthy();
  });

  // ── Interact mode: tour then new chat ──
  test("interact tour completes then new chat works", async ({ page }) => {
    await setMode(page, "interact");
    await clearChat(page);

    // Start a walkthrough
    await sendMessage(page, "Show me how to use the chart");
    const tour = await waitForTourOverlay(page, 120000);
    expect(tour).not.toBeNull();

    // Complete the tour (click keep)
    for (let i = tour!.step; i < tour!.total; i++) {
      const overlayText = await page.locator('[data-testid="interact-board"]').innerText();
      if (overlayText.includes("Keep") || overlayText.includes("Finish") || overlayText.includes("finish")) break;
      const nextBtn = page.locator('[data-testid="interact-board-next"]').first();
      await nextBtn.click();
      await page.waitForTimeout(1000);
    }
    // Finish button
    await page.locator('[data-testid="interact-board-next"]').first().click();
    await page.waitForTimeout(3000);
    const keepBtn = page.locator('[data-testid="ai-tour-keep"]').first();
    if (await keepBtn.isVisible()) {
      await keepBtn.click();
      await page.waitForTimeout(2000);
    }

    // Clear and start new chat
    await clearChat(page);
    const ta = page.locator('textarea').first();
    await expect(ta).toBeEnabled({ timeout: 10000 });
    await sendMessage(page, "What is RSI?");
    await page.waitForTimeout(15000);
    const msg = page.locator('[data-testid^="ai-message-"]').last();
    await expect(msg).toBeVisible({ timeout: 10000 });
  });
});

test.describe("AI Helper – Multi-intent & Chained Queries (G3)", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await setMode(page, "ask");
    await clearChat(page);
  });

  // ── Chained queries: same session ──
  test("chained TA questions in single session", async ({ page }) => {
    const questions = [
      "What does RSI above 70 mean?",
      "How does MACD confirm trend changes?",
      "What is a golden cross?",
    ];
    for (const q of questions) {
      await sendMessage(page, q);
      await page.waitForTimeout(18000);
    }
    // All 3 responses should exist
    const msgs = page.locator('[data-testid^="ai-message-"]');
    const count = await msgs.count();
    expect(count).toBeGreaterThanOrEqual(3);
  });

  // ── User opinion + follow-up ──
  test("user opinion followed by analysis request", async ({ page }) => {
    await sendMessage(page, "I think BTC looks bullish right now");
    await page.waitForTimeout(12000);

    await sendMessage(page, "What indicators support that view?");
    await page.waitForTimeout(20000);

    const lastMsg = page.locator('[data-testid^="ai-message-"]').last();
    const text = await lastMsg.innerText();
    // Should reference BTC or bullish indicators
    const hasRelevant = text.includes('BTC') || text.includes('bullish') || text.includes('indicator');
    expect(hasRelevant).toBeTruthy();
  });

  // ── Out-of-scope + recovery ──
  test("out-of-scope refusal then recovery to crypto topic", async ({ page }) => {
    await sendMessage(page, "What's the weather today?");
    await page.waitForTimeout(10000);

    const firstMsg = page.locator('[data-testid^="ai-message-"]').last();
    const firstText = await firstMsg.innerText();
    // Should refuse weather
    const refused = firstText.includes('crypto') || firstText.includes('trade') || firstText.includes('analysis') || firstText.includes("can't") || firstText.includes("cannot") || firstText.includes("unable");
    expect(refused).toBeTruthy();

    // Recovery: ask crypto question
    await sendMessage(page, "How does RSI work for crypto?");
    await page.waitForTimeout(15000);

    const secondMsg = page.locator('[data-testid^="ai-message-"]').last();
    const secondText = await secondMsg.innerText();
    const answered = secondText.includes('RSI') || secondText.includes('Relative Strength') || secondText.includes('overbought');
    expect(answered).toBeTruthy();
  });
});

test.describe("AI Helper – Mode Switching (G3)", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await clearChat(page);
  });

  test("switch between ask and interact modes", async ({ page }) => {
    // Default is ask
    await setMode(page, "ask");
    await sendMessage(page, "What is MACD?");
    await page.waitForTimeout(15000);
    const askMsg = page.locator('[data-testid^="ai-message-"]').last();
    const askText = await askMsg.innerText();
    expect(askText.length).toBeGreaterThan(20);

    // Switch to interact
    await setMode(page, "interact");
    await clearChat(page);
    await sendMessage(page, "Analyze BTC chart");
    const tour = await waitForTourOverlay(page, 60000);
    expect(tour).not.toBeNull();
  });
});
