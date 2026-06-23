// End-to-end test of the tour
import { chromium } from "playwright";
const log = (m) => console.log(`[t] ${m}`);

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => log(`PAGEERROR: ${e.message}`));

  await page.goto("https://lmview.duckdns.org/", { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  const loginBtn = page.locator('button:has-text("Login")').first();
  if (await loginBtn.count() > 0 && await loginBtn.isVisible()) {
    await loginBtn.click();
    await page.waitForTimeout(1000);
    await page.fill('input[type="email"]', "admin@example.com");
    await page.fill('input[type="password"]', "Admin@1234");
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);
  }

  await page.click('button:has-text("AI Helper")');
  await page.waitForTimeout(2000);

  // Start fresh chat
  await page.evaluate(() => window.dispatchEvent(new CustomEvent("lmview:ai-clear-chat")));
  await page.waitForTimeout(1000);

  // Force interact mode
  const toggle = page.locator('button[role="switch"]').first();
  if (await toggle.count() > 0) {
    const checked = await toggle.getAttribute('aria-checked');
    if (checked !== 'true') await toggle.click();
  }
  await page.waitForTimeout(500);

  // Send message
  const ta = page.locator('textarea').first();
  await ta.click();
  await page.keyboard.type("How to use LMView?", { delay: 20 });
  await page.waitForTimeout(500);
  const sendBtn = page.locator('button:has-text("Send")').first();
  if (await sendBtn.isEnabled()) {
    await sendBtn.click();
    log("sent");
  }

  // Wait for tour
  log("waiting for tour overlay...");
  const overlay = page.locator('[data-testid="ai-tour-overlay"]');
  let found = false;
  for (let i = 0; i < 30; i++) {
    await page.waitForTimeout(2000);
    if (await overlay.count() > 0) {
      const visible = await overlay.isVisible();
      if (visible) {
        log(`overlay visible after ${(i+1)*2}s!`);
        found = true;
        break;
      }
    }
  }
  if (!found) {
    log("OVERLAY NEVER APPEARED");
    await page.screenshot({ path: "/tmp/t-fail.png" });
  } else {
    // Test next button
    const nextBtn = page.locator('[data-testid="ai-tour-next"]');
    const nextVisible = await nextBtn.isVisible();
    log(`next button visible: ${nextVisible}`);
    if (nextVisible) {
      log("clicking next...");
      await nextBtn.click();
      await page.waitForTimeout(2000);
      const ov2 = page.locator('[data-testid="ai-tour-overlay"]');
      const txt2 = await ov2.textContent();
      log(`step 2 text: ${txt2?.slice(0, 80).replace(/\s+/g, ' ')}`);
      // Click next again
      await nextBtn.click();
      await page.waitForTimeout(2000);
      const txt3 = await ov2.textContent();
      log(`step 3 text: ${txt3?.slice(0, 80).replace(/\s+/g, ' ')}`);
    }
    await page.screenshot({ path: "/tmp/t-success.png" });
    log("screenshot saved");
  }

  await browser.close();
})();