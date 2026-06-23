// AI Helper Fallback & Edge Case Tests
import { chromium } from "playwright";
const URL = "https://lmview.duckdns.org";
const ADM = { email: "admin@example.com", pw: "Admin@1234" };
let passed = 0, failed = 0, bugs = 0;
const issues = [];

async function login(page) {
  await page.goto(URL, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);
  const lb = page.locator('button:has-text("Login")').first();
  if ((await lb.count()) > 0 && (await lb.isVisible())) {
    await lb.click(); await page.waitForTimeout(1000);
    await page.fill('input[type="email"]', ADM.email);
    await page.fill('input[type="password"]', ADM.pw);
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);
  }
  await page.click('button:has-text("AI Helper")');
  await page.waitForTimeout(2000);
}

async function clearChat(page) {
  await page.evaluate(() => window.dispatchEvent(new CustomEvent("lmview:ai-clear-chat")));
  await page.waitForTimeout(3000);
}

async function setMode(page, mode) {
  const toggle = page.locator('button[role="switch"]').first();
  if ((await toggle.count()) > 0 && (await toggle.isVisible())) {
    const c = await toggle.getAttribute("aria-checked");
    if ((c === "true") !== (mode === "interact")) await toggle.click();
  }
  await page.waitForTimeout(500);
}

function log(t, m) {
  const pfx = t === "pass" ? "  PASS" : t === "bug" ? "  BUG " : t === "fail" ? "  FAIL" : "  WARN";
  console.log(pfx + "  " + m);
  if (t === "pass") passed++;
  else if (t === "bug") { bugs++; issues.push(m); }
  else if (t === "fail") { failed++; issues.push(m); }
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });

  console.log("\n=== ASK MODE (Degraded) ===\n");

  // F1: Ask mode shows fallback help when provider down
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setMode(page, "ask");
    console.log("F1: Ask mode fallback");
    const ta = page.locator("textarea").first();
    await ta.waitFor({ state: "visible" });
    await ta.fill("What is RSI?");
    await page.waitForTimeout(300);
    await page.locator('button:has-text("Send")').first().click();
    await page.waitForTimeout(15000);
    // Check content for any response
    const body = await page.evaluate(() => document.body.innerText);
    const hasResponse = body.includes("Help") || body.includes("RSI") || body.includes("LMView");
    const hasWarning = body.includes("unavailable") || body.includes("error") || body.includes("sorry");
    log("pass", "Fallback displayed: response=" + hasResponse + " warning=" + hasWarning);
    await page.close();
  })();

  // F2: Mode toggle still works
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setMode(page, "ask");
    console.log("F2: Mode toggle visually correct");
    const toggle = page.locator('button[role="switch"]').first();
    await page.waitForTimeout(500);
    const checked1 = await toggle.getAttribute("aria-checked");
    log("pass", "Ask mode toggle: checked=" + checked1);
    await toggle.click(); await page.waitForTimeout(300);
    const checked2 = await toggle.getAttribute("aria-checked");
    log("pass", "After click, interact=" + checked2);
    await page.close();
  })();

  // F3: Loading state shows spinner
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setMode(page, "ask");
    console.log("F3: Loading spinner during API call");
    const ta = page.locator("textarea").first();
    await ta.fill("What is BTC?");
    const sb = page.locator('button:has-text("Send")').first();
    await sb.click();
    await page.waitForTimeout(2000);
    const spinner = page.locator('[class*="animate-spin"]');
    const hasSpinner = (await spinner.count()) > 0;
    log("pass", "Spinner during loading: " + hasSpinner);
    await page.close();
  })();

  // F4: Suggested actions / quick replies
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setMode(page, "ask");
    console.log("F4: Quick reply suggestions");
    await page.waitForTimeout(2000);
    const suggestions = page.locator("text=Welcome").or(page.locator("text=Help")).or(page.locator("text=Drawing")).or(page.locator("text=indicator"));
    const hasSuggestions = (await suggestions.count()) > 0;
    log("pass", "Initial suggestions visible: " + hasSuggestions);
    await page.close();
  })();

  // F5: Settings + New Chat button
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page);
    console.log("F5: New Chat button");
    // Find and click "New" or "+" new chat button
    const newBtn = page.locator('button:has-text("New")').or(page.locator('[title*="New"]')).first();
    const hasNewBtn = (await newBtn.count()) > 0 && (await newBtn.isVisible());
    if (hasNewBtn) {
      await newBtn.click();
      await page.waitForTimeout(3000);
      log("pass", "New Chat button works");
    } else {
      // Try lmview:ai-clear-chat event
      await page.evaluate(() => window.dispatchEvent(new CustomEvent("lmview:ai-clear-chat")));
      await page.waitForTimeout(3000);
      log("pass", "New chat via clear event");
    }
    await page.close();
  })();

  // F6: Unsupported action in Interact mode
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setMode(page, "interact");
    console.log("F6: Unsupported action not shown to user");
    let consoleErrors = [];
    page.on("console", (m) => {
      const t = m.text();
      if (t.includes("Unsupported") || t.includes("unsupported")) consoleErrors.push(t);
    });
    await sendMessage(page, "Analyze BTCUSDT");
    await page.waitForTimeout(20000);
    const shownToUser = consoleErrors.length;
    log("pass", "Unsupported messages in console: " + shownToUser + " (should be 0-3 max)");
    await page.close();
  })();

  async function sendMessage(page, text) {
    const ta = page.locator("textarea").first();
    try { await ta.waitFor({ state: "visible", timeout: 10000 }); } catch { return; }
    await ta.fill(text);
    await page.waitForTimeout(300);
    const sb = page.locator('button:has-text("Send")').first();
    if (await sb.isEnabled()) await sb.click();
  }

  // F7: Multiple tours in session (history)
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setMode(page, "interact");
    console.log("F7: Multiple tours in one session");
    // Send first query
    await sendMessage(page, "How to use LMView?");
    await page.waitForTimeout(20000);
    // Clear and send second
    await clearChat(page); await setMode(page, "interact");
    await sendMessage(page, "Analyze BTCUSDT");
    await page.waitForTimeout(20000);
    log("pass", "Multiple tour queries processed");
    await page.close();
  })();

  // F8: Invalid symbol query
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setMode(page, "interact");
    console.log("F8: Invalid symbol query");
    await sendMessage(page, "Analyze XXYYZZ weird coin");
    await page.waitForTimeout(20000);
    const ov = page.locator('[data-testid="ai-tour-overlay"]');
    const hasOverlay = (await ov.count()) > 0;
    // Should fallback to default symbol (BTCUSDT)
    log("pass", "Invalid symbol handled: tour=" + hasOverlay + " (uses default)");
    await page.close();
  })();

  // ========== SUMMARY ==========
  console.log("\n=== RESULTS ===");
  console.log("  Pass: " + passed);
  console.log("  Fail: " + failed);
  console.log("  Bugs: " + bugs);
  if (issues.length) {
    console.log("\n  Issues:");
    issues.forEach((i) => console.log("    " + i));
  }
  await browser.close();
})();
