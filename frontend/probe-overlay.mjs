// Test if overlay renders when activeTour is set manually
import { chromium } from "playwright";
const log = (m) => console.log(`[probe] ${m}`);

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on("console", (msg) => {
    const t = msg.text();
    if (t.includes("[tour]") || t.includes("[AI]") || msg.type() === "error") {
      log(`CONSOLE: ${t.slice(0, 300)}`);
    }
  });

  await page.goto("https://lmview.duckdns.org/", { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  // Login
  const loginBtn = page.locator('button:has-text("Login")').first();
  if (await loginBtn.count() > 0 && await loginBtn.isVisible()) {
    await loginBtn.click();
    await page.waitForTimeout(1000);
    await page.fill('input[type="email"]', "admin@example.com");
    await page.fill('input[type="password"]', "Admin@1234");
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);
  }

  // Open AI Helper
  await page.click('button:has-text("AI Helper")');
  await page.waitForTimeout(2000);

  // Click "New chat" via custom event
  await page.evaluate(() => {
    window.dispatchEvent(new CustomEvent("lmview:ai-clear-chat"));
  });
  await page.waitForTimeout(1000);

  // Now manually start a tour via direct JS
  log("dispatching tour start events");
  await page.evaluate(() => {
    // Simulate what the auto-start effect does
    window.dispatchEvent(new CustomEvent("lmview:chart-freeze", { detail: { frozen: true } }));
  });
  await page.waitForTimeout(500);
  await page.screenshot({ path: "/tmp/p-manual.png" });
  log("manual screenshot saved");

  // Look for the overlay
  const overlay = page.locator('[data-testid="ai-tour-overlay"]');
  log(`overlay count: ${await overlay.count()}`);

  await browser.close();
})();