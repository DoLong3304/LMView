import React from 'react';
import { Play, Pause, SkipForward, X } from 'lucide-react';
import { useI18n } from "@/i18n";

interface ReplayControlsProps {
  isPlaying: boolean;
  playbackSpeed: number;
  currentIndex: number;
  totalCandles: number;
  onPlayPause: () => void;
  onStepForward: () => void;
  onSpeedChange: (speed: number) => void;
  onExit: () => void;
}

const SPEED_OPTIONS = [
  { value: 1, label: '1x' },
  { value: 3, label: '3x' },
  { value: 10, label: '10x' },
  { value: 100, label: '100x' },
];

export const ReplayControls: React.FC<ReplayControlsProps> = ({
  isPlaying,
  playbackSpeed,
  currentIndex,
  totalCandles,
  onPlayPause,
  onStepForward,
  onSpeedChange,
  onExit,
}) => {
  const { t } = useI18n();

  const progress = totalCandles > 1 ? (currentIndex / (totalCandles - 1)) * 100 : 0;
  const isAtEnd = totalCandles === 0 || currentIndex >= totalCandles - 1;

  return (
    <div className="replay-controls">
      {/* Progress Bar */}
      <div className="replay-progress-bar">
        <div
          className="replay-progress-fill"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Controls Container */}
      <div className="replay-controls-container">
        {/* Left: Play/Pause & Step */}
        <div className="replay-controls-left">
          <button
            className="replay-btn replay-btn-primary"
            onClick={onPlayPause}
            title={isPlaying ? t('pause') : t('play')}
          >
            {isPlaying ? <Pause size={18} /> : <Play size={18} />}
          </button>

          <button
            className="replay-btn"
            onClick={onStepForward}
            disabled={isPlaying || isAtEnd}
            title={t('stepForward')}
          >
            <SkipForward size={18} />
          </button>
        </div>

        {/* Center: Progress Info */}
        <div className="replay-info">
          <span className="replay-counter">
            {Math.min(currentIndex + 1, totalCandles)} / {totalCandles}
          </span>
          <span className="replay-label">{t('replayMode')}</span>
        </div>

        {/* Right: Speed Selector & Exit */}
        <div className="replay-controls-right">
          <div className="replay-speed-selector">
            {SPEED_OPTIONS.map((option) => (
              <button
                key={option.value}
                className={`replay-speed-btn ${
                  playbackSpeed === option.value ? 'active' : ''
                }`}
                onClick={() => onSpeedChange(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>

          <button
            className="replay-btn replay-btn-exit"
            onClick={onExit}
            title={t('exitReplay')}
          >
            <X size={18} />
          </button>
        </div>
      </div>
    </div>
  );
};
