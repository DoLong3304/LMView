import type { PriceAlert, AlertType } from "@/types/alerts";
import { saveToStorage, loadFromStorage } from "@/utils/storageHelpers";

const ALERTS_STORAGE_KEY = "app_price_alerts";

export function loadAlerts(): PriceAlert[] {
  return loadFromStorage<PriceAlert[]>(ALERTS_STORAGE_KEY, []);
}

export function saveAlerts(alerts: PriceAlert[]): void {
  saveToStorage(ALERTS_STORAGE_KEY, alerts);
}

export function createAlert(
  symbol: string,
  type: AlertType,
  value: number,
  note?: string
): PriceAlert {
  const alert: PriceAlert = {
    id: `alert-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    symbol,
    type,
    value,
    enabled: true,
    triggered: false,
    createdAt: Date.now(),
    note,
  };
  const alerts = loadAlerts();
  alerts.push(alert);
  saveAlerts(alerts);
  return alert;
}

export function deleteAlert(id: string): void {
  const alerts = loadAlerts().filter((a) => a.id !== id);
  saveAlerts(alerts);
}

export function toggleAlert(id: string): void {
  const alerts = loadAlerts().map((a) =>
    a.id === id ? { ...a, enabled: !a.enabled } : a
  );
  saveAlerts(alerts);
}

export function checkAlerts(
  symbol: string,
  currentPrice: number,
  prevPrice: number,
  volume24h: number,
  prevVolume24h: number,
  rsi14?: number
): PriceAlert[] {
  const alerts = loadAlerts();
  const triggered: PriceAlert[] = [];

  for (const alert of alerts) {
    if (alert.symbol !== symbol || !alert.enabled || alert.triggered) continue;

    let isTriggered = false;
    switch (alert.type) {
      case "price_above":
        isTriggered = currentPrice >= alert.value;
        break;
      case "price_below":
        isTriggered = currentPrice <= alert.value;
        break;
      case "percent_change":
        if (prevPrice > 0) {
          const pctChange = ((currentPrice - prevPrice) / prevPrice) * 100;
          isTriggered = Math.abs(pctChange) >= alert.value;
        }
        break;
      case "volume_spike":
        if (prevVolume24h > 0) {
          const volChange = ((volume24h - prevVolume24h) / prevVolume24h) * 100;
          isTriggered = volChange >= alert.value;
        }
        break;
      case "rsi_above":
        isTriggered = rsi14 !== undefined && rsi14 >= alert.value;
        break;
      case "rsi_below":
        isTriggered = rsi14 !== undefined && rsi14 <= alert.value;
        break;
    }

    if (isTriggered) {
      const updated = { ...alert, triggered: true, triggeredAt: Date.now() };
      triggered.push(updated);
    }
  }

  if (triggered.length > 0) {
    const updatedAlerts = alerts.map((a) => {
      const t = triggered.find((t) => t.id === a.id);
      return t ?? a;
    });
    saveAlerts(updatedAlerts);
  }

  return triggered;
}

export function clearTriggeredAlerts(): void {
  const alerts = loadAlerts().map((a) => ({ ...a, triggered: false, triggeredAt: undefined }));
  saveAlerts(alerts);
}