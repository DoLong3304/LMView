// AI Helper ASK Mode Tests
import { chromium } from "playwright";
const log = (m) => console.log("[test]", m);
const URL = "https://lmview.duckdns.org";
const ADM = { email: "admin@example.com", pw: "Admin@1234" };
let passed = 0, failed = 0, bugs = 0;
const issues = [];

async function login(page) {
  await page.goto(URL, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);
  const lb = page.locator('button:has-text("Login")').first();
  if ((await lb.count()) > 0 && (await lb.isVisible())) {
    await lb.click();
    await page.waitForTimeout(1000);
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
    const checked = await toggle.getAttribute("aria-checked");
    if ((checked === "true") !== (mode === "interact")) await toggle.click();
  }
  await page.waitForTimeout(500);
}

async function sendAndWait(page, text, timeoutMs = 45000) {
  const ta = page.locator("textarea").first();
  try { await ta.waitFor({ state: "visible", timeout: 10000 }); } catch { return null; }
  await ta.fill(text);
  await page.waitForTimeout(300);
  const sb = page.locator('button:has-text("Send")').first();
  if (!(await sb.isEnabled())) return "disabled";
  // Count existing messages so we wait for a NEW one
  const beforeCount = await page.locator('[data-testid^="ai-message-"]').count();
  await sb.click();
  // Wait for response
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const msgs = page.locator('[data-testid^="ai-message-"]');
    const n = await msgs.count();
    if (n > beforeCount) {
      const t = (await msgs.last().textContent()) || "";
      if (t.trim() && !t.includes("\u2026") && !t.includes("Progressing")) return t;
    }
    await page.waitForTimeout(1000);
  }
  return null;
}

