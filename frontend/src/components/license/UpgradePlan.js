import { useState } from 'react';

const UpgradePlan = ({ currentLicense, userEmail, onUpgradeInitiated, onClose }) => {
  const [selectedPackage, setSelectedPackage] = useState('business_1y');
  const [isLoading, setIsLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  // FIXED: Custom notification system instead of alert()
  const showNotification = (message, type = 'info') => {
    setNotification({ message, type, timestamp: Date.now() });
    setTimeout(() => setNotification(null), 5000);
  };

  const upgradeOptions = {
    'personal_1y': {
      name: 'Personal Annual',
      price: 20000,
      duration: '365 ngày',
      features: ['Unlimited cameras', 'Advanced analytics', 'Priority support'],
      badge: null
    },
    'business_1m': {
      name: 'Business Monthly',
      price: 5000,
      duration: '30 ngày',
      features: ['Multi-location support', 'Advanced analytics', 'API access', 'Priority support'],
      badge: null
    },
    'business_1y': {
      name: 'Business Annual',
      price: 50000,
      duration: '365 ngày',
      features: ['Multi-location support', 'Advanced analytics', 'API access', 'Dedicated support'],
      badge: '🚀 RECOMMENDED'
    }
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND',
      minimumFractionDigits: 0
    }).format(price);
  };

  const handleUpgrade = async () => {
    if (!userEmail) {
      // FIXED: Use custom notification instead of alert()
      showNotification('Vui lòng đăng nhập trước khi nâng cấp', 'error');
      return;
    }

    setIsLoading(true);

    try {
      // Create upgrade payment
      const response = await fetch('http://localhost:8080/api/payment/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_email: userEmail,
          package_type: selectedPackage,
          provider: 'payos',
          upgrade_from: currentLicense?.package_type || 'unknown'
        })
      });

      const result = await response.json();

      if (result.success && result.payment_url) {
        // Notify parent component
        if (onUpgradeInitiated) {
          onUpgradeInitiated({
            from: currentLicense?.package_type,
            to: selectedPackage,
            email: userEmail,
            order_code: result.order_code
          });
        }

        // FIXED: Custom notification instead of alert()
        showNotification('Đang chuyển hướng đến trang thanh toán...', 'info');

        // Open payment popup
        const popup = window.open(
          result.payment_url,
          'payos_upgrade',
          'width=600,height=700,scrollbars=yes,resizable=yes'
        );

        if (!popup) {
          showNotification('Vui lòng cho phép popup để mở trang thanh toán', 'warning');
          return;
        }

        // FIXED: Handle payment messages without alerts
        const handleMessage = (event) => {
          if (event.origin !== 'http://localhost:8080') return;

          if (event.data.type === 'payment_flow_completed') {
            clearInterval(checkClosed);
            window.removeEventListener('message', handleMessage);
            
            // FIXED: Check actual payment status
            const urlParams = new URLSearchParams(window.location.search);
            const paymentStatus = urlParams.get('status');
            const paymentCode = urlParams.get('code');
            
            if (paymentCode === '00') {
              // FIXED: Use custom notification instead of alert()
              showNotification(
                `✅ Thay đổi gói thành công!\n\nMã đơn: ${event.data.orderCode || result.order_code}\nLicense key mới đã được gửi về email: ${userEmail}\n\nVui lòng kiểm tra email và kích hoạt license key mới.`,
                'success'
              );
            } else if (paymentStatus === 'CANCELLED') {
              // FIXED: Use custom notification instead of alert()
              showNotification('❌ Thanh toán đã bị hủy. Thay đổi gói không thành công.', 'warning');
            } else {
              // FIXED: Use custom notification instead of alert()
              showNotification('✅ Thanh toán đã hoàn tất!\n\nVui lòng kiểm tra email để lấy license key mới (nếu thanh toán thành công).', 'info');
            }
          }
        };

        window.addEventListener('message', handleMessage);

        // FIXED: Fallback monitoring without alerts
        const checkClosed = setInterval(() => {
          if (popup.closed) {
            clearInterval(checkClosed);
            window.removeEventListener('message', handleMessage);
            
            console.log('PayOS upgrade popup closed without message');
            // FIXED: Use custom notification instead of alert()
            showNotification('Cửa sổ thanh toán đã đóng. Nếu bạn đã thanh toán thành công, vui lòng kiểm tra email để lấy license key mới.', 'info');
          }
        }, 1000);

        // Auto-close popup after 15 minutes (timeout)
        setTimeout(() => {
          if (!popup.closed) {
            popup.close();
            clearInterval(checkClosed);
            window.removeEventListener('message', handleMessage);
            showNotification('Hết thời gian chờ thanh toán. Vui lòng thử lại nếu cần.', 'warning');
          }
        }, 15 * 60 * 1000);

      } else {
        // FIXED: Use custom notification instead of alert()
        showNotification('Không thể tạo thanh toán: ' + (result.error || result.message || 'Lỗi không xác định'), 'error');
      }
    } catch (error) {
      console.error('Upgrade payment error:', error);
      // FIXED: Use custom notification instead of alert()
      showNotification('Lỗi kết nối. Vui lòng thử lại sau.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // FIXED: Custom Notification Component
  const CustomNotification = () => {
    if (!notification) return null;
    
    const typeStyles = {
      success: 'bg-green-50 border-green-200 text-green-800',
      error: 'bg-red-50 border-red-200 text-red-800',
      warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
      info: 'bg-blue-50 border-blue-200 text-blue-800'
    };
    
    return (
      <div className={`fixed top-4 right-4 z-50 p-4 border rounded-lg shadow-lg max-w-md ${typeStyles[notification.type]} animate-slide-in`}>
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <p className="text-sm font-medium whitespace-pre-line">{notification.message}</p>
          </div>
          <button 
            onClick={() => setNotification(null)}
            className="ml-3 text-gray-400 hover:text-gray-600 text-lg leading-none"
          >
            ×
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4 relative">
      {/* FIXED: Custom Notification */}
      <CustomNotification />
      
      <h3 className="text-lg font-semibold text-white mb-4">Nâng cấp gói license</h3>
      
      {/* Current License Info */}
      <div className="bg-gray-700 p-4 rounded-lg mb-4">
        <h4 className="text-white font-medium mb-2">Gói hiện tại</h4>
        <div className="space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Loại gói:</span>
            <span className="text-white">{currentLicense?.package_type || 'Unknown'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Hết hạn:</span>
            <span className="text-white">
              {currentLicense?.expires_at 
                ? new Date(currentLicense.expires_at).toLocaleDateString('vi-VN')
                : 'Không giới hạn'
              }
            </span>
          </div>
        </div>
      </div>
      
      {/* Upgrade Options */}
      <div className="space-y-3">
        {Object.entries(upgradeOptions).map(([key, option]) => (
          <div
            key={key}
            className={`relative p-4 border-2 rounded-lg cursor-pointer transition-all ${
              selectedPackage === key
                ? 'border-purple-500 bg-purple-600 bg-opacity-20'
                : 'border-gray-600 bg-gray-700 hover:border-gray-500'
            }`}
            onClick={() => setSelectedPackage(key)}
          >
            {option.badge && (
              <div className="absolute -top-2 -right-2 bg-purple-500 text-white text-xs px-2 py-1 rounded-full font-bold">
                {option.badge}
              </div>
            )}
            
            <div className="flex justify-between items-start">
              <div className="space-y-2 flex-1">
                <h4 className="font-semibold text-white">{option.name}</h4>
                <div className="text-xl font-bold text-purple-400">{formatPrice(option.price)}</div>
                <div className="text-sm text-gray-400">Thời hạn: {option.duration}</div>
                
                <ul className="space-y-1 text-sm text-gray-300">
                  {option.features.map((feature, idx) => (
                    <li key={idx} className="flex items-center">
                      <span className="text-green-400 mr-2">✓</span>
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
              
              {selectedPackage === key && (
                <div className="ml-2">
                  <div className="w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center">
                    <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Upgrade Summary */}
      <div className="bg-gray-700 p-4 rounded-lg">
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Nâng cấp lên:</span>
            <span className="text-white font-medium">{upgradeOptions[selectedPackage].name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Giá:</span>
            <span className="text-purple-400 font-bold">{formatPrice(upgradeOptions[selectedPackage].price)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Email:</span>
            <span className="text-white">{userEmail}</span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={onClose}
          className="flex-1 py-2 px-4 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
        >
          Hủy
        </button>
        <button
          onClick={handleUpgrade}
          disabled={isLoading}
          className="flex-2 py-2 px-4 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 disabled:from-gray-600 disabled:to-gray-600 text-white rounded-lg transition-all font-medium disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Đang xử lý...
            </span>
          ) : (
            `🚀 Nâng cấp lên ${upgradeOptions[selectedPackage].name}`
          )}
        </button>
      </div>

      {/* Upgrade Info */}
      <div className="text-xs text-gray-400 space-y-1">
        <p>• License cũ sẽ được thay thế bằng license mới</p>
        <p>• License key mới được gửi về email sau khi thanh toán</p>
        <p>• Hỗ trợ: alanngaongo@gmail.com</p>
      </div>
      
      {/* FIXED: Add custom CSS for animations */}
      <style jsx>{`
        @keyframes slide-in {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
        
        .animate-slide-in {
          animation: slide-in 0.3s ease-out;
        }
      `}</style>
    </div>
  );
};

export default UpgradePlan;