import React, { useState, useEffect } from 'react';
import GoogleDriveAuthButton from './GoogleDriveAuthButton';

const OptionalGoogleDriveConfig = ({ 
  userEmail, 
  onDriveStatusChange,
  className = '' 
}) => {
  const [driveState, setDriveState] = useState({
    connected: false,
    loading: false,
    error: null,
    userEmail: null,
    folders: []
  });

  // Check existing Google Drive connection status
  useEffect(() => {
    const checkDriveStatus = async () => {
      if (!userEmail) return;

      try {
        const response = await fetch('http://localhost:8080/api/cloud/drive-auth-status', {
          method: 'GET',
          headers: { 
            'Content-Type': 'application/json'
          },
          credentials: 'include'
        });

        if (response.ok) {
          const result = await response.json();
          if (result.success && result.authenticated && result.google_drive_connected) {
            setDriveState(prev => ({
              ...prev,
              connected: true,
              userEmail: result.user_email,
              folders: result.folders || []
            }));
          }
        }
      } catch (error) {
        console.error('Error checking Google Drive status:', error);
      }
    };

    checkDriveStatus();
  }, [userEmail]);

  const handleDriveAuth = (authResult) => {
    if (authResult.success) {
      console.log('✅ Google Drive connected:', authResult.user_email);
      
      setDriveState(prev => ({
        ...prev,
        connected: true,
        loading: false,
        error: null,
        userEmail: authResult.user_email,
        folders: authResult.folders || []
      }));

      // Notify parent component
      if (onDriveStatusChange) {
        onDriveStatusChange({
          connected: true,
          userEmail: authResult.user_email,
          folders: authResult.folders || []
        });
      }
    } else {
      console.error('❌ Google Drive connection failed:', authResult.message);
      setDriveState(prev => ({
        ...prev,
        connected: false,
        loading: false,
        error: authResult.message || 'Google Drive connection failed'
      }));

      if (onDriveStatusChange) {
        onDriveStatusChange({
          connected: false,
          error: authResult.message
        });
      }
    }
  };

  const handleDriveDisconnect = async () => {
    try {
      setDriveState(prev => ({ ...prev, loading: true }));
      
      const response = await fetch('http://localhost:8080/api/cloud/disconnect', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          provider: 'google_drive',
          user_email: driveState.userEmail
        })
      });

      const result = await response.json();
      
      if (result.success) {
        setDriveState({
          connected: false,
          loading: false,
          error: null,
          userEmail: null,
          folders: []
        });

        if (onDriveStatusChange) {
          onDriveStatusChange({
            connected: false,
            disconnected: true
          });
        }
      } else {
        throw new Error(result.message || 'Disconnect failed');
      }
      
    } catch (error) {
      console.error('❌ Google Drive disconnect error:', error);
      setDriveState(prev => ({ 
        ...prev, 
        loading: false, 
        error: error.message 
      }));
    }
  };

  return (
    <div className={`optional-google-drive-config ${className}`}>
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            🗂️ Google Drive Cloud Storage
          </h3>
          <p className="text-sm text-gray-600">
            Kết nối với Google Drive để sử dụng cloud storage cho video và dữ liệu của bạn (tùy chọn).
          </p>
        </div>

        {!driveState.connected ? (
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <span className="text-2xl">☁️</span>
                </div>
                <div className="ml-3">
                  <h4 className="text-sm font-medium text-blue-900">
                    Lợi ích của Google Drive
                  </h4>
                  <ul className="mt-2 text-sm text-blue-700 space-y-1">
                    <li>• Lưu trữ video và dữ liệu trên cloud</li>
                    <li>• Truy cập từ nhiều thiết bị khác nhau</li>
                    <li>• Tự động đồng bộ và backup</li>
                    <li>• Chia sẻ dữ liệu với team dễ dàng</li>
                  </ul>
                </div>
              </div>
            </div>

            <GoogleDriveAuthButton
              onAuth={handleDriveAuth}
              isLoading={driveState.loading}
              className="w-full"
            />

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
              <p className="text-xs text-gray-600">
                <strong>Lưu ý:</strong> V_Track có thể hoạt động mà không cần Google Drive. 
                Bạn vẫn có thể xử lý video từ local storage và các nguồn khác.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <span className="text-2xl mr-3">✅</span>
                  <div>
                    <div className="font-medium text-green-800">
                      Google Drive đã kết nối
                    </div>
                    <div className="text-sm text-green-600">
                      {driveState.userEmail}
                    </div>
                    {driveState.folders.length > 0 && (
                      <div className="text-sm text-green-600">
                        {driveState.folders.length} folders có sẵn
                      </div>
                    )}
                  </div>
                </div>
                
                <button
                  onClick={handleDriveDisconnect}
                  disabled={driveState.loading}
                  className="px-3 py-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white rounded text-sm transition-colors"
                >
                  {driveState.loading ? 'Đang ngắt...' : 'Ngắt kết nối'}
                </button>
              </div>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <p className="text-sm text-blue-700">
                <strong>💡 Mẹo:</strong> Giờ đây bạn có thể sử dụng Google Drive làm nguồn video 
                trong phần cấu hình Video Sources.
              </p>
            </div>
          </div>
        )}

        {/* Error Display */}
        {driveState.error && (
          <div className="mt-4 p-3 bg-red-100 border border-red-400 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="text-red-700">
                <div className="font-medium">Lỗi kết nối Google Drive</div>
                <div className="text-sm mt-1">{driveState.error}</div>
              </div>
              <button
                onClick={() => setDriveState(prev => ({ ...prev, error: null }))}
                className="text-red-500 hover:text-red-700 text-lg leading-none"
              >
                ×
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default OptionalGoogleDriveConfig;