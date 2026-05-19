// Design tokens cho toàn app — Pure Black Theme

export const tradingTheme = {
  // Background layers — PURE BLACK
  bgPrimary: "#000000",
  bgSecondary: "#0a0a0a",
  bgTertiary: "#141414",
  bgElevated: "#1a1a1a",

  // Text hierarchy
  textPrimary: "#ffffff",
  textSecondary: "#b0b0b0",
  textMuted: "#666666",

  // Trading colors — bright on black
  green: "#00c853",
  red: "#ff1744",

  // Candle colors
  candleUpColor: "#00c853",
  candleDownColor: "#ff1744",
  candleBorderUpColor: "#00c853",
  candleBorderDownColor: "#ff1744",
  candleWickUpColor: "#00c853",
  candleWickDownColor: "#ff1744",

  // Volume histogram
  volumeUp: "rgba(0, 200, 83, 0.5)",
  volumeDown: "rgba(255, 23, 68, 0.5)",

  // Grid & borders — subtle on black
  gridColor: "#1a1a1a",
  borderColor: "#222222",

  // Scale colors
  priceScaleText: "#b0b0b0",
  timeScaleText: "#b0b0b0",
  crosshair: "#555555",
  crosshairLabelBg: "#1a1a1a",

  // Accent
  accent: "#ffffff",
} as const;

export type TradingTheme = typeof tradingTheme;
