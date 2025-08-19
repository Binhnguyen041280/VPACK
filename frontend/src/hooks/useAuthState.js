import { useState, useEffect } from 'react';

const useAuthState = () => {
  const [authState, setAuthState] = useState({
    // Gmail authentication (required for basic app functionality)
    isAuthenticated: false,
    isFirstRun: true,
    isLoading: true,
    userEmail: null,
    sessionToken: null,
    authenticationMethod: null,
    
    // Google Drive authentication (optional, for video processing)
    googleDriveConnected: false,
    driveSessionToken: null,
    driveAuthRequired: false, // Set to true when user needs Drive access
    
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
      
      // Check Gmail authentication status
      let gmailAuthResult = { authenticated: false, user_email: null };
      if (sessionToken) {
        try {
          const gmailAuthResponse = await fetch('http://localhost:8080/api/cloud/gmail-auth-status', {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${sessionToken}`
            },
            credentials: 'include'
          });
          
          if (gmailAuthResponse.ok) {
            gmailAuthResult = await gmailAuthResponse.json();
          }
        } catch (authError) {
          console.log('Gmail auth status check failed:', authError.message);
        }
      }

      // Check Google Drive authentication status (only if Gmail is authenticated)
      let driveAuthResult = { authenticated: false, drive_connected: false };
      const driveSessionToken = sessionStorage.getItem('drive_session_token');
      if (gmailAuthResult.authenticated && driveSessionToken) {
        try {
          const driveAuthResponse = await fetch('http://localhost:8080/api/cloud/drive-auth-status', {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${driveSessionToken}`
            },
            credentials: 'include'
          });
          
          if (driveAuthResponse.ok) {
            driveAuthResult = await driveAuthResponse.json();
          }
        } catch (driveAuthError) {
          console.log('Drive auth status check failed:', driveAuthError.message);
        }
      }

      setAuthState({
        // Gmail authentication state
        isAuthenticated: gmailAuthResult.authenticated || false,
        isFirstRun: !gmailAuthResult.authenticated, // If not authenticated, consider it first run
        isLoading: false,
        userEmail: gmailAuthResult.user_email || null,
        sessionToken: gmailAuthResult.authenticated ? sessionToken : null,
        authenticationMethod: gmailAuthResult.authentication_method || 'gmail_only',
        
        // Google Drive authentication state
        googleDriveConnected: driveAuthResult.authenticated || false,
        driveSessionToken: driveAuthResult.authenticated ? driveSessionToken : null,
        driveAuthRequired: false, // Will be set by components that need Drive access
        
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
    sessionStorage.removeItem('drive_session_token');
    setAuthState({
      isAuthenticated: false,
      isFirstRun: true,
      isLoading: false,
      userEmail: null,
      sessionToken: null,
      authenticationMethod: null,
      googleDriveConnected: false,
      driveSessionToken: null,
      driveAuthRequired: false,
      error: null
    });
  };

  // New function to handle Drive authentication success
  const handleDriveAuthSuccess = (driveAuthResult) => {
    setAuthState(prev => ({
      ...prev,
      googleDriveConnected: true,
      driveSessionToken: driveAuthResult.session_token,
      driveAuthRequired: false,
      error: null
    }));

    // Store Drive session token
    if (driveAuthResult.session_token) {
      sessionStorage.setItem('drive_session_token', driveAuthResult.session_token);
    }
  };

  // New function to request Drive authentication when needed
  const requestDriveAuth = () => {
    setAuthState(prev => ({
      ...prev,
      driveAuthRequired: true
    }));
  };

  // New function to cancel Drive authentication request
  const cancelDriveAuth = () => {
    setAuthState(prev => ({
      ...prev,
      driveAuthRequired: false
    }));
  };

  const refreshAuthStatus = () => {
    checkAuthStatus();
  };

  return {
    authState,
    handleAuthSuccess,
    handleLogout,
    refreshAuthStatus,
    // New Drive authentication functions
    handleDriveAuthSuccess,
    requestDriveAuth,
    cancelDriveAuth
  };
};

export default useAuthState;