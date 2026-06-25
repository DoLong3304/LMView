// Failure origin classifier – run after `npm run test:full-ui`
// Analyzes test results JSON to classify each failure as Frontend, Backend,
// DataPipeline, or Infra.
//
// Usage: node classify-failures.mjs <path-to-report.json>

import { readFileSync, existsSync } from "fs";

const reportPath = process.argv[2] || "full-suite-report/.last_run.json";
if (!existsSync(reportPath)) {
  console.error("Report not found:", reportPath);
  console.error("Run `npm run test:full-ui` first, then pass the report path.");
  process.exit(1);
}

const report = JSON.parse(readFileSync(reportPath, "utf-8"));
const results = report.suites?.flatMap((s: any) => s.specs || []) || [];

const classify = (error: string): string => {
  const msg = error.toLowerCase();

  // ── Infra ──
  if (
    msg.includes("timeout") ||
    msg.includes("etimedout") ||
    msg.includes("enotfound") ||
    msg.includes("connection refused") ||
    msg.includes("net::err_connection") ||
    msg.includes("docker") ||
    msg.includes("swarm")
  )
    return "Infra";

  // ── Data pipeline (stale/missing candles) ──
  if (
    msg.includes("stale") ||
    msg.includes("candle") ||
    msg.includes("no data") ||
    msg.includes("price gap") ||
    msg.includes("empty response") ||
    msg.includes("influx") ||
    msg.includes("kafka")
  )
    return "DataPipeline";

  // ── Backend API – malformed response, 500, missing field ──
  if (
    msg.includes("500") ||
    msg.includes("internal server error") ||
    msg.includes("unexpected response") ||
    msg.includes("json") ||
    msg.includes("cannot read property") ||
    msg.includes("undefined") ||
    msg.includes("null") ||
    msg.includes("bad gateway") ||
    msg.includes("502") ||
    msg.includes("503")
  )
    return "Backend";

  // ── Frontend – UI assertion, selector, CSS, React error ──
  if (
    msg.includes("visible") ||
    msg.includes("enabled") ||
    msg.includes("aria") ||
    msg.includes("z-index") ||
    msg.includes("rendering") ||
    msg.includes("not found") ||
    msg.includes("locator") ||
    msg.includes("minified react error") ||
    msg.includes("unexpected token") ||
    msg.includes("assertion")
  )
    return "Frontend";

  // ── Rate limiting ──
  if (msg.includes("429") || msg.includes("rate limit") || msg.includes("too many requests"))
    return "Infra (Rate Limit)";

  return "Unknown";
};

let passed = 0,
  failed = 0;
const byOrigin: Record<string, number> = {};
const details: Array<{ name: string; origin: string; msg: string }> = [];

for (const spec of results) {
  const ok = spec.ok !== false;
  if (ok) {
    passed++;
    continue;
  }
  failed++;
  const errorText = spec.errors?.[0]?.message || spec.err?.message || "No error details";
  const origin = classify(errorText);
  byOrigin[origin] = (byOrigin[origin] || 0) + 1;
  details.push({ name: spec.title || spec.name, origin, msg: errorText.slice(0, 200) });
}

console.log("\n========== FULL UI SUITE RESULTS ==========");
console.log(`  Passed: ${passed}   Failed: ${failed}   Total: ${passed + failed}`);
console.log("── Failure Origin Breakdown ──");
for (const [origin, count] of Object.entries(byOrigin).sort((a, b) => b[1] - a[1])) {
  console.log(`  ${origin}: ${count}`);
}
console.log("── Failure Details ──");
for (const d of details) {
  console.log(`  [${d.origin}] ${d.name}`);
  console.log(`    ${d.msg}`);
}
console.log("==========================================");

// Exit code: non-zero if any real bugs found
const infraCount = (byOrigin["Infra"] || 0) + (byOrigin["Infra (Rate Limit)"] || 0);
const pipelineCount = byOrigin["DataPipeline"] || 0;
const backendCount = byOrigin["Backend"] || 0;
const frontendCount = byOrigin["Frontend"] || 0;

console.log("\n📊 Diagnostic Summary:");
if (frontendCount > 0) console.log("  🔴 Frontend bugs found – check component code");
if (backendCount > 0) console.log("  🟠 Backend API issues found – check API routes");
if (pipelineCount > 0) console.log("  🟡 Data pipeline gaps found – check Kafka/Influx");
if (infraCount > 0) console.log("  🔵 Infra / network issues found – check Docker Swarm health");
if (frontendCount + backendCount + pipelineCount + infraCount === 0)
  console.log("  ✅ No failures classified (all unknown)");
