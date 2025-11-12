/**
 * API Configuration
 * Centralized API endpoint configuration to avoid hardcoded URLs
 *
 * Environment Variables:
 * - NEXT_PUBLIC_API_BASE_URL: Base URL for API endpoints (default: http://localhost:8080)
 * - NEXT_PUBLIC_API_TIMEOUT: Request timeout in milliseconds (default: 30000)
 */

// Base URL configuration - supports production deployment
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';

// API timeout configuration
export const API_TIMEOUT = parseInt(process.env.NEXT_PUBLIC_API_TIMEOUT || '30000', 10);

/**
 * Centralized API endpoints
 * All API paths should be defined here for easy maintenance
 */
export const API_ENDPOINTS = {
  // Program Management
  programs: {
    base: '/api/programs',
    list: '/api/programs',
    byId: (id: string | number) => `/api/programs/${id}`,
    create: '/api/programs',
    update: (id: string | number) => `/api/programs/${id}`,
    delete: (id: string | number) => `/api/programs/${id}`,
    export: (id: string | number) => `/api/programs/${id}/export`,
  },

  // Step Configuration
  steps: {
    base: '/api/config/steps',
    list: '/api/config/steps',
    create: '/api/config/steps',
    update: (stepId: string | number) => `/api/config/steps/${stepId}`,
    delete: (stepId: string | number) => `/api/config/steps/${stepId}`,
    reorder: '/api/config/steps/reorder',
  },

  // Step 1: Video Source Configuration
  step1: {
    sources: '/api/config/step1/sources',
    addSource: '/api/config/step1/sources',
    updateSource: (sourceId: string | number) => `/api/config/step1/sources/${sourceId}`,
    deleteSource: (sourceId: string | number) => `/api/config/step1/sources/${sourceId}`,
    testConnection: '/api/config/step1/test-connection',
  },

  // Step 2: Advanced Settings
  step2: {
    settings: '/api/config/step2/settings',
    update: '/api/config/step2/settings',
  },

  // Step 3: Scheduling
  step3: {
    schedule: '/api/config/step3/schedule',
    update: '/api/config/step3/schedule',
  },

  // Step 4: ROI Configuration
  step4: {
    roi: '/api/config/step4/roi',
    streamVideo: '/api/config/step4/roi/stream-video',
    saveConfig: '/api/config/step4/roi/save',
    loadConfig: '/api/config/step4/roi/load',
  },

  // QR Detection
  qrDetection: {
    preprocess: '/api/qr-detection/preprocess-video',
    detect: '/api/qr-detection/detect',
    status: '/api/qr-detection/status',
  },

  // Hand Detection
  handDetection: {
    preprocess: '/api/hand-detection/preprocess-video',
    detect: '/api/hand-detection/detect',
    status: '/api/hand-detection/status',
  },

  // Simple Hand Detection
  simpleHandDetection: {
    preprocess: '/api/simple-hand-detection/preprocess-video',
    detect: '/api/simple-hand-detection/detect',
    status: '/api/simple-hand-detection/status',
  },

  // Cutter
  cutter: {
    base: '/api/cutter',
    process: '/api/cutter/process',
    status: '/api/cutter/status',
  },

  // Account Management
  account: {
    login: '/api/account/login',
    logout: '/api/account/logout',
    register: '/api/account/register',
    profile: '/api/account/profile',
    updateProfile: '/api/account/profile',
    changePassword: '/api/account/password',
  },

  // Payment
  payment: {
    create: '/api/payments/create',
    verify: '/api/payments/verify',
    history: '/api/payments/history',
    status: (paymentId: string) => `/api/payments/${paymentId}/status`,
  },

  // License Management
  license: {
    info: '/api/license/info',
    activate: '/api/license/activate',
    deactivate: '/api/license/deactivate',
    validate: '/api/license/validate',
  },

  // Camera Health
  camera: {
    health: '/api/camera/health',
    status: '/api/camera/status',
    restart: (cameraId: string | number) => `/api/camera/${cameraId}/restart`,
  },

  // Trace & Monitoring
  trace: {
    logs: '/api/trace/logs',
    events: '/api/trace/events',
    metrics: '/api/trace/metrics',
  },

  // Usage Statistics
  usage: {
    stats: '/api/usage/stats',
    export: '/api/usage/export',
  },

  // System
  system: {
    health: '/api/health',
    version: '/api/version',
    config: '/api/config',
  },
} as const;

/**
 * Helper function to build full API URL
 * @param endpoint - API endpoint path
 * @returns Full API URL
 */
export function buildApiUrl(endpoint: string): string {
  // Remove leading slash if present to avoid double slashes
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  return `${API_BASE_URL}/${cleanEndpoint}`;
}

/**
 * Helper function to build API URL with query parameters
 * @param endpoint - API endpoint path
 * @param params - Query parameters object
 * @returns Full API URL with query string
 */
export function buildApiUrlWithParams(endpoint: string, params: Record<string, any>): string {
  const baseUrl = buildApiUrl(endpoint);
  const queryString = new URLSearchParams(
    Object.entries(params)
      .filter(([_, value]) => value !== undefined && value !== null)
      .map(([key, value]) => [key, String(value)])
  ).toString();

  return queryString ? `${baseUrl}?${queryString}` : baseUrl;
}

/**
 * API Configuration object for export
 */
export const API_CONFIG = {
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  endpoints: API_ENDPOINTS,
  buildUrl: buildApiUrl,
  buildUrlWithParams: buildApiUrlWithParams,
} as const;

export default API_CONFIG;
