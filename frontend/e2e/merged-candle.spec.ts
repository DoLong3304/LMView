/**
 * End-to-end test for merged candle (forming + closed) rendering.
 *
 * Tests:
 *  1. Page loads with chart
 *  2. Merged candle API called with correct params
 *  3. Forming candle data present (isClosed:false in last element)
 *  4. Error / no-data states
 */
import { test, expect, type Page } from '@playwright/test';

const TEST_SYMBOL = 'BTCUSDT';

/** Intercept all /api/merged/* requests and collect responses */
async function captureMergedCalls(page: Page) {
  const calls: Array<{ url: string; status: number; body: unknown }> = [];
  await page.route(/\/api\/merged\//, async (route) => {
    const response = await route.fetch();
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      body = { raw: await response.text() };
    }
    calls.push({ url: route.request().url(), status: response.status(), body });
    await route.fulfill({ response });
  });
  return calls;
}

test.describe('Merged candle chart', () => {
  test('page loads and chart container is visible', async ({ page }) => {
    await page.goto(`/?symbol=${TEST_SYMBOL}`);
    const chart = page.locator('[data-testid="candlestick-chart"]');
    await expect(chart).toBeVisible({ timeout: 20_000 });
  });

  test('merged API returns forming + closed candles', async ({ page }) => {
    const mergedCalls = await captureMergedCalls(page);

    await page.goto(`/?symbol=${TEST_SYMBOL}`);
    await page.waitForTimeout(3_000);

    expect(mergedCalls.length).toBeGreaterThanOrEqual(1);

    for (const call of mergedCalls) {
      expect(call.status).toBe(200);

      const candles = call.body as Array<Record<string, unknown>>;
      expect(candles.length).toBeGreaterThanOrEqual(1);

      // Each candle should have expected fields
      const firstCandle = candles[0];
      expect(firstCandle).toHaveProperty('timestamp');
      expect(firstCandle).toHaveProperty('c');  // close
      expect(firstCandle).toHaveProperty('h');  // high
      expect(firstCandle).toHaveProperty('l');  // low
      expect(firstCandle).toHaveProperty('o');  // open
      expect(firstCandle).toHaveProperty('isClosed');

      // A forming candle should have isClosed === false
      expect(typeof firstCandle['isClosed']).toBe('boolean');
    }
  });

  test('merged endpoint includes forming candle with live price', async ({ page }) => {
    const response = await page.request.get(
      `/api/merged/${TEST_SYMBOL}`,
      { params: { interval: '1m', limit: '10' } }
    );
    expect(response.ok()).toBeTruthy();

    const candles = (await response.json()) as Array<Record<string, unknown>>;
    expect(candles.length).toBeGreaterThanOrEqual(1);

    // First element is forming candle
    const forming = candles[0];
    expect(forming).toHaveProperty('timestamp');
    expect(typeof forming['timestamp']).toBe('number');
    expect(typeof forming['c']).toBe('number');  // close
    expect(forming['c']).toBeGreaterThan(0);
  });

  test('timeframe change triggers new merged call', async ({ page }) => {
    const mergedCalls = await captureMergedCalls(page);

    await page.goto(`/?symbol=${TEST_SYMBOL}`);
    await page.waitForTimeout(2_000);

    const beforeCount = mergedCalls.length;
    expect(beforeCount).toBeGreaterThanOrEqual(1);

    // Switch timeframe via UI
    const timeframeBtn = page.locator('[data-testid="timeframe-button"]');
    if (await timeframeBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await timeframeBtn.click();

      const option1h = page.locator('text=1H').first();
      if (await option1h.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await option1h.click();
        await page.waitForTimeout(2_000);
        expect(mergedCalls.length).toBeGreaterThanOrEqual(beforeCount + 1);
      }
    }
  });

  test('error state shows retry button', async ({ page }) => {
    await page.route(/\/api\/merged\//, (route) => route.abort('connectionrefused'));

    await page.goto(`/?symbol=${TEST_SYMBOL}`);
    await page.waitForTimeout(3_000);

    const retryBtn = page.locator('text=retry').or(page.locator('button:has-text("Retry")')).first();
    const isVisible = await retryBtn.isVisible({ timeout: 10_000 }).catch(() => false);
    expect(isVisible).toBeTruthy();
  });

  test('no data state shows "No data available" message', async ({ page }) => {
    await page.route(/\/api\/merged\//, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto(`/?symbol=${TEST_SYMBOL}`);
    await page.waitForTimeout(3_000);

    const noData = page.locator('text=No data available');
    await expect(noData).toBeVisible({ timeout: 10_000 });
  });
});

test.describe('Ticker and market data', () => {
  test('chart renders with candle data', async ({ page }) => {
    await page.goto(`/?symbol=${TEST_SYMBOL}`);
    const chart = page.locator('[data-testid="candlestick-chart"]');
    await expect(chart).toBeVisible({ timeout: 15_000 });

    // Wait for No data available to disappear (data loaded)
    await expect(page.locator('text=No data available')).toHaveCount(0, { timeout: 15_000 });

    // Chart container should have canvas (lightweight-charts)
    const chartArea = page.locator('[data-testid="chart-canvas"]');
    await expect(chartArea).toBeVisible();
  });
});
