// Multi-scenario probe of Interact mode
import { chromium } from "playwright";
const log = (m) => console.log(`[p] ${m}`);

const QUERIES = [
  "How to use LMView?",
  "Analyze BTCUSDT current price action",
  "Show me the order book for ETH",
  "Compare Bitcoin and Ethereum on 4H timeframe",
  "Show recent crypto news and explain market impact",
  "Help me set up RSI indicator on SOL 1H",
  "Walk me through the full LMView workflow",
];

async function runQuery(page, query) {
  log(`\n=== QUERY: "${query}" ===`);

  // Clear chat first — this dispatches lmview:ai-clear-chat and
  // should re-show the textarea even after a completed tour.
  await page.evaluate(() => window.dispatchEvent(new CustomEvent("lmview:ai-clear-chat")));
  await page.waitForTimeout(3000);

  // Wait for textarea to become visible (after tour cleanup)
  const ta = page.locator('textarea').first();
  try {
    await ta.waitFor({ state: 'visible', timeout: 30000 });
  } catch {
    // If still hidden, try clicking new chat via the settings
    log("textarea not visible, trying new chat");
    await page.click('header button:has-text("New")').catch(() => {});
    await page.waitForTimeout(2000);
    await ta.waitFor({ state: 'visible', timeout: 15000 });
  }

  // Toggle interact mode
  const toggle = page.locator('button[role="switch"]').first();
  if (await toggle.count() > 0 && await toggle.isVisible()) {
    const checked = await toggle.getAttribute('aria-checked');
    if (checked !== 'true') await toggle.click();
  }
  await page.waitForTimeout(1000);

  // Send - use fill on textarea
  await ta.waitFor({ state: 'visible' });
  await ta.fill(query);
  await page.waitForTimeout(300);
  const sendBtn = page.locator('button:has-text("Send")').first();
  if (await sendBtn.isEnabled()) {
    await sendBtn.click();
    log("sent");
  } else {
    log("send disabled");
    return;
  }

  // Wait for response
  let tourSteps = 0;
  let stepTexts = [];
  for (let i = 0; i < 25; i++) {
    await page.waitForTimeout(2000);
    const overlay = page.locator('[data-testid="ai-tour-overlay"]');
    if (await overlay.count() > 0) {
      const txt = (await overlay.textContent()) || "";
      const m = txt.match(/Step\s+(\d+)\s+of\s+(\d+)/);
      if (m) {
        const stepNum = parseInt(m[1]);
        const total = parseInt(m[2]);
        const cleanTxt = txt.replace(/Step\s+\d+\s+of\s+\d+%\d*/, "").replace(/\s+/g, " ").trim();
        if (stepNum > tourSteps) {
          tourSteps = stepNum;
          stepTexts.push(`Step ${stepNum}/${total}: ${cleanTxt.slice(0, 100)}`);
          log(`step ${stepNum}/${total}: ${cleanTxt.slice(0, 80)}`);
        }
        // Check if we reached the end
        const isLast = stepNum >= total;
        // Check for keep/revert/finish buttons
        const keepBtn = page.locator('[data-testid="ai-tour-keep"]');
        const nextBtn = page.locator('[data-testid="ai-tour-next"]');
        const hasKeep = await keepBtn.count() > 0;
        if (isLast && hasKeep) {
          log(`final step: clicking keep`);
          await keepBtn.click();
          break;
        }
        if (isLast) {
          // Try Finish button (Next/Finish combined)
          if (await nextBtn.isVisible()) {
            const nextText = (await nextBtn.textContent()) || "";
            log(`final: nextBtn text="${nextText.trim()}"`);
            await nextBtn.click();
            break;
          }
          // Last resort: dispatch end-tour event
          log(`final: dispatching end-tour`);
          await page.evaluate(() => {
            window.dispatchEvent(new CustomEvent("lmview:ai-tour-end"));
            window.dispatchEvent(new CustomEvent("lmview:chart-freeze", { detail: { frozen: false } }));
            window.dispatchEvent(new CustomEvent("lmview:ai-clear-highlights"));
          });
          break;
        }
        // Click next for non-last steps
        if (await nextBtn.isVisible()) {
          await nextBtn.click();
          await page.waitForTimeout(500);
        }
      }
    }
  }
  if (tourSteps === 0) log("NO TOUR STARTED");
  // Ensure tour is fully cleaned up before next query
  await page.waitForTimeout(3000);
  return tourSteps;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => log(`PAGEERROR: ${e.message}`));
  const consoleErrors = [];
  page.on("console", (m) => {
    if (m.type() === "error" || m.text().includes("notification") || m.text().includes("toast") || m.text().includes("Unsupported")) {
      const t = m.text();
      if (!consoleErrors.includes(t)) consoleErrors.push(t);
    }
  });

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

  for (const q of QUERIES.slice(0, 3)) {
    await runQuery(page, q);
    await page.waitForTimeout(2000);
  }
  if (consoleErrors.length) {
    log("\n=== CONSOLE ERRORS / NOTIFICATIONS ===");
    // Dedup by normalizing, group by category
    const unsupported = consoleErrors.filter(e => e.includes("Unsupported") || e.includes("error: unsupported"));
    const other = consoleErrors.filter(e => !e.includes("Unsupported") && !e.includes("error: unsupported"));
    if (unsupported.length) {
      // Show unique unsupported types
      const seen = new Set();
      unsupported.forEach(e => {
        const m = e.match(/unsupported[^"']*["']([^"']+)/i);
        if (m && !seen.has(m[1])) { seen.add(m[1]); log(`  unsupported action: "${m[1]}"`); }
      });
    }
    other.slice(0, 10).forEach(e => log(`  other: ${e.slice(0, 150)}`));
  }
  await browser.close();
})();