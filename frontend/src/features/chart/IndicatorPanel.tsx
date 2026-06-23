import React, { useState } from "react";
import { Activity, ChevronDown, ChevronUp, Search } from "lucide-react";
import { useI18n } from "@/i18n";
import type { IndicatorSettings } from "@/types";
import type { TranslationKey } from "@/i18n/translations";

type IndicatorGroup = "trend" | "momentum" | "volatility" | "volume";

export interface IndicatorDef {
  key: string;
  labelKey: TranslationKey;
  group: IndicatorGroup;
  pane: "chart" | "pane" | "volume";
  descriptionKey: TranslationKey;
  available?: boolean;
}

const GROUP_LABEL_KEYS: Record<IndicatorGroup, TranslationKey> = {
  trend: "trend",
  momentum: "momentum",
  volatility: "volatility",
  volume: "volumeIndicators",
};

const PANE_LABEL_KEYS: Record<IndicatorDef["pane"], TranslationKey> = {
  chart: "chartPane",
  pane: "separatePane",
  volume: "volumePane",
};

export const INDICATORS: IndicatorDef[] = [
  { key: "sma20", labelKey: "indicatorSma20", group: "trend", pane: "chart", descriptionKey: "indicatorDescSimpleMovingAverage" },
  { key: "sma50", labelKey: "indicatorSma50", group: "trend", pane: "chart", descriptionKey: "indicatorDescSimpleMovingAverage" },
  { key: "ema12", labelKey: "indicatorEma12", group: "trend", pane: "chart", descriptionKey: "indicatorDescExponentialMovingAverage" },
  { key: "ema26", labelKey: "indicatorEma26", group: "trend", pane: "chart", descriptionKey: "indicatorDescExponentialMovingAverage" },
  { key: "vwap", labelKey: "indicatorVwap", group: "trend", pane: "chart", descriptionKey: "indicatorDescVwap" },
  { key: "ichimoku", labelKey: "indicatorIchimoku", group: "trend", pane: "chart", descriptionKey: "indicatorDescIchimoku" },
  { key: "supertrend", labelKey: "indicatorSupertrend", group: "trend", pane: "chart", descriptionKey: "indicatorDescSupertrend" },
  { key: "psar", labelKey: "indicatorPsar", group: "trend", pane: "chart", descriptionKey: "indicatorDescPsar" },
  { key: "support_resistance", labelKey: "indicatorSupportResistance", group: "trend", pane: "chart", descriptionKey: "indicatorDescSupportResistance" },
  { key: "rsi", labelKey: "indicatorRsi", group: "momentum", pane: "pane", descriptionKey: "indicatorDescRsi" },
  { key: "macd", labelKey: "indicatorMacd", group: "momentum", pane: "pane", descriptionKey: "indicatorDescMacd" },
  { key: "stochastic", labelKey: "indicatorStochastic", group: "momentum", pane: "pane", descriptionKey: "indicatorDescStochastic" },
  { key: "mfi", labelKey: "indicatorMfi", group: "momentum", pane: "pane", descriptionKey: "indicatorDescMfi" },
  { key: "bb", labelKey: "indicatorBollingerBands", group: "volatility", pane: "chart", descriptionKey: "indicatorDescBollingerBands" },
  { key: "atr", labelKey: "indicatorAtr", group: "volatility", pane: "pane", descriptionKey: "indicatorDescAtr" },
  { key: "volume", labelKey: "indicatorVolume", group: "volume", pane: "volume", descriptionKey: "indicatorDescVolume" },
  { key: "volumeMa", labelKey: "indicatorVolumeMa", group: "volume", pane: "volume", descriptionKey: "indicatorDescVolumeMa" },
  { key: "whale_alert", labelKey: "indicatorWhaleAlert", group: "volume", pane: "chart", descriptionKey: "indicatorDescWhaleAlert", available: false },
];

export interface IndicatorPanelStatus {
  loading?: boolean;
  messageKey?: TranslationKey | null;
}

interface IndicatorPanelProps {
  indSettings: Record<string, IndicatorSettings>;
  onChange: (settings: Record<string, IndicatorSettings>) => void;
  status?: IndicatorPanelStatus;
}

const NUMBER_FIELDS: Array<{ key: string; labelKey: TranslationKey; min: number; max: number; step?: number }> = [
  { key: "period", labelKey: "period", min: 1, max: 500 },
  { key: "fastPeriod", labelKey: "fast", min: 1, max: 200 },
  { key: "slowPeriod", labelKey: "slow", min: 1, max: 500 },
  { key: "signalPeriod", labelKey: "signal", min: 1, max: 100 },
  { key: "multiplier", labelKey: "multiplier", min: 0.5, max: 10, step: 0.1 },
  { key: "step", labelKey: "step", min: 0.01, max: 0.2, step: 0.01 },
  { key: "maxStep", labelKey: "maxStep", min: 0.02, max: 0.5, step: 0.01 },
  { key: "conversionPeriod", labelKey: "conversion", min: 1, max: 100 },
  { key: "basePeriod", labelKey: "base", min: 1, max: 200 },
  { key: "spanPeriod", labelKey: "span", min: 1, max: 300 },
  { key: "displacement", labelKey: "displacement", min: 0, max: 100 },
];

const COLOR_FIELDS: Array<{ key: string; labelKey: TranslationKey }> = [
  { key: "color", labelKey: "mainColor" },
  { key: "basisColor", labelKey: "basisColor" },
  { key: "signalColor", labelKey: "signalColor" },
  { key: "baseColor", labelKey: "baseColor" },
  { key: "spanAColor", labelKey: "spanAColor" },
  { key: "spanBColor", labelKey: "spanBColor" },
];

const IndicatorPanel: React.FC<IndicatorPanelProps> = ({ indSettings, onChange, status }) => {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const set = (key: string, field: string, value: unknown) => {
    onChange({
      ...indSettings,
      [key]: { ...indSettings[key], [field]: value },
    });
  };

  const toggleVisible = (key: string) => {
    const indicator = INDICATORS.find((item) => item.key === key);
    if (indicator?.available === false) return;
    const cfg = indSettings[key];
    if (!cfg) return;
    set(key, "visible", !cfg.visible);
  };

  const visibleIndicators = INDICATORS.filter((indicator) => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return true;
    return `${t(indicator.labelKey)} ${t(indicator.descriptionKey)} ${t(GROUP_LABEL_KEYS[indicator.group])}`
      .toLowerCase()
      .includes(normalizedQuery);
  });
  const activeCount = INDICATORS.filter((indicator) => indSettings[indicator.key]?.visible).length;

  return (
    <div className="mt-1 w-[min(320px,calc(100vw-1rem))] overflow-hidden rounded-lg border border-gray-700 bg-gray-850 shadow-2xl">
      <div className="border-b border-gray-700 bg-gray-800 px-3 py-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-200">
            <Activity size={12} /> {t("technicalIndicators")}
          </div>
          <span className="rounded bg-blue-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-blue-300">
            {activeCount} {t("active")}
          </span>
        </div>
        <div className="relative mt-2">
          <Search size={13} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t("searchIndicators")}
            className="h-8 w-full rounded border border-gray-700 bg-gray-900 pl-7 pr-2 text-xs text-gray-200 outline-none transition-colors placeholder:text-gray-600 focus:border-blue-500"
          />
        </div>
        {(status?.loading || status?.messageKey) && (
          <div className={`mt-2 rounded border px-2 py-1.5 text-[10px] ${
            status.loading
              ? "border-blue-500/30 bg-blue-500/10 text-blue-200"
              : "border-amber-500/30 bg-amber-500/10 text-amber-200"
          }`}>
            {status.loading ? t("indicatorLoading") : status.messageKey ? t(status.messageKey) : null}
          </div>
        )}
      </div>

      <div className="max-h-[440px] overflow-y-auto py-1">
        {(["trend", "momentum", "volatility", "volume"] as IndicatorGroup[]).map((group) => {
          const groupIndicators = visibleIndicators.filter((indicator) => indicator.group === group);
          if (groupIndicators.length === 0) return null;

          return (
            <div key={group} className="py-1">
              <div className="px-3 pb-1 pt-2 text-[10px] font-bold uppercase tracking-wide text-gray-500">
                {t(GROUP_LABEL_KEYS[group])}
              </div>
              {groupIndicators.map((indicator) => {
                const cfg = indSettings[indicator.key] || { visible: false };
                const isOpen = expanded === indicator.key;
                const isAvailable = indicator.available !== false;
                return (
                  <div key={indicator.key} className={`border-t border-gray-800 first:border-t-0 ${isAvailable ? "" : "opacity-60"}`}>
                    <button
                      type="button"
                      className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left transition-colors hover:bg-gray-800"
                      onClick={() => setExpanded(isOpen ? null : indicator.key)}
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          {cfg.color && (
                            <span
                              className="h-2.5 w-2.5 flex-shrink-0 rounded-full"
                              style={{ backgroundColor: String(cfg.color) }}
                            />
                          )}
                          <span className="truncate text-xs font-semibold text-gray-200">{t(indicator.labelKey)}</span>
                          <span className="rounded bg-gray-900 px-1.5 py-0.5 text-[10px] uppercase text-gray-500">
                            {t(PANE_LABEL_KEYS[indicator.pane])}
                          </span>
                          {!isAvailable && (
                            <span className="rounded bg-gray-900 px-1.5 py-0.5 text-[10px] text-amber-300">
                              {t("unavailable")}
                            </span>
                          )}
                        </div>
                        <p className="mt-0.5 truncate text-[10px] text-gray-500">{t(indicator.descriptionKey)}</p>
                      </div>
                      <div className="flex flex-shrink-0 items-center gap-1.5">
                        <span
                          role="switch"
                          aria-checked={cfg.visible}
                          aria-disabled={!isAvailable}
                          aria-label={`${t(indicator.labelKey)} ${cfg.visible ? t("active") : t("inactive")}`}
                          title={isAvailable ? (cfg.visible ? t("active") : t("inactive")) : t("indicatorFutureUnavailable")}
                          tabIndex={isAvailable ? 0 : -1}
                          onClick={(event) => {
                            event.stopPropagation();
                            toggleVisible(indicator.key);
                          }}
                          onKeyDown={(event) => {
                            if (event.key === "Enter" || event.key === " ") {
                              event.preventDefault();
                              event.stopPropagation();
                              toggleVisible(indicator.key);
                            }
                          }}
                          className={`h-4 w-8 rounded-full p-0.5 transition-colors ${
                            cfg.visible && isAvailable ? "bg-blue-600" : "bg-gray-600"
                          }`}
                        >
                          <span
                            className={`block h-3 w-3 rounded-full bg-white shadow transition-transform ${
                              cfg.visible && isAvailable ? "translate-x-4" : "translate-x-0"
                            }`}
                          />
                        </span>
                        {isOpen ? <ChevronUp size={12} className="text-gray-400" /> : <ChevronDown size={12} className="text-gray-400" />}
                      </div>
                    </button>

                    {isOpen && (
                      <div className="space-y-2 bg-gray-900 px-3 pb-3 pt-2">
                        {NUMBER_FIELDS.filter(({ key }) => cfg[key] !== undefined).map(({ key, labelKey, min, max, step }) => (
                          <div key={key} className="flex items-center justify-between gap-2">
                            <span className="text-xs text-gray-400">{t(labelKey)}</span>
                            <input
                              type="number"
                              min={min}
                              max={max}
                              step={step ?? 1}
                              value={Number(cfg[key])}
                              onChange={(event) => set(indicator.key, key, Number(event.target.value))}
                              className="h-6 w-20 rounded border border-gray-700 bg-gray-800 px-2 text-right text-xs text-white outline-none focus:border-blue-500"
                            />
                          </div>
                        ))}

                        {COLOR_FIELDS.filter(({ key }) => typeof cfg[key] === "string").map(({ key, labelKey }) => (
                          <div key={key} className="flex items-center justify-between gap-2">
                            <span className="text-xs text-gray-400">{t(labelKey)}</span>
                            <input
                              type="color"
                              value={String(cfg[key])}
                              onChange={(event) => set(indicator.key, key, event.target.value)}
                              className="h-5 w-8 cursor-pointer rounded border-0 bg-transparent"
                            />
                          </div>
                        ))}

                        {cfg.lineWidth !== undefined && (
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs text-gray-400">{t("thickness")}</span>
                            <input
                              type="range"
                              min="0.5"
                              max="4"
                              step="0.5"
                              value={cfg.lineWidth}
                              onChange={(event) => set(indicator.key, "lineWidth", parseFloat(event.target.value))}
                              className="w-24 accent-blue-500"
                            />
                            <span className="w-5 text-right text-xs text-gray-300">{String(cfg.lineWidth)}</span>
                          </div>
                        )}

                        {cfg.overbought !== undefined && (
                          <>
                            <div className="flex items-center justify-between gap-2">
                              <span className="text-xs text-gray-400">{t("overbought")}</span>
                              <input
                                type="number"
                                min="50"
                                max="100"
                                value={Number(cfg.overbought)}
                                onChange={(event) => set(indicator.key, "overbought", Number(event.target.value))}
                                className="h-6 w-20 rounded border border-gray-700 bg-gray-800 px-2 text-right text-xs text-white outline-none focus:border-blue-500"
                              />
                            </div>
                            <div className="flex items-center justify-between gap-2">
                              <span className="text-xs text-gray-400">{t("oversold")}</span>
                              <input
                                type="number"
                                min="0"
                                max="50"
                                value={Number(cfg.oversold)}
                                onChange={(event) => set(indicator.key, "oversold", Number(event.target.value))}
                                className="h-6 w-20 rounded border border-gray-700 bg-gray-800 px-2 text-right text-xs text-white outline-none focus:border-blue-500"
                              />
                            </div>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default IndicatorPanel;
