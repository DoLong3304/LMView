// Direct injection test
import { chromium } from "playwright";
const log = (m) => console.log(`[probe] ${m}`);

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const apiCalls = [];
  page.on("request", (req) => {
    if (req.url().includes("/api/")) {
      apiCalls.push({ method: req.method(), url: req.url() });
    }
  });
  page.on("console", (msg) => {
    const t = msg.text();
    if (t.includes("[tour") || t.includes("[AI]") || msg.type() === "error") {
      log(`C: ${t.slice(0, 300)}`);
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

  // Start a fresh chat
  await page.evaluate(() => {
    window.dispatchEvent(new CustomEvent("lmview:ai-clear-chat"));
  });
  await page.waitForTimeout(1000);

  // Force interact mode
  const toggle = page.locator('button[role="switch"]').first();
  if (await toggle.count() > 0) {
    const checked = await toggle.getAttribute('aria-checked');
    if (checked !== 'true') {
      await toggle.click();
      log("toggled to interact");
    } else {
      log("already interact");
    }
  }
  await page.waitForTimeout(500);

  // Verify AI panel is visible
  const aiPanel = page.locator('[data-ai-section="ai-panel"]');
  const aiPanelCount = await aiPanel.count();
  log(`ai-panel count: ${aiPanelCount}`);
  if (aiPanelCount === 0) {
    // Maybe not on AI tab. Click it.
    log("clicking AI Helper tab again");
    const aiTab = page.locator('button:has-text("AI Helper")').first();
    if (await aiTab.count() > 0 && await aiTab.isVisible()) {
      await aiTab.click();
      await page.waitForTimeout(2000);
    }
    log(`ai-panel count after re-click: ${await aiPanel.count()}`);
  }

  // Type into textarea
  const ta = page.locator('textarea').first();
  await ta.click();
  await page.waitForTimeout(200);
  await page.keyboard.type("how to use lmview", { delay: 30 });
  await page.waitForTimeout(500);
  const val = await ta.inputValue();
  log(`input value: "${val}"`);

  // Click send
  const sendBtn = page.locator('button:has-text("Send")').first();
  const enabled = await sendBtn.isEnabled();
  log(`send: count=${await sendBtn.count()}, visible=${await sendBtn.isVisible()}, enabled=${enabled}`);
  if (enabled) {
    await sendBtn.click();
    log("send clicked");
  }
  await page.waitForTimeout(30000);
  const chatCalls = apiCalls.filter(a => a.url.includes('/api/ai/chat'));
  log(`/api/ai/chat requests: ${chatCalls.length}`);
  for (const c of chatCalls.slice(-3)) log(`  ${c.method} ${c.url.replace('https://lmview.duckdns.org', '')}`);

  const overlay = page.locator('[data-testid="ai-tour-overlay"]');
  log(`overlay count: ${await overlay.count()}`);
  if (await overlay.count() > 0) {
    const box = await overlay.first().boundingBox();
    log(`overlay box: ${JSON.stringify(box)}`);
    const visible = await overlay.first().isVisible();
    log(`overlay visible: ${visible}`);
  }
  // Also check if it's in the DOM at all (even hidden)
  const allOverlays = await page.evaluate(() => {
    const els = document.querySelectorAll('[data-testid="ai-tour-overlay"]');
    return Array.from(els).map(el => ({
      rect: el.getBoundingClientRect().toJSON(),
      display: window.getComputedStyle(el).display,
      visibility: window.getComputedStyle(el).visibility,
      opacity: window.getComputedStyle(el).opacity,
      text: (el.textContent || '').slice(0, 100).replace(/\s+/g, ' '),
    }));
  });
  log(`overlay DOM probes: ${JSON.stringify(allOverlays, null, 2).slice(0, 1000)}`);

  await browser.close();
})();