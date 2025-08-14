import { useState, useEffect } from 'react';

const UpgradePlan = ({ currentLicense, userEmail, onUpgradeInitiated, onClose }) => {
  const [selectedPackage, setSelectedPackage] = useState('business_1y');
  const [isLoading, setIsLoading] = useState(false);
  const [notification, setNotification] = useState(null);
  const [showLicenseActivation, setShowLicenseActivation] = useState(false);
  const [newLicenseKey, setNewLicenseKey] = useState('');
  const [isActivatingLicense, setIsActivatingLicense] = useState(false);
  const [upgradeStep, setUpgradeStep] = useState('select'); // 'select', 'payment', 'activate'

  // ✅ NEW: Dynamic pricing state
  const [upgradeOptions, setUpgradeOptions] = useState({});
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
        const response = await fetch('http://localhost:8080/api/payment/packages?for_upgrade=true');
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.success && data.packages) {
          // ✅ Map API response to component format
          const mappedOptions = {};
          
          Object.entries(data.packages).forEach(([key, pkg]) => {
            // Skip current license package from upgrade options
            if (key === currentLicense?.package_type) {
              return;
            }

            // Map package to upgrade options format
            mappedOptions[key] = {
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

          setUpgradeOptions(mappedOptions);

          // ✅ Auto-select first available upgrade option
          const availableOptions = Object.keys(mappedOptions);
          if (availableOptions.length > 0) {
            // Prefer business_1y if available, otherwise first option
            if (mappedOptions['business_1y']) {
              setSelectedPackage('business_1y');
            } else if (mappedOptions['trial_24h']) {
              setSelectedPackage('trial_24h');
            } else {
              setSelectedPackage(availableOptions[0]);
            }
          }

          console.log('✅ Upgrade options loaded:', mappedOptions);
        } else {
          throw new Error(data.error || 'Failed to load packages');
        }
      } catch (error) {
        console.error('❌ Failed to fetch pricing:', error);
        setPricingError(error.message);
        
        // ❌ No fallback pricing - show error only
        setUpgradeOptions({});
        showNotification(`❌ Không thể kết nối server: ${error.message}`, 'error');
      } finally {
        setIsPricingLoading(false);
      }
    };

    fetchPricing();
  }, [currentLicense?.package_type]);

  // ✅ Helper: Get badge for package
  const getBadgeForPackage = (key, pkg) => {
    if (key === 'business_1y') return '🚀 RECOMMENDED';
    if (key === 'personal_1y') return '🔥 POPULAR';
    if (key === 'trial_24h') return '⏰ TRIAL';
    if (pkg.recommended) return '⭐ BEST VALUE';
    return null;
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND',
      minimumFractionDigits: 0
    }).format(price);
  };

  const handleLicenseActivation = async () => {
    if (!newLicenseKey.trim()) {
      showNotification('Vui lòng nhập license key mới', 'error');
      return;
    }

    setIsActivatingLicense(true);

    try {
      const response = await fetch('http://localhost:8080/api/payment/activate-license', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          license_key: newLicenseKey.trim()
        })
      });

      const result = await response.json();

      if (result.success && result.valid) {
        showNotification('✅ Nâng cấp hoàn tất! License mới đã được kích hoạt thành công.', 'success');
        
        // Notify parent component about successful upgrade completion
        if (onUpgradeInitiated) {
          onUpgradeInitiated({
            from: currentLicense?.package_type,
            to: selectedPackage,
            email: userEmail,
            completed: true,
            newLicense: result.data
          });
        }

        // Close the upgrade modal after successful activation
        setTimeout(() => {
          onClose();
        }, 2000);
      } else {
        showNotification('❌ ' + (result.error || 'Kích hoạt license thất bại'), 'error');
      }
    } catch (error) {
      console.error('License activation error:', error);
      showNotification('❌ Lỗi kết nối. Vui lòng thử lại.', 'error');
    } finally {
      setIsActivatingLicense(false);
    }
  };

  const handleUpgrade = async () => {
    if (!userEmail) {
      showNotification('Vui lòng đăng nhập trước khi nâng cấp', 'error');
      return;
    }

    if (!upgradeOptions[selectedPackage]) {
      showNotification('Gói đã chọn không hợp lệ', 'error');
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

        // Handle payment messages without alerts
        const handleMessage = (event) => {
          if (event.origin !== 'http://localhost:8080') return;

          if (event.data.type === 'payment_flow_completed') {
            clearInterval(checkClosed);
            window.removeEventListener('message', handleMessage);
            
            const urlParams = new URLSearchParams(window.location.search);
            const paymentStatus = urlParams.get('status');
            const paymentCode = urlParams.get('code');
            
            if (paymentCode === '00') {
              showNotification(
                `✅ Thanh toán thành công!\n\nMã đơn: ${event.data.orderCode || result.order_code}\nLicense key mới đã được gửi về email: ${userEmail}`,
                'success'
              );
              
              // Move to license activation step
              setUpgradeStep('activate');
              setShowLicenseActivation(true);
            } else if (paymentStatus === 'CANCELLED') {
              showNotification('❌ Thanh toán đã bị hủy. Thay đổi gói không thành công.', 'warning');
            } else {
              showNotification('✅ Thanh toán đã hoàn tất!\n\nVui lòng kiểm tra email để lấy license key mới (nếu thanh toán thành công).', 'info');
            }
          }
        };

        window.addEventListener('message', handleMessage);

        // Fallback monitoring without alerts
        const checkClosed = setInterval(() => {
          if (popup.closed) {
            clearInterval(checkClosed);
            window.removeEventListener('message', handleMessage);
            
            console.log('PayOS upgrade popup closed without message');
            setUpgradeStep('activate');
            setShowLicenseActivation(true);
            showNotification('Cửa sổ thanh toán đã đóng. Nếu bạn đã thanh toán thành công, vui lòng nhập license key mới bên dưới.', 'info');
          }
        }, 1000);

        // Auto-close popup after 15 minutes (timeout)
        setTimeout(() => {
          if (!popup.closed) {
            popup.close();
            clearInterval(checkClosed);
            window.removeEventListener('message', handleMessage);
            setUpgradeStep('activate');
            setShowLicenseActivation(true);
            showNotification('Hết thời gian chờ. Nếu bạn đã hoàn tất thanh toán, vui lòng nhập license key mới bên dưới.', 'warning');
          }
        }, 15 * 60 * 1000);

      } else {
        showNotification('Không thể tạo thanh toán: ' + (result.error || result.message || 'Lỗi không xác định'), 'error');
      }
    } catch (error) {
      console.error('Upgrade payment error:', error);
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
  if (pricingError && Object.keys(upgradeOptions).length === 0) {
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
              <p>• Vui lòng liên hệ để được hỗ trợ nâng cấp gói</p>
              <p>• Cung cấp thông tin gói hiện tại và gói muốn nâng cấp</p>
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
      
      {upgradeStep === 'select' && (
        <>
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
          
          {/* ✅ Show available upgrade options count */}
          {Object.keys(upgradeOptions).length === 0 ? (
            <div className="bg-yellow-600 bg-opacity-20 border border-yellow-500 rounded-lg p-4">
              <p className="text-yellow-200">⚠️ Không có gói nâng cấp khả dụng từ gói hiện tại.</p>
            </div>
          ) : (
            <>
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
                        <div className="flex items-center space-x-2">
                          <div className="text-xl font-bold text-purple-400">{formatPrice(option.price)}</div>
                          {option.original_price > option.price && (
                            <div className="text-sm text-gray-400 line-through">{formatPrice(option.original_price)}</div>
                          )}
                        </div>
                        <div className="text-sm text-gray-400">Thời hạn: {option.duration}</div>
                        
                        {option.features && option.features.length > 0 && (
                          <ul className="space-y-1 text-sm text-gray-300">
                            {option.features.map((feature, idx) => (
                              <li key={idx} className="flex items-center">
                                <span className="text-green-400 mr-2">✓</span>
                                {feature}
                              </li>
                            ))}
                          </ul>
                        )}
                        
                        {option.description && (
                          <p className="text-xs text-gray-400">{option.description}</p>
                        )}
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
                    <span className="text-white font-medium">{upgradeOptions[selectedPackage]?.name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Giá:</span>
                    <span className="text-purple-400 font-bold">{formatPrice(upgradeOptions[selectedPackage]?.price || 0)}</span>
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
                    `🚀 Nâng cấp lên ${upgradeOptions[selectedPackage]?.name || 'Gói đã chọn'}`
                  )}
                </button>
              </div>

              {/* Upgrade Info */}
              <div className="text-xs text-gray-400 space-y-1">
                <p>• License cũ sẽ được thay thế bằng license mới</p>
                <p>• License key mới được gửi về email sau khi thanh toán</p>
                <p>• Hỗ trợ: alanngaongo@gmail.com</p>
              </div>
            </>
          )}
        </>
      )}

      {upgradeStep === 'activate' && (
        <>
          <h3 className="text-lg font-semibold text-white mb-4">Kích hoạt License Mới</h3>
          
          {/* Success Message */}
          <div className="bg-green-600 bg-opacity-20 border border-green-500 rounded-lg p-4 mb-4">
            <div className="flex items-center mb-2">
              <span className="text-green-400 text-xl mr-2">✅</span>
              <h4 className="text-green-300 font-medium">Thanh toán thành công!</h4>
            </div>
            <p className="text-green-200 text-sm">
              License key mới đã được gửi về email: <strong>{userEmail}</strong>
            </p>
          </div>

          {/* Current License Info */}
          <div className="bg-gray-700 p-4 rounded-lg mb-4">
            <h4 className="text-white font-medium mb-2">Thông tin nâng cấp</h4>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Từ gói:</span>
                <span className="text-white">{currentLicense?.package_type || 'Unknown'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Lên gói:</span>
                <span className="text-purple-400 font-medium">{upgradeOptions[selectedPackage]?.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Email:</span>
                <span className="text-white">{userEmail}</span>
              </div>
            </div>
          </div>

          {/* License Activation Form */}
          <div className="space-y-4">
            <div>
              <label className="block text-gray-400 text-sm mb-2">
                Nhập License Key Mới:
              </label>
              <input
                type="text"
                value={newLicenseKey}
                onChange={(e) => setNewLicenseKey(e.target.value)}
                placeholder="Dán license key mới từ email vào đây..."
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-purple-500 focus:outline-none font-mono text-sm"
                disabled={isActivatingLicense}
              />
            </div>

            {/* Instructions */}
            <div className="bg-blue-600 bg-opacity-20 border border-blue-500 rounded-lg p-3">
              <h5 className="text-blue-300 font-medium mb-2 flex items-center">
                <span className="mr-2">💡</span>
                Hướng dẫn:
              </h5>
              <ul className="text-blue-200 text-sm space-y-1">
                <li>1. Kiểm tra email <strong>{userEmail}</strong></li>
                <li>2. Tìm email với tiêu đề "V_Track License Key"</li>
                <li>3. Copy license key từ email</li>
                <li>4. Dán vào ô bên trên và nhấn "Kích hoạt"</li>
              </ul>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={() => {
                  setUpgradeStep('select');
                  setShowLicenseActivation(false);
                  setNewLicenseKey('');
                }}
                className="flex-1 py-2 px-4 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
                disabled={isActivatingLicense}
              >
                ← Quay lại
              </button>
              <button
                onClick={handleLicenseActivation}
                disabled={isActivatingLicense || !newLicenseKey.trim()}
                className="flex-2 py-2 px-4 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 disabled:from-gray-600 disabled:to-gray-600 text-white rounded-lg transition-all font-medium disabled:cursor-not-allowed"
              >
                {isActivatingLicense ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Đang kích hoạt...
                  </span>
                ) : (
                  '🔓 Kích hoạt License Mới'
                )}
              </button>
            </div>

            {/* Additional Info */}
            <div className="text-xs text-gray-400 space-y-1">
              <p>• License key có dạng: VTRACK-XXXXX-XXXXX-XXXXX</p>
              <p>• Nếu không nhận được email, kiểm tra thư mục spam</p>
              <p>• Liên hệ hỗ trợ: alanngaongo@gmail.com</p>
            </div>
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

export default UpgradePlan;