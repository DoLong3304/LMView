import { test, expect } from '@playwright/test';

test('merged candle rendering', async ({ page }) => {
  await page.goto('http://localhost:3000');
  // wait for chart element
  const chart = page.locator('[data-testid="candlestick-chart"]');
  await expect(chart).toBeVisible({ timeout: 15000 });
  // get last two candles data attributes (assume they expose via DOM?)
  const candles = await chart.locator('.candle').all();
  const last = candles[candles.length - 1];
  const prev = candles[candles.length - 2];
  // forming candle should have opacity < 1 (e.g., 0.5) and no indicator lines
  await expect(last).toHaveCSS('opacity', '0.5');
  await expect(last.locator('.indicator')).toHaveCount(0);
  // previous closed candle should have opacity 1 and indicator lines present
  await expect(prev).toHaveCSS('opacity', '1');
  await expect(prev.locator('.indicator')).toHaveCountGreaterThan(0);
});
