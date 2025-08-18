import { useState, useEffect, useCallback } from 'react';
import apiTimezoneMiddleware from '../utils/ApiTimezoneMiddleware';

/**
 * Hook for managing global timezone configuration
 * 
 * Provides functions to get and set the global timezone configuration,
 * replacing hardcoded timezone values throughout the application.
 * 
 * @returns {Object} Global timezone state and functions
 */
const useGlobalTimezone = () => {
  const [timezoneInfo, setTimezoneInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load global timezone configuration
  const loadGlobalTimezone = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiTimezoneMiddleware.fetchWithTimezone('/api/config/global-timezone', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setTimezoneInfo(data);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to load global timezone');
      }
    } catch (err) {
      console.error('Error loading global timezone:', err);
      setError(err.message);
      
      // Fallback to hardcoded values for backward compatibility
      setTimezoneInfo({
        timezone_iana: 'Asia/Ho_Chi_Minh',
        timezone_display: 'Asia/Ho Chi Minh (UTC+7)',
        utc_offset_hours: 7,
        is_validated: false,
        source: 'fallback'
      });
    } finally {
      setLoading(false);
    }
  }, []);

  // Set global timezone
  const setGlobalTimezone = useCallback(async (timezoneIana) => {
    try {
      setError(null);

      const response = await apiTimezoneMiddleware.fetchWithTimezone('/api/config/global-timezone', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          timezone: timezoneIana
        }),
      });

      if (response.ok) {
        // Reload the timezone info after successful update
        await loadGlobalTimezone();
        return { success: true };
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to set global timezone');
      }
    } catch (err) {
      console.error('Error setting global timezone:', err);
      setError(err.message);
      return { success: false, error: err.message };
    }
  }, [loadGlobalTimezone]);

  // Migrate to global timezone configuration
  const migrateToGlobalTimezone = useCallback(async () => {
    try {
      setError(null);

      const response = await apiTimezoneMiddleware.fetchWithTimezone('/api/config/global-timezone/migrate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const migrationResult = await response.json();
        // Reload the timezone info after migration
        await loadGlobalTimezone();
        return migrationResult;
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Migration failed');
      }
    } catch (err) {
      console.error('Error during migration:', err);
      setError(err.message);
      return { success: false, error: err.message };
    }
  }, [loadGlobalTimezone]);

  // Get timezone display string for UI
  const getTimezoneDisplay = useCallback(() => {
    if (!timezoneInfo) return 'Loading...';
    
    const offset = timezoneInfo.utc_offset_hours > 0 
      ? `+${timezoneInfo.utc_offset_hours}` 
      : timezoneInfo.utc_offset_hours.toString();
    
    return `${timezoneInfo.timezone_display || timezoneInfo.timezone_iana} (UTC${offset})`;
  }, [timezoneInfo]);

  // Get timezone offset string
  const getTimezoneOffset = useCallback(() => {
    if (!timezoneInfo) return 'UTC+7'; // Fallback
    
    const offset = timezoneInfo.utc_offset_hours;
    return offset > 0 ? `UTC+${offset}` : `UTC${offset}`;
  }, [timezoneInfo]);

  // Get IANA timezone name
  const getTimezoneIana = useCallback(() => {
    return timezoneInfo?.timezone_iana || 'Asia/Ho_Chi_Minh'; // Fallback
  }, [timezoneInfo]);

  // Load timezone on mount
  useEffect(() => {
    loadGlobalTimezone();
  }, [loadGlobalTimezone]);

  return {
    // State
    timezoneInfo,
    loading,
    error,
    
    // Functions
    loadGlobalTimezone,
    setGlobalTimezone,
    migrateToGlobalTimezone,
    
    // Convenience getters
    getTimezoneDisplay,
    getTimezoneOffset,
    getTimezoneIana,
    
    // Computed values for backward compatibility
    timezone: timezoneInfo?.timezone_iana || 'Asia/Ho_Chi_Minh',
    timezoneDisplay: getTimezoneDisplay(),
    timezoneOffset: getTimezoneOffset(),
  };
};

export default useGlobalTimezone;