import React from "react";
import { useI18n } from "@/i18n";
import type { ChartType, ChartTypeSettings } from "@/types";

interface ChartTypeSettingsModalProps {
  type: ChartType;
  settings: ChartTypeSettings;
  onChange: (settings: ChartTypeSettings) => void;
  onClose: () => void;
}

const ChartTypeSettingsModal: React.FC<ChartTypeSettingsModalProps> = ({
  type,
  settings,
  onChange,
  onClose,
}) => {
  const { t } = useI18n();
  const set = (key: keyof ChartTypeSettings, value: unknown) =>
    onChange({ ...settings, [key]: value });

  const renderSettings = () => {
    switch (type) {
      case "renko":
        return (
          <>
            <div className="mb-4">
              <label className="block text-sm mb-2 text-gray-300">
                {t("brickSizeType") || "Brick Size Type"}
              </label>
              <div className="flex gap-3">
                <button
                  onClick={() => set("brickSizeType", "fixed")}
                  className={`px-3 py-1.5 text-xs rounded transition-colors ${
                    settings.brickSizeType !== "atr"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-700 text-gray-300"
                  }`}
                >
                  {t("fixed") || "Fixed"}
                </button>
                <button
                  onClick={() => set("brickSizeType", "atr")}
                  className={`px-3 py-1.5 text-xs rounded transition-colors ${
                    settings.brickSizeType === "atr"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-700 text-gray-300"
                  }`}
                >
                  {t("atrBased") || "ATR Based"}
                </button>
              </div>
            </div>

            {settings.brickSizeType !== "atr" && (
              <div className="mb-4">
                <label className="block text-sm mb-2 text-gray-300">
                  {t("fixedBrickSize") || "Fixed Brick Size"}
                </label>
                <input
                  type="number"
                  min="0.0001"
                  step="any"
                  value={settings.fixedBrickSize || 100}
                  onChange={(e) =>
                    set("fixedBrickSize", parseFloat(e.target.value) || 100)
                  }
                  className="w-full px-3 py-2 bg-gray-800 text-white text-sm rounded border border-gray-600 focus:outline-none focus:border-blue-500"
                />
              </div>
            )}

            {settings.brickSizeType === "atr" && (
              <div className="mb-4">
                <label className="block text-sm mb-2 text-gray-300">
                  {t("atrPeriod") || "ATR Period"}
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={settings.atrPeriod || 14}
                  onChange={(e) =>
                    set("atrPeriod", parseInt(e.target.value) || 14)
                  }
                  className="w-full px-3 py-2 bg-gray-800 text-white text-sm rounded border border-gray-600 focus:outline-none focus:border-blue-500"
                />
              </div>
            )}
          </>
        );

      case "kagi":
        return (
          <>
            <div className="mb-4">
              <label className="block text-sm mb-2 text-gray-300">
                {t("reversalPercent") || "Reversal Percentage"}:{" "}
                <span className="text-blue-400">
                  {settings.reversalPercent || 4}%
                </span>
              </label>
              <input
                type="range"
                min="1"
                max="10"
                step="0.5"
                value={settings.reversalPercent || 4}
                onChange={(e) =>
                  set("reversalPercent", parseFloat(e.target.value))
                }
                className="w-full accent-blue-500"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>1%</span>
                <span>5%</span>
                <span>10%</span>
              </div>
            </div>
            <div className="mb-4">
              <label className="block text-sm mb-2 text-gray-300">
                {t("priceSource") || "Price Source"}
              </label>
              <div className="flex gap-3">
                <button
                  onClick={() => set("kagiUseClose", true)}
                  className={`px-3 py-1.5 text-xs rounded transition-colors ${
                    settings.kagiUseClose !== false
                      ? "bg-blue-600 text-white"
                      : "bg-gray-700 text-gray-300"
                  }`}
                >
                  {t("close") || "Close"}
                </button>
                <button
                  onClick={() => set("kagiUseClose", false)}
                  className={`px-3 py-1.5 text-xs rounded transition-colors ${
                    settings.kagiUseClose === false
                      ? "bg-blue-600 text-white"
                      : "bg-gray-700 text-gray-300"
                  }`}
                >
                  {(t("highLow") as string) || "High/Low"}
                </button>
              </div>
            </div>
          </>
        );

      case "lineBreak":
        return (
          <div className="mb-4">
            <label className="block text-sm mb-2 text-gray-300">
              {t("lookbackPeriod") || "Lookback Period"}:{" "}
              <span className="text-blue-400">{settings.lookback || 3}</span>
            </label>
            <input
              type="range"
              min="1"
              max="10"
              step="1"
              value={settings.lookback || 3}
              onChange={(e) => set("lookback", parseInt(e.target.value))}
              className="w-full accent-blue-500"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>1</span>
              <span>3</span>
              <span>5</span>
              <span>10</span>
            </div>
          </div>
        );

      default:
        return (
          <p className="text-sm text-gray-400">
            {t("noSettingsForChartType") || "No settings for this chart type."}
          </p>
        );
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg p-5 w-96 border border-gray-700 shadow-2xl">
        <h3 className="text-base font-semibold text-white mb-4">
          {t("chartTypeSettings") || "Chart Type Settings"} — {type}
        </h3>
        {renderSettings()}
        <div className="flex justify-end gap-2 mt-4 pt-3 border-t border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
          >
            {t("apply") || "Apply"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChartTypeSettingsModal;
