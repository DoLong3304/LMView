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
  page.on("response", async (resp) => {
    const url = resp.url();
    if (url.includes("/api/ai/chat")) {
      try {
        const body = await resp.json();
        log(`API chat resp: status=${resp.status()}, msg_id=${body.message_id?.slice(0, 20)}, has_tour=${!!body.tour_plan}`);
      } catch (e) {}
    }
  });
  page.on("pageerror", (e) => log(`PAGEERROR: ${e.message}`));
  page.on("console", (msg) => {
    const t = msg.text();
    if (t.includes("[tour]")) log(`CONSOLE: ${t.slice(0, 400)}`);
    else if (msg.type() === "error") log(`CONSOLE.error: ${t.slice(0, 200)}`);
  });

  await page.goto("https://lmview.duckdns.org/", { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  // Login if needed
  const loginBtn = page.locator('button:has-text("Login")').first();
  if (await loginBtn.count() > 0 && await loginBtn.isVisible()) {
    log("logging in");
    await loginBtn.click();
    await page.waitForTimeout(1000);
    await page.fill('input[type="email"]', "admin@example.com");
    await page.fill('input[type="password"]', "Admin@1234");
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);
  } else {
    log("already logged in");
  }

  // Open AI Helper - look for any element with text "AI Helper"
  log("opening AI Helper");
  const aiButtons = await page.locator('button:has-text("AI Helper")').all();
  log(`AI Helper button count: ${aiButtons.length}`);
  for (let i = 0; i < aiButtons.length; i++) {
    const box = await aiButtons[i].boundingBox();
    log(`  [${i}] box: ${JSON.stringify(box)}`);
  }
  if (aiButtons.length > 0) {
    // Click the rightmost one (in the right panel tab area)
    const last = aiButtons[aiButtons.length - 1];
    const box = await last.boundingBox();
    log(`clicking AI Helper at (${Math.round(box.x)}, ${Math.round(box.y)})`);
    await last.click();
    await page.waitForTimeout(2000);
  }

  // Verify AI panel state
  const placeholders = await page.locator('input[placeholder], textarea[placeholder]').evaluateAll(els => els.map(el => el.getAttribute('placeholder')));
  log(`placeholders after AI open: ${placeholders.join(' | ')}`);

  // Find the toggle (mode switch) and ensure interact is on
  const toggle = page.locator('button[role="switch"]').first();
  log(`toggle count: ${await toggle.count()}`);
  if (await toggle.count() > 0) {
    const checked = await toggle.getAttribute('aria-checked');
    log(`toggle aria-checked: ${checked}`);
    if (checked !== 'true') {
      await toggle.click();
      log("toggled to interact");
      await page.waitForTimeout(500);
    }
  }

  // Find the chat textarea/input
  const chatInput = page.locator('textarea[placeholder*="Ask"], input[placeholder*="Ask"]').first();
  log(`chat input count: ${await chatInput.count()}`);
  if (await chatInput.count() > 0) {
    await chatInput.click();
    await page.keyboard.type("How to use LMView?");
    await page.waitForTimeout(500);
    // Check input value
    const val = await chatInput.inputValue();
    log(`input value: "${val}"`);
    const sendBtn = page.locator('button:has-text("Send")').first();
    const enabled = await sendBtn.isEnabled();
    log(`send btn count: ${await sendBtn.count()}, visible: ${await sendBtn.isVisible()}, enabled: ${enabled}`);
    if (enabled) {
      // Click via dispatchEvent to bypass any onClick traps
      await sendBtn.evaluate((el) => el.click());
      log("send evaluated click()");
      await page.waitForTimeout(2000);
      const chatCalls = apiCalls.filter(a => a.url.includes('/api/ai/chat'));
      log(`chat calls: ${chatCalls.length}`);
      // Print full URL of /api/ai/*  if any
      const allAi = apiCalls.filter(a => a.url.includes('/api/'));
      log(`/api/* calls (last 10):`);
      for (const a of allAi.slice(-10)) log(`  ${a.method} ${a.url.replace('https://lmview.duckdns.org', '')}`);
    } else {
      log("send disabled, trying Enter");
      await page.keyboard.press("Enter");
    }
  } else {
    log("no chat input found");
  }

  log("waiting 20s for response + tour");
  await page.waitForTimeout(20000);
  await page.screenshot({ path: "/tmp/p-tour.png", fullPage: false });
  log("screenshot saved");

  // Inspect
  const overlay = page.locator('[data-testid="ai-tour-overlay"]');
  log(`overlay count: ${await overlay.count()}`);
  if (await overlay.count() > 0) {
    const box = await overlay.first().boundingBox();
    const text = (await overlay.first().textContent())?.slice(0, 200);
    log(`overlay box: ${JSON.stringify(box)}`);
    log(`overlay text: ${text?.replace(/\s+/g, ' ')}`);
  }

  const nextBtn = page.locator('[data-testid="ai-tour-next"]');
  const prevBtn = page.locator('[data-testid="ai-tour-prev"]');
  const keepBtn = page.locator('[data-testid="ai-tour-keep"]');
  const revertBtn = page.locator('[data-testid="ai-tour-revert"]');
  log(`next: ${await nextBtn.count()}, prev: ${await prevBtn.count()}, keep: ${await keepBtn.count()}, revert: ${await revertBtn.count()}`);

  // Now look at the AI panel content - try multiple selectors
  const panelText = await page.evaluate(() => {
    const candidates = [
      document.querySelector('[data-ai-section="ai"]'),
      document.querySelector('[data-testid="ai-tour-overlay"]'),
      document.querySelector('[data-testid="ai-analysis-card"]'),
    ];
    const results = {};
    for (let i = 0; i < candidates.length; i++) {
      results[`sel${i}`] = candidates[i] ? candidates[i].outerHTML.slice(0, 2000) : null;
    }
    return JSON.stringify(results, null, 2);
  });
  log(`panel probe: ${panelText.slice(0, 3000)}`);

  log(`API calls total: ${apiCalls.length}`);
  for (const a of apiCalls.slice(-10)) {
    log(`  ${a.method} ${a.url.replace('https://lmview.duckdns.org', '')}`);
  }

  await browser.close();
})();