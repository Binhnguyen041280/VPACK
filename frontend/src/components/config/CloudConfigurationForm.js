// components/config/GoogleDriveAuthButton.js - FIXED: Origin & COOP Issues
import React, { useState, useEffect } from 'react';

const GoogleDriveAuthButton = ({ 
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

  // 🔒 SECURITY: Session validation and auto-refresh
  useEffect(() => {
    const validateSession = async () => {
      const token = sessionStorage.getItem('session_token');
      if (token) {
        try {
          const response = await fetch('http://localhost:8080/api/cloud/auth-status', {
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
              sessionStorage.removeItem('session_token');
              setAuthState(prev => ({
                ...prev,
                authenticated: false,
                userEmail: null,
                sessionToken: null
              }));
            }
          }
        } catch (error) {
          console.error('Session validation failed:', error);
          sessionStorage.removeItem('session_token');
        }
      }
    };

    validateSession();
  }, []);

  // 🔒 SECURITY: Auto-refresh session token
  useEffect(() => {
    let refreshInterval;
    
    if (authState.authenticated && authState.sessionToken) {
      refreshInterval = setInterval(async () => {
        try {
          const response = await fetch('http://localhost:8080/api/cloud/auth-status', {
            method: 'GET',
            headers: { 
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${authState.sessionToken}`
            },
            credentials: 'include'
          });
          
          if (response.ok) {
            const result = await response.json();
            if (result.session_token) {
              sessionStorage.setItem('session_token', result.session_token);
              setAuthState(prev => ({
                ...prev,
                sessionToken: result.session_token
              }));
            }
          }
        } catch (error) {
          console.error('Session refresh failed:', error);
        }
      }, 25 * 60 * 1000); // Refresh every 25 minutes
    }
    
    return () => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    };
  }, [authState.authenticated, authState.sessionToken]);

  // 🔧 FIXED: Handle postMessage from OAuth popup with correct origin handling
  useEffect(() => {
    const handleOAuthMessage = (event) => {
      console.log('📬 Received OAuth message:', event.data);
      console.log('📍 Message origin:', event.origin);

      // 🔧 FIX: Accept messages from OAuth callback (port 8080)
      if (event.origin !== 'http://localhost:8080') {
        console.warn('🚫 Ignoring message from unauthorized origin:', event.origin);
        return;
      }

      if (event.data.type === 'OAUTH_SUCCESS') {
        console.log('✅ OAuth success via postMessage:', event.data);
        
        // 🔒 SECURITY: Handle session token instead of credentials
        const userData = event.data.user_info || event.data.user || {};
        const userEmail = event.data.user_email || userData.email || 'unknown';
        const folders = event.data.folders || [];
        const sessionToken = event.data.session_token;
        
        console.log('📧 User email:', userEmail);
        console.log('📁 Folders count:', folders.length);
        console.log('🔑 Session token received:', !!sessionToken);
        
        // 🔒 SECURITY: Store session token securely
        if (sessionToken) {
          sessionStorage.setItem('session_token', sessionToken);
          console.log('💾 Session token stored in sessionStorage');
        }
        
        setAuthState(prev => ({
          ...prev,
          loading: false,
          authenticated: true,
          userEmail: userEmail,
          error: null,
          sessionToken: sessionToken
        }));

        // 🔒 SECURITY: Notify parent component WITHOUT credentials
        if (onAuth) {
          onAuth({
            success: true,
            user_email: userEmail,
            user_info: userData,
            folders: folders,
            message: `Authenticated as ${userEmail}`,
            backend_port: event.data.backend_port || 8080,
            session_token: sessionToken,
            lazy_loading_enabled: event.data.lazy_loading_enabled || false
          });
        }

      } else if (event.data.type === 'OAUTH_ERROR') {
        console.error('❌ OAuth error via postMessage:', event.data.error);
        
        setAuthState(prev => ({
          ...prev,
          loading: false,
          authenticated: false,
          error: event.data.error
        }));

        if (onAuth) {
          onAuth({
            success: false,
            message: event.data.error || 'Authentication failed',
            error: event.data.details || ''
          });
        }
      }
    };

    // Listen for OAuth messages
    window.addEventListener('message', handleOAuthMessage);

    return () => {
      window.removeEventListener('message', handleOAuthMessage);
    };
  }, [onAuth]);

  const handleAuthenticate = async () => {
    if (authState.loading) return;

    try {
      setAuthState(prev => ({ ...prev, loading: true, error: null }));
      console.log('🔐 Starting Google Drive authentication...');

      // Step 1: Initiate OAuth flow
      const response = await fetch('http://localhost:8080/api/cloud/authenticate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          provider: 'google_drive',
          action: 'initiate_auth',
          redirect_uri: 'http://localhost:8080/api/cloud/oauth/callback'
        })
      });

      if (!response.ok) {
        throw new Error(`Authentication request failed: ${response.status}`);
      }

      const authData = await response.json();

      if (!authData.success || !authData.auth_url) {
        throw new Error(authData.message || 'Failed to get authorization URL');
      }

      console.log('🌐 Opening OAuth popup...', authData.auth_url);

      // Step 2: Open OAuth popup - IMPROVED with COOP workaround
      await handleOAuthPopup(authData.auth_url);

    } catch (error) {
      console.error('❌ Authentication error:', error);
      setAuthState(prev => ({
        ...prev,
        loading: false,
        error: error.message
      }));

      if (onAuth) {
        onAuth({
          success: false,
          message: error.message || 'Authentication failed'
        });
      }
    }
  };

  // 🔧 FIXED: Better popup handling with COOP workaround
  const handleOAuthPopup = async (authUrl) => {
    return new Promise((resolve, reject) => {
      const popup = window.open(
        authUrl,
        'google_drive_auth',
        'width=600,height=700,scrollbars=yes,resizable=yes,popup=yes'
      );

      if (!popup) {
        reject(new Error('Popup blocked. Please allow popups for this site.'));
        return;
      }

      let checkCompleted = false;

      // 🆕 NEW: Use postMessage instead of polling popup.closed (COOP workaround)
      const handlePopupMessage = (event) => {
        // 🔧 FIX: Only accept messages from OAuth callback
        if (event.origin !== 'http://localhost:8080') return;
        
        if (event.data.type === 'OAUTH_SUCCESS' || event.data.type === 'OAUTH_ERROR') {
          if (!checkCompleted) {
            checkCompleted = true;
            console.log('✅ OAuth popup completed via postMessage');
            
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

      window.addEventListener('message', handlePopupMessage);

      // 🔧 TIMEOUT: Auto-timeout after 5 minutes
      setTimeout(() => {
        if (!checkCompleted) {
          checkCompleted = true;
          window.removeEventListener('message', handlePopupMessage);
          
          try {
            popup.close();
          } catch (e) {
            console.log('📝 Note: Could not close popup (COOP prevents access)');
          }
          
          reject(new Error('Authentication timeout (5 minutes)'));
        }
      }, 300000);
    });
  };

  // 🔒 SECURITY: Updated disconnect handler with session cleanup
  const handleDisconnect = async () => {
    try {
      setAuthState(prev => ({ ...prev, loading: true }));
      
      const response = await fetch('http://localhost:8080/api/cloud/disconnect', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authState.sessionToken}`
        },
        credentials: 'include',
        body: JSON.stringify({
          provider: 'google_drive',
          user_email: authState.userEmail
        })
      });

      const result = await response.json();
      
      if (result.success) {
        // 🔒 SECURITY: Clean up session token
        sessionStorage.removeItem('session_token');
        
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
            message: 'Disconnected from Google Drive',
            disconnected: true
          });
        }
      } else {
        throw new Error(result.message || 'Disconnect failed');
      }
      
    } catch (error) {
      console.error('❌ Disconnect error:', error);
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

  // Component render
  return (
    <div className={`google-drive-auth-button ${className}`}>
      {!authState.authenticated ? (
        <div className="auth-section">
          <button
            onClick={handleAuthenticate}
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
                Authenticating...
              </span>
            ) : (
              <span className="flex items-center">
                🔐 Connect to Google Drive
                <span className="ml-2 text-xs opacity-75">(Required)</span>
              </span>
            )}
          </button>
          
          <div className="mt-2 text-xs text-gray-400">
            Click to authenticate and access your Google Drive folders
          </div>
        </div>
      ) : (
        <div className="authenticated-section">
          <div className="flex items-center justify-between p-4 bg-green-100 border border-green-400 rounded-lg">
            <div className="flex items-center">
              <span className="text-2xl mr-3">✅</span>
              <div>
                <div className="font-medium text-green-800">
                  Connected to Google Drive
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
              {authState.loading ? 'Disconnecting...' : 'Disconnect'}
            </button>
          </div>
        </div>
      )}

      {/* Error Display */}
      {authState.error && (
        <div className="error-display mt-3 p-3 bg-red-100 border border-red-400 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="text-red-700">
              <div className="font-medium">Authentication Error</div>
              <div className="text-sm mt-1">{authState.error}</div>
            </div>
            <button
              onClick={() => setAuthState(prev => ({ ...prev, error: null }))}
              className="text-red-500 hover:text-red-700 text-lg leading-none"
            >
              ×
            </button>
          </div>

          {/* Error Actions */}
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleAuthenticate}
              className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
            >
              Try Again
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700"
            >
              Refresh Page
            </button>
          </div>
        </div>
      )}

      {/* Help Text */}
      {!authState.authenticated && !authState.error && (
        <div className="help-text mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="text-sm text-blue-700">
            <div className="font-medium mb-1">🔒 Secure Authentication</div>
            <ul className="text-xs space-y-1 ml-4">
              <li>• Opens Google's official OAuth login</li>
              <li>• VTrack never sees your Google password</li>
              <li>• Only folder access permission requested</li>
              <li>• Can be revoked anytime from Google Account settings</li>
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
              backendPort: 8080
            }, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
};

export default GoogleDriveAuthButton;