import { useState, useEffect } from 'react';

const useAuthState = () => {
  const [authState, setAuthState] = useState({
    isAuthenticated: false,
    isFirstRun: true,
    isLoading: true,
    userEmail: null,
    sessionToken: null,
    authenticationMethod: null,
    googleDriveConnected: false,
    error: null
  });

  // Check authentication status on component mount
  useEffect(() => {
    let isMounted = true;
    
    const doCheck = async () => {
      if (isMounted) {
        await checkAuthStatus();
      }
    };
    
    doCheck();
    
    return () => {
      isMounted = false;
    };
  }, []);

  const checkAuthStatus = async () => {
    try {
      setAuthState(prev => ({ ...prev, isLoading: true }));

      // Check if user has session token (try both old and new token keys)
      const sessionToken = sessionStorage.getItem('session_token') || sessionStorage.getItem('gmail_session_token');
      
      // Check first run status with error handling for timezone middleware
      let firstRunData = { first_run: true };
      try {
        const firstRunResponse = await fetch('http://localhost:8080/check-first-run', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        });
        if (firstRunResponse.ok) {
          firstRunData = await firstRunResponse.json();
        }
      } catch (firstRunError) {
        console.log('First run check failed, assuming first run:', firstRunError.message);
        // Continue with default first_run: true
      }
      
      // Check authentication status if session token exists
      let authResult = { authenticated: false, user_email: null };
      if (sessionToken) {
        try {
          // Determine which endpoint to use based on token type
          const isGmailToken = sessionStorage.getItem('gmail_session_token');
          const authUrl = isGmailToken 
            ? 'http://localhost:8080/api/cloud/gmail-auth-status'
            : 'http://localhost:8080/api/cloud/auth-status';
          
          const authResponse = await fetch(authUrl, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${sessionToken}`
            },
            credentials: 'include'
          });
          
          if (authResponse.ok) {
            authResult = await authResponse.json();
          }
        } catch (authError) {
          console.log('Auth status check failed:', authError.message);
          // Don't remove tokens immediately, might be temporary error
        }
      }

      setAuthState({
        isAuthenticated: authResult.authenticated || false,
        isFirstRun: !authResult.authenticated, // If not authenticated, consider it first run
        isLoading: false,
        userEmail: authResult.user_email || null,
        sessionToken: authResult.authenticated ? sessionToken : null,
        authenticationMethod: authResult.authentication_method || null,
        googleDriveConnected: authResult.google_drive_connected || false,
        error: null
      });

    } catch (error) {
      console.error('Error checking auth status:', error);
      setAuthState(prev => ({
        ...prev,
        isLoading: false,
        error: error.message,
        isFirstRun: true, // Default to first run on error
        isAuthenticated: false
      }));
    }
  };

  const handleAuthSuccess = (authResult) => {
    setAuthState(prev => ({
      ...prev,
      isAuthenticated: true,
      isFirstRun: false,
      userEmail: authResult.user_email,
      sessionToken: authResult.session_token,
      authenticationMethod: authResult.authentication_method || 'gmail_only',
      googleDriveConnected: authResult.google_drive_connected || false,
      error: null
    }));

    // Store session token with appropriate key
    if (authResult.session_token) {
      if (authResult.authentication_method === 'gmail_only') {
        sessionStorage.setItem('gmail_session_token', authResult.session_token);
        // Remove old token if exists
        sessionStorage.removeItem('session_token');
      } else {
        sessionStorage.setItem('session_token', authResult.session_token);
      }
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem('session_token');
    sessionStorage.removeItem('gmail_session_token');
    setAuthState({
      isAuthenticated: false,
      isFirstRun: true,
      isLoading: false,
      userEmail: null,
      sessionToken: null,
      authenticationMethod: null,
      googleDriveConnected: false,
      error: null
    });
  };

  const refreshAuthStatus = () => {
    checkAuthStatus();
  };

  return {
    authState,
    handleAuthSuccess,
    handleLogout,
    refreshAuthStatus
  };
};

export default useAuthState;