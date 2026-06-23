import type { ActionHandler } from "./index";

/**
 * Fetch historical candles for the requested market + timeframe.
 * @param ctx.args.symbol     Optional; defaults to current.
 * @param ctx.args.timeframe  Optional; defaults to current.
 * @param ctx.args.start_ms   Required (unix ms).
 * @param ctx.args.end_ms     Required (unix ms).
 * @param ctx.args.limit      Optional; default 100.
 */
export const handleFetchHistoricalPrices: ActionHandler = async ({
  runtime,
  fetchHistoricalCandles,
  args,
}) => {
  const symbol = String(args.symbol || runtime.selectedSymbol || "BTCUSDT").toUpperCase();
  const timeframe = String(args.timeframe || runtime.currentTimeframe || "1h");
  if (timeframe === "1s") {
    return "error: 1s historical candles are not supported. Use live mode or choose 1m+.";
  }
  const startMs = Number(args.start_ms);
  const endMs = Number(args.end_ms);
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs)) {
    return "error: 'start_ms' and 'end_ms' are required (unix ms)";
  }
  const limit = Number(args.limit ?? 100);
  const candles = await fetchHistoricalCandles(symbol, startMs, endMs, limit, timeframe);
  runtime.setSymbol?.(symbol);
  runtime.setTimeframe?.(timeframe as never);
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("lmview:historical-query-result", {
      detail: { symbol, timeframe, startMs, endMs, limit, candles },
    }));
  }
  return `success: fetched ${candles.length} ${timeframe} candles for ${symbol}`;
};