async function test(page, name, fn) {
  process.stdout.write(`  ${name}... `);
  try {
    const r = await fn(page);
    if (r.ok) { log("PASS  " + r.detail); passed++; }
    else if (r.bug) { log("BUG   " + r.detail); bugs++; issues.push({ name, detail: r.detail }); }
    else { log("FAIL  " + r.detail); failed++; issues.push({ name, detail: r.detail }); }
  } catch (e) { log("FAIL  EXCEPTION: " + e.message.slice(0, 150)); failed++; }
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });

  // ASK MODE TESTS
  log("\n--- ASK MODE ---");

  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await test(page, "T1: 'What is RSI?'", async (p) => {
      await clearChat(p); await setMode(p, "ask");
      const r = await sendAndWait(p, "What is RSI?");
      if (!r) return { ok: false, detail: "No reply" };
      if (!/RSI|Relative Strength|momentum|overbought|oversold/i.test(r))
        return { bug: true, detail: "Lacks RSI explanation: " + r.slice(0, 100) };
      return { ok: true, detail: "RSI explanation received" };
    });
    await page.close();
  })();

  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await test(page, "T2: 'BTC price?'", async (p) => {
      await clearChat(p); await setMode(p, "ask");
      const r = await sendAndWait(p, "What is the current price of Bitcoin?", 60000);
      if (!r) return { ok: false, detail: "No reply" };
      if (!/[0-9]/.test(r)) return { bug: true, detail: "No numbers in reply" };
      return { ok: true, detail: "Price response received" };
    });
    await page.close();
  })();

  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await test(page, "T3: 'SOL trend 4H'", async (p) => {
      await clearChat(p); await setMode(p, "ask");
      const r = await sendAndWait(p, "Analyze the trend for SOL on 4H timeframe", 90000);
      if (!r) return { ok: false, detail: "No reply (timeout)" };
      return { ok: true, detail: "Analysis received (" + r.length + " chars)" };
    });
    await page.close();
  })();

  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await test(page, "T4: 'ETH support/resistance'", async (p) => {
      await clearChat(p); await setMode(p, "ask");
      const r = await sendAndWait(p, "What support/resistance levels for ETH?", 90000);
      if (!r) return { ok: false, detail: "No reply" };
      if (!/support|resistance/i.test(r))
        return { bug: true, detail: "No levels: " + r.slice(0, 100) };
      return { ok: true, detail: "S/R analysis received" };
    });
    await page.close();
  })();

  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await test(page, "T5: Empty input disabled", async (p) => {
      await clearChat(p); await setMode(p, "ask");
      const ta = p.locator("textarea").first();
      await ta.waitFor({ state: "visible" });
      await ta.fill("");
      await p.waitForTimeout(300);
      const sb = p.locator('button:has-text("Send")').first();
      const disabled = !(await sb.isEnabled());
      return disabled
        ? { ok: true, detail: "Send disabled on empty" }
        : { bug: true, detail: "Send enabled with empty input" };
    });
    await page.close();
  })();

  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await test(page, "T6: 'hi' greeting", async (p) => {
      await clearChat(p); await setMode(p, "ask");
      const r = await sendAndWait(p, "hi", 30000);
      if (!r) return { ok: false, detail: "No reply" };
      return { ok: true, detail: "Greeting replied" };
    });
    await page.close();
  })();

  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await test(page, "T7: Non-crypto 'weather'", async (p) => {
      await clearChat(p); await setMode(p, "ask");
      const r = await sendAndWait(p, "What's the weather like today?", 45000);
      if (!r) return { ok: false, detail: "No reply" };
      if (!/sorry|cannot|unable|crypto|trading|chart|indicator|cant/i.test(r))
        return { bug: true, detail: "No scope disclaimer: " + r.slice(0, 100) };
      return { ok: true, detail: "Politely declined" };
    });
    await page.close();
  })();

  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await test(page, "T8: Gibberish input", async (p) => {
      await clearChat(p); await setMode(p, "ask");
      const r = await sendAndWait(p, "xylophone42@#$% banana quantum", 45000);
      if (!r) return { ok: false, detail: "No reply" };
      return { ok: true, detail: "Gibberish handled without crash" };
    });
    await page.close();
  })();

  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await test(page, "T9: Long message", async (p) => {
      await clearChat(p); await setMode(p, "ask");
      const long = "Tell me about Bitcoin. ".repeat(100).slice(0, 2000);
      const r = await sendAndWait(p, long, 60000);
      if (!r) return { ok: false, detail: "No reply" };
      return { ok: true, detail: "Long msg handled (" + r.length + " chars)" };
    });
    await page.close();
  })();

  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await test(page, "T10: Rapid 3 messages", async (p) => {
      await clearChat(p); await setMode(p, "ask");
      for (const q of ["What is BTC?", "What is ETH?", "What is SOL?"]) {
        const ta = p.locator("textarea").first();
        await ta.fill(q);
        await p.waitForTimeout(200);
        const sb = p.locator('button:has-text("Send")').first();
        if (await sb.isEnabled()) await sb.click();
        await p.waitForTimeout(500);
      }
      const r = await sendAndWait(p, "What is the last one?", 60000);
      if (!r) return { bug: true, detail: "No reply to rapid (rate-limited?)" };
      return { ok: true, detail: "Rapid messages handled" };
    });
    await page.close();
  })();

  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await test(page, "T11: Ask mode - session persistence", async (p) => {
      await clearChat(p); await setMode(p, "ask");
      const r1 = await sendAndWait(p, "What is MACD?", 45000);
      if (!r1) return { ok: false, detail: "No first reply" };
      // Reload and check messages persist
      await p.reload({ waitUntil: "networkidle" });
      await p.waitForTimeout(3000);
      const msgs = p.locator('[data-testid^="ai-message-"]');
      const n = await msgs.count();
      return n > 0
        ? { ok: true, detail: n + " messages after reload" }
        : { bug: true, detail: "No messages after reload" };
    });
    await page.close();
  })();

  await (async () => {
    const page = await ctx.newPage();
    await login(page);
    await test(page, "T12: Switch ask to interact mid-session", async (p) => {
      await clearChat(p); await setMode(p, "ask");
      await sendAndWait(p, "What is RSI?", 30000);
      await setMode(p, "interact");
      await clearChat(p); await setMode(p, "interact");
      const r = await sendAndWait(p, "How to use LMView?", 60000);
      // Check if overlay appears
      let overlay = false;
      for (let i = 0; i < 15; i++) {
        const o = p.locator('[data-testid="ai-tour-overlay"]');
        if ((await o.count()) > 0) { overlay = true; break; }
        await p.waitForTimeout(2000);
      }
      return overlay
        ? { ok: true, detail: "Mode switch OK, tour started" }
        : { bug: true, detail: "No tour after mode switch" };
    });
    await page.close();
  })();

  // SUMMARY
  console.log("\n--- RESULTS ---");
  console.log("  Pass: " + passed + "  Fail: " + failed + "  Bugs: " + bugs);
  for (const i of issues) {
    console.log("  " + (i.detail.startsWith("BUG") ? "[BUG]" : "[FAIL]") + " " + i.name + ": " + i.detail);
  }
  await browser.close();
})();
