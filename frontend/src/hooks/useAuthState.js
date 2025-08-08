import { useState, useEffect } from 'react';

const useAuthState = () => {
  const [authState, setAuthState] = useState({
    isAuthenticated: false,
    isFirstRun: true,
    isLoading: true,
    userEmail: null,
    sessionToken: null,
    error: null
  });

  // Check authentication status on component mount
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      setAuthState(prev => ({ ...prev, isLoading: true }));

      // Check if user has session token
      const sessionToken = sessionStorage.getItem('session_token');
      
      // Check first run status
      const firstRunResponse = await fetch('http://localhost:8080/check-first-run');
      const firstRunData = await firstRunResponse.json();
      
      // Check authentication status if session token exists
      let authResult = { authenticated: false, user_email: null };
      if (sessionToken) {
        try {
          const authResponse = await fetch('http://localhost:8080/api/cloud/auth-status', {
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
        } catch (error) {
          console.log('Auth status check failed:', error);
          sessionStorage.removeItem('session_token');
        }
      }

      setAuthState({
        isAuthenticated: authResult.authenticated || false,
        isFirstRun: !authResult.authenticated, // If not authenticated, consider it first run
        isLoading: false,
        userEmail: authResult.user_email || null,
        sessionToken: authResult.authenticated ? sessionToken : null,
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
      error: null
    }));

    // Store session token
    if (authResult.session_token) {
      sessionStorage.setItem('session_token', authResult.session_token);
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem('session_token');
    setAuthState({
      isAuthenticated: false,
      isFirstRun: true,
      isLoading: false,
      userEmail: null,
      sessionToken: null,
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