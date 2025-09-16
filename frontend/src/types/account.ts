// Account and Payment related TypeScript interfaces

export interface PricingPackage {
  code: string;
  name: string;
  price: number;
  original_price?: number;
  duration_days: number;
  features: string[];
  description?: string;
  recommended?: boolean;
  badge?: string;
}

export interface PricingResponse {
  success: boolean;
  packages: Record<string, PricingPackage>;
  version?: string;
  timestamp?: string;
  error?: string;
}

export interface LicenseInfo {
  package_type: string;
  expires_at?: string;
  is_active: boolean;
  features: string[];
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