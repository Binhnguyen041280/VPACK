/**
 * Error Handler Utilities for V_Track Program Control
 *
 * Provides centralized error handling, user-friendly messages,
 * and retry mechanisms for better user experience.
 */

export interface ApiError {
  message: string;
  code?: string;
  details?: any;
  statusCode?: number;
}

export interface ErrorDisplayOptions {
  showToast?: boolean;
  toastDuration?: number;
  fallbackMessage?: string;
  context?: string;
}

/**
 * Parse and normalize API errors to a consistent format
 */
export const parseApiError = (error: any): ApiError => {
  // If already a structured error
  if (error && typeof error === 'object' && error.message) {
    return {
      message: error.message,
      code: error.code,
      details: error.details,
      statusCode: error.status || error.statusCode
    };
  }

  // If it's a network error
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return {
      message: 'Network connection failed. Please check your internet connection.',
      code: 'NETWORK_ERROR',
      statusCode: 0
    };
  }

  // If it's a string error
  if (typeof error === 'string') {
    return {
      message: error,
      code: 'UNKNOWN_ERROR'
    };
  }

  // Fallback for unknown errors
  return {
    message: 'An unexpected error occurred. Please try again.',
    code: 'UNKNOWN_ERROR',
    details: error
  };
};

/**
 * Get user-friendly error messages for common scenarios
 */
export const getUserFriendlyMessage = (error: ApiError, context?: string): string => {
  const { message, code, statusCode } = error;

  // Network errors
  if (code === 'NETWORK_ERROR' || statusCode === 0) {
    return 'Unable to connect to the server. Please check your internet connection and try again.';
  }

  // Server errors
  if (statusCode && statusCode >= 500) {
    return 'Server error occurred. Please try again in a few moments.';
  }

  // Authentication errors
  if (statusCode === 401 || statusCode === 403) {
    return 'Authentication failed. Please refresh the page and try again.';
  }

  // Not found errors
  if (statusCode === 404) {
    return context
      ? `${context} not found. Please check your settings and try again.`
      : 'Resource not found. Please check your settings and try again.';
  }

  // Bad request errors
  if (statusCode === 400) {
    return message || 'Invalid request. Please check your input and try again.';
  }

  // Program-specific errors
  if (message.includes('first run already completed')) {
    return 'First run has already been completed. You can only run it once.';
  }

  if (message.includes('already processed')) {
    return 'This file has already been processed. Please select a different file.';
  }

  if (message.includes('does not exist')) {
    return 'The specified path does not exist. Please check the path and try again.';
  }

  if (message.includes('Custom path required')) {
    return 'Please enter a valid file or directory path for custom processing.';
  }

  if (message.includes('Days required')) {
    return 'Please enter the number of days for first run processing.';
  }

  // Default to original message if it's user-friendly, otherwise provide generic message
  if (message && message.length < 100 && !message.includes('Error:') && !message.includes('Exception')) {
    return message;
  }

  return 'An error occurred while processing your request. Please try again.';
};

/**
 * Determine if an error is retryable
 */
export const isRetryableError = (error: ApiError): boolean => {
  const { code, statusCode } = error;

  // Network errors are retryable
  if (code === 'NETWORK_ERROR' || statusCode === 0) {
    return true;
  }

  // Server errors are retryable
  if (statusCode && statusCode >= 500) {
    return true;
  }

  // Timeout errors are retryable
  if (code === 'TIMEOUT_ERROR') {
    return true;
  }

  // Rate limiting is retryable (with delay)
  if (statusCode === 429) {
    return true;
  }

  // Client errors are generally not retryable
  if (statusCode && statusCode >= 400 && statusCode < 500) {
    return false;
  }

  return false;
};

/**
 * Get appropriate retry delay based on error type
 */
export const getRetryDelay = (error: ApiError, attemptNumber: number): number => {
  const { statusCode } = error;

  // Rate limiting - longer delay
  if (statusCode === 429) {
    return Math.min(30000, 5000 * attemptNumber); // 5s, 10s, 15s, max 30s
  }

  // Server errors - exponential backoff
  if (statusCode && statusCode >= 500) {
    return Math.min(10000, 1000 * Math.pow(2, attemptNumber - 1)); // 1s, 2s, 4s, 8s, max 10s
  }

  // Network errors - shorter delay
  return Math.min(5000, 1000 * attemptNumber); // 1s, 2s, 3s, 4s, max 5s
};

/**
 * Enhanced retry mechanism with exponential backoff
 */
export const retryOperation = async <T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  shouldRetry?: (error: any) => boolean
): Promise<T> => {
  let lastError: any;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;
      const apiError = parseApiError(error);

      // Check if we should retry
      const defaultShouldRetry = isRetryableError(apiError);
      const customShouldRetry = shouldRetry ? shouldRetry(error) : true;

      if (attempt === maxRetries || (!defaultShouldRetry && !customShouldRetry)) {
        throw lastError;
      }

      // Wait before retrying
      const delay = getRetryDelay(apiError, attempt);
      await new Promise(resolve => setTimeout(resolve, delay));

      console.log(`Retrying operation (attempt ${attempt + 1}/${maxRetries}) after ${delay}ms delay`);
    }
  }

  throw lastError;
};

/**
 * Create a toast-compatible error object
 */
export const createToastError = (
  error: any,
  context?: string,
  options: ErrorDisplayOptions = {}
): {
  title: string;
  description: string;
  status: 'error' | 'warning';
  duration: number;
} => {
  const apiError = parseApiError(error);
  const userMessage = getUserFriendlyMessage(apiError, context);

  return {
    title: options.fallbackMessage || 'Error',
    description: userMessage,
    status: isRetryableError(apiError) ? 'warning' : 'error',
    duration: options.toastDuration || (isRetryableError(apiError) ? 4000 : 6000)
  };
};

export default {
  parseApiError,
  getUserFriendlyMessage,
  isRetryableError,
  getRetryDelay,
  retryOperation,
  createToastError
};