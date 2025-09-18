/**
 * DateTime helper functions for Trace functionality
 */

/**
 * Format datetime-local input value for API calls
 * @param dateTime - DateTime string from datetime-local input (YYYY-MM-DDTHH:MM)
 * @returns ISO datetime string with seconds or null if empty
 */
export const formatDateTimeForAPI = (dateTime: string): string | null => {
  if (!dateTime) return null;
  return `${dateTime}:00`; // Add seconds to match API format
};

/**
 * Get current datetime in YYYY-MM-DDTHH:MM format for datetime-local input
 */
export const getCurrentDateTime = (): string => {
  const now = new Date();
  const year = now.getFullYear();
  const month = (now.getMonth() + 1).toString().padStart(2, '0');
  const date = now.getDate().toString().padStart(2, '0');
  const hours = now.getHours().toString().padStart(2, '0');
  const minutes = now.getMinutes().toString().padStart(2, '0');

  return `${year}-${month}-${date}T${hours}:${minutes}`;
};

/**
 * Get datetime range for last N days
 * @param days - Number of days to go back
 * @returns Object with fromDateTime and toDateTime strings
 */
export const getLastNDaysRange = (days: number = 7): { fromDateTime: string; toDateTime: string } => {
  const toDate = new Date();
  const fromDate = new Date();
  fromDate.setDate(toDate.getDate() - days);

  const toDateTime = getCurrentDateTime();
  const fromDateTime = `${fromDate.getFullYear()}-${(fromDate.getMonth() + 1).toString().padStart(2, '0')}-${fromDate.getDate().toString().padStart(2, '0')}T00:00`;

  return {
    fromDateTime,
    toDateTime
  };
};

/**
 * Format datetime for display in chat messages
 * @param dateTime - DateTime string from datetime-local input
 * @returns Formatted string for user display
 */
export const formatDateTimeForDisplay = (dateTime: string): string => {
  if (!dateTime) return 'Not set';
  try {
    return new Date(dateTime).toLocaleString();
  } catch {
    return dateTime;
  }
};

/**
 * Validate date range (from should be before to)
 * @param fromDateTime - Start datetime
 * @param toDateTime - End datetime
 * @returns Validation result
 */
export const validateDateRange = (fromDateTime: string, toDateTime: string): { valid: boolean; message?: string } => {
  if (!fromDateTime || !toDateTime) {
    return { valid: true }; // Allow empty dates
  }

  if (new Date(fromDateTime) > new Date(toDateTime)) {
    return {
      valid: false,
      message: 'From date must be before To date'
    };
  }

  return { valid: true };
};

/**
 * Parse ISO datetime string to datetime-local format
 * @param isoString - ISO datetime string
 * @returns datetime-local format string (YYYY-MM-DDTHH:MM)
 */
export const parseISOToLocal = (isoString: string): string => {
  if (!isoString) return '';

  try {
    const dateObj = new Date(isoString);
    const year = dateObj.getFullYear();
    const month = (dateObj.getMonth() + 1).toString().padStart(2, '0');
    const date = dateObj.getDate().toString().padStart(2, '0');
    const hours = dateObj.getHours().toString().padStart(2, '0');
    const minutes = dateObj.getMinutes().toString().padStart(2, '0');

    return `${year}-${month}-${date}T${hours}:${minutes}`;
  } catch (error) {
    return '';
  }
};

/**
 * Auto-set date range based on default days selection
 * @param days - Number of days
 * @returns Object with fromDateTime and toDateTime
 */
export const autoSetDateRange = (days: number): { fromDateTime: string; toDateTime: string } => {
  return getLastNDaysRange(days);
};