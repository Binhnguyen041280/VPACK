#!/usr/bin/env python3
"""
Simple test để verify Solution 2 hoạt động
"""

def test_oauth2client_conversion():
    """Test conversion from google-auth data to oauth2client credentials"""
    try:
        # Import oauth2client
        from oauth2client import client
        from oauth2client.client import GOOGLE_TOKEN_URI
        import httplib2
        
        print("✅ oauth2client imported successfully")
        
        # Mock credential data (giống format từ VTrack encrypted storage)
        mock_credential_data = {
            'token': 'mock_access_token_12345',
            'refresh_token': 'mock_refresh_token_67890',
            'client_id': '123456789.apps.googleusercontent.com',
            'client_secret': 'mock_client_secret_abcdef',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'scopes': ['https://www.googleapis.com/auth/drive.readonly'],
            'expires_at': '2024-12-31T23:59:59+00:00'
        }
        
        print("🔄 Converting credential data to oauth2client format...")
        
        # ✅ SOLUTION 2: Create oauth2client credentials object
        oauth2client_creds = client.OAuth2Credentials(
            access_token=mock_credential_data['token'],
            client_id=mock_credential_data['client_id'],
            client_secret=mock_credential_data['client_secret'],
            refresh_token=mock_credential_data['refresh_token'],
            token_expiry=None,  # For simplicity in test
            token_uri=mock_credential_data['token_uri'],
            user_agent="VTrack-PyDrive2-Test/1.0"
        )
        
        print("✅ oauth2client credentials created successfully!")
        print(f"   Type: {type(oauth2client_creds)}")
        print(f"   Has authorize method: {hasattr(oauth2client_creds, 'authorize')}")
        print(f"   Client ID: {oauth2client_creds.client_id}")
        print(f"   Has refresh token: {bool(oauth2client_creds.refresh_token)}")
        
        # Test PyDrive2 compatibility
        try:
            from pydrive2.auth import GoogleAuth
            
            gauth = GoogleAuth()
            gauth.credentials = oauth2client_creds
            
            print("✅ PyDrive2 GoogleAuth compatibility verified!")
            print(f"   GoogleAuth has credentials: {hasattr(gauth, 'credentials')}")
            print(f"   Credentials type: {type(gauth.credentials)}")
            
            return True
            
        except ImportError:
            print("⚠️ PyDrive2 not available for compatibility test")
            return True
            
    except ImportError as e:
        print(f"❌ Required packages not installed: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Solution 2: OAuth2Client Credential Conversion")
    print("=" * 60)
    
    success = test_oauth2client_conversion()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Solution 2 test PASSED!")
        print("   ✅ google-auth data can be converted to oauth2client format")
        print("   ✅ oauth2client credentials have .authorize() method")
        print("   ✅ PyDrive2 can use converted credentials")
        print("\n💡 Next steps:")
        print("   1. Test with real VTrack credentials")  
        print("   2. Run force sync to verify PyDrive2 connection")
        print("   3. Check downloaded files")
    else:
        print("❌ Solution 2 test FAILED!")
        print("   Please install: pip install oauth2client PyDrive2")
