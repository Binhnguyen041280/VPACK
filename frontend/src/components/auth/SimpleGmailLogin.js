import React, { useState, useRef, useEffect } from 'react';

const SimpleGmailLogin = ({ onAuthSuccess }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const popupRef = useRef(null);
  const intervalRef = useRef(null);
  const messageHandlerRef = useRef(null);

  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (messageHandlerRef.current) {
        window.removeEventListener('message', messageHandlerRef.current);
      }
      if (popupRef.current && !popupRef.current.closed) {
        popupRef.current.close();
      }
    };
  }, []);

  const handleGmailLogin = async () => {
    if (isLoading) {
      console.log('⚠️ Authentication already in progress, skipping...');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      
      console.log('🔐 Starting Gmail authentication...');

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

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Authentication failed: ${response.status} - ${errorText}`);
      }

      const authData = await response.json();
      console.log('✅ Auth data received:', authData);

      if (!authData.success || !authData.auth_url) {
        throw new Error(authData.message || 'Failed to get authorization URL');
      }

      console.log('🌐 Opening OAuth popup...');
      
      // Close any existing popup
      if (popupRef.current && !popupRef.current.closed) {
        popupRef.current.close();
      }
      
      // Clear any existing intervals/listeners
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (messageHandlerRef.current) {
        window.removeEventListener('message', messageHandlerRef.current);
      }
      
      // Open popup window
      const popup = window.open(
        authData.auth_url,
        'gmail_auth',
        'width=600,height=700,scrollbars=yes,resizable=yes'
      );

      if (!popup) {
        throw new Error('Popup blocked. Please allow popups for this site.');
      }
      
      popupRef.current = popup;

      // Listen for popup completion using message passing instead of window.closed
      const handleMessage = (event) => {
        // Only accept messages from our OAuth callback
        if (event.origin !== 'http://localhost:8080') {
          return;
        }

        console.log('📨 Received OAuth message:', event.data);

        if (event.data.type === 'GMAIL_AUTH_SUCCESS') {
          // Cleanup listeners and intervals
          if (messageHandlerRef.current) {
            window.removeEventListener('message', messageHandlerRef.current);
            messageHandlerRef.current = null;
          }
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          
          // Close popup
          if (popupRef.current && !popupRef.current.closed) {
            popupRef.current.close();
          }
          popupRef.current = null;
          
          setIsLoading(false);
          
          console.log('✅ Authentication successful via message:', event.data.user_email);
          
          if (onAuthSuccess) {
            onAuthSuccess({
              success: true,
              user_email: event.data.user_email,
              user_info: event.data.user_info,
              authentication_method: 'gmail_only',
              google_drive_connected: false,
              session_token: event.data.session_token
            });
          }
        } else if (event.data.type === 'GMAIL_AUTH_ERROR') {
          // Cleanup listeners and intervals
          if (messageHandlerRef.current) {
            window.removeEventListener('message', messageHandlerRef.current);
            messageHandlerRef.current = null;
          }
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          
          // Close popup
          if (popupRef.current && !popupRef.current.closed) {
            popupRef.current.close();
          }
          popupRef.current = null;
          
          setIsLoading(false);
          setError(event.data.message || 'Authentication failed');
        }
      };

      // Store reference and listen for messages from popup
      messageHandlerRef.current = handleMessage;
      window.addEventListener('message', handleMessage);

      // Fallback: Check popup status with try-catch to handle COOP errors
      const checkPopup = setInterval(() => {
        // Skip if popup ref is null (already cleaned up)
        if (!popupRef.current) {
          clearInterval(checkPopup);
          return;
        }
        
        try {
          if (popupRef.current.closed) {
            // Cleanup
            clearInterval(checkPopup);
            intervalRef.current = null;
            
            if (messageHandlerRef.current) {
              window.removeEventListener('message', messageHandlerRef.current);
              messageHandlerRef.current = null;
            }
            
            popupRef.current = null;
            setIsLoading(false);
            
            // Check if authentication was successful via polling (fallback)
            setTimeout(async () => {
              try {
                const statusResponse = await fetch('http://localhost:8080/api/cloud/gmail-auth-status', {
                  credentials: 'include'
                });
                
                if (statusResponse.ok) {
                  const result = await statusResponse.json();
                  if (result.success && result.authenticated) {
                    console.log('✅ Authentication successful (fallback check):', result.user_email);
                    
                    if (onAuthSuccess) {
                      onAuthSuccess({
                        success: true,
                        user_email: result.user_email,
                        user_info: result.user_info,
                        authentication_method: 'gmail_only',
                        google_drive_connected: false,
                        session_token: result.session_token
                      });
                    }
                  } else {
                    setError('Authentication was not completed successfully');
                  }
                } else {
                  setError('Failed to verify authentication status');
                }
              } catch (error) {
                console.error('Error checking auth status:', error);
                setError('Failed to verify authentication');
              }
            }, 1000);
          }
        } catch (coopError) {
          // Silently ignore COOP errors - this is expected with OAuth providers
          // Don't log these as they spam the console
        }
      }, 2000);  // Check every 2 seconds instead of 1 second
      
      intervalRef.current = checkPopup;

      // Timeout after 5 minutes
      setTimeout(() => {
        if (popupRef.current && !popupRef.current.closed) {
          // Cleanup
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          if (messageHandlerRef.current) {
            window.removeEventListener('message', messageHandlerRef.current);
            messageHandlerRef.current = null;
          }
          
          popupRef.current.close();
          popupRef.current = null;
          setIsLoading(false);
          setError('Authentication timeout - please try again');
        }
      }, 300000);

    } catch (error) {
      console.error('❌ Gmail authentication error:', error);
      setIsLoading(false);
      setError(error.message);
    }
  };

  return (
    <div className="simple-gmail-login">
      <button
        onClick={handleGmailLogin}
        disabled={isLoading}
        className={`px-6 py-3 rounded-lg font-medium transition-all duration-200 w-full ${
          isLoading
            ? 'bg-gray-400 text-gray-600 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700 text-white shadow-lg hover:shadow-xl'
        }`}
      >
        {isLoading ? (
          <span className="flex items-center justify-center">
            <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Đang đăng nhập...
          </span>
        ) : (
          <span className="flex items-center justify-center">
            📧 Đăng nhập Gmail (chỉ thông tin cơ bản)
          </span>
        )}
      </button>

      {error && (
        <div className="mt-3 p-3 bg-red-100 border border-red-400 rounded-lg">
          <div className="text-red-700">
            <div className="font-medium">Lỗi đăng nhập</div>
            <div className="text-sm mt-1">{error}</div>
          </div>
          <button
            onClick={() => setError(null)}
            className="mt-2 px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
          >
            Thử lại
          </button>
        </div>
      )}
    </div>
  );
};

export default SimpleGmailLogin;