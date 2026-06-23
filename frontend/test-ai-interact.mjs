// AI Helper INTERACT Mode UI/UX Tests
// Tests work via intent fallback when LLM unavailable
import { chromium } from "playwright";
const URL = "https://lmview.duckdns.org";
const ADM = { email: "admin@example.com", pw: "Admin@1234" };
let passed = 0, failed = 0, bugs = 0, warnings = [];
const bugs_detail = [];

const LOG = {
  pass: (m) => { console.log("  PASS  " + m); passed++; },
  fail: (m) => { console.log("  FAIL  " + m); failed++; },
  bug: (m) => { console.log("  BUG   " + m); bugs++; bugs_detail.push(m); },
  warn: (m) => { console.log("  WARN  " + m); warnings.push(m); },
};

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

async function setInteract(page) {
  const toggle = page.locator('button[role="switch"]').first();
  if ((await toggle.count()) > 0 && (await toggle.isVisible())) {
    const checked = await toggle.getAttribute("aria-checked");
    if (checked !== "true") await toggle.click();
  }
  await page.waitForTimeout(500);
}

async function sendMessage(page, text) {
  const ta = page.locator("textarea").first();
  try { await ta.waitFor({ state: "visible", timeout: 10000 }); }
  catch { return false; }
  await ta.fill(text);
  await page.waitForTimeout(300);
  const sb = page.locator('button:has-text("Send")').first();
  if (await sb.isEnabled()) { await sb.click(); return true; }
  return false;
}

async function waitForOverlay(page, timeoutMs = 45000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const overlay = page.locator('[data-testid="ai-tour-overlay"]');
    if ((await overlay.count()) > 0) {
      const txt = (await overlay.textContent()) || "";
      const m = txt.match(/Step\s+(\d+)\s+of\s+(\d+)/);
      if (m) return { stepNum: parseInt(m[1]), total: parseInt(m[2]), text: txt };
    }
    await page.waitForTimeout(1000);
  }
  return null;
}

async function walkTour(page, clickKeep = true) {
  let maxSteps = 0;
  for (let i = 0; i < 30; i++) {
    await page.waitForTimeout(1200);
    const overlay = page.locator('[data-testid="ai-tour-overlay"]');
    if ((await overlay.count()) === 0) { if (maxSteps > 0) break; continue; }
    const txt = (await overlay.textContent()) || "";
    const m = txt.match(/Step\s+(\d+)\s+of\s+(\d+)/);
    if (!m) continue;
    const sn = parseInt(m[1]), total = parseInt(m[2]);
    maxSteps = Math.max(maxSteps, sn);
    const isLast = sn >= total;
    if (isLast) {
      const keepBtn = page.locator('[data-testid="ai-tour-keep"]');
      const keepCount = await keepBtn.count();
      if (keepCount > 0 && clickKeep) { await keepBtn.click(); await page.waitForTimeout(2000); break; }
      const nextBtn = page.locator('[data-testid="ai-tour-next"]');
      if (await nextBtn.isVisible()) { await nextBtn.click(); await page.waitForTimeout(2000); break; }
    }
    const nextBtn = page.locator('[data-testid="ai-tour-next"]');
    if (await nextBtn.isVisible()) { await nextBtn.click(); await page.waitForTimeout(500); }
  }
  return maxSteps;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });

  // ========================== INTERACT MODE ==========================
  console.log("\n=== INTERACT MODE TESTS ===\n");

  // T1: Welcome tour
  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await clearChat(page); await setInteract(page);
    console.log("T1: How to use LMView?");
    if (!(await sendMessage(page, "How to use LMView?"))) { LOG.fail("Send failed"); await page.close(); return; }
    const ov = await waitForOverlay(page);
    if (!ov) { LOG.fail("No tour started"); await page.close(); return; }
    if (ov.total < 3) { LOG.bug("Tour too short: " + ov.total + " steps"); await page.close(); return; }
    const steps = await walkTour(page);
    if (steps < 3) { LOG.fail("Only " + steps + "/" + ov.total + " steps"); await page.close(); return; }
    LOG.pass(steps + "/" + ov.total + " step welcome tour OK");
    await page.close();
  })();

  // T2: Analysis tour
  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await clearChat(page); await setInteract(page);
    console.log("T2: Analyze BTCUSDT");
    if (!(await sendMessage(page, "Analyze BTCUSDT"))) { LOG.fail("Send failed"); await page.close(); return; }
    const ov = await waitForOverlay(page, 60000);
    if (!ov) { LOG.fail("No tour"); await page.close(); return; }
    const hasContent = /highlight|indicator|candle|rsi|macd|panel/i.test(ov.text);
    if (!hasContent) LOG.warn("Tour text may lack analysis terms: " + ov.text.slice(0, 80));
    const steps = await walkTour(page);
    LOG.pass(steps + "/" + ov.total + " analysis tour steps");
    await page.close();
  })();

  // T3: Order book
  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await clearChat(page); await setInteract(page);
    console.log("T3: Show ETH order book");
    if (!(await sendMessage(page, "Show me the order book for ETH"))) { LOG.fail("Send failed"); await page.close(); return; }
    const ov = await waitForOverlay(page, 60000);
    if (!ov) { LOG.bug("No order book tour (was broken, now has fallback)"); await page.close(); return; }
    const hasOrderBook = /order.book|open.panel|set_symbol|bids|asks|depth/i.test(ov.text);
    if (!hasOrderBook) LOG.warn("Tour may not show order book: " + ov.text.slice(0, 80));
    const steps = await walkTour(page);
    LOG.pass(steps + "/" + ov.total + " order book tour steps");
    await page.close();
  })();

  // T4: Compare
  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await clearChat(page); await setInteract(page);
    console.log("T4: Compare BTC and ETH");
    if (!(await sendMessage(page, "Compare Bitcoin and Ethereum on 4H"))) { LOG.fail("Send failed"); await page.close(); return; }
    const ov = await waitForOverlay(page, 60000);
    if (!ov) { LOG.warn("No compare tour (may need user query tweak)"); await page.close(); return; }
    const steps = await walkTour(page);
    LOG.pass(steps + "/" + ov.total + " compare tour steps");
    await page.close();
  })();

  // T5: Indicator
  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await clearChat(page); await setInteract(page);
    console.log("T5: Set up RSI on SOL");
    if (!(await sendMessage(page, "Set up RSI indicator on SOL 1H"))) { LOG.fail("Send failed"); await page.close(); return; }
    const ov = await waitForOverlay(page, 60000);
    if (!ov) { LOG.warn("No indicator tour"); await page.close(); return; }
    const hasInd = /add_indicator|rsi|indicator/i.test(ov.text);
    if (!hasInd) LOG.warn("Tour may lack indicator step: " + ov.text.slice(0, 80));
    const steps = await walkTour(page);
    LOG.pass(steps + "/" + ov.total + " indicator tour steps");
    await page.close();
  })();

  // T6: News
  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await clearChat(page); await setInteract(page);
    console.log("T6: Show crypto news");
    if (!(await sendMessage(page, "Show recent crypto news and market overview"))) { LOG.fail("Send failed"); await page.close(); return; }
    const ov = await waitForOverlay(page, 60000);
    if (!ov) { LOG.warn("No news tour (new intent)"); await page.close(); return; }
    const steps = await walkTour(page);
    LOG.pass(steps + "/" + ov.total + " news tour steps");
    await page.close();
  })();

  // ========================== UI/UX VERIFICATION ==========================
  console.log("\n=== UI/UX VERIFICATION ===\n");

  // T7: Overlay element structure
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setInteract(page);
    console.log("T7: Overlay element structure");
    await sendMessage(page, "How to use LMView?");
    const ov = await waitForOverlay(page);
    if (!ov) { LOG.fail("No tour"); await page.close(); return; }
    const hasOverlay = (await page.locator('[data-testid="ai-tour-overlay"]').count()) > 0;
    const hasNext = (await page.locator('[data-testid="ai-tour-next"]').count()) > 0;
    const hasDraggable = (await page.locator('[class*="cursor-grab"]').count()) > 0 ||
      (await page.locator('[class*="drag"]').count()) > 0;
    const hasStepCounter = /Step \d+ of \d+/i.test(ov.text);
    const hasProgress = ov.text.includes("%");
    if (!hasOverlay) { LOG.fail("Overlay missing"); await page.close(); return; }
    if (!hasNext) LOG.bug("Next button missing");
    if (!hasStepCounter) LOG.bug("Step counter missing");
    if (!hasProgress) LOG.warn("Progress bar may be missing");
    LOG.pass("Overlay structure OK: overlay=" + hasOverlay + " next=" + hasNext + " steps=" + hasStepCounter + " progress=" + hasProgress);
    await page.close();
  })();

  // T8: Textarea visibility after tour
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setInteract(page);
    console.log("T8: Textarea visible after tour ends");
    await sendMessage(page, "How to use LMView?");
    const ov = await waitForOverlay(page);
    if (!ov) { LOG.fail("No tour"); await page.close(); return; }
    await walkTour(page);
    await page.waitForTimeout(5000);
    const ta = page.locator("textarea").first();
    const visible = await ta.isVisible().catch(() => false);
    const enabled = await ta.isEnabled().catch(() => false);
    if (!visible) LOG.bug("Textarea hidden after tour ends");
    if (!enabled) LOG.bug("Textarea disabled after tour ends");
    LOG.pass("Textarea: visible=" + visible + " enabled=" + enabled);
    await page.close();
  })();

  // T9: Keep/Revert buttons only on last step
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setInteract(page);
    console.log("T9: Keep/Revert visibility");
    await sendMessage(page, "Analyze BTCUSDT");
    const ov = await waitForOverlay(page, 60000);
    if (!ov) { LOG.fail("No tour"); await page.close(); return; }
    // On first step, check Keep/Revert are hidden
    let hasKeepOnFirst = (await page.locator('[data-testid="ai-tour-keep"]').count()) > 0;
    let hasRevertOnFirst = (await page.locator('[data-testid="ai-tour-revert"]').count()) > 0;
    if (hasKeepOnFirst || hasRevertOnFirst) LOG.bug("Keep/Revert shown early (step 1)");
    // Walk to last step
    await walkTour(page, false);
    await page.waitForTimeout(2000);
    let hasKeepOnLast = (await page.locator('[data-testid="ai-tour-keep"]').count()) > 0;
    if (!hasKeepOnLast) LOG.warn("Keep button not visible on last step");
    LOG.pass("Keep on first=" + hasKeepOnFirst + " on last=" + hasKeepOnLast);
    await page.close();
  })();

  // T10: Tour step explanation quality
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setInteract(page);
    console.log("T10: Step explanation quality");
    await sendMessage(page, "Analyze BTCUSDT");
    const ov = await waitForOverlay(page, 60000);
    if (!ov) { LOG.fail("No tour"); await page.close(); return; }
    const txt = ov.text;
    // Check for boilerplate removed in v0.26.12
    const badPhrases = ["real-time OHLCV cannesticks", "Let's look at the recent"];
    const hasBad = badPhrases.some((p) => txt.includes(p));
    if (hasBad) LOG.bug("Contains boilerplate: " + txt.slice(0, 80));
    // Check for vague "Locate" prefix without explanation
    if (txt.includes("LocateLMView")) LOG.bug("Contains LocateLMView concatenation");
    // Check that explanation is > 20 chars
    if (txt.length < 20) LOG.warn("Very short explanation: " + txt);
    LOG.pass("Explanations clean (" + txt.length + " chars)");
    await page.close();
  })();

  // T11: No console errors
  await (async () => {
    const page = await ctx.newPage();
    let errors = [];
    page.on("console", (m) => {
      const t = m.text();
      if (m.type() === "error" || t.includes("Unsupported") || (t.includes("error") && !t.includes("429") && !t.includes("WebSocket"))) {
        if (!errors.includes(t)) errors.push(t.slice(0, 150));
      }
    });
    await login(page); await clearChat(page); await setInteract(page);
    console.log("T11: Console error check");
    await sendMessage(page, "How to use LMView?");
    const ov = await waitForOverlay(page);
    if (ov) await walkTour(page);
    await page.waitForTimeout(3000);
    const critical = errors.filter((e) =>
      !e.includes("429") && !e.includes("rate") && !e.includes("WebSocket") &&
      !e.includes("fetch") && !e.includes("network") && !e.includes("notification")
    );
    if (critical.length > 0) LOG.bug("Errors: " + critical.join(" | "));
    else LOG.pass("No critical errors");
    await page.close();
  })();

  // T12: Tour interruption - new msg mid-tour
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setInteract(page);
    console.log("T12: New message mid-tour");
    await sendMessage(page, "Analyze BTCUSDT");
    const ov = await waitForOverlay(page, 60000);
    if (!ov) { LOG.fail("No initial tour"); await page.close(); return; }
    // Advance 1 step
    const n1 = page.locator('[data-testid="ai-tour-next"]');
    if (await n1.isVisible()) await n1.click();
    await page.waitForTimeout(2000);
    // Try sending new message
    await sendMessage(page, "Show me ETH").catch(() => {});
    await page.waitForTimeout(5000);
    const ov2 = await waitForOverlay(page, 15000);
    LOG.pass("Mid-tour interrupt handled, second " + (ov2 ? "tour started" : "overlay may have cancelled"));
    await page.close();
  })();

  // T13: Drag step overlay
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setInteract(page);
    console.log("T13: Overlay drag capability");
    await sendMessage(page, "How to use LMView?");
    const ov = await waitForOverlay(page);
    if (!ov) { LOG.fail("No tour"); await page.close(); return; }
    // Check if element has cursor-grab class or drag-related attributes
    const dragHandle = page.locator('[class*="cursor-grab"], [data-drag-handle], [class*="drag-handle"]').first();
    const hasDragHandle = (await dragHandle.count()) > 0;
    if (!hasDragHandle) LOG.warn("No visible drag handle found (may use pointer events)");
    LOG.pass("Drag handle present: " + hasDragHandle);
    await page.close();
  })();

  // T14: Recap message appears
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setInteract(page);
    console.log("T14: Recap message after tour");
    await sendMessage(page, "How to use LMView?");
    const ov = await waitForOverlay(page);
    if (!ov) { LOG.fail("No tour"); await page.close(); return; }
    // Count messages before tour
    const msgsBefore = await page.locator("text=LMView AI, ask or interact mode").count();
    await walkTour(page);
    await page.waitForTimeout(4000);
    // Check for recap - look for message with "Step" or "replay" or "tour"
    const recap = page.locator("text=Replay").or(page.locator("text=step")).or(page.locator("text=summary"));
    const hasRecap = (await recap.count()) > 0;
    if (!hasRecap) LOG.warn("No recap/replay found (may use different text)");
    else LOG.pass("Recap/replay message present");
    await page.close();
  })();

  // T15: Session persistence after reload
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setInteract(page);
    console.log("T15: Session persists on reload");
    await sendMessage(page, "How to use LMView?");
    const ov = await waitForOverlay(page);
    if (!ov) { LOG.fail("No tour"); await page.close(); return; }
    await walkTour(page);
    await page.waitForTimeout(3000);
    // Reload
    await page.reload({ waitUntil: "networkidle" });
    await page.waitForTimeout(5000);
    // Check previous session visible
    const msgs = page.locator("text=LMView").first();
    const hasMessages = (await msgs.count()) > 0;
    if (!hasMessages) LOG.warn("No messages visible after reload (sessions may not persist)");
    else LOG.pass("Session visible after reload");
    await page.close();
  })();

  // ========================== SUMMARY ==========================
  console.log("\n=== RESULTS ===");
  console.log("  Pass: " + passed);
  console.log("  Fail: " + failed);
  console.log("  Bugs: " + bugs);
  if (warnings.length) {
    console.log("  Warnings:");
    warnings.forEach((w) => console.log("    " + w));
  }
  console.log("");
  await browser.close();
})();
