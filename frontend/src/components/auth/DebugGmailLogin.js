import React, { useState, useRef } from 'react';

const DebugGmailLogin = () => {
  const [status, setStatus] = useState('Ready');
  const [details, setDetails] = useState('');
  const [testing, setTesting] = useState(false);
  const abortControllerRef = useRef(null);

  const testBackendConnectivity = async () => {
    if (testing) return false;
    
    try {
      setTesting(true);
      setStatus('Testing backend connectivity...');
      
      // Cancel any previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      
      abortControllerRef.current = new AbortController();
      
      const healthResponse = await fetch('http://localhost:8080/health', {
        signal: abortControllerRef.current.signal,
        timeout: 5000
      });
      
      if (!healthResponse.ok) {
        throw new Error(`Backend not reachable: ${healthResponse.status}`);
      }
      
      const healthData = await healthResponse.json();
      setStatus('✅ Backend is healthy');
      setDetails(JSON.stringify(healthData, null, 2));
      return true;
    } catch (error) {
      if (error.name === 'AbortError') {
        setStatus('❌ Request cancelled');
        setDetails('Request was cancelled');
      } else {
        setStatus('❌ Backend connectivity failed');
        setDetails(error.message);
      }
      return false;
    } finally {
      setTesting(false);
    }
  };

  const testGmailAuth = async () => {
    if (testing) return;
    
    try {
      setTesting(true);
      setStatus('Testing Gmail auth endpoint...');
      
      // Cancel any previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      
      abortControllerRef.current = new AbortController();
      
      const response = await fetch('http://localhost:8080/api/cloud/gmail-auth', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        credentials: 'include',
        signal: abortControllerRef.current.signal,
        body: JSON.stringify({
          action: 'initiate_auth'
        })
      });
      
      console.log('Response status:', response.status);
      console.log('Response headers:', [...response.headers.entries()]);
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Gmail auth failed: ${response.status} - ${errorText}`);
      }
      
      const authData = await response.json();
      setStatus('✅ Gmail auth endpoint working');
      setDetails(JSON.stringify(authData, null, 2));
      
      // Test opening the auth URL
      if (authData.auth_url) {
        window.open(authData.auth_url, 'gmail_auth', 'width=600,height=700');
      }
      
    } catch (error) {
      if (error.name === 'AbortError') {
        setStatus('❌ Request cancelled');
        setDetails('Request was cancelled');
      } else {
        setStatus('❌ Gmail auth failed');
        setDetails(`Error: ${error.message}\nStack: ${error.stack}`);
        console.error('Gmail auth error:', error);
      }
    } finally {
      setTesting(false);
    }
  };

  const runFullTest = async () => {
    const backendOk = await testBackendConnectivity();
    if (backendOk) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      await testGmailAuth();
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h2>🔧 Gmail Auth Debug Tool</h2>
      
      <div style={{ marginBottom: '20px' }}>
        <button 
          onClick={testBackendConnectivity} 
          disabled={testing}
          style={{ marginRight: '10px', padding: '10px', opacity: testing ? 0.5 : 1 }}
        >
          {testing ? 'Testing...' : 'Test Backend'}
        </button>
        <button 
          onClick={testGmailAuth} 
          disabled={testing}
          style={{ marginRight: '10px', padding: '10px', opacity: testing ? 0.5 : 1 }}
        >
          {testing ? 'Testing...' : 'Test Gmail Auth'}
        </button>
        <button 
          onClick={runFullTest} 
          disabled={testing}
          style={{ padding: '10px', opacity: testing ? 0.5 : 1 }}
        >
          {testing ? 'Testing...' : 'Run Full Test'}
        </button>
        
        {testing && (
          <button 
            onClick={() => {
              if (abortControllerRef.current) {
                abortControllerRef.current.abort();
              }
              setTesting(false);
              setStatus('Cancelled');
            }}
            style={{ marginLeft: '10px', padding: '10px', backgroundColor: '#ff4444', color: 'white' }}
          >
            Cancel
          </button>
        )}
      </div>
      
      <div style={{ marginBottom: '20px' }}>
        <strong>Status:</strong> {status}
      </div>
      
      {details && (
        <div>
          <strong>Details:</strong>
          <pre style={{ 
            background: '#f5f5f5', 
            padding: '10px', 
            overflow: 'auto',
            maxHeight: '400px',
            border: '1px solid #ccc'
          }}>
            {details}
          </pre>
        </div>
      )}
    </div>
  );
};

export default DebugGmailLogin;