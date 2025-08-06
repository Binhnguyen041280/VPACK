/**
 * V_Track Desktop Payment System
 * Version: 2.1.0 - Complete Fix - No Loop
 */

class VTrackPaymentSystem {
    constructor() {
        this.selectedPackage = '';
        this.packages = {};
        this.isProcessing = false;
        this.isLoadingPackages = false;
        
        // DOM elements
        this.packagesContainer = document.getElementById('packages-container');
        this.paymentForm = document.getElementById('payment-form');
        this.paymentButton = document.getElementById('payment-btn');
        this.emailInput = document.getElementById('customer-email');
        this.messageContainer = document.getElementById('message-container');
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.loadingText = document.getElementById('loading-text');
        
        // Bind methods to prevent context loss
        this.loadPackages = this.loadPackages.bind(this);
        this.selectPackage = this.selectPackage.bind(this);
        
        this.init();
    }
    
    /**
     * Initialize the payment system
     */
    init() {
        console.log('🚀 V_Track Payment System initializing...');
        
        // Check if DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.setup();
            });
        } else {
            this.setup();
        }
    }
    
    /**
     * Setup after DOM is ready
     */
    setup() {
        // Re-get DOM elements in case they weren't available during construction
        this.packagesContainer = document.getElementById('packages-container');
        this.paymentForm = document.getElementById('payment-form');
        this.paymentButton = document.getElementById('payment-btn');
        this.emailInput = document.getElementById('customer-email');
        this.messageContainer = document.getElementById('message-container');
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.loadingText = document.getElementById('loading-text');
        
        // Bind event listeners
        this.bindEvents();
        
        // Load packages
        this.loadPackages();
        
        console.log('✅ Payment system initialized');
    }
    
    /**
     * Bind event listeners
     */
    bindEvents() {
        // Payment form submission
        if (this.paymentForm) {
            this.paymentForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.processPayment();
            });
        }
        
        // Email input validation - NO LOOP
        if (this.emailInput) {
            this.emailInput.addEventListener('input', () => {
                this.updateFormValidation();
            });
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideLoadingOverlay();
            }
        });
    }
    
    /**
     * Update form validation - SINGLE FUNCTION NO LOOP
     */
    updateFormValidation() {
        const email = this.emailInput?.value?.trim();
        const isEmailValid = email && this.isValidEmail(email);
        const isPackageSelected = !!this.selectedPackage;
        const isFormValid = isEmailValid && isPackageSelected && !this.isProcessing;
        
        // Update email border
        if (this.emailInput) {
            this.emailInput.style.borderColor = isEmailValid ? 'var(--success-color)' : 'var(--border-color)';
        }
        
        // Update payment button
        if (this.paymentButton) {
            this.paymentButton.disabled = !isFormValid;
        }
        
        return isFormValid;
    }
    
    /**
     * Load available packages from API
     */
    async loadPackages() {
        // Prevent multiple simultaneous calls
        if (this.isLoadingPackages) {
            console.log('⚠️ Packages already loading, skipping...');
            return;
        }
        
        try {
            this.isLoadingPackages = true;
            this.showMessage('🔄 Đang tải danh sách gói...', 'loading');
            
            console.log('📦 Loading packages...');
            
            const response = await this.apiCall('/api/payment/packages', {
                method: 'GET'
            });
            
            if (response && response.success && response.packages) {
                this.packages = response.packages;
                this.renderPackages();
                this.clearMessage();
                console.log('✅ Packages loaded:', Object.keys(this.packages).length);
            } else {
                throw new Error(response?.error || 'Invalid response format');
            }
        } catch (error) {
            console.error('❌ Failed to load packages:', error);
            this.showMessage(`❌ Không thể tải danh sách gói: ${error.message}`, 'error');
            this.renderErrorState();
        } finally {
            this.isLoadingPackages = false;
        }
    }
    
    /**
     * Render packages in the UI
     */
    renderPackages() {
        if (!this.packagesContainer) return;
        
        const packageOrder = ['personal_1m', 'personal_1y', 'business_1m', 'business_1y'];
        let html = '';
        
        packageOrder.forEach(packageKey => {
            if (!this.packages[packageKey]) return;
            
            const pkg = this.packages[packageKey];
            const icon = this.getPackageIcon(packageKey);
            const badge = this.getPackageBadge(packageKey);
            const isPopular = packageKey === 'personal_1y' || packageKey === 'business_1y';
            
            html += `
                <div class="package-card ${isPopular ? 'popular' : ''}" 
                     data-package="${packageKey}" 
                     onclick="window.paymentSystem.selectPackage('${packageKey}')">
                    ${badge}
                    <div class="package-header">
                        <div class="package-name">${icon} ${pkg.name}</div>
                        <div class="package-price">${this.formatPrice(pkg.price)}</div>
                    </div>
                    <div class="package-description">${pkg.description}</div>
                    <ul class="package-features">
                        ${pkg.features.map(feature => `<li>${this.formatFeature(feature)}</li>`).join('')}
                        <li>⏰ ${pkg.duration_days} ngày sử dụng</li>
                    </ul>
                </div>
            `;
        });
        
        this.packagesContainer.innerHTML = html;
        
        // Auto-select most popular package
        const defaultPackage = 'personal_1y';
        if (this.packages[defaultPackage]) {
            setTimeout(() => this.selectPackage(defaultPackage), 100);
        }
    }
    
    /**
     * Get package icon based on type
     */
    getPackageIcon(packageKey) {
        if (packageKey.includes('business')) return '🏢';
        return '👤';
    }
    
    /**
     * Get package badge HTML
     */
    getPackageBadge(packageKey) {
        if (packageKey.includes('1y')) {
            return '<div class="package-badge save">🔥 POPULAR</div>';
        }
        return '';
    }
    
    /**
     * Format price for display
     */
    formatPrice(price) {
        if (!price) return 'N/A';
        return new Intl.NumberFormat('vi-VN', {
            style: 'currency',
            currency: 'VND',
            minimumFractionDigits: 0
        }).format(price);
    }
    
    /**
     * Format feature names
     */
    formatFeature(feature) {
        const featureMap = {
            'unlimited_cameras': 'Camera không giới hạn',
            'basic_analytics': 'Phân tích cơ bản',
            'advanced_analytics': 'Phân tích nâng cao',
            'email_support': 'Hỗ trợ email',
            'priority_support': 'Hỗ trợ ưu tiên',
            'dedicated_support': 'Hỗ trợ chuyên biệt',
            'api_access': 'Truy cập API',
            'multi_location_support': 'Hỗ trợ đa địa điểm',
            'Unlimited cameras': 'Camera không giới hạn',
            'Basic analytics': 'Phân tích cơ bản',
            'Advanced analytics': 'Phân tích nâng cao',
            'Email support': 'Hỗ trợ email',
            'Priority support': 'Hỗ trợ ưu tiên',
            'API access': 'Truy cập API',
            'Multi-location support': 'Hỗ trợ đa địa điểm'
        };
        
        return featureMap[feature] || feature;
    }
    
    /**
     * Select a package
     */
    selectPackage(packageKey) {
        console.log('📦 Selecting package:', packageKey);
        
        // Remove previous selection
        document.querySelectorAll('.package-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        // Select new package
        const selectedCard = document.querySelector(`[data-package="${packageKey}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
            this.selectedPackage = packageKey;
            
            // Update validation
            this.updateFormValidation();
            
            console.log('✅ Package selected:', packageKey);
        }
    }
    
    /**
     * Check if email format is valid
     */
    isValidEmail(email) {
        if (!email || email.length < 5) return false;
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    /**
     * Process payment
     */
    async processPayment() {
        if (!this.updateFormValidation()) {
            this.showMessage('❌ Vui lòng kiểm tra thông tin và thử lại', 'error');
            return;
        }
        
        const email = this.emailInput.value.trim();
        
        try {
            this.isProcessing = true;
            this.updatePaymentButton('⏳ Đang xử lý...', true);
            this.showLoadingOverlay('Đang tạo đơn thanh toán...');
            this.showMessage('🔄 Đang tạo đơn thanh toán, vui lòng đợi...', 'loading');
            
            console.log('💳 Processing payment:', { email, package: this.selectedPackage });
            
            const response = await this.apiCall('/api/payment/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    customer_email: email,
                    package_type: this.selectedPackage,
                    provider: 'payos'
                })
            });
            
            if (response && response.success && response.payment_url) {
                this.showMessage('✅ Đơn thanh toán đã được tạo thành công!', 'success');
                
                // Open payment URL
                setTimeout(() => {
                    this.openPaymentUrl(response.payment_url);
                    this.showMessage('💡 Cửa sổ thanh toán đã mở. Hoàn tất thanh toán để nhận license key qua email.', 'info');
                }, 1500);
                
                console.log('✅ Payment created:', response.order_code);
            } else {
                throw new Error(response?.error || 'Không thể tạo đơn thanh toán');
            }
        } catch (error) {
            console.error('❌ Payment processing failed:', error);
            this.showMessage(`❌ Lỗi: ${error.message}`, 'error');
        } finally {
            this.isProcessing = false;
            this.updatePaymentButton('💳 Thanh toán với PayOS', false);
            this.hideLoadingOverlay();
            this.updateFormValidation();
        }
    }
    
    /**
     * Open payment URL in default browser
     */
    openPaymentUrl(url) {
        try {
            // Try to open in new window/tab
            const newWindow = window.open(url, '_blank', 'noopener,noreferrer');
            
            if (!newWindow) {
                // Fallback: show URL for manual opening
                this.showMessage(
                    `💡 Vui lòng mở link thanh toán: <a href="${url}" target="_blank" style="color: var(--primary-color); text-decoration: underline;">${url}</a>`,
                    'info'
                );
            }
        } catch (error) {
            console.error('❌ Failed to open payment URL:', error);
            this.showMessage(`💡 Link thanh toán: ${url}`, 'info');
        }
    }
    
    /**
     * Update payment button state
     */
    updatePaymentButton(text, disabled = false) {
        if (this.paymentButton) {
            const buttonText = this.paymentButton.querySelector('.button-text');
            if (buttonText) {
                buttonText.textContent = text;
            } else {
                this.paymentButton.innerHTML = text;
            }
            this.paymentButton.disabled = disabled;
        }
    }
    
    /**
     * Show loading overlay
     */
    showLoadingOverlay(text = 'Processing...') {
        if (this.loadingOverlay) {
            this.loadingOverlay.classList.remove('hidden');
            if (this.loadingText) {
                this.loadingText.textContent = text;
            }
        }
    }
    
    /**
     * Hide loading overlay
     */
    hideLoadingOverlay() {
        if (this.loadingOverlay) {
            this.loadingOverlay.classList.add('hidden');
        }
    }
    
    /**
     * Show message to user
     */
    showMessage(message, type = 'info') {
        if (!this.messageContainer) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.innerHTML = message;
        
        this.messageContainer.innerHTML = '';
        this.messageContainer.appendChild(messageDiv);
        
        // Auto-hide success messages
        if (type === 'success') {
            setTimeout(() => {
                if (messageDiv.parentNode) {
                    messageDiv.remove();
                }
            }, 5000);
        }
    }
    
    /**
     * Clear message
     */
    clearMessage() {
        if (this.messageContainer) {
            this.messageContainer.innerHTML = '';
        }
    }
    
    /**
     * Render error state when packages fail to load
     */
    renderErrorState() {
        if (!this.packagesContainer) return;
        
        this.packagesContainer.innerHTML = `
            <div class="error-state" style="text-align: center; padding: 40px 20px; color: var(--text-secondary);">
                <div style="font-size: 3rem; margin-bottom: 20px;">😞</div>
                <h3>Không thể tải danh sách gói</h3>
                <p>Vui lòng kiểm tra kết nối mạng và thử lại</p>
                <button onclick="window.paymentSystem.loadPackages()" class="btn btn-primary" style="margin-top: 15px;">
                    🔄 Thử lại
                </button>
            </div>
        `;
    }
    
    /**
     * Make API call with error handling
     */
    async apiCall(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000);
        
        try {
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
                return await response.json();
            } else {
                throw new Error('Invalid response format');
            }
        } catch (error) {
            clearTimeout(timeoutId);
            
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
            selectedPackage: this.selectedPackage,
            packagesLoaded: Object.keys(this.packages).length,
            isProcessing: this.isProcessing,
            isLoadingPackages: this.isLoadingPackages,
            emailValue: this.emailInput?.value || '',
            emailValid: this.emailInput?.value ? this.isValidEmail(this.emailInput.value.trim()) : false,
            formValid: this.updateFormValidation()
        };
    }
}

// Global functions for HTML onclick handlers
window.showSupport = function() {
    alert('Hỗ trợ kỹ thuật:\n\nEmail: alanngaongo@gmail.com\nHotline: 1900-xxxx\n\nGiờ làm việc: 8:00-17:00 (T2-T6)');
};

window.showAbout = function() {
    alert('V_Track Desktop v2.1.0\n\nProfessional Video Analytics System\n\n© 2025 V_Track Team\nAll rights reserved.');
};

// Initialize payment system when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 DOM loaded, initializing payment system...');
    window.paymentSystem = new VTrackPaymentSystem();
});

// Export for testing/debugging
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VTrackPaymentSystem;
}