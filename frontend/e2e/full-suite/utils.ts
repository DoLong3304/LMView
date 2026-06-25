// Shared helpers for full UI/UX test suite
import { Page, Locator } from "@playwright/test";

export const ADMIN = { email: "admin@example.com", password: "Admin@1234" };

export async function login(page: Page) {
  await page.goto("https://lmview.duckdns.org", { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);
  const loginBtn = page.locator('button:has-text("Login")').first();
  if ((await loginBtn.count()) > 0 && await loginBtn.isVisible()) {
    await loginBtn.click();
    await page.waitForTimeout(500);
    await page.fill('input[type="email"]', ADMIN.email);
    await page.fill('input[type="password"]', ADMIN.password);
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);
  }
  // Open AI Helper (common entry point)
  const aiBtn = page.locator('button:has-text("AI Helper")').first();
  await aiBtn.click();
  await page.waitForTimeout(1500);
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
  await ta.waitFor({ state: 'visible', timeout: 15000 });
  // wait for enabled (re-enabled after previous tour)
  for (let w = 0; w < 30; w++) {
    if (await ta.isEnabled()) break;
    await page.waitForTimeout(1000);
  }
  await ta.fill(text);
  await page.waitForTimeout(300);
  const sendBtn = page.locator('button:has-text("Send")').first();
  await sendBtn.click();
}

export async function waitForTourOverlay(page: Page, timeout = 120000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const overlay = page.locator('[data-testid="ai-tour-overlay"]').first();
    if ((await overlay.count()) > 0) {
      const text = await overlay.innerText();
      const m = text.match(/Step\s+(\d+)\s+of\s+(\d+)/i);
      if (m) return { step: parseInt(m[1]), total: parseInt(m[2]), text };
    }
    await page.waitForTimeout(1000);
  }
  return null;
}

export async function clearChat(page: Page) {
  // Try clicking the New Chat button; if not found, navigate fresh.
  const newChatBtn = page.locator('button:has-text("New Chat")').first();
  if ((await newChatBtn.count()) > 0 && await newChatBtn.isVisible()) {
    await newChatBtn.click();
    await page.waitForTimeout(1000);
  } else {
    // Fallback: re-open AI Helper
    const aiBtn = page.locator('button:has-text("AI Helper")').first();
    if ((await aiBtn.count()) > 0 && await aiBtn.isVisible()) {
      await aiBtn.click();
      await page.waitForTimeout(1500);
    }
  }
}

export async function setViewport(page: Page, width: number, height: number) {
  await page.setViewportSize({ width, height });
  await page.waitForTimeout(500);
}
