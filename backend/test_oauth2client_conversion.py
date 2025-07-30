#!/usr/bin/env python3
"""
Test Script for OAuth2Client Conversion - Solution 2
Verifies that google-auth credentials can be converted to oauth2client format for PyDrive2
"""

import sys
import os
import logging

# Add backend to path
sys.path.append(os.path.dirname(__file__))

from modules.sources.pydrive_downloader import PyDriveDownloader

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_oauth2client_installation():
    """Test if oauth2client is installed"""
    try:
        import oauth2client
        from oauth2client import client
        from oauth2client.client import GOOGLE_TOKEN_URI
        print("✅ oauth2client installed successfully")
        print(f"   Version: {oauth2client.__version__ if hasattr(oauth2client, '__version__') else 'Unknown'}")
        return True
    except ImportError as e:
        print("❌ oauth2client not installed")
        print(f"   Error: {e}")
        print("   Install with: pip install oauth2client")
        return False

def test_pydrive2_installation():
    """Test if PyDrive2 is installed"""
    try:
        from pydrive2.auth import GoogleAuth
        from pydrive2.drive import GoogleDrive
        print("✅ PyDrive2 installed successfully")
        return True
    except ImportError as e:
        print("❌ PyDrive2 not installed")
        print(f"   Error: {e}")
        print("   Install with: pip install PyDrive2")
        return False

def test_credential_conversion():
    """Test credential conversion method"""
    try:
        downloader = PyDriveDownloader()
        
        # Mock credential data (like what comes from VTrack encrypted storage)  
        mock_credential_data = {
            'token': 'mock_access_token',
            'refresh_token': 'mock_refresh_token',
            'client_id': 'mock_client_id.apps.googleusercontent.com',
            'client_secret': 'mock_client_secret',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'scopes': ['https://www.googleapis.com/auth/drive.readonly'],
            'expires_at': '2024-12-31T23:59:59+00:00'
        }
        
        print("🔄 Testing credential conversion...")
        oauth2client_creds = downloader._convert_to_oauth2client_credentials(mock_credential_data)
        
        if oauth2client_creds:
            print("✅ Credential conversion successful")
            print(f"   Type: {type(oauth2client_creds)}")
            print(f"   Has authorize method: {hasattr(oauth2client_creds, 'authorize')}")
            print(f"   Client ID: {oauth2client_creds.client_id}")
            print(f"   Access token expired: {oauth2client_creds.access_token_expired}")
            return True
        else:
            print("❌ Credential conversion failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing credential conversion: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pydrive2_compatibility():
    """Test PyDrive2 compatibility with converted credentials"""
    try:
        downloader = PyDriveDownloader()
        
        # Mock credential data
        mock_credential_data = {
            'token': 'mock_access_token',
            'refresh_token': 'mock_refresh_token', 
            'client_id': 'mock_client_id.apps.googleusercontent.com',
            'client_secret': 'mock_client_secret',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'scopes': ['https://www.googleapis.com/auth/drive.readonly'],
            'expires_at': '2024-12-31T23:59:59+00:00'
        }
        
        oauth2client_creds = downloader._convert_to_oauth2client_credentials(mock_credential_data)
        
        if not oauth2client_creds:
            print("❌ Could not create credentials for compatibility test")
            return False
        
        print("🔄 Testing PyDrive2 compatibility...")
        
        from pydrive2.auth import GoogleAuth
        from pydrive2.drive import GoogleDrive
        
        # Create GoogleAuth and set credentials
        gauth = GoogleAuth()
        gauth.credentials = oauth2client_creds
        
        # Create GoogleDrive object (this will fail with real API call but should create object)
        drive = GoogleDrive(gauth)
        
        print("✅ PyDrive2 compatibility test passed")
        print(f"   GoogleAuth type: {type(gauth)}")
        print(f"   GoogleDrive type: {type(drive)}")
        print(f"   Credentials attached: {hasattr(gauth, 'credentials') and gauth.credentials is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ PyDrive2 compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🧪 Testing OAuth2Client Conversion - Solution 2")
    print("=" * 50)
    
    tests = [
        ("OAuth2Client Installation", test_oauth2client_installation),
        ("PyDrive2 Installation", test_pydrive2_installation), 
        ("Credential Conversion", test_credential_conversion),
        ("PyDrive2 Compatibility", test_pydrive2_compatibility)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                failed += 1
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Solution 2 is ready to use.")
    else:
        print("⚠️ Some tests failed. Please install missing dependencies:")
        print("   pip install oauth2client PyDrive2")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
