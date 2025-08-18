import timezoneManager from './TimezoneManager';
import { DateTime } from 'luxon';

/**
 * API Timezone Middleware
 * Automatically handles timezone conversions for all time-related API calls
 */
class ApiTimezoneMiddleware {
  constructor() {
    this.timeFields = [
      'start_time', 'end_time', 'from_time', 'to_time', 'event_time',
      'timestamp', 'created_at', 'updated_at', 'startDate', 'endDate',
      'fromTime', 'toTime', 'start_date', 'end_date', 'time', 'datetime'
    ];
    
    this.retryConfig = {
      maxRetries: 3,
      baseDelay: 1000, // 1 second
      maxDelay: 5000   // 5 seconds
    };
  }

  /**
   * Add timezone headers to API request
   * @param {Object} headers - Existing headers
   * @returns {Object} Headers with timezone info
   */
  addTimezoneHeaders(headers = {}) {
    try {
      const tzInfo = timezoneManager.getTimezoneInfo();
      return {
        ...headers,
        'X-Client-Timezone': tzInfo.userTimezone || 'UTC',
        'X-Client-Offset': (tzInfo.currentOffsetMinutes || 0).toString(),
        'X-Client-DST': (tzInfo.isDST || false).toString(),
        'X-Timezone-Version': '1.0'
      };
    } catch (error) {
      console.warn('Failed to add timezone headers:', error);
      return {
        ...headers,
        'X-Client-Timezone': 'UTC',
        'X-Client-Offset': '0',
        'X-Client-DST': 'false',
        'X-Timezone-Version': '1.0'
      };
    }
  }

  /**
   * Convert time values in request data to UTC
   * @param {Object} data - Request data
   * @returns {Object} Data with UTC times
   */
  convertRequestToUtc(data) {
    if (!data || typeof data !== 'object') return data;

    const converted = { ...data };
    
    try {
      // Handle nested objects and arrays
      for (const [key, value] of Object.entries(data)) {
        if (this.isTimeField(key)) {
          converted[key] = this.convertSingleTimeToUtc(value, key);
        } else if (Array.isArray(value)) {
          converted[key] = value.map(item => 
            typeof item === 'object' ? this.convertRequestToUtc(item) : item
          );
        } else if (typeof value === 'object' && value !== null) {
          converted[key] = this.convertRequestToUtc(value);
        }
      }

      return converted;
    } catch (error) {
      console.error('Error converting request to UTC:', error);
      return data; // Return original data on error
    }
  }

  /**
   * Convert single time value to UTC
   * @param {*} value - Time value
   * @param {string} fieldName - Field name for context
   * @returns {string} UTC time string
   */
  convertSingleTimeToUtc(value, fieldName) {
    if (!value) return value;

    try {
      // Handle different time formats
      if (typeof value === 'string') {
        // Handle time-only formats (HH:mm)
        if (fieldName.includes('time') && value.match(/^\d{2}:\d{2}$/)) {
          // For time-only fields, just return the time part since it's relative
          return value;
        }
        
        // Handle full datetime strings
        return timezoneManager.toUtcForBackend(value);
      }
      
      if (value instanceof Date) {
        return timezoneManager.toUtcForBackend(value);
      }
      
      if (typeof value === 'number') {
        // Assume Unix timestamp
        const date = new Date(value * 1000);
        return timezoneManager.toUtcForBackend(date);
      }

      return value;
    } catch (error) {
      console.warn(`Failed to convert time field ${fieldName}:`, error);
      return value; // Return original value on error
    }
  }

  /**
   * Convert response times from UTC to user timezone
   * @param {Object} data - Response data
   * @returns {Object} Data with local times
   */
  convertResponseToLocal(data) {
    if (!data || typeof data !== 'object') return data;

    const converted = Array.isArray(data) ? [...data] : { ...data };
    
    try {
      if (Array.isArray(converted)) {
        // Handle array responses
        return converted.map(item => 
          typeof item === 'object' ? this.convertResponseToLocal(item) : item
        );
      }

      // Handle object responses
      for (const [key, value] of Object.entries(data)) {
        if (this.isTimeField(key) && value) {
          converted[key] = this.convertSingleTimeToLocal(value, key);
        } else if (Array.isArray(value)) {
          converted[key] = value.map(item => 
            typeof item === 'object' ? this.convertResponseToLocal(item) : item
          );
        } else if (typeof value === 'object' && value !== null) {
          converted[key] = this.convertResponseToLocal(value);
        }
      }

      return converted;
    } catch (error) {
      console.error('Error converting response to local time:', error);
      return data; // Return original data on error
    }
  }

  /**
   * Convert single time value to local timezone
   * @param {*} value - UTC time value
   * @param {string} fieldName - Field name for context
   * @returns {*} Local time value
   */
  convertSingleTimeToLocal(value, fieldName) {
    if (!value) return value;

    try {
      // Don't convert time-only fields
      if (fieldName.includes('time') && typeof value === 'string' && value.match(/^\d{2}:\d{2}$/)) {
        return value;
      }

      // Additional validation to prevent parsing timezone identifiers
      if (typeof value === 'string') {
        // Check if value looks like a timezone identifier rather than a timestamp
        const timezonePatterns = [
          /^[A-Z][a-z]+\/[A-Z][a-z_]+$/,  // "Asia/Ho_Chi_Minh"
          /^[A-Z][a-z]+ \([A-Za-z ]+\)$/,  // "Vietnam (Ho Chi Minh City)"
          /^UTC[+-]\d+$/,                   // "UTC+7"
          /^[A-Z]{3,4}$/                    // "PST", "GMT"
        ];
        
        const isTimezoneIdentifier = timezonePatterns.some(pattern => pattern.test(value.trim()));
        if (isTimezoneIdentifier) {
          // This is a timezone identifier, not a timestamp - return as-is
          return value;
        }

        // Check if it looks like a timestamp
        const timestampPatterns = [
          /\d{4}[-\/]\d{1,2}[-\/]\d{1,2}/,  // Date pattern
          /\d{10,13}/,                       // Unix timestamp
          /\d{1,2}:\d{2}/,                   // Time pattern
          /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/   // ISO datetime
        ];
        
        const hasTimestampPattern = timestampPatterns.some(pattern => pattern.test(value));
        if (!hasTimestampPattern) {
          // Doesn't look like a timestamp - return as-is
          return value;
        }
      }

      // Parse and convert UTC time to local
      const result = timezoneManager.parseVideoTimestamp(value);
      if (result.isValid && result.userTime) {
        return result.userTime.toISO();
      }

      return value;
    } catch (error) {
      console.warn(`Failed to convert response field ${fieldName}:`, error);
      return value;
    }
  }

  /**
   * Check if field name represents a time field
   * @param {string} fieldName - Field name to check
   * @returns {boolean} True if time field
   */
  isTimeField(fieldName) {
    const lowercaseField = fieldName.toLowerCase();
    return this.timeFields.some(timeField => 
      lowercaseField.includes(timeField.toLowerCase())
    );
  }

  /**
   * Create timezone-aware fetch wrapper
   * @param {string} url - API endpoint URL
   * @param {Object} options - Fetch options
   * @returns {Promise} Fetch promise with timezone handling
   */
  async fetchWithTimezone(url, options = {}) {
    const startTime = performance.now();
    
    try {
      // Add timezone headers
      const headers = this.addTimezoneHeaders(options.headers);
      
      // Convert request data to UTC
      let body = options.body;
      if (body && typeof body === 'string') {
        try {
          const parsedBody = JSON.parse(body);
          const convertedBody = this.convertRequestToUtc(parsedBody);
          body = JSON.stringify(convertedBody);
        } catch (e) {
          // Not JSON, keep original body
        }
      }

      const requestOptions = {
        ...options,
        headers,
        body
      };

      // Execute request with retry logic
      const response = await this.executeWithRetry(url, requestOptions);
      
      // Convert response data to local timezone
      if (response.ok) {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const originalJson = response.json.bind(response);
          response.json = async () => {
            const data = await originalJson();
            return this.convertResponseToLocal(data);
          };
        }
      }

      // Log performance
      const duration = performance.now() - startTime;
      if (duration > 1000) { // Log slow requests
        console.warn(`Slow API request: ${url} took ${duration.toFixed(2)}ms`);
      }

      return response;
    } catch (error) {
      console.error('API timezone middleware error:', error);
      throw this.enhanceError(error, url, options);
    }
  }

  /**
   * Execute API request with retry logic for timezone-related failures
   * @param {string} url - API endpoint URL
   * @param {Object} options - Fetch options
   * @returns {Promise} Fetch response
   */
  async executeWithRetry(url, options) {
    let lastError;
    
    for (let attempt = 0; attempt <= this.retryConfig.maxRetries; attempt++) {
      try {
        const response = await fetch(url, options);
        
        // Check for timezone-related errors
        if (!response.ok && this.isTimezoneError(response)) {
          throw new Error(`Timezone error: ${response.status} ${response.statusText}`);
        }
        
        return response;
      } catch (error) {
        lastError = error;
        
        // Only retry timezone-related errors
        if (attempt < this.retryConfig.maxRetries && this.shouldRetry(error)) {
          const delay = Math.min(
            this.retryConfig.baseDelay * Math.pow(2, attempt),
            this.retryConfig.maxDelay
          );
          
          console.warn(`API request failed (attempt ${attempt + 1}/${this.retryConfig.maxRetries + 1}), retrying in ${delay}ms:`, error.message);
          await this.delay(delay);
          continue;
        }
        
        break;
      }
    }
    
    throw lastError;
  }

  /**
   * Check if response indicates timezone-related error
   * @param {Response} response - Fetch response
   * @returns {boolean} True if timezone error
   */
  isTimezoneError(response) {
    // Check for common timezone error status codes or headers
    const timezoneErrorCodes = [400, 422]; // Bad Request, Unprocessable Entity
    if (timezoneErrorCodes.includes(response.status)) {
      const errorHeader = response.headers.get('X-Error-Type');
      return errorHeader && errorHeader.toLowerCase().includes('timezone');
    }
    return false;
  }

  /**
   * Check if error should trigger retry
   * @param {Error} error - Error object
   * @returns {boolean} True if should retry
   */
  shouldRetry(error) {
    // Retry network errors and timezone-related errors
    return (
      error.message.includes('timezone') ||
      error.message.includes('fetch') ||
      error.message.includes('network') ||
      error.code === 'NETWORK_ERROR'
    );
  }

  /**
   * Enhance error with timezone context
   * @param {Error} error - Original error
   * @param {string} url - Request URL
   * @param {Object} options - Request options
   * @returns {Error} Enhanced error
   */
  enhanceError(error, url, options) {
    let tzInfo = { userTimezone: 'UTC', currentOffset: '+00:00' };
    
    try {
      tzInfo = timezoneManager.getTimezoneInfo();
    } catch (tzError) {
      console.warn('Failed to get timezone info for error enhancement:', tzError);
    }
    
    const enhancedError = new Error(`API Error [${url}]: ${error.message}`);
    enhancedError.originalError = error;
    enhancedError.url = url;
    enhancedError.timezone = tzInfo.userTimezone || 'UTC';
    enhancedError.offset = tzInfo.currentOffset || '+00:00';
    enhancedError.timestamp = new Date().toISOString();
    
    return enhancedError;
  }

  /**
   * Utility delay function
   * @param {number} ms - Milliseconds to delay
   * @returns {Promise} Promise that resolves after delay
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Validate timezone compatibility with API
   * @returns {Promise<boolean>} True if timezone is supported
   */
  async validateTimezoneCompatibility() {
    try {
      const tzInfo = timezoneManager.getTimezoneInfo();
      
      // Test API call to validate timezone handling
      const testPayload = {
        timezone_test: true,
        client_timezone: tzInfo.userTimezone,
        test_time: new Date().toISOString()
      };

      const response = await fetch('/api/timezone-test', {
        method: 'POST',
        headers: this.addTimezoneHeaders({
          'Content-Type': 'application/json'
        }),
        body: JSON.stringify(testPayload)
      });

      return response.ok;
    } catch (error) {
      console.warn('Timezone compatibility check failed:', error);
      return true; // Assume compatible on error
    }
  }
}

// Create singleton instance
const apiTimezoneMiddleware = new ApiTimezoneMiddleware();

export default apiTimezoneMiddleware;
export { ApiTimezoneMiddleware };