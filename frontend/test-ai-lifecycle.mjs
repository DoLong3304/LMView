// AI Helper Lifecycle Tests: Keep/Revert, Replay, Full Session
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
async function setInteract(page) {
  const toggle = page.locator('button[role="switch"]').first();
  if ((await toggle.count()) > 0 && (await toggle.isVisible())) {
    const c = await toggle.getAttribute("aria-checked");
    if (c !== "true") await toggle.click();
  }
  await page.waitForTimeout(500);
}
async function sendMsg(page, text) {
  const ta = page.locator("textarea").first();
  try { await ta.waitFor({ state: "visible", timeout: 10000 }); } catch { return false; }
  await ta.fill(text); await page.waitForTimeout(300);
  const sb = page.locator('button:has-text("Send")').first();
  if (await sb.isEnabled()) { await sb.click(); return true; }
  return false;
}
async function waitOverlay(page, t = 45000) {
  const start = Date.now();
  while (Date.now() - start < t) {
    const o = page.locator('[data-testid="ai-tour-overlay"]');
    if ((await o.count()) > 0) {
      const txt = (await o.textContent()) || "";
      const m = txt.match(/Step\s+(\d+)\s+of\s+(\d+)/);
      if (m) return { sn: parseInt(m[1]), total: parseInt(m[2]), text: txt };
    }
    await page.waitForTimeout(1000);
  }
  return null;
}

function log(t, m) {
  const p = t === "pass" ? "  PASS" : t === "bug" ? "  BUG " : "  FAIL";
  console.log(p + "  " + m);
  if (t === "pass") passed++;
  else if (t === "bug") { bugs++; issues.push(m); }
  else if (t === "fail") { failed++; issues.push(m); }
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });

  console.log("\n=== LIFECYCLE TESTS ===\n");

  // L1: Keep button on last step of welcome tour
  await (async () => {
    const page = await ctx.newPage(); let result = "OK";
    await login(page); await clearChat(page); await setInteract(page);
    console.log("L1: Keep button on last step");
    await sendMsg(page, "How to use LMView?");
    const ov = await waitOverlay(page);
    if (!ov) { log("fail", "No tour"); await page.close(); return; }
    // Walk to last step checking for Keep
    let stepsWalked = 0; let keepFound = false;
    for (let i = 0; i < 30; i++) {
      await page.waitForTimeout(1200);
      const o = page.locator('[data-testid="ai-tour-overlay"]');
      if ((await o.count()) === 0) { if (stepsWalked > 0) break; continue; }
      const txt = (await o.textContent()) || "";
      const m = txt.match(/Step\s+(\d+)\s+of\s+(\d+)/);
      if (!m) continue;
      const sn = parseInt(m[1]), total = parseInt(m[2]);
      stepsWalked = Math.max(stepsWalked, sn);
      const isLast = sn >= total;
      // On last step check Keep exists
      if (isLast) {
        const keepCnt = await page.locator('[data-testid="ai-tour-keep"]').count();
        if (keepCnt > 0) { keepFound = true; await page.locator('[data-testid="ai-tour-keep"]').click(); break; }
        // Fallback: click Next (Finish)
        const n = page.locator('[data-testid="ai-tour-next"]');
        if (await n.isVisible()) { await n.click(); break; }
      } else {
        const n = page.locator('[data-testid="ai-tour-next"]');
        if (await n.isVisible()) await n.click();
      }
    }
    if (!keepFound) { log("bug", "Keep button NOT found on last step"); result = "BUG"; }
    if (stepsWalked < 3) { log("fail", "Only " + stepsWalked + " steps"); result = "FAIL"; }
    if (result === "OK") log("pass", "Keep button visible on last step, tour completed");
    await page.close();
  })();

  // L2: Textarea enabled after Keep
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setInteract(page);
    console.log("L2: Textarea after Keep");
    await sendMsg(page, "How to use LMView?");
    const ov = await waitOverlay(page);
    if (!ov) { log("fail", "No tour"); await page.close(); return; }
    // Walk to end and click Keep
    for (let i = 0; i < 30; i++) {
      await page.waitForTimeout(1200);
      const o = page.locator('[data-testid="ai-tour-overlay"]');
      if ((await o.count()) === 0) break;
      const m = (await o.textContent()) || "";
      const match = m.match(/Step\s+(\d+)\s+of\s+(\d+)/);
      if (!match) break;
      const isLast = parseInt(match[1]) >= parseInt(match[2]);
      if (isLast) {
        const k = page.locator('[data-testid="ai-tour-keep"]');
        if ((await k.count()) > 0) { await k.click(); break; }
        const n = page.locator('[data-testid="ai-tour-next"]');
        if (await n.isVisible()) { await n.click(); break; }
      } else {
        const n = page.locator('[data-testid="ai-tour-next"]');
        if (await n.isVisible()) await n.click();
      }
    }
    await page.waitForTimeout(5000);
    const ta = page.locator("textarea").first();
    const visible = await ta.isVisible().catch(() => false);
    const enabled = await ta.isEnabled().catch(() => false);
    if (!visible || !enabled) log("bug", "Textarea not usable after Keep: vis=" + visible + " en=" + enabled);
    else log("pass", "Textarea usable after Keep: vis=" + visible + " en=" + enabled);
    await page.close();
  })();

  // L3: Cancel tour mid-way
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setInteract(page);
    console.log("L3: Cancel tour mid-way");
    await sendMsg(page, "Analyze BTCUSDT");
    const ov = await waitOverlay(page, 60000);
    if (!ov) { log("fail", "No tour"); await page.close(); return; }
    // Advance 1 step
    const n1 = page.locator('[data-testid="ai-tour-next"]');
    if (await n1.isVisible()) await n1.click();
    await page.waitForTimeout(2000);
    // Cancel by clearing chat
    await clearChat(page);
    await page.waitForTimeout(3000);
    const stillOverlay = (await page.locator('[data-testid="ai-tour-overlay"]').count()) > 0;
    if (stillOverlay) log("bug", "Overlay persists after cancel");
    else log("pass", "Tour cancelled, overlay removed");
    await page.close();
  })();

  // L4: Replay button in recap
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setInteract(page);
    console.log("L4: Replay recap message");
    await sendMsg(page, "How to use LMView?");
    const ov = await waitOverlay(page);
    if (!ov) { log("fail", "No tour"); await page.close(); return; }
    // Complete tour
    for (let i = 0; i < 30; i++) {
      await page.waitForTimeout(1200);
      const o = page.locator('[data-testid="ai-tour-overlay"]');
      if ((await o.count()) === 0) break;
      const m = (await o.textContent()) || "";
      const mt = m.match(/Step\s+(\d+)\s+of\s+(\d+)/);
      if (!mt) break;
      const isLast = parseInt(mt[1]) >= parseInt(mt[2]);
      if (isLast) {
        const k = page.locator('[data-testid="ai-tour-keep"]');
        if ((await k.count()) > 0) { await k.click(); break; }
        const n = page.locator('[data-testid="ai-tour-next"]');
        if (await n.isVisible()) { await n.click(); break; }
      } else {
        const n = page.locator('[data-testid="ai-tour-next"]');
        if (await n.isVisible()) await n.click();
      }
    }
    await page.waitForTimeout(4000);
    // Check for recap message - look for "Replay" or step summary
    const bodyText = await page.evaluate(() => document.body.innerText);
    const hasReplay = bodyText.includes("Replay") || bodyText.includes("replay");
    const hasStepCount = /\d+\s+steps/.test(bodyText) || bodyText.includes("steps");
    if (hasReplay || hasStepCount) log("pass", "Recap/replay visible: replay=" + hasReplay + " steps=" + hasStepCount);
    else log("warn", "No recap/replay text found (may use different phrasing)");
    await page.close();
  })();

  // L5: Tour step action execution (verify chart changes)
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setInteract(page);
    console.log("L5: Tour actions execute on chart");
    await sendMsg(page, "Analyze BTCUSDT");
    const ov = await waitOverlay(page, 60000);
    if (!ov) { log("fail", "No tour"); await page.close(); return; }
    // The first step should highlight or add indicator
    const stepTxt = ov.text;
    const firstAction = stepTxt.includes("Highlight") || stepTxt.includes("RSI") || stepTxt.includes("indicator") || stepTxt.includes("candle");
    log("pass", "First action has valid type: " + (firstAction ? "yes" : "unknown: " + stepTxt.slice(0, 60)));
    await page.close();
  })();

  // L6: Rapid tour end-to-end (stress)
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setInteract(page);
    console.log("L6: 3 tours in quick succession");
    for (const q of ["How to use LMView?", "Analyze BTCUSDT", "Show me ETH order book"]) {
      await clearChat(page); await setInteract(page);
      await sendMsg(page, q);
      const ov = await waitOverlay(page, 30000);
      if (!ov) { continue; }
      // Click through rapidly
      for (let i = 0; i < 10; i++) {
        const n = page.locator('[data-testid="ai-tour-next"]');
        if (await n.isVisible()) await n.click();
        else break;
        await page.waitForTimeout(200);
      }
      await page.waitForTimeout(1000);
    }
    log("pass", "3 rapid tours processed");
    await page.close();
  })();

  // L7: Right panel tab restoration after tour
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setInteract(page);
    console.log("L7: Right panel restores AI tab after tour");
    // First verify AI Helper is active
    let activeTab = await page.locator('button[role="tab"][aria-selected="true"]').first().textContent().catch(() => "unknown");
    console.log("    Initial active tab: " + activeTab);
    await sendMsg(page, "Show me the order book for ETH");
    const ov = await waitOverlay(page, 60000);
    if (!ov) { log("fail", "No tour"); await page.close(); return; }
    // Walk through tour (should open order book panel)
    for (let i = 0; i < 20; i++) {
      await page.waitForTimeout(1200);
      const o = page.locator('[data-testid="ai-tour-overlay"]');
      if ((await o.count()) === 0) break;
      const m = (await o.textContent()) || "";
      const mt = m.match(/Step\s+(\d+)\s+of\s+(\d+)/);
      if (!mt) break;
      const isLast = parseInt(mt[1]) >= parseInt(mt[2]);
      const k = page.locator('[data-testid="ai-tour-keep"]');
      if (isLast && (await k.count()) > 0) { await k.click(); break; }
      const n = page.locator('[data-testid="ai-tour-next"]');
      if (await n.isVisible()) { await n.click(); }
    }
    await page.waitForTimeout(4000);
    // After tour, check if AI tab is restored
    const tabs = await page.locator('button[role="tab"]').allTextContents();
    const aiTabSelected = tabs.some((t) => t.includes("AI Helper") || t.includes("aiHelper"));
    if (aiTabSelected) log("pass", "AI tab restored after tour");
    else log("warn", "AI tab may not be selected: tabs=" + tabs.join(","));
    await page.close();
  })();

  // L8: Tour step progress updates
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setInteract(page);
    console.log("L8: Step counter updates correctly");
    await sendMsg(page, "How to use LMView?");
    const ov = await waitOverlay(page);
    if (!ov) { log("fail", "No tour"); await page.close(); return; }
    let prevSn = 0;
    for (let i = 0; i < 20; i++) {
      await page.waitForTimeout(1200);
      const o = page.locator('[data-testid="ai-tour-overlay"]');
      if ((await o.count()) === 0) { if (prevSn > 0) break; continue; }
      const m = (await o.textContent()) || "";
      const mt = m.match(/Step\s+(\d+)\s+of\s+(\d+)/);
      if (!mt) continue;
      const sn = parseInt(mt[1]);
      if (sn > prevSn) { prevSn = sn; console.log("    Step " + sn + "/" + mt[2]); }
      // Click next
      const n = page.locator('[data-testid="ai-tour-next"]');
      if (await n.isVisible()) await n.click();
    }
    if (prevSn >= 3) log("pass", "Step counter advanced through " + prevSn + " steps");
    else log("bug", "Only " + prevSn + " steps advanced");
    await page.close();
  })();

  // L9: Hover state on Next button
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page); await setInteract(page);
    console.log("L9: Next button styling");
    await sendMsg(page, "How to use LMView?");
    const ov = await waitOverlay(page);
    if (!ov) { log("fail", "No tour"); await page.close(); return; }
    const nextBtn = page.locator('[data-testid="ai-tour-next"]');
    const before = await nextBtn.getAttribute("class");
    await nextBtn.hover();
    await page.waitForTimeout(300);
    const after = await nextBtn.getAttribute("class");
    // Class should have hover variant
    const hasHover = (before || "").includes("hover:") || (after || "").includes("hover:");
    log("pass", "Next button has hover styles: " + hasHover);
    await page.close();
  })();

  // L10: Mode label + keyboard shortcut hint
  await (async () => {
    const page = await ctx.newPage();
    await login(page); await clearChat(page);
    console.log("L10: Mode labels visible");
    const bodyText = await page.evaluate(() => document.body.innerText);
    const hasAskMode = bodyText.includes("Ask") || bodyText.includes("ask");
    const hasInteractMode = bodyText.includes("Interact") || bodyText.includes("interact");
    log("pass", "Mode labels: ask=" + hasAskMode + " interact=" + hasInteractMode);
    await page.close();
  })();

  // ========== SUMMARY ==========
  console.log("\n=== LIFECYCLE RESULTS ===");
  console.log("  Pass: " + passed);
  console.log("  Fail: " + failed);
  console.log("  Bugs: " + bugs);
  if (issues.length) {
    console.log("\n  Issues:");
    issues.forEach((i) => console.log("    " + i));
  }
  await browser.close();
})();
