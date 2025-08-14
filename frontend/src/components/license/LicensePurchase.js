import { useState, useEffect } from 'react';

const LicensePurchase = ({ userEmail, onPurchaseInitiated }) => {
  const [selectedPackage, setSelectedPackage] = useState('personal_1y');
  const [isLoading, setIsLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  // ✅ NEW: Dynamic pricing state
  const [packages, setPackages] = useState({});
  const [isPricingLoading, setIsPricingLoading] = useState(true);
  const [pricingError, setPricingError] = useState(null);

  // FIXED: Custom notification system instead of alert()
  const showNotification = (message, type = 'info') => {
    setNotification({ message, type, timestamp: Date.now() });
    setTimeout(() => setNotification(null), 5000);
  };

  // ✅ NEW: Fetch pricing from API
  useEffect(() => {
    const fetchPricing = async () => {
      setIsPricingLoading(true);
      setPricingError(null);

      try {
        const response = await fetch('http://localhost:8080/api/payment/packages');
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.success && data.packages) {
          // ✅ Map API response to component format
          const mappedPackages = {};
          
          Object.entries(data.packages).forEach(([key, pkg]) => {
            mappedPackages[key] = {
              name: pkg.name,
              price: pkg.price,
              original_price: pkg.original_price || pkg.price,
              duration: pkg.duration_days === 1 ? '24 giờ' : 
                        pkg.duration_days === 30 ? '30 ngày' : 
                        pkg.duration_days === 365 ? '365 ngày' : 
                        `${pkg.duration_days} ngày`,
              features: pkg.features || [],
              description: pkg.description || '',
              badge: getBadgeForPackage(key, pkg)
            };
          });

          setPackages(mappedPackages);

          // ✅ Auto-select recommended package
          if (mappedPackages['personal_1y']) {
            setSelectedPackage('personal_1y');
          } else if (mappedPackages['business_1y']) {
            setSelectedPackage('business_1y');
          } else {
            const availableOptions = Object.keys(mappedPackages);
            if (availableOptions.length > 0) {
              setSelectedPackage(availableOptions[0]);
            }
          }

          console.log('✅ Purchase packages loaded:', mappedPackages);
        } else {
          throw new Error(data.error || 'Failed to load packages');
        }
      } catch (error) {
        console.error('❌ Failed to fetch pricing:', error);
        setPricingError(error.message);
        
        // ❌ No fallback pricing - show error only  
        setPackages({});
        showNotification(`❌ Không thể kết nối server: ${error.message}`, 'error');
      } finally {
        setIsPricingLoading(false);
      }
    };

    fetchPricing();
  }, []);

  // ✅ Helper: Get badge for package
  const getBadgeForPackage = (key, pkg) => {
    if (key === 'personal_1y') return '🔥 POPULAR';
    if (key === 'business_1y') return '💎 BEST VALUE';
    if (key === 'trial_24h') return '⏰ TRIAL';
    if (pkg.recommended) return '🚀 RECOMMENDED';
    return null;
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND',
      minimumFractionDigits: 0
    }).format(price);
  };

  const handlePurchase = async () => {
    if (!userEmail) {
      showNotification('Vui lòng đăng nhập trước khi mua license', 'error');
      return;
    }

    if (!packages[selectedPackage]) {
      showNotification('Gói đã chọn không hợp lệ', 'error');
      return;
    }

    setIsLoading(true);

    try {
      // Create payment
      const response = await fetch('http://localhost:8080/api/payment/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_email: userEmail,
          package_type: selectedPackage,
          provider: 'payos'
        })
      });

      const result = await response.json();

      if (result.success && result.payment_url) {
        // Notify parent component
        if (onPurchaseInitiated) {
          onPurchaseInitiated({
            package: selectedPackage,
            email: userEmail,
            order_code: result.order_code
          });
        }

        showNotification('Đang chuyển hướng đến trang thanh toán...', 'info');

        // Open payment popup
        const popup = window.open(
          result.payment_url,
          'payos_payment',
          'width=600,height=700,scrollbars=yes,resizable=yes'
        );

        if (!popup) {
          showNotification('Vui lòng cho phép popup để mở trang thanh toán', 'warning');
          return;
        }

        // Handle payment messages without alerts
        const handleMessage = (event) => {
          if (event.origin !== 'http://localhost:8080') return;

          if (event.data.type === 'payment_flow_completed') {
            clearInterval(checkClosed);
            window.removeEventListener('message', handleMessage);
            
            // Check actual payment status from URL params
            const urlParams = new URLSearchParams(window.location.search);
            const paymentStatus = urlParams.get('status');
            const paymentCode = urlParams.get('code');
            
            if (paymentCode === '00') {
              showNotification(
                `✅ Thanh toán thành công!\n\nMã đơn: ${event.data.orderCode || result.order_code}\nLicense key đã được gửi về email: ${userEmail}\n\nVui lòng kiểm tra email và kích hoạt license key.`,
                'success'
              );
            } else if (paymentStatus === 'CANCELLED') {
              showNotification('❌ Thanh toán đã bị hủy. Vui lòng thử lại nếu cần.', 'warning');
            } else {
              showNotification('✅ Thanh toán đã hoàn tất!\n\nVui lòng kiểm tra email để lấy license key (nếu thanh toán thành công).', 'info');
            }
          }
        };

        window.addEventListener('message', handleMessage);

        // Fallback monitoring without alerts
        const checkClosed = setInterval(() => {
          if (popup.closed) {
            clearInterval(checkClosed);
            window.removeEventListener('message', handleMessage);
            
            console.log('PayOS popup closed without message - payment status unknown');
            showNotification('Cửa sổ thanh toán đã đóng. Nếu bạn đã thanh toán thành công, vui lòng kiểm tra email để lấy license key.', 'info');
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
        showNotification('Không thể tạo thanh toán: ' + (result.error || result.message || 'Lỗi không xác định'), 'error');
      }
    } catch (error) {
      console.error('Payment creation error:', error);
      showNotification('Lỗi kết nối. Vui lòng thử lại sau.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Custom Notification Component
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

  // ✅ Loading State
  if (isPricingLoading) {
    return (
      <div className="space-y-4 relative">
        <CustomNotification />
        <div className="flex items-center justify-center py-8">
          <div className="flex items-center space-x-2 text-white">
            <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Đang tải thông tin gói...</span>
          </div>
        </div>
      </div>
    );
  }

  // ✅ Error State
  if (pricingError && Object.keys(packages).length === 0) {
    return (
      <div className="space-y-4 relative">
        <CustomNotification />
        <div className="bg-red-600 bg-opacity-20 border border-red-500 rounded-lg p-4">
          <h4 className="text-red-300 font-medium mb-2">❌ Không thể tải thông tin gói</h4>
          <p className="text-red-200 text-sm mb-3">{pricingError}</p>
          <div className="bg-yellow-600 bg-opacity-20 border border-yellow-500 rounded-lg p-3 mt-3">
            <h5 className="text-yellow-300 font-medium mb-2">📞 Liên hệ hỗ trợ</h5>
            <div className="text-yellow-200 text-sm space-y-1">
              <p>• Email: <strong>alanngaongo@gmail.com</strong></p>
              <p>• Vui lòng liên hệ để được hỗ trợ mua license</p>
              <p>• Cung cấp thông tin email và gói muốn mua</p>
            </div>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-sm mt-3"
          >
            🔄 Thử lại
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 relative">
      {/* Custom Notification */}
      <CustomNotification />
      
      <h3 className="text-lg font-semibold text-white mb-4">Chọn gói license</h3>
      
      {Object.keys(packages).length === 0 ? (
        <div className="bg-yellow-600 bg-opacity-20 border border-yellow-500 rounded-lg p-4">
          <p className="text-yellow-200">⚠️ Không có gói license khả dụng.</p>
        </div>
      ) : (
        <>
          {/* Package Selection */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(packages).map(([key, pkg]) => (
              <div
                key={key}
                className={`relative p-4 border-2 rounded-lg cursor-pointer transition-all ${
                  selectedPackage === key
                    ? 'border-blue-500 bg-blue-600 bg-opacity-20'
                    : 'border-gray-600 bg-gray-700 hover:border-gray-500'
                }`}
                onClick={() => setSelectedPackage(key)}
              >
                {pkg.badge && (
                  <div className="absolute -top-2 -right-2 bg-orange-500 text-white text-xs px-2 py-1 rounded-full font-bold">
                    {pkg.badge}
                  </div>
                )}
                
                <div className="space-y-2">
                  <h4 className="font-semibold text-white">{pkg.name}</h4>
                  <div className="flex items-center space-x-2">
                    <div className="text-2xl font-bold text-blue-400">{formatPrice(pkg.price)}</div>
                    {pkg.original_price > pkg.price && (
                      <div className="text-sm text-gray-400 line-through">{formatPrice(pkg.original_price)}</div>
                    )}
                  </div>
                  <div className="text-sm text-gray-400">Thời hạn: {pkg.duration}</div>
                  
                  {pkg.features && pkg.features.length > 0 && (
                    <ul className="space-y-1 text-sm text-gray-300">
                      {pkg.features.map((feature, idx) => (
                        <li key={idx} className="flex items-center">
                          <span className="text-green-400 mr-2">✓</span>
                          {feature}
                        </li>
                      ))}
                    </ul>
                  )}
                  
                  {pkg.description && (
                    <p className="text-xs text-gray-400">{pkg.description}</p>
                  )}
                </div>
                
                {selectedPackage === key && (
                  <div className="absolute top-2 right-2">
                    <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                      <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Purchase Info */}
          <div className="bg-gray-700 p-4 rounded-lg">
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Gói đã chọn:</span>
                <span className="text-white font-medium">{packages[selectedPackage]?.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Giá:</span>
                <span className="text-blue-400 font-bold">{formatPrice(packages[selectedPackage]?.price || 0)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Thời hạn:</span>
                <span className="text-white">{packages[selectedPackage]?.duration}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Email:</span>
                <span className="text-white">{userEmail}</span>
              </div>
            </div>
          </div>

          {/* Purchase Button */}
          <button
            onClick={handlePurchase}
            disabled={isLoading || !packages[selectedPackage]}
            className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:from-gray-600 disabled:to-gray-600 text-white rounded-lg transition-all font-medium disabled:cursor-not-allowed"
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
              `💳 Mua ${packages[selectedPackage]?.name} - ${formatPrice(packages[selectedPackage]?.price || 0)}`
            )}
          </button>

          {/* Payment Info */}
          <div className="text-xs text-gray-400 space-y-1">
            <p>• Thanh toán an toàn qua PayOS</p>
            <p>• License key được gửi về email sau khi thanh toán thành công</p>
            <p>• Hỗ trợ: alanngaongo@gmail.com</p>
            {packages[selectedPackage]?.duration === '24 giờ' && (
              <p className="text-yellow-400">• ⏰ Gói trial 24h có tính năng giới hạn</p>
            )}
            <p>• Có thể mua gói trial 24h nếu hết thời gian dùng thử</p>
          </div>
        </>
      )}
      
      {/* Custom CSS for animations */}
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

export default LicensePurchase;