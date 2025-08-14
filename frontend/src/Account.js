import { useState, useEffect } from 'react';
import LicensePurchase from './components/license/LicensePurchase';
import UpgradePlan from './components/license/UpgradePlan';

const Account = ({ authState, onLogout }) => {
  const [licenseKey, setLicenseKey] = useState('');
  const [licenseStatus, setLicenseStatus] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [licenseError, setLicenseError] = useState(null);
  const [showPurchase, setShowPurchase] = useState(false);
  const [showUpgrade, setShowUpgrade] = useState(false);
  
  // FIXED: Add notification state for custom notifications
  const [notification, setNotification] = useState(null);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  // FIXED: Custom notification system instead of alert()
  const showCustomNotification = (message, type = 'success') => {
    setNotification({ message, type, timestamp: Date.now() });
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
      setNotification(null);
    }, 5000);
  };

  // FIXED: Custom logout confirmation instead of window.confirm()
  const handleLogout = () => {
    setShowLogoutConfirm(true);
  };

  const confirmLogout = () => {
    setShowLogoutConfirm(false);
    onLogout();
  };

  const cancelLogout = () => {
    setShowLogoutConfirm(false);
  };

  const checkLicenseStatus = async () => {
    try {
      // Try to get current license from local database first
      const response = await fetch('http://localhost:8080/api/payment/license-status', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log('License status response:', result);
        
        if (result.success && result.license) {
          console.log('Full license data from backend:', result.license);
          console.log('System status from backend:', result.system_status);
          
          // Map product_type to display name
          const packageDisplayNames = {
            'personal_1m': 'Personal Monthly',
            'personal_1y': 'Personal Annual', 
            'business_1m': 'Business Monthly',
            'business_1y': 'Business Annual',
            'desktop': 'Desktop'
          };
          
          const displayName = packageDisplayNames[result.license.product_type] || 
                             result.license.package_name || 
                             result.license.product_type || 
                             'Desktop';
          
          // FIXED: Proper validation_source mapping based on system_status.source
          const validationSource = result.system_status?.source === 'cloud' ? 'cloud' : 'offline';
          const isOnline = result.system_status?.online || false;
          
          setLicenseStatus({
            valid: true,
            package_type: displayName,
            expires_at: result.license.expires_at,
            license_key: result.license.license_key,
            activated_at: result.license.activated_at || result.license.created_at,
            validation_source: validationSource,  // FIXED: Use source field, not online field
            is_online: isOnline
          });
        } else {
          setLicenseStatus({ valid: false });
        }
      } else {
        setLicenseStatus({ valid: false });
      }
    } catch (error) {
      console.error('Error checking license status:', error);
      setLicenseStatus({ valid: false });
    }
  };

  const handleLicenseActivation = async () => {
    if (!licenseKey.trim()) {
      setLicenseError('Vui lòng nhập license key');
      return;
    }

    setIsValidating(true);
    setLicenseError(null);

    try {
      // Use the activate-license endpoint like webapp does
      const response = await fetch('http://localhost:8080/api/payment/activate-license', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          license_key: licenseKey.trim()
        })
      });

      const result = await response.json();
      console.log('License activation response:', result);

      if (result.success && result.valid) {
        // Update license status with proper data structure
        setLicenseStatus({
          valid: true,
          package_type: result.data.package_name || result.data.product_type || 'desktop',
          expires_at: result.data.expires_at,
          license_key: result.data.license_key,
          activated_at: result.data.created_at
        });
        setLicenseKey('');
        
        // FIXED: Use custom notification instead of alert()
        showCustomNotification('License đã được kích hoạt thành công!', 'success');
        
        // Refresh the license status to get latest data
        setTimeout(() => {
          checkLicenseStatus();
        }, 1000);
      } else {
        setLicenseError(result.error || result.message || 'Kích hoạt license thất bại');
      }
    } catch (error) {
      setLicenseError('Lỗi kết nối server. Vui lòng thử lại.');
      console.error('License activation error:', error);
    } finally {
      setIsValidating(false);
    }
  };

  useEffect(() => {
    checkLicenseStatus();
  }, []);

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
            <p className="text-sm font-medium">{notification.message}</p>
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

  // FIXED: Custom Logout Confirmation Modal
  const LogoutConfirmModal = () => {
    if (!showLogoutConfirm) return null;
    
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
        <div className="bg-gray-800 p-6 rounded-lg shadow-xl max-w-md w-full mx-4">
          <h3 className="text-lg font-semibold text-white mb-4">Xác nhận đăng xuất</h3>
          <p className="text-gray-300 mb-6">Bạn có chắc muốn đăng xuất? Điều này sẽ xóa tất cả dữ liệu đăng nhập.</p>
          <div className="flex gap-3 justify-end">
            <button
              onClick={cancelLogout}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
            >
              Hủy
            </button>
            <button
              onClick={confirmLogout}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
            >
              Đăng xuất
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="p-6 relative">
      {/* FIXED: Custom Notification System */}
      <CustomNotification />
      
      {/* FIXED: Custom Logout Confirmation Modal */}
      <LogoutConfirmModal />
      
      <h1 className="text-3xl font-bold mb-6">Tài khoản</h1>
      
      {authState && authState.isAuthenticated ? (
        <div className="space-y-6">
          {/* User Info Card */}
          <div className="bg-gray-800 p-6 rounded-lg">
            <h2 className="text-xl font-semibold mb-4">Thông tin tài khoản</h2>
            <div className="space-y-3">
              <div className="flex items-center">
                <span className="text-gray-400 w-32">Email:</span>
                <span className="text-white">{authState.userEmail || 'N/A'}</span>
              </div>
              <div className="flex items-center">
                <span className="text-gray-400 w-32">Trạng thái:</span>
                <span className="text-green-400 flex items-center">
                  <span className="w-2 h-2 bg-green-400 rounded-full mr-2"></span>
                  Đã kết nối
                </span>
              </div>
              <div className="flex items-center">
                <span className="text-gray-400 w-32">Dịch vụ:</span>
                <span className="text-white">Google Drive</span>
              </div>
            </div>
          </div>

          {/* License Status */}
          <div className="bg-gray-800 p-6 rounded-lg">
            <h2 className="text-xl font-semibold mb-4">Trạng thái License</h2>
            
            {licenseStatus?.valid ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Trạng thái:</span>
                  <div className="flex items-center gap-2">
                    <span className="text-green-400 flex items-center">
                      <span className="w-2 h-2 bg-green-400 rounded-full mr-2"></span>
                      Đã kích hoạt
                    </span>
                    {/* FIXED: Proper validation source indicators */}
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      licenseStatus.validation_source === 'cloud' 
                        ? 'bg-blue-100 text-blue-800' 
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {licenseStatus.validation_source === 'cloud' ? 'Cloud Verified' : 'Local Verified'}
                    </span>
                    {/* FIXED: Show offline warning only when source is not cloud */}
                    {licenseStatus.validation_source !== 'cloud' && (
                      <span className="text-yellow-400 text-xs flex items-center">
                        ⚠️ Offline Mode
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Loại gói:</span>
                  <span className="text-white capitalize">{licenseStatus.package_type || 'Desktop'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Hết hạn:</span>
                  <span className="text-white">
                    {licenseStatus.expires_at 
                      ? new Date(licenseStatus.expires_at).toLocaleDateString('vi-VN', {
                          year: 'numeric',
                          month: '2-digit',
                          day: '2-digit'
                        })
                      : 'Không giới hạn'
                    }
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">License Key:</span>
                  <span className="text-white font-mono text-sm">
                    {licenseStatus.license_key 
                      ? `...${licenseStatus.license_key.slice(-8)}`
                      : 'N/A'
                    }
                  </span>
                </div>
                
                {/* Upgrade Plan Section */}
                <div className="mt-4 pt-4 border-t border-gray-700">
                  {!showUpgrade ? (
                    <button
                      onClick={() => setShowUpgrade(true)}
                      className="w-full py-2 px-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-lg transition-all font-medium"
                    >
                      ⬆️ Upgrade Plan
                    </button>
                  ) : (
                    <div>
                      <div className="flex justify-between items-center mb-4">
                        <h4 className="text-white font-medium">Nâng cấp gói</h4>
                        <button
                          onClick={() => setShowUpgrade(false)}
                          className="text-gray-400 hover:text-white"
                        >
                          ✕ Đóng
                        </button>
                      </div>
                      <UpgradePlan 
                        currentLicense={licenseStatus}
                        userEmail={authState?.userEmail}
                        onUpgradeInitiated={(upgradeInfo) => {
                          console.log('Upgrade initiated:', upgradeInfo);
                          
                          if (upgradeInfo.completed) {
                            // Upgrade completed successfully, refresh license status
                            showCustomNotification('✅ Nâng cấp thành công! Đang cập nhật thông tin license...', 'success');
                            
                            // Refresh license status after successful upgrade
                            setTimeout(() => {
                              checkLicenseStatus();
                              setShowUpgrade(false); // Close upgrade modal
                            }, 1500);
                          } else {
                            // Payment process initiated
                            showCustomNotification('Đang chuyển hướng đến trang thanh toán...', 'info');
                          }
                        }}
                        onClose={() => setShowUpgrade(false)}
                      />
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Trạng thái:</span>
                  <span className="text-red-400 flex items-center">
                    <span className="w-2 h-2 bg-red-400 rounded-full mr-2"></span>
                    Chưa kích hoạt
                  </span>
                </div>

                {/* Purchase License Section */}
                {!showPurchase ? (
                  <div className="p-4 bg-blue-600 bg-opacity-20 border border-blue-500 rounded-lg mb-4">
                    <h4 className="text-blue-300 font-medium mb-2 flex items-center">
                      <span className="mr-2">💳</span>
                      Mua License V_Track
                    </h4>
                    <p className="text-blue-200 text-sm mb-3">
                      Để sử dụng đầy đủ tính năng V_Track, bạn cần mua license. 
                      Sau khi thanh toán, license key sẽ được gửi qua email.
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setShowPurchase(true)}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm"
                      >
                        🛒 Mua License ngay
                      </button>
                      <button
                        onClick={() => window.open('http://localhost:8080/payment', '_blank')}
                        className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors text-sm"
                      >
                        🌐 Webapp (cũ)
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="mb-4">
                    <div className="flex justify-between items-center mb-4">
                      <h4 className="text-white font-medium">Mua License</h4>
                      <button
                        onClick={() => setShowPurchase(false)}
                        className="text-gray-400 hover:text-white"
                      >
                        ✕ Đóng
                      </button>
                    </div>
                    <LicensePurchase 
                      userEmail={authState?.userEmail}
                      onPurchaseInitiated={(pkg) => {
                        console.log('Purchase initiated for:', pkg);
                        showCustomNotification('Đang chuyển hướng đến trang thanh toán...', 'info');
                      }}
                    />
                  </div>
                )}
                
                {/* License Activation Form */}
                <div className="space-y-3">
                  <div>
                    <label className="block text-gray-400 text-sm mb-2">
                      Nhập License Key:
                    </label>
                    <input
                      type="text"
                      value={licenseKey}
                      onChange={(e) => setLicenseKey(e.target.value)}
                      placeholder="Nhập license key của bạn..."
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                      disabled={isValidating}
                    />
                  </div>
                  
                  {licenseError && (
                    <div className="p-3 bg-red-600 bg-opacity-20 border border-red-500 rounded-lg">
                      <p className="text-red-400 text-sm">{licenseError}</p>
                    </div>
                  )}
                  
                  <button
                    onClick={handleLicenseActivation}
                    disabled={isValidating || !licenseKey.trim()}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                  >
                    {isValidating ? (
                      <span className="flex items-center">
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Đang kích hoạt...
                      </span>
                    ) : (
                      'Kích hoạt License'
                    )}
                  </button>
                  
                  <div className="text-xs text-gray-400">
                    <p>• License key được cung cấp sau khi thanh toán</p>
                    <p>• Liên hệ support nếu gặp vấn đề kích hoạt</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="bg-gray-800 p-6 rounded-lg">
            <h2 className="text-xl font-semibold mb-4">Hành động</h2>
            <div className="space-y-3">
              <button
                onClick={handleLogout}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
              >
                Đăng xuất
              </button>
              <p className="text-gray-400 text-sm">
                Đăng xuất sẽ xóa tất cả dữ liệu đăng nhập và yêu cầu đăng nhập lại.
              </p>
            </div>
          </div>

          {/* Session Info */}
          <div className="bg-gray-800 p-6 rounded-lg">
            <h2 className="text-xl font-semibold mb-4">Phiên làm việc</h2>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Trạng thái phiên:</span>
                <span className="text-green-400">Đang hoạt động</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Tự động làm mới:</span>
                <span className="text-white">Bật</span>
              </div>
              <p className="text-gray-400 text-xs mt-2">
                Phiên đăng nhập sẽ tự động được làm mới để duy trì kết nối.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-gray-800 p-6 rounded-lg">
          <p className="text-gray-400">Không có thông tin tài khoản.</p>
        </div>
      )}
      
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

export default Account;