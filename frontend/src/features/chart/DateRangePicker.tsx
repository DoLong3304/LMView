import React, { useRef, useState } from "react";
import { Calendar, X, Clock } from "lucide-react";
import { useI18n } from "@/i18n";
import DropdownPortal from "@/components/ui/DropdownPortal";
import type { HistoricalRange } from "@/types";

interface DateRangePickerProps {
  onApply: (range: HistoricalRange) => void;
  onClear: () => void;
  active?: boolean;
}

const DateRangePicker: React.FC<DateRangePickerProps> = ({
  onApply,
  onClear,
  active = false,
}) => {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Default to last 30 days
  const today = new Date();
  const thirtyDaysAgo = new Date(today);
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

  const toLocalISO = (d: Date): string => {
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  const [startDt, setStartDt] = useState(toLocalISO(thirtyDaysAgo));
  const [endDt, setEndDt] = useState(toLocalISO(today));

  const handleApply = () => {
    const startMs = new Date(startDt).getTime();
    const endMs = new Date(endDt).getTime();
    if (isNaN(startMs) || isNaN(endMs) || startMs >= endMs) return;
    onApply({ startMs, endMs });
    setOpen(false);
  };

  const handleClear = () => {
    onClear();
    setOpen(false);
  };

  // Preset ranges
  const applyPreset = (hours: number) => {
    const end = new Date();
    const start = new Date(end.getTime() - hours * 3600_000);
    setStartDt(toLocalISO(start));
    setEndDt(toLocalISO(end));
  };

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        onClick={() => setOpen((v) => !v)}
        className={`flex h-7 items-center justify-center gap-1.5 rounded px-2 text-xs font-semibold transition-colors
          ${active ? "bg-amber-600 text-white shadow-sm shadow-amber-950/40" : "text-gray-400 hover:bg-gray-700 hover:text-white"}`}
        title={
          active
            ? t("historicalModeTooltip")
            : t("queryHistorical")
        }
      >
        {active ? <Clock size={12} /> : <Calendar size={12} />}
        {active ? t("historical") : t("history")}
      </button>

      <DropdownPortal
        anchorRef={buttonRef}
        className="rounded-lg border border-gray-600 bg-gray-800 p-3 shadow-xl"
        maxWidth={288}
        minWidth={260}
        onClose={() => setOpen(false)}
        open={open}
        width={288}
      >
          <div className="text-xs text-gray-400 mb-2 font-medium">
            {t("selectDateRange")}
          </div>

          {/* Presets */}
          <div className="flex gap-1 mb-3 flex-wrap">
            {[
              { label: "6H", hours: 6 },
              { label: "12H", hours: 12 },
              { label: "24H", hours: 24 },
              { label: "7D", hours: 7 * 24 },
              { label: "30D", hours: 30 * 24 },
              { label: "90D", hours: 90 * 24 },
              { label: "1Y", hours: 365 * 24 },
            ].map(({ label, hours }) => (
              <button
                key={label}
                onClick={() => applyPreset(hours)}
                className="px-2 py-0.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors"
              >
                {label}
              </button>
            ))}
          </div>

          {/* Datetime inputs */}
          <div className="space-y-2 mb-3">
            <div>
              <label className="block text-xs text-gray-500 mb-0.5">
                {t("start")}
              </label>
              <input
                type="datetime-local"
                value={startDt}
                onChange={(e) => setStartDt(e.target.value)}
                className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-0.5">
                {t("end")}
              </label>
              <input
                type="datetime-local"
                value={endDt}
                onChange={(e) => setEndDt(e.target.value)}
                className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <button
              onClick={handleApply}
              className="flex-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded transition-colors"
            >
              {t("apply")}
            </button>
            {active && (
              <button
                onClick={handleClear}
                className="flex items-center gap-1 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs font-medium rounded transition-colors"
              >
                <X size={10} /> {t("live")}
              </button>
            )}
          </div>
      </DropdownPortal>
    </div>
  );
};

export default DateRangePicker;
