// Account and Payment related TypeScript interfaces
// Updated for Phase 4: Simplified 2-plan model (Starter vs Pro)

// License features structure - matches backend SSOT
export interface LicenseFeatures {
  default_mode: boolean;    // Pro only: true, Starter: false
  custom_mode: boolean;     // Both plans: true
  max_cameras: number;      // Starter: 5, Pro: 10
}

export interface PricingPackage {
  package_id?: string;
  code: string;
  name: string;
  price: number;
  original_price?: number;
  currency?: string;
  duration_days: number;
  features: string[] | LicenseFeatures;  // Can be array (display) or object (computed)
  description?: string;
  recommended?: boolean;
  badge?: string;
  is_active?: boolean;
  is_recommended?: boolean;
}

export interface PricingResponse {
  success: boolean;
  packages: Record<string, PricingPackage>;
  version?: string;
  timestamp?: string;
  error?: string;
}

export interface LicenseInfo {
  license_key?: string;
  package_type: string;
  package_name?: string;
  badge?: string;
  price?: number;
  features: string[] | LicenseFeatures;  // Can be array (display) or object (computed)
  expires_at?: string;      // ISO string format - SSOT field name
  created_at?: string;
  status?: 'active' | 'expired' | 'suspended';
  is_active: boolean;
  machine_fingerprint?: string;
  activation_date?: string;
  is_trial?: boolean;
}

export interface LicenseStatusResponse {
  success: boolean;
  valid: boolean;
  license?: LicenseInfo;
  trial_status?: {
    is_trial: boolean;
    status: string;
    days_left: number;
    eligible?: boolean;
    expires_at?: string;
  };
  error?: string;
}

export interface UserProfile {
  name: string;
  email: string;
  avatar?: string;
  google_drive_connected: boolean;
  oauth_session_active: boolean;
  oauth_expires_at?: string;
}

export interface PaymentTransaction {
  id: string;
  package_type: string;
  amount: number;
  status: 'pending' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  order_code?: string;
}

export interface CreatePaymentRequest {
  customer_email: string;
  package_type: string;
  provider?: string;
  upgrade_from?: string;
}

export interface CreatePaymentResponse {
  success: boolean;
  payment_url?: string;
  order_code?: string;
  error?: string;
}

export interface LicenseActivationRequest {
  license_key: string;
}

export interface LicenseActivationResponse {
  success: boolean;
  valid: boolean;
  data?: LicenseInfo;
  error?: string;
}

export interface NotificationState {
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  timestamp: number;
}

export type PaymentStep = 'packages' | 'payment' | 'activation';

export interface PaymentFlowState {
  currentStep: PaymentStep;
  selectedPackage?: string;
  paymentData?: {
    order_code: string;
    package_type: string;
    email: string;
  };
  isProcessing: boolean;
}

// Helper type guard to check if features is LicenseFeatures object
export function isLicenseFeatures(features: string[] | LicenseFeatures | undefined): features is LicenseFeatures {
  return features !== undefined &&
         typeof features === 'object' &&
         !Array.isArray(features) &&
         'max_cameras' in features;
}

// Helper to get max_cameras from license
export function getMaxCameras(license: LicenseInfo | null | undefined): number {
  if (!license) return 5; // Default to Starter limit
  if (isLicenseFeatures(license.features)) {
    return license.features.max_cameras;
  }
  // Fallback: check package_type
  if (license.package_type?.toLowerCase().includes('pro')) {
    return 10;
  }
  return 5; // Starter default
}

// Helper to check if default_mode is available
export function hasDefaultMode(license: LicenseInfo | null | undefined): boolean {
  if (!license) return false;
  if (isLicenseFeatures(license.features)) {
    return license.features.default_mode;
  }
  // Fallback: check package_type
  return license.package_type?.toLowerCase().includes('pro') ?? false;
}
