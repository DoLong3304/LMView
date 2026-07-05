// Shared helpers for full UI/UX test suite
import { Page, Locator } from "@playwright/test";

export const ADMIN = { email: "admin@lmview.com", password: "LMViewAdminPassword2026!" };

export async function login(page: Page) {
  await page.goto("https://lmview.duckdns.org", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(3000);

  // Check if already logged in — look for any non-login button
  const loginBtn = page.locator('button[title="Login"]').first();
  if ((await loginBtn.count()) > 0 && await loginBtn.isVisible()) {
    await loginBtn.click();
    await page.waitForTimeout(2000);
    const emailInput = page.locator('input[type="email"]').first();
    await emailInput.waitFor({ state: 'visible', timeout: 10000 });
    await emailInput.fill(ADMIN.email);
    await page.locator('input[type="password"]').first().fill(ADMIN.password);
    await page.locator('button[type="submit"]').first().click();
    await page.waitForTimeout(4000);
    // Close any modal/overlay
    await page.keyboard.press("Escape");
    await page.waitForTimeout(1000);
    await page.keyboard.press("Escape");
    await page.waitForTimeout(1000);
  }

  // Open AI Helper panel
  const aiBtn = page.locator('button[title="AI Helper"]').first();
  if ((await aiBtn.count()) > 0 && await aiBtn.isVisible()) {
    await aiBtn.click();
    await page.waitForTimeout(2000);
  }

  // Verify AI Helper panel opened — look for textarea
  const ta = page.locator('textarea').first();
  await ta.waitFor({ state: 'visible', timeout: 15000 }).catch(() => {});
}

export async function setMode(page: Page, mode: "ask" | "interact") {
  const toggle = page.locator('button[role="switch"]').first();
  if ((await toggle.count()) > 0 && await toggle.isVisible()) {
    const checked = await toggle.getAttribute("aria-checked");
    const want = mode === "interact";
    if ((checked === "true") !== want) await toggle.click();
  }
  await page.waitForTimeout(500);
}

export async function sendMessage(page: Page, text: string) {
  const ta = page.locator('textarea').first();
  await ta.waitFor({ state: 'visible', timeout: 30000 });
  // wait for enabled (re-enabled after previous tour)
  for (let w = 0; w < 30; w++) {
    if (await ta.isEnabled()) break;
    await page.waitForTimeout(1000);
  }
  await ta.click();
  await ta.fill(text);
  await page.waitForTimeout(500);
  // AiChatInput uses plain Enter for newline; send via button (or Ctrl/Cmd+Enter).
  const sendBtn = page.locator('button:has-text("Send")').first();
  if ((await sendBtn.count()) > 0 && await sendBtn.isVisible()) {
    await sendBtn.click();
  } else {
    await page.keyboard.press(process.platform === "darwin" ? "Meta+Enter" : "Control+Enter");
  }
}

export async function waitForTourOverlay(page: Page, timeout = 150000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const overlay = page.locator('[data-testid="interact-board"]').first();
    if ((await overlay.count()) > 0) {
      const text = await overlay.innerText();
      // Match "2/6" step numbers in new format
      const m = text.match(/(\d+)\s*\/\s*(\d+)/);
      if (m) return { step: parseInt(m[1]), total: parseInt(m[2]), text };
    }
    await page.waitForTimeout(2000);
  }
  return null;
}

export async function clearChat(page: Page) {
  // Wait for session to fully load — poll until stable for 1s
  for (let attempt = 0; attempt < 10; attempt++) {
    const count = await page.locator('[data-testid^="ai-message-"]').count();
    await page.waitForTimeout(1000);
    const newCount = await page.locator('[data-testid^="ai-message-"]').count();
    if (count === newCount) break;
  }

  // Now clear the chat
  const newChatBtn = page.locator('button[title="New chat"]').first();
  if ((await newChatBtn.count()) > 0 && await newChatBtn.isVisible()) {
    await newChatBtn.click();
    await page.waitForTimeout(2000);
  } else {
    // Fallback: re-open AI Helper
    const aiBtn = page.locator('button[title="AI Helper"]').first();
    if ((await aiBtn.count()) > 0 && await aiBtn.isVisible()) {
      await aiBtn.click();
      await page.waitForTimeout(1500);
    }
  }
  // Wait for messages to actually clear
  await page.waitForTimeout(1000);
}

export async function setViewport(page: Page, width: number, height: number) {
  await page.setViewportSize({ width, height });
  await page.waitForTimeout(500);
}
