import React, { useState, useEffect } from 'react';

const GmailLoginButton = ({ 
  onAuth, 
  isAuthenticated = false, 
  isLoading = false, 
  userEmail = null,
  className = '' 
}) => {
  const [authState, setAuthState] = useState({
    loading: isLoading,
    authenticated: isAuthenticated,
    userEmail: userEmail,
    error: null,
    sessionToken: null
  });

  // Session validation and auto-refresh
  useEffect(() => {
    const validateSession = async () => {
      const token = sessionStorage.getItem('gmail_session_token');
      if (token) {
        try {
          const response = await fetch('http://localhost:8080/api/cloud/gmail-auth-status', {
            method: 'GET',
            headers: { 
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            credentials: 'include'
          });
          
          if (response.ok) {
            const result = await response.json();
            if (result.authenticated) {
              setAuthState(prev => ({
                ...prev,
                authenticated: true,
                userEmail: result.user_email,
                sessionToken: token
              }));
            } else {
              // Session expired, clean up
              sessionStorage.removeItem('gmail_session_token');
              setAuthState(prev => ({
                ...prev,
                authenticated: false,
                userEmail: null,
                sessionToken: null
              }));
            }
          }
        } catch (error) {
          console.error('Gmail session validation failed:', error);
          sessionStorage.removeItem('gmail_session_token');
        }
      }
    };

    validateSession();
  }, []);

  // Listen for OAuth messages
  useEffect(() => {
    const handleOAuthMessage = (event) => {
      console.log('📬 Received Gmail OAuth message:', event.data);
      console.log('📍 Message origin:', event.origin);

      // Accept messages from backend
      const allowedOrigins = [
        'http://localhost:8080',
        'http://127.0.0.1:8080'
      ];
      
      if (!allowedOrigins.includes(event.origin)) {
        console.warn('🚫 Ignoring message from unauthorized origin:', event.origin);
        return;
      }

      if (event.data.type === 'OAUTH_SUCCESS') {
        console.log('✅ Gmail OAuth success via postMessage:', event.data);
        
        const userData = event.data.user_info || event.data.user || {};
        const userEmail = event.data.user_email || userData.email || 'unknown';
        const sessionToken = event.data.session_token;
        const authMethod = event.data.authentication_method || 'gmail_only';
        
        console.log('📧 User email:', userEmail);
        console.log('🔐 Authentication method:', authMethod);
        console.log('🔑 Session token received:', !!sessionToken);
        
        // Store session token securely
        if (sessionToken) {
          sessionStorage.setItem('gmail_session_token', sessionToken);
          console.log('💾 Gmail session token stored in sessionStorage');
        }
        
        setAuthState(prev => ({
          ...prev,
          loading: false,
          authenticated: true,
          userEmail: userEmail,
          error: null,
          sessionToken: sessionToken
        }));

        // Notify parent component
        if (onAuth) {
          onAuth({
            success: true,
            user_email: userEmail,
            user_info: userData,
            message: `Gmail authentication successful: ${userEmail}`,
            authentication_method: authMethod,
            google_drive_connected: event.data.google_drive_connected || false,
            session_token: sessionToken
          });
        }

      } else if (event.data.type === 'OAUTH_ERROR') {
        console.error('❌ Gmail OAuth error via postMessage:', event.data.error);
        
        setAuthState(prev => ({
          ...prev,
          loading: false,
          authenticated: false,
          error: event.data.error
        }));

        if (onAuth) {
          onAuth({
            success: false,
            message: event.data.error || 'Gmail authentication failed',
            error: event.data.details || ''
          });
        }
      }
    };

    window.addEventListener('message', handleOAuthMessage);
    return () => {
      window.removeEventListener('message', handleOAuthMessage);
    };
  }, [onAuth]);

  const handleGmailAuthenticate = async () => {
    if (authState.loading) return;

    try {
      setAuthState(prev => ({ ...prev, loading: true, error: null }));
      console.log('🔐 Starting Gmail authentication...');

      // Request Gmail-only authentication
      console.log('📞 Making request to:', 'http://localhost:8080/api/cloud/gmail-auth');
      const response = await fetch('http://localhost:8080/api/cloud/gmail-auth', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          action: 'initiate_auth'
        })
      });
      
      console.log('📡 Response status:', response.status);
      console.log('📡 Response ok:', response.ok);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Response not ok. Status:', response.status);
        console.error('❌ Error text:', errorText);
        throw new Error(`Gmail authentication request failed: ${response.status} - ${errorText}`);
      }

      const authData = await response.json();
      console.log('✅ Auth data received:', authData);

      if (!authData.success || !authData.auth_url) {
        throw new Error(authData.message || 'Failed to get Gmail authorization URL');
      }

      console.log('🌐 Opening Gmail OAuth popup...', authData.auth_url);

      // Open OAuth popup
      await handleOAuthPopup(authData.auth_url);

    } catch (error) {
      console.error('❌ Gmail authentication error:', error);
      console.error('❌ Error details:', {
        message: error.message,
        stack: error.stack,
        name: error.name
      });
      
      let errorMessage = 'Gmail authentication failed';
      if (error.message) {
        errorMessage = error.message;
      } else if (error.toString) {
        errorMessage = error.toString();
      }
      
      setAuthState(prev => ({
        ...prev,
        loading: false,
        error: errorMessage
      }));

      if (onAuth) {
        onAuth({
          success: false,
          message: errorMessage,
          error: error
        });
      }
    }
  };

  const handleOAuthPopup = async (authUrl) => {
    return new Promise((resolve, reject) => {
      const popup = window.open(
        authUrl,
        'gmail_auth',
        'width=600,height=700,scrollbars=yes,resizable=yes,popup=yes,left=' + 
        (window.screen.width / 2 - 300) + ',top=' + (window.screen.height / 2 - 350)
      );

      if (!popup) {
        reject(new Error('Popup blocked. Please allow popups for this site.'));
        return;
      }

      let checkCompleted = false;
      let messageReceived = false;

      // Multi-origin postMessage listener
      const handlePopupMessage = (event) => {
        const allowedOrigins = [
          'http://localhost:8080',
          'http://127.0.0.1:8080'
        ];
        
        if (!allowedOrigins.includes(event.origin)) {
          console.log(`📍 Ignoring message from: ${event.origin}`);
          return;
        }
        
        if (event.data.type === 'OAUTH_SUCCESS' || event.data.type === 'OAUTH_ERROR') {
          if (!checkCompleted) {
            checkCompleted = true;
            messageReceived = true;
            console.log('✅ Gmail OAuth popup completed via postMessage');
            
            try {
              popup.close();
            } catch (e) {
              console.log('📝 Note: Could not close popup (COOP prevents access)');
            }
            
            window.removeEventListener('message', handlePopupMessage);
            resolve();
          }
        }
      };

      // Popup close detection
      const checkPopupStatus = () => {
        try {
          if (popup.closed) {
            if (!checkCompleted && !messageReceived) {
              checkCompleted = true;
              console.log('🔄 Popup closed, checking for auth result...');
              
              setTimeout(async () => {
                try {
                  await checkAuthResult();
                  resolve();
                } catch (error) {
                  reject(error);
                }
              }, 1500);
            }
            return;
          }
        } catch (error) {
          console.log('🔒 COOP prevents popup.closed check (normal behavior)');
        }

        if (!checkCompleted) {
          setTimeout(checkPopupStatus, 2000);
        }
      };

      // Start listeners
      window.addEventListener('message', handlePopupMessage);
      setTimeout(checkPopupStatus, 3000);

      // Timeout
      setTimeout(() => {
        if (!checkCompleted) {
          checkCompleted = true;
          window.removeEventListener('message', handlePopupMessage);
          
          try {
            popup.close();
          } catch (e) {
            console.log('📝 Note: Could not close popup during timeout');
          }
          
          reject(new Error('Gmail authentication timeout (5 minutes). Please try again.'));
        }
      }, 300000);
    });
  };

  const checkAuthResult = async (maxRetries = 3) => {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        console.log(`🔍 Checking Gmail auth result (attempt ${attempt}/${maxRetries})...`);
        
        const response = await fetch('http://localhost:8080/api/cloud/gmail-auth-status', {
          method: 'GET',
          headers: { 
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache'
          },
          credentials: 'include',
          cache: 'no-cache'
        });

        if (!response.ok) {
          throw new Error(`Auth status check failed: ${response.status}`);
        }

        const result = await response.json();
        
        if (result.success && result.authenticated) {
          console.log('✅ Gmail authentication confirmed:', result.user_email);
          
          if (result.session_token) {
            sessionStorage.setItem('gmail_session_token', result.session_token);
          }
          
          setAuthState(prev => ({
            ...prev,
            loading: false,
            authenticated: true,
            userEmail: result.user_email,
            error: null,
            sessionToken: result.session_token
          }));

          if (onAuth) {
            onAuth({
              success: true,
              user_email: result.user_email,
              user_info: result.user_info,
              message: `Gmail authentication successful: ${result.user_email}`,
              authentication_method: result.authentication_method || 'gmail_only',
              google_drive_connected: result.google_drive_connected || false,
              session_token: result.session_token
            });
          }
          
          return;
        } else if (attempt === maxRetries) {
          throw new Error(result.message || 'No Gmail authentication found');
        } else {
          await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        }
        
      } catch (error) {
        console.error(`❌ Gmail auth status check failed (attempt ${attempt}):`, error);
        
        if (attempt === maxRetries) {
          throw error;
        } else {
          await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        }
      }
    }
  };

  const handleDisconnect = async () => {
    try {
      setAuthState(prev => ({ ...prev, loading: true }));
      
      // Clear session token
      sessionStorage.removeItem('gmail_session_token');
      
      setAuthState({
        loading: false,
        authenticated: false,
        userEmail: null,
        error: null,
        sessionToken: null
      });

      if (onAuth) {
        onAuth({
          success: false,
          message: 'Disconnected from Gmail',
          disconnected: true
        });
      }
      
    } catch (error) {
      console.error('❌ Gmail disconnect error:', error);
      setAuthState(prev => ({ ...prev, loading: false, error: error.message }));
    }
  };

  // Update state when props change
  useEffect(() => {
    setAuthState(prev => ({
      ...prev,
      loading: isLoading,
      authenticated: isAuthenticated,
      userEmail: userEmail
    }));
  }, [isLoading, isAuthenticated, userEmail]);

  return (
    <div className={`gmail-login-button ${className}`}>
      {!authState.authenticated ? (
        <div className="auth-section">
          <button
            onClick={handleGmailAuthenticate}
            disabled={authState.loading}
            className={`px-6 py-3 rounded-lg font-medium transition-all duration-200 ${
              authState.loading
                ? 'bg-gray-400 text-gray-600 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white shadow-lg hover:shadow-xl transform hover:scale-105'
            }`}
          >
            {authState.loading ? (
              <span className="flex items-center">
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Đang đăng nhập...
              </span>
            ) : (
              <span className="flex items-center">
                🔐 Đăng nhập với Gmail
              </span>
            )}
          </button>
          
          <div className="mt-2 text-xs text-gray-400">
            Đăng nhập để sử dụng V_Track
          </div>
        </div>
      ) : (
        <div className="authenticated-section">
          <div className="flex items-center justify-between p-4 bg-green-100 border border-green-400 rounded-lg">
            <div className="flex items-center">
              <span className="text-2xl mr-3">✅</span>
              <div>
                <div className="font-medium text-green-800">
                  Đã đăng nhập với Gmail
                </div>
                <div className="text-sm text-green-600">
                  {authState.userEmail}
                </div>
              </div>
            </div>
            
            <button
              onClick={handleDisconnect}
              disabled={authState.loading}
              className="px-3 py-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white rounded text-sm transition-colors"
            >
              {authState.loading ? 'Đang đăng xuất...' : 'Đăng xuất'}
            </button>
          </div>
        </div>
      )}

      {/* Error Display */}
      {authState.error && (
        <div className="error-display mt-3 p-3 bg-red-100 border border-red-400 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="text-red-700">
              <div className="font-medium">Lỗi đăng nhập</div>
              <div className="text-sm mt-1">{authState.error}</div>
            </div>
            <button
              onClick={() => setAuthState(prev => ({ ...prev, error: null }))}
              className="text-red-500 hover:text-red-700 text-lg leading-none"
            >
              ×
            </button>
          </div>

          <div className="mt-3 flex gap-2">
            <button
              onClick={handleGmailAuthenticate}
              className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
            >
              Thử lại
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700"
            >
              Tải lại trang
            </button>
          </div>
        </div>
      )}

      {/* Help Text */}
      {!authState.authenticated && !authState.error && (
        <div className="help-text mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="text-sm text-blue-700">
            <div className="font-medium mb-1">🔒 Đăng nhập an toàn</div>
            <ul className="text-xs space-y-1 ml-4">
              <li>• Sử dụng trang đăng nhập chính thức của Google</li>
              <li>• V_Track không bao giờ thấy mật khẩu Google của bạn</li>
              <li>• Chỉ yêu cầu quyền truy cập thông tin cơ bản</li>
              <li>• Có thể hủy bỏ bất cứ lúc nào từ cài đặt Google</li>
            </ul>
          </div>
        </div>
      )}

      {/* Development Debug Info */}
      {process.env.NODE_ENV === 'development' && (
        <details className="debug-info mt-3 p-2 bg-gray-100 rounded text-xs">
          <summary className="cursor-pointer text-gray-600">🔧 Debug Info</summary>
          <pre className="mt-2 text-gray-500 overflow-auto">
            {JSON.stringify({
              authenticated: authState.authenticated,
              loading: authState.loading,
              userEmail: authState.userEmail,
              hasError: !!authState.error,
              errorMessage: authState.error,
              hasSessionToken: !!authState.sessionToken,
              backendPort: 8080,
              authMethod: 'gmail_only'
            }, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
};

export default GmailLoginButton;