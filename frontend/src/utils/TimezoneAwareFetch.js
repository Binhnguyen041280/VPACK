import apiTimezoneMiddleware from './ApiTimezoneMiddleware';

/**
 * Timezone-aware fetch wrapper for components that use fetch directly
 * Provides compatibility layer for existing fetch-based API calls
 */
class TimezoneAwareFetch {
  /**
   * Enhanced fetch with automatic timezone conversion
   * @param {string} url - API endpoint URL
   * @param {Object} options - Fetch options
   * @returns {Promise<Response>} Enhanced response
   */
  static async fetch(url, options = {}) {
    return apiTimezoneMiddleware.fetchWithTimezone(url, options);
  }

  /**
   * POST request with timezone handling
   * @param {string} url - API endpoint URL
   * @param {Object} data - Request data
   * @param {Object} options - Additional options
   * @returns {Promise<Response>} API response
   */
  static async post(url, data, options = {}) {
    const requestOptions = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      body: JSON.stringify(data),
      ...options
    };

    return this.fetch(url, requestOptions);
  }

  /**
   * GET request with timezone headers
   * @param {string} url - API endpoint URL
   * @param {Object} options - Additional options
   * @returns {Promise<Response>} API response
   */
  static async get(url, options = {}) {
    const requestOptions = {
      method: 'GET',
      ...options
    };

    return this.fetch(url, requestOptions);
  }

  /**
   * PUT request with timezone handling
   * @param {string} url - API endpoint URL
   * @param {Object} data - Request data
   * @param {Object} options - Additional options
   * @returns {Promise<Response>} API response
   */
  static async put(url, data, options = {}) {
    const requestOptions = {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      body: JSON.stringify(data),
      ...options
    };

    return this.fetch(url, requestOptions);
  }

  /**
   * DELETE request with timezone headers
   * @param {string} url - API endpoint URL
   * @param {Object} options - Additional options
   * @returns {Promise<Response>} API response
   */
  static async delete(url, options = {}) {
    const requestOptions = {
      method: 'DELETE',
      ...options
    };

    return this.fetch(url, requestOptions);
  }

  /**
   * Helper to parse JSON response with timezone conversion
   * @param {Response} response - Fetch response
   * @returns {Promise<Object>} Parsed JSON data with timezone conversion
   */
  static async parseJsonResponse(response) {
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return apiTimezoneMiddleware.convertResponseToLocal(data);
  }

  /**
   * Convenience method for POST + JSON parsing
   * @param {string} url - API endpoint URL
   * @param {Object} data - Request data
   * @param {Object} options - Additional options
   * @returns {Promise<Object>} Parsed response data
   */
  static async postJson(url, data, options = {}) {
    const response = await this.post(url, data, options);
    return this.parseJsonResponse(response);
  }

  /**
   * Convenience method for GET + JSON parsing
   * @param {string} url - API endpoint URL
   * @param {Object} options - Additional options
   * @returns {Promise<Object>} Parsed response data
   */
  static async getJson(url, options = {}) {
    const response = await this.get(url, options);
    return this.parseJsonResponse(response);
  }
}

/**
 * Replace global fetch with timezone-aware version for components
 * This provides a drop-in replacement for existing fetch calls
 */
export const createTimezoneAwareFetch = () => {
  const originalFetch = window.fetch;
  
  // Override global fetch
  window.fetch = async (url, options = {}) => {
    // Check if URL is for our API
    if (typeof url === 'string' && (
      url.includes('localhost:8080') || 
      url.startsWith('/api/') ||
      url.startsWith('/save-') ||
      url.startsWith('/get-') ||
      url.startsWith('/update-') ||
      url.startsWith('/delete-')
    )) {
      return apiTimezoneMiddleware.fetchWithTimezone(url, options);
    }
    
    // Use original fetch for external APIs
    return originalFetch(url, options);
  };

  // Return restore function
  return () => {
    window.fetch = originalFetch;
  };
};

export default TimezoneAwareFetch;