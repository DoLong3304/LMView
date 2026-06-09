import type { TimeframeKey } from "@/types";

export type PatternType =
  | "double_top"
  | "double_bottom"
  | "head_shoulders"
  | "inverse_head_shoulders"
  | "ascending_triangle"
  | "descending_triangle"
  | "symmetrical_triangle"
  | "cup_handle"
  | "wedge_up"
  | "wedge_down"
  | "pennant_bullish"
  | "pennant_bearish"
  | "rectangle_bullish"
  | "rectangle_bearish"
  | "triple_top"
  | "triple_bottom";

export interface DetectedPattern {
  id: string;
  type: PatternType;
  symbol: string;
  timeframe: TimeframeKey;
  confidence: number;
  startTime: number;
  endTime: number;
  startPrice: number;
  endPrice: number;
  targetPrice?: number;
  stopLoss?: number;
  bullish: boolean;
  detectedAt: number;
}

export interface PatternDetectionConfig {
  enabled: boolean;
  minConfidence: number;
  patterns: PatternType[];
  timeframes: TimeframeKey[];
}

export const DEFAULT_PATTERN_CONFIG: PatternDetectionConfig = {
  enabled: true,
  minConfidence: 60,
  patterns: [
    "double_top",
    "double_bottom",
    "ascending_triangle",
    "descending_triangle",
    "head_shoulders",
  ],
  timeframes: ["1h", "4h", "1d"],
};

export const PATTERN_LABELS: Record<PatternType, string> = {
  double_top: "Double Top",
  double_bottom: "Double Bottom",
  head_shoulders: "Head & Shoulders",
  inverse_head_shoulders: "Inverse Head & Shoulders",
  ascending_triangle: "Ascending Triangle",
  descending_triangle: "Descending Triangle",
  symmetrical_triangle: "Symmetrical Triangle",
  cup_handle: "Cup & Handle",
  wedge_up: "Wedge Up",
  wedge_down: "Wedge Down",
  pennant_bullish: "Bullish Pennant",
  pennant_bearish: "Bearish Pennant",
  rectangle_bullish: "Bullish Rectangle",
  rectangle_bearish: "Bearish Rectangle",
  triple_top: "Triple Top",
  triple_bottom: "Triple Bottom",
};

export const PATTERN_BULLISH: Record<PatternType, boolean> = {
  double_top: false,
  double_bottom: true,
  head_shoulders: false,
  inverse_head_shoulders: true,
  ascending_triangle: true,
  descending_triangle: false,
  symmetrical_triangle: false,
  cup_handle: true,
  wedge_up: true,
  wedge_down: false,
  pennant_bullish: true,
  pennant_bearish: false,
  rectangle_bullish: true,
  rectangle_bearish: false,
  triple_top: false,
  triple_bottom: true,
};