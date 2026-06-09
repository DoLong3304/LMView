export type AlertType =
  | "price_above"
  | "price_below"
  | "percent_change"
  | "volume_spike"
  | "rsi_above"
  | "rsi_below";

export interface PriceAlert {
  id: string;
  symbol: string;
  type: AlertType;
  value: number;
  enabled: boolean;
  triggered: boolean;
  triggeredAt?: number;
  createdAt: number;
  note?: string;
}

export interface AlertCondition {
  type: AlertType;
  value: number;
  label: string;
}

export const ALERT_TYPES: AlertCondition[] = [
  { type: "price_above", value: 0, label: "Price above" },
  { type: "price_below", value: 0, label: "Price below" },
  { type: "percent_change", value: 5, label: "Change %" },
  { type: "volume_spike", value: 200, label: "Volume spike %" },
  { type: "rsi_above", value: 70, label: "RSI above" },
  { type: "rsi_below", value: 30, label: "RSI below" },
];