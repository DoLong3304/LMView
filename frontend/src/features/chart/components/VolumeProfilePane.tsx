import React, { useMemo } from "react";
import type { Candle } from "@/types";
import {
  calculateVolumeProfile,
  type VolumeProfileConfig,
  type VolumeProfileResult,
} from "../indicators/volumeProfile";

interface VolumeProfilePaneProps {
  candles: Candle[];
  config?: Partial<VolumeProfileConfig>;
  visible: boolean;
  width?: number;
}

const DEFAULT_CONFIG: VolumeProfileConfig = {
  bins: 24,
  valueAreaPercent: 70,
};

/**
 * Volume Profile pane — renders horizontal volume bars beside the chart.
 * Shows POC (Point of Control), VAH (Value Area High), VAL (Value Area Low).
 */
const VolumeProfilePane: React.FC<VolumeProfilePaneProps> = ({
  candles,
  config,
  visible,
  width = 200,
}) => {
  const profile: VolumeProfileResult = useMemo(
    () => calculateVolumeProfile(candles, { ...DEFAULT_CONFIG, ...config }),
    [candles, config],
  );

  if (!visible || profile.levels.length === 0) return null;

  const maxVol = Math.max(...profile.levels.map((l) => l.volume));
  if (maxVol === 0) return null;

  // Calculate height per bin
  const chartHeight = 600; // Approximate — will be overridden by container
  const binHeight = Math.max(2, chartHeight / profile.levels.length);

  return (
    <div className="absolute right-0 top-0 h-full pointer-events-none" style={{ width }}>
      <svg width="100%" height="100%" className="overflow-visible">
        {profile.levels.map((level, idx) => {
          const barWidth = (level.volume / maxVol) * (width - 40);
          const y = idx * binHeight;
          const isPOC = level.poc;
          const isVA = level.vah || level.val;

          return (
            <g key={`vp-${level.price}`}>
              {/* Volume bar */}
              <rect
                x={width - barWidth - 30}
                y={y}
                width={barWidth}
                height={binHeight - 1}
                fill={
                  isPOC
                    ? "#fb8c00"
                    : isVA
                      ? "#7b1fa2"
                      : level.buyVolume > level.sellVolume
                        ? "#26a69a"
                        : "#ef5350"
                }
                opacity={isPOC ? 0.9 : 0.6}
              />

              {/* Labels for POC/VAH/VAL */}
              {(isPOC || isVA) && (
                <text
                  x={width - barWidth - 34}
                  y={y + binHeight / 2 + 3}
                  textAnchor="end"
                  fontSize="9"
                  fontWeight="bold"
                  fill={isPOC ? "#fb8c00" : "#7b1fa2"}
                >
                  {isPOC ? "POC" : level.vah ? "VAH" : "VAL"}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
};

export default VolumeProfilePane;
