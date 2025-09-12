import { 
  PricingResponse, 
  CreatePaymentRequest, 
  CreatePaymentResponse,
  LicenseActivationRequest,
  LicenseActivationResponse,
  LicenseStatusResponse
} from '@/types/account';

const API_BASE = 'http://localhost:8080/api';

export class PaymentService {
  /**
   * Fetch available pricing packages from Google Cloud Function
   */
  static async getPackages(): Promise<PricingResponse> {
    try {
      const response = await fetch(`${API_BASE}/payment/packages`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to load packages');
      }

      return data;
    } catch (error) {
      console.error('Failed to fetch pricing packages:', error);
      throw error;
    }
  }

  /**
   * Get packages for upgrade (excludes current package)
   */
  static async getUpgradePackages(): Promise<PricingResponse> {
    try {
      const response = await fetch(`${API_BASE}/payment/packages?for_upgrade=true`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to load upgrade packages');
      }

      return data;
    } catch (error) {
      console.error('Failed to fetch upgrade packages:', error);
      throw error;
    }
  }

  /**
   * Create a payment session with PayOS
   */
  static async createPayment(request: CreatePaymentRequest): Promise<CreatePaymentResponse> {
    try {
      const response = await fetch(`${API_BASE}/payment/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...request,
          provider: request.provider || 'payos'
        })
      });

      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || result.message || 'Failed to create payment');
      }

      return result;
    } catch (error) {
      console.error('Payment creation error:', error);
      throw error;
    }
  }

  /**
   * Get current license status
   */
  static async getLicenseStatus(): Promise<LicenseStatusResponse> {
    try {
      console.log('📡 Fetching license status from:', `${API_BASE}/payment/license-status`);
      
      const response = await fetch(`${API_BASE}/payment/license-status`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (!response.ok) {
        console.warn('❌ License status API failed:', response.status, response.statusText);
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      console.log('📊 License status data received:', data);
      
      return data;
    } catch (error) {
      console.error('❌ Failed to get license status:', error);
      throw error;
    }
  }

  /**
   * Activate a license key
   */
  static async activateLicense(request: LicenseActivationRequest): Promise<LicenseActivationResponse> {
    try {
      const response = await fetch(`${API_BASE}/payment/activate-license`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      });

      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || 'License activation failed');
      }

      return result;
    } catch (error) {
      console.error('License activation error:', error);
      throw error;
    }
  }

  /**
   * Format price in Vietnamese Dong
   */
  static formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND',
      minimumFractionDigits: 0
    }).format(price);
  }

  /**
   * Get badge for package type
   */
  static getBadgeForPackage(packageCode: string): string | null {
    switch (packageCode) {
      case 'personal_1y':
        return '🔥 POPULAR';
      case 'business_1y':
        return '💎 BEST VALUE';
      case 'trial_24h':
        return '⏰ TRIAL';
      default:
        return null;
    }
  }

  /**
   * Format duration text
   */
  static formatDuration(durationDays: number): string {
    if (durationDays === 1) return '24 giờ';
    if (durationDays === 30) return '30 ngày';
    if (durationDays === 365) return '365 ngày';
    return `${durationDays} ngày`;
  }

  /**
   * Handle PayOS popup payment flow
   */
  static openPayOSPopup(paymentUrl: string, onComplete: (result: any) => void): void {
    const popup = window.open(
      paymentUrl,
      'payos_payment',
      'width=600,height=700,scrollbars=yes,resizable=yes'
    );

    if (!popup) {
      throw new Error('Please allow popups to complete payment');
    }

    // Handle payment messages
    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== 'http://localhost:8080') return;

      if (event.data.type === 'payment_flow_completed') {
        clearInterval(checkClosed);
        window.removeEventListener('message', handleMessage);
        
        onComplete({
          status: event.data.status,
          orderCode: event.data.orderCode
        });
      }
    };

    window.addEventListener('message', handleMessage);

    // Monitor popup close
    const checkClosed = setInterval(() => {
      if (popup.closed) {
        clearInterval(checkClosed);
        window.removeEventListener('message', handleMessage);
        
        onComplete({
          status: 'closed',
          message: 'Payment window was closed'
        });
      }
    }, 1000);

    // Auto-close after 15 minutes
    setTimeout(() => {
      if (!popup.closed) {
        popup.close();
        clearInterval(checkClosed);
        window.removeEventListener('message', handleMessage);
        onComplete({
          status: 'timeout',
          message: 'Payment timed out'
        });
      }
    }, 15 * 60 * 1000);
  }
}