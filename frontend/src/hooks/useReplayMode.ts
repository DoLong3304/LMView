import { useState, useRef, useCallback, useEffect } from 'react';
import type { Candle } from "@/types";

export interface ReplayState {
  isReplayActive: boolean;
  isPlaying: boolean;
  playbackSpeed: number; // 1x, 3x, 10x, or updates per second
  currentIndex: number;
  totalCandles: number;
  currentTime: number; // Unix timestamp of current candle
}

interface UseReplayModeProps {
  onCandleUpdate?: (candle: Candle) => void;
  onReplayEnd?: () => void;
}

/**
 * Custom hook for Replay Mode (Bar Replay)
 *
 * Features:
 * - Load historical buffer
 * - Play/Pause controls
 * - Variable playback speed (1x, 3x, 10x, 1 update/sec)
 * - Step forward (advance 1 candle)
 * - Exit replay mode
 *
 * CRITICAL: When replay is active, caller MUST block WebSocket updates
 * to prevent live data from interfering with replay.
 */
export function useReplayMode({ onCandleUpdate, onReplayEnd }: UseReplayModeProps = {}) {
  const [isReplayActive, setIsReplayActive] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1); // 1x default
  const [currentIndex, setCurrentIndex] = useState(0);

  const historicalBufferRef = useRef<Candle[]>([]);
  const timerRef = useRef<number | null>(null);

  // Get current replay state
  const getReplayState = useCallback((): ReplayState => {
    const buffer = historicalBufferRef.current;
    const currentCandle = buffer[currentIndex];

    return {
      isReplayActive,
      isPlaying,
      playbackSpeed,
      currentIndex,
      totalCandles: buffer.length,
      currentTime: currentCandle?.time || 0,
    };
  }, [isReplayActive, isPlaying, playbackSpeed, currentIndex]);

  // Initialize replay with historical data
  const startReplay = useCallback((historicalCandles: Candle[], startIndex: number = 0) => {
    if (historicalCandles.length === 0) {
      console.warn('[useReplayMode] Cannot start replay with empty buffer');
      return;
    }

    historicalBufferRef.current = historicalCandles;
    setCurrentIndex(startIndex);
    setIsReplayActive(true);
    setIsPlaying(false); // Start paused

    console.log(`[useReplayMode] Replay initialized with ${historicalCandles.length} candles, starting at index ${startIndex}`);
  }, []);

  // Stop timer
  const stopTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  // Advance to next candle
  const advanceCandle = useCallback(() => {
    const buffer = historicalBufferRef.current;

    setCurrentIndex((prevIndex) => {
      const nextIndex = prevIndex + 1;

      if (nextIndex >= buffer.length) {
        // Reached end of replay
        console.log('[useReplayMode] Replay ended');
        setIsPlaying(false);
        stopTimer();
        onReplayEnd?.();
        return prevIndex; // Stay at last candle
      }

      // Emit candle update
      const nextCandle = buffer[nextIndex];
      if (nextCandle && onCandleUpdate) {
        onCandleUpdate(nextCandle);
      }

      return nextIndex;
    });
  }, [onCandleUpdate, onReplayEnd, stopTimer]);

  // Play replay
  const play = useCallback(() => {
    if (!isReplayActive) {
      console.warn('[useReplayMode] Cannot play - replay not active');
      return;
    }

    if (currentIndex >= historicalBufferRef.current.length - 1) {
      console.warn('[useReplayMode] Cannot play - already at end');
      return;
    }

    setIsPlaying(true);

    // Calculate interval based on speed
    // 1x = 1000ms, 3x = 333ms, 10x = 100ms, 1 update/sec = 1000ms
    const interval = playbackSpeed >= 1 ? 1000 / playbackSpeed : 1000;

    // Clear existing timer
    stopTimer();

    // Start new timer
    timerRef.current = window.setInterval(() => {
      advanceCandle();
    }, interval);

    console.log(`[useReplayMode] Playing at ${playbackSpeed}x speed (${interval}ms interval)`);
  }, [isReplayActive, currentIndex, playbackSpeed, stopTimer, advanceCandle]);

  // Pause replay
  const pause = useCallback(() => {
    setIsPlaying(false);
    stopTimer();
    console.log('[useReplayMode] Paused');
  }, [stopTimer]);

  // Toggle play/pause
  const togglePlayPause = useCallback(() => {
    if (isPlaying) {
      pause();
    } else {
      play();
    }
  }, [isPlaying, play, pause]);

  // Step forward (advance 1 candle)
  const stepForward = useCallback(() => {
    if (!isReplayActive) return;

    // Pause if playing
    if (isPlaying) {
      pause();
    }

    advanceCandle();
  }, [isReplayActive, isPlaying, pause, advanceCandle]);

  // Change playback speed
  const changeSpeed = useCallback((speed: number) => {
    setPlaybackSpeed(speed);

    // If currently playing, restart timer with new speed
    if (isPlaying) {
      pause();
      // Use setTimeout to restart after pause completes
      setTimeout(() => {
        setIsPlaying(true);
        const interval = speed >= 1 ? 1000 / speed : 1000;
        timerRef.current = window.setInterval(() => {
          advanceCandle();
        }, interval);
      }, 50);
    }

    console.log(`[useReplayMode] Speed changed to ${speed}x`);
  }, [isPlaying, pause, advanceCandle]);

  // Exit replay mode
  const exitReplay = useCallback(() => {
    stopTimer();
    setIsReplayActive(false);
    setIsPlaying(false);
    setCurrentIndex(0);
    historicalBufferRef.current = [];
    console.log('[useReplayMode] Exited replay mode');
  }, [stopTimer]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopTimer();
    };
  }, [stopTimer]);

  // Auto-pause when reaching end
  useEffect(() => {
    if (isReplayActive && currentIndex >= historicalBufferRef.current.length - 1) {
      pause();
    }
  }, [isReplayActive, currentIndex, pause]);

  return {
    // State
    isReplayActive,
    isPlaying,
    playbackSpeed,
    currentIndex,
    totalCandles: historicalBufferRef.current.length,
    currentCandle: historicalBufferRef.current[currentIndex] || null,

    // Actions
    startReplay,
    play,
    pause,
    togglePlayPause,
    stepForward,
    changeSpeed,
    exitReplay,
    getReplayState,
  };
}
