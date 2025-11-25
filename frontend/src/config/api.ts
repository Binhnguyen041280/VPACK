/**
 * Centralized API Configuration
 * Phase 4: Single source of truth for all API endpoints
 *
 * Usage:
 *   import API_CONFIG from '@/config/api';
 *   const response = await fetch(`${API_CONFIG.BASE_URL}/payment/packages`);
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

const API_CONFIG = {
  // Base URL for all API calls
  BASE_URL: `${API_BASE_URL}/api`,

  // Service-specific endpoints
  ENDPOINTS: {
    // Payment & License
    PAYMENT: {
      PACKAGES: '/payment/packages',
      CREATE: '/payment/create',
      LICENSE_STATUS: '/payment/license-status',
      ACTIVATE_LICENSE: '/payment/activate-license',
    },

    // User & Account
    USER: {
      PROFILE: '/user/latest',
    },

    // Program Control
    PROGRAM: {
      STATUS: '/program/status',
      START: '/program/start',
      STOP: '/program/stop',
      CAMERAS: '/cameras/list',
    },

    // License (legacy endpoint)
    LICENSE: {
      STATUS: '/license-status',
    },

    // AI Features
    AI: {
      CONFIG: '/ai/config',
      TEST: '/ai/test',
      STATS: '/ai/stats',
      RECOVERY_LOGS: '/ai/recovery-logs',
    },

    // Cloud Storage
    CLOUD: {
      GMAIL_AUTH_STATUS: '/cloud/gmail-auth-status',
      DRIVE_AUTH_STATUS: '/cloud/drive-auth-status',
      DRIVE_AUTH: '/cloud/drive-auth',
      LIST_SUBFOLDERS: '/cloud/list_subfolders',
      DISCONNECT: '/cloud/disconnect',
      SET_SETUP_STEP: '/cloud/set-setup-step',
    },

    // Docker & Configuration
    CONFIG: {
      SCAN_FOLDERS: '/config/scan-folders',
      SETUP_LOCAL_SOURCE: '/docker/setup-local-source',
    },
  },

  // Helper to build full URL
  buildUrl(endpoint: string): string {
    return `${this.BASE_URL}${endpoint}`;
  },

  // Default fetch options with credentials
  defaultFetchOptions: {
    credentials: 'include' as RequestCredentials,
    headers: {
      'Content-Type': 'application/json',
    },
  },
};

export default API_CONFIG;

// Export individual helpers for common use cases
export const getApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};

export const fetchWithCredentials = async (
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> => {
  return fetch(getApiUrl(endpoint), {
    ...API_CONFIG.defaultFetchOptions,
    ...options,
    headers: {
      ...API_CONFIG.defaultFetchOptions.headers,
      ...options.headers,
    },
  });
};
