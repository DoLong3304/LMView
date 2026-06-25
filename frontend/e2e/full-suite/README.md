# Full Frontend UI/UX Test Suite

Validates all user‑facing interactions across device sizes and edge cases.

## Run

```bash
cd frontend
npm run test:full-ui
```

Uses `e2e/full-suite/playwright.config.ts` (no retries, longer timeouts, chromium only).

## Report

After run:
```bash
npx playwright show-report full-suite-report
```

## Failure Classification

```bash
node scripts/classify-failures.mjs full-suite-report/.last_run.json
```

Each failure is tagged `Frontend`, `Backend`, `DataPipeline` or `Infra`.

## Structure

| File | Scope |
|---|---|
| `auth.spec.ts` | Login, logout, token, invalid creds |
| `layout.spec.ts` | Header, sidebar, right panel, theme |
| `chart.spec.ts` | Candles, timeframes, type switch, indicators, OHLCV |
| `ai-helper-ask.spec.ts` | Ask mode EN/VN, mode switch |
| `ai-helper-interact.spec.ts` | Tours (welcome, analysis, order‑book, compare), step nav, interruption, recap, textarea recovery |
| `watchlist.spec.ts` | Add/remove symbols, empty state |
| `market.spec.ts` | Market overview, price ticker, change % |
| `export.spec.ts` | Export chart, download |
| `responsive.spec.ts` | Re‑runs core flows on 375px / 768px / 1440px |
| `edge-cases.spec.ts` | Slow 3G, 429/500/403, rapid flood, locale switch, empty data, long session, settings, browser back |

## Adding Tests

1. Create `*.spec.ts` in this directory.
2. Import helpers from `./utils.ts`.
3. Run `npm run test:full-ui`.
