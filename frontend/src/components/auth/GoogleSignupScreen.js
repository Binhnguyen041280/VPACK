import React, { useState } from 'react';
import GoogleDriveAuthButton from '../config/GoogleDriveAuthButton';

const GoogleSignupScreen = ({ onAuthSuccess }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [authError, setAuthError] = useState(null);

  const handleGoogleAuth = (authResult) => {
    if (authResult.success) {
      console.log('✅ Google authentication successful:', authResult.user_email);
      setAuthError(null);
      
      // Call parent callback to proceed to main app
      if (onAuthSuccess) {
        onAuthSuccess(authResult);
      }
    } else {
      console.error('❌ Google authentication failed:', authResult.message);
      setAuthError(authResult.message || 'Đăng nhập Google thất bại');
    }
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center font-montserrat">
      <div className="bg-gray-800 p-8 rounded-lg shadow-xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">V_TRACK</h1>
          <p className="text-gray-300 text-sm">Video Tracking & Monitoring System</p>
        </div>

        {/* Welcome Message */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-white mb-4 text-center">
            Chào mừng đến với V_Track!
          </h2>
          <p className="text-gray-300 text-sm text-center leading-relaxed">
            Để bắt đầu sử dụng V_Track, bạn cần kết nối với tài khoản Google Drive 
            để lưu trữ và xử lý video.
          </p>
        </div>

        {/* Google Authentication Section */}
        <div className="mb-6">
          <GoogleDriveAuthButton
            onAuth={handleGoogleAuth}
            isLoading={isLoading}
            className="w-full"
          />
        </div>

        {/* Error Display */}
        {authError && (
          <div className="mb-4 p-3 bg-red-600 bg-opacity-20 border border-red-500 rounded-lg">
            <p className="text-red-400 text-sm text-center">{authError}</p>
          </div>
        )}

        {/* Features Info */}
        <div className="bg-gray-700 p-4 rounded-lg">
          <h3 className="text-white font-medium mb-3 flex items-center">
            <span className="mr-2">✨</span>
            Tính năng chính
          </h3>
          <ul className="text-gray-300 text-xs space-y-2">
            <li className="flex items-start">
              <span className="mr-2 text-blue-400">•</span>
              Phát hiện chuyển động và tay trong video
            </li>
            <li className="flex items-start">
              <span className="mr-2 text-green-400">•</span>
              Tự động xử lý và phân tích video
            </li>
            <li className="flex items-start">
              <span className="mr-2 text-yellow-400">•</span>
              Đồng bộ với Google Drive cloud storage
            </li>
            <li className="flex items-start">
              <span className="mr-2 text-purple-400">•</span>
              Báo cáo và truy vấn dữ liệu chi tiết
            </li>
          </ul>
        </div>

        {/* Footer Note */}
        <div className="mt-6 text-center">
          <p className="text-gray-400 text-xs">
            🔒 Thông tin tài khoản được bảo mật và không được chia sẻ
          </p>
        </div>
      </div>
    </div>
  );
};

export default GoogleSignupScreen;