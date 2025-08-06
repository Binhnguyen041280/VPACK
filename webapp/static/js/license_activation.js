/**
 * V_Track Desktop License Activation System
 * Handles license key validation and activation
 */

class VTrackLicenseActivation {
    constructor() {
        this.isActivating = false;
        
        // DOM elements
        this.activationForm = document.getElementById('activation-form');
        this.licenseKeyInput = document.getElementById('license-key');
        this.activationMessageContainer = document.getElementById('activation-message');
        this.activationButton = this.activationForm?.querySelector('button[type="submit"]');
        
        this.init();
    }
    
    /**
     * Initialize the license activation system
     */
    init() {
        console.log('🔑 V_Track License Activation initializing...');
        
        // Bind event listeners
        this.bindEvents();
        
        // Check existing license status
        this.checkExistingLicense();
        
        console.log('✅ License activation system initialized');
    }
    
    /**
     * Bind event listeners
     */
    bindEvents() {
        // Activation form submission
        if (this.activationForm) {
            this.activationForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.activateLicense();
            });
        }
        
        // License key input validation
        if (this.licenseKeyInput) {
            this.licenseKeyInput.addEventListener('input', () => {
                this.validateLicenseKeyFormat();
            });
            
            this.licenseKeyInput.addEventListener('paste', (e) => {
                // Clean pasted license key
                setTimeout(() => {
                    this.cleanLicenseKey();
                }, 10);
            });
        }
    }
    
    /**
     * Check if there's an existing active license
     */
    async checkExistingLicense() {
        try {
            // Try to get current license status from backend
            const response = await this.apiCall('/api/payment/license-status', {
                method: 'GET'
            });
            
            if (response && response.success && response.license) {
                this.displayExistingLicense(response.license);
            }
        } catch (error) {
            console.log('ℹ️ No existing license found or error checking:', error.message);
        }
    }
    
    /**
     * Display existing license information
     */
    displayExistingLicense(license) {
        const expiryDate = this.formatDate(license.expires_at);
        const isExpired = new Date(license.expires_at) < new Date();
        
        if (isExpired) {
            this.showActivationMessage(
                `⚠️ License hiện tại đã hết hạn (${expiryDate}). Vui lòng kích hoạt license mới.`,
                'warning'
            );
        } else {
            this.showActivationMessage(
                `✅ License đang hoạt động: ${license.package_name}<br>
                 📅 Hết hạn: ${expiryDate}<br>
                 🔑 Key: ...${license.license_key.slice(-8)}`,
                'success'
            );
        }
    }
    
    /**
     * Validate license key format as user types
     */
    validateLicenseKeyFormat() {
        const licenseKey = this.licenseKeyInput?.value?.trim();
        
        if (!licenseKey) {
            this.clearActivationMessage();
            return false;
        }
        
        // Accept multiple formats:
        // 1. VT-XXXX-XXXX-XXXX-XXXX (original format)  
        // 2. VTRACK-XXX-XXXXXXXXXX-XXXXXXXX (new format)
        // 3. TEST-VTRACK-2025-XXXXXXXXXXXX (test format)
        // 4. Any string 16+ characters (flexible)
        // 5. UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        
        const formats = [
            /^VT-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/,  // VT format
            /^VTRACK-[A-Z0-9]{3}-[A-Z0-9]{10}-[A-Z0-9]{8}$/,  // New VTRACK format
            /^TEST-VTRACK-\d{4}-\d{14}$/,  // Test format
            /^[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}$/,  // UUID
            /^[A-Za-z0-9\-_]{16,}$/  // Generic 16+ chars
        ];
        
        const isValidFormat = formats.some(regex => regex.test(licenseKey));
        
        if (!isValidFormat && licenseKey.length > 5) {
            this.showActivationMessage('❌ License key quá ngắn hoặc chứa ký tự không hợp lệ', 'error');
            return false;
        } else if (isValidFormat || licenseKey.length >= 16) {
            this.showActivationMessage('✅ Định dạng license key hợp lệ', 'success');
            return true;
        }
        
        this.clearActivationMessage();
        return false;
    }
    
    /**
     * Clean pasted license key (remove extra spaces, newlines, etc.)
     */
    cleanLicenseKey() {
        if (!this.licenseKeyInput) return;
        
        let licenseKey = this.licenseKeyInput.value;
        
        // Remove extra whitespace and convert to uppercase only if needed
        licenseKey = licenseKey.replace(/\s+/g, '').trim();
        
        // Keep original case for UUID-style keys
        if (!licenseKey.includes('-') && licenseKey.length === 32) {
            // Might be a UUID without dashes, add them
            licenseKey = licenseKey.replace(/(.{8})(.{4})(.{4})(.{4})(.{12})/, '$1-$2-$3-$4-$5');
        }
        
        this.licenseKeyInput.value = licenseKey;
        this.validateLicenseKeyFormat();
    }
    
    /**
     * Activate license key - FIXED TO CALL activate-license API
     */
    async activateLicense() {
        if (!this.validateLicenseKeyFormat()) {
            this.showActivationMessage('❌ Vui lòng nhập license key hợp lệ', 'error');
            return;
        }
        
        const licenseKey = this.licenseKeyInput.value.trim();
        
        try {
            this.isActivating = true;
            this.updateActivationButton('⏳ Đang kích hoạt...', true);
            this.showActivationMessage('🔄 Đang xác thực và lưu license vào hệ thống...', 'loading');
            
            console.log('🔑 Activating license:', licenseKey.substring(0, 20) + '...');
            
            // IMPORTANT: Call activate-license API instead of validate-license
            const response = await this.apiCall('/api/payment/activate-license', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    license_key: licenseKey
                })
            });
            
            console.log('📋 Activation response:', response);
            
            if (response && response.success && response.valid) {
                this.handleSuccessfulActivation(response.data);
            } else {
                this.handleActivationFailure(response?.error || 'License key không hợp lệ hoặc đã hết hạn');
            }
        } catch (error) {
            console.error('❌ License activation failed:', error);
            this.handleActivationFailure(`Lỗi kết nối: ${error.message}`);
        } finally {
            this.isActivating = false;
            this.updateActivationButton('🚀 Activate License', false);
        }
    }
    
    /**
     * Handle successful license activation
     */
    handleSuccessfulActivation(licenseData) {
        console.log('✅ License activated successfully:', licenseData);
        
        // Show success message with license details
        const expiryDate = this.formatDate(licenseData.expires_at);
        const packageName = licenseData.package_name || licenseData.product_type || 'Desktop License';
        
        this.showActivationMessage(
            `✅ License kích hoạt thành công!<br>
             📦 Gói: ${packageName}<br>
             📅 Hết hạn: ${expiryDate}<br>
             🎯 Tất cả tính năng đã được mở khóa!<br>
             💾 License đã được lưu vào hệ thống`,
            'success'
        );
        
        // Clear the input field
        if (this.licenseKeyInput) {
            this.licenseKeyInput.value = '';
        }
        
        // Show reload suggestion
        setTimeout(() => {
            this.showActivationMessage(
                `✅ License kích hoạt thành công!<br>
                 📦 Gói: ${packageName}<br>
                 📅 Hết hạn: ${expiryDate}<br>
                 🔄 Vui lòng khởi động lại ứng dụng để áp dụng thay đổi.`,
                'success'
            );
        }, 5000);
    }
    
    /**
     * Handle license activation failure
     */
    handleActivationFailure(errorMessage) {
        console.error('❌ License activation failed:', errorMessage);
        
        let userMessage = '❌ Kích hoạt license thất bại: ';
        
        if (errorMessage.includes('not found') || errorMessage.includes('invalid')) {
            userMessage += 'License key không tồn tại hoặc không hợp lệ.';
        } else if (errorMessage.includes('expired')) {
            userMessage += 'License key đã hết hạn.';
        } else if (errorMessage.includes('already used')) {
            userMessage += 'License key đã được sử dụng.';
        } else if (errorMessage.includes('network') || errorMessage.includes('timeout')) {
            userMessage += 'Lỗi kết nối mạng. Vui lòng thử lại.';
        } else {
            userMessage += errorMessage;
        }
        
        this.showActivationMessage(userMessage, 'error');
    }
    
    /**
     * Update activation button state
     */
    updateActivationButton(text, disabled = false) {
        if (this.activationButton) {
            const buttonText = this.activationButton.querySelector('.button-text');
            if (buttonText) {
                buttonText.textContent = text;
            } else {
                this.activationButton.innerHTML = text;
            }
            this.activationButton.disabled = disabled;
        }
    }
    
    /**
     * Show activation message
     */
    showActivationMessage(message, type = 'info') {
        if (!this.activationMessageContainer) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.innerHTML = message;
        
        this.activationMessageContainer.innerHTML = '';
        this.activationMessageContainer.appendChild(messageDiv);
        
        // Auto-hide success messages after 10 seconds
        if (type === 'success') {
            setTimeout(() => {
                if (messageDiv.parentNode) {
                    messageDiv.style.opacity = '0.7';
                }
            }, 10000);
        }
    }
    
    /**
     * Clear activation message
     */
    clearActivationMessage() {
        if (this.activationMessageContainer) {
            this.activationMessageContainer.innerHTML = '';
        }
    }
    
    /**
     * Format date for display
     */
    formatDate(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('vi-VN', {
                year: 'numeric',
                month: '2-digit',  
                day: '2-digit'
            });
        } catch (error) {
            return dateString;
        }
    }
    
    /**
     * Make API call with error handling
     */
    async apiCall(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000);
        
        try {
            console.log('🌐 API Call:', url, options);
            
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const result = await response.json();
                console.log('📨 API Response:', result);
                return result;
            } else {
                throw new Error('Invalid response format');
            }
        } catch (error) {
            clearTimeout(timeoutId);
            console.error('🚫 API Error:', error);
            
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            throw error;
        }
    }
    
    /**
     * Get system status for debugging
     */
    getSystemStatus() {
        return {
            isActivating: this.isActivating,
            licenseKeyValue: this.licenseKeyInput?.value || '',
            licenseKeyValid: this.validateLicenseKeyFormat(),
            hasActivationForm: !!this.activationForm,
            hasLicenseKeyInput: !!this.licenseKeyInput
        };
    }
}

// Initialize license activation system when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on the payment page with activation form
    if (document.getElementById('activation-form')) {
        console.log('🔧 DOM loaded, initializing license activation system...');
        window.licenseActivation = new VTrackLicenseActivation();
    }
});

// Export for testing/debugging
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VTrackLicenseActivation;
}