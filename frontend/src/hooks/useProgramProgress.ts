import { useState, useEffect, useCallback, useRef } from 'react';
import { programService, ProgressData } from '../services/programService';

interface UseProgramProgressReturn {
  progressData: ProgressData | null;
  isLoading: boolean;
  error: string | null;
  startPolling: () => void;
  stopPolling: () => void;
  isPolling: boolean;
}

interface UseProgramProgressOptions {
  interval?: number; // Polling interval in milliseconds
  autoStart?: boolean; // Auto start polling on mount
  onError?: (error: string) => void; // Error callback
  onUpdate?: (data: ProgressData) => void; // Update callback
}

/**
 * Custom hook for real-time program progress monitoring
 *
 * Features:
 * - Automatic polling with configurable interval
 * - Start/stop polling control
 * - Error handling with retry logic
 * - Memory leak prevention with cleanup
 */
export const useProgramProgress = (options: UseProgramProgressOptions = {}): UseProgramProgressReturn => {
  const {
    interval = 2000, // 2 seconds default
    autoStart = false,
    onError,
    onUpdate
  } = options;

  const [progressData, setProgressData] = useState<ProgressData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const retryCountRef = useRef(0);
  const maxRetries = 3;

  /**
   * Fetch progress data from backend
   */
  const fetchProgress = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const data = await programService.getProgramProgress();

      setProgressData(data);
      retryCountRef.current = 0; // Reset retry count on success

      if (onUpdate) {
        onUpdate(data);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch progress';

      // Increment retry count
      retryCountRef.current += 1;

      if (retryCountRef.current >= maxRetries) {
        // Stop polling after max retries
        stopPolling();
        setError(`${errorMessage} (Max retries exceeded)`);

        if (onError) {
          onError(errorMessage);
        }
      } else {
        // Set temporary error but continue polling
        setError(`${errorMessage} (Retrying... ${retryCountRef.current}/${maxRetries})`);
      }
    } finally {
      setIsLoading(false);
    }
  }, [onError, onUpdate]);

  /**
   * Start polling for progress updates
   */
  const startPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    setIsPolling(true);
    retryCountRef.current = 0;

    // Fetch immediately
    fetchProgress();

    // Set up interval
    intervalRef.current = setInterval(fetchProgress, interval);
  }, [fetchProgress, interval]);

  /**
   * Stop polling for progress updates
   */
  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    setIsPolling(false);
    setError(null);
    retryCountRef.current = 0;
  }, []);

  /**
   * Auto start polling if enabled
   */
  useEffect(() => {
    if (autoStart) {
      startPolling();
    }

    // Cleanup on unmount
    return () => {
      stopPolling();
    };
  }, [autoStart, startPolling, stopPolling]);

  return {
    progressData,
    isLoading,
    error,
    startPolling,
    stopPolling,
    isPolling
  };
};

export default useProgramProgress;