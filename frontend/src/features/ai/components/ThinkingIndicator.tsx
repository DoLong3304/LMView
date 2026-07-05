/**
 * ThinkingIndicator — animated "Thinking…" with cycling educational facts.
 *
 * During LLM response generation, shows animated dots + a rotating fact
 * about the project, TA, or crypto to keep users engaged.
 * Disappears when the answer arrives.
 */
import React, { useEffect, useState } from "react";
import { Bot, Lightbulb, Loader2 } from "lucide-react";

const FACTS: string[] = [
  "RSI above 70 = overbought; below 30 = oversold — but can stay extended in strong trends.",
  "MACD crossover = momentum shift. Histogram shrinking = momentum fading.",
  "Bollinger Bands: price touching upper band ≠ sell signal — trends can ride the band.",
  "Volume confirms price. Breakout on low volume = false breakout risk.",
  "Support/resistance levels are zones, not exact lines — expect some slippage.",
  "Higher timeframe trends (4H/1D) dominate lower timeframe (5m/15m) moves.",
  "Fibonacci retracement levels (0.382, 0.5, 0.618) are common reversal zones — not magic.",
  "Divergence between price and oscillators (RSI, MACD) often precedes reversals.",
  "Candlestick patterns: doji after uptrend = potential reversal, hammer at support = bounce.",
  "Order book imbalance > 0.3 = buy pressure; < -0.3 = sell pressure.",
  "LMView uses real-time Kafka streams for sub-second candle updates.",
  "AI runs as a standalone LangGraph DAG — 6 parallel experts feed one LLM call.",
  "Knowledge base has 23 sources, 28 documents, 1500+ chunks via pgvector hybrid search.",
  "LMView supports 8 timeframes from 1-second to 1-week tick resolution.",
  "Iceberg lakehouse stores years of tick history on MinIO/S3.",
  "Trino SQL engine queries both real-time and historical data through one endpoint.",
  "Redis Sentinel cluster provides high-availability market data cache.",
  "OKX exchange support is built but opt-in — set ENABLE_OKX=true to activate.",
  "Market data comes from Binance WebSocket streams with automatic reconnection.",
  "Dagster orchestrates batch backfills and historical data processing pipelines.",
];

interface ThinkingIndicatorProps {
  /** True while the LLM is generating */
  active: boolean;
}

const ThinkingIndicator: React.FC<ThinkingIndicatorProps> = ({ active }) => {
  const [factIdx, setFactIdx] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (active) {
      setVisible(true);
      // Pick a random start fact
      setFactIdx(Math.floor(Math.random() * FACTS.length));
      return;
    }
    // Brief delay before hiding so transition is smooth
    const t = setTimeout(() => setVisible(false), 300);
    return () => clearTimeout(t);
  }, [active]);

  // Rotate facts every 4 seconds
  useEffect(() => {
    if (!active) return;
    const interval = setInterval(() => {
      setFactIdx((prev) => (prev + 1) % FACTS.length);
    }, 4000);
    return () => clearInterval(interval);
  }, [active]);

  if (!visible) return null;

  return (
    <div
      className={`flex justify-start gap-2 transition-opacity duration-200 ${
        active ? "opacity-100" : "opacity-0"
      }`}
    >
      <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded bg-blue-500/10 text-blue-300">
        <Bot size={13} />
      </div>
      <div className="flex-1">
        <div className="rounded border border-gray-800 bg-gray-850 px-3 py-2 text-xs text-gray-400">
          <span className="inline-flex items-center gap-2">
            <Loader2 size={14} className="animate-spin" />
            {'Thinking'}
            <span className="inline-flex">
              <span className="animate-bounce" style={{ animationDelay: "0ms", animationDuration: "1.2s" }}>.</span>
              <span className="animate-bounce" style={{ animationDelay: "200ms", animationDuration: "1.2s" }}>.</span>
              <span className="animate-bounce" style={{ animationDelay: "400ms", animationDuration: "1.2s" }}>.</span>
            </span>
          </span>
        </div>
        <div className="mt-1.5 flex items-start gap-1.5 rounded border border-dashed border-gray-800 bg-gray-850/50 px-2.5 py-1.5">
          <Lightbulb size={12} className="mt-0.5 flex-shrink-0 text-amber-400" />
          <p className="text-[10px] leading-relaxed text-gray-500 animate-pulse">
            {FACTS[factIdx]}
          </p>
        </div>
      </div>
    </div>
  );
};

export { ThinkingIndicator, FACTS };
