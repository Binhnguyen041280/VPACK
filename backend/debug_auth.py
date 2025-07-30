#!/usr/bin/env python3
"""
Standalone authentication debugging script for V_track
Usage: python backend/debug_auth.py
"""

import sys
import os
import json
import hashlib

# Add modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))
sys.path.append(os.path.dirname(__file__))

def debug_authentication(source_id=88):
    """Debug authentication step by step"""
    print(f"🔍 Debugging authentication for source {source_id}")
    print("=" * 50)
    
    try:
        # Step 1: Import dependencies
        print("Step 1: Importing dependencies...")
        from modules.db_utils import get_db_connection
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        print("✅ All imports successful")
        
        # Step 2: Get source config
        print("\nStep 2: Loading source config...")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT config FROM video_sources 
            WHERE id = ? AND source_type = 'cloud' AND active = 1
        """, (source_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            print(f"❌ No source config found for source {source_id}")
            return False
        
        print("✅ Source config found")
        
        # Step 3: Parse config
        print("\nStep 3: Parsing config...")
        config_data = json.loads(result[0])
        user_email = config_data.get('user_email')
        print(f"📧 User email: {user_email}")
        
        if not user_email:
            print("❌ No user_email in source config")
            return False
        
        # Step 4: Calculate file path
        print("\nStep 4: Calculating credentials file path...")
        tokens_dir = os.path.join(os.path.dirname(__file__), 'modules', 'sources', 'tokens')
        email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
        token_filename = f"google_drive_{email_hash}.json"
        token_filepath = os.path.join(tokens_dir, token_filename)
        
        print(f"📁 Tokens directory: {tokens_dir}")
        print(f"📄 Token filename: {token_filename}")
        print(f"🔗 Full path: {token_filepath}")
        print(f"📋 File exists: {os.path.exists(token_filepath)}")
        
        if not os.path.exists(token_filepath):
            print(f"❌ Credentials file not found: {token_filepath}")
            # List available files
            if os.path.exists(tokens_dir):
                files = os.listdir(tokens_dir)
                print(f"Available files in tokens dir: {files}")
            return False
        
        # Step 5: Load encrypted storage
        print("\nStep 5: Loading encrypted storage...")
        with open(token_filepath, 'r') as f:
            encrypted_storage = json.load(f)
        
        print(f"🔑 Storage keys: {list(encrypted_storage.keys())}")
        print(f"📦 Has encrypted_data: {'encrypted_data' in encrypted_storage}")
        
        # Step 6: Test decryption
        print("\nStep 6: Testing decryption...")
        try:
            from modules.sources.cloud_endpoints import decrypt_credentials
            credential_data = decrypt_credentials(encrypted_storage['encrypted_data'])
            
            if not credential_data:
                print("❌ Decryption returned None")
                return False
            
            print("✅ Decryption successful")
            print(f"🔐 Credential keys: {list(credential_data.keys())}")
            
        except Exception as e:
            print(f"❌ Decryption failed: {e}")
            return False
        
        # Step 7: Test credentials object creation
        print("\nStep 7: Creating credentials object...")
        try:
            credentials = Credentials(
                token=credential_data['token'],
                refresh_token=credential_data['refresh_token'],
                token_uri=credential_data['token_uri'],
                client_id=credential_data['client_id'],
                client_secret=credential_data['client_secret'],
                scopes=credential_data['scopes']
            )
            print("✅ Credentials object created")
            print(f"⏰ Credentials expired: {credentials.expired}")
            print(f"🔄 Has refresh token: {credentials.refresh_token is not None}")
            
        except Exception as e:
            print(f"❌ Credentials object creation failed: {e}")
            return False
        
        # Step 8: Test credential refresh if needed
        if credentials.expired and credentials.refresh_token:
            print("\nStep 8: Refreshing expired credentials...")
            try:
                credentials.refresh(Request())
                print("✅ Credentials refreshed successfully")
            except Exception as e:
                print(f"❌ Credential refresh failed: {e}")
                return False
        else:
            print("\nStep 8: Credentials are valid, no refresh needed")
        
        # Step 9: Test oauth2client conversion (NEW)
        print("\nStep 9: Testing oauth2client conversion...")
        try:
            # Import oauth2client
            from oauth2client import client
            from oauth2client.client import GOOGLE_TOKEN_URI
            import httplib2
            
            # Extract required data
            access_token = credential_data.get('token')
            refresh_token = credential_data.get('refresh_token')
            client_id = credential_data.get('client_id')
            client_secret = credential_data.get('client_secret')
            token_uri = credential_data.get('token_uri', GOOGLE_TOKEN_URI)
            
            # Handle token expiry
            token_expiry = None
            if credential_data.get('expires_at'):
                from datetime import datetime
                expires_at_str = credential_data['expires_at']
                # Handle both ISO format with and without timezone
                if expires_at_str.endswith('Z'):
                    expires_at_str = expires_at_str[:-1] + '+00:00'
                elif '+' not in expires_at_str and 'T' in expires_at_str:
                    # No timezone info, assume UTC
                    expires_at_str += '+00:00'
                
                try:
                    token_expiry = datetime.fromisoformat(expires_at_str)
                except ValueError as e:
                    print(f"⚠️ Could not parse token expiry: {expires_at_str}, error: {e}")
                    token_expiry = None
            
            print("🔄 Converting to oauth2client credentials...")
            print(f"   Client ID: {client_id[:20]}..." if client_id else "   No client_id")
            print(f"   Has refresh token: {bool(refresh_token)}")
            print(f"   Has access token: {bool(access_token)}")
            print(f"   Token expiry: {token_expiry}")
            
            # Create oauth2client credentials object
            oauth2client_creds = client.OAuth2Credentials(
                access_token=access_token,
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                token_expiry=token_expiry,
                token_uri=token_uri,
                user_agent="VTrack-Debug-Client/1.0"
            )
            
            # Check and refresh token if expired
            if oauth2client_creds.access_token_expired and refresh_token:
                print("🔄 Refreshing expired access token using oauth2client...")
                http = httplib2.Http()
                oauth2client_creds.refresh(http)
                print("✅ Access token refreshed successfully")
            
            print("✅ oauth2client credentials created successfully")
            
        except ImportError as e:
            print(f"❌ oauth2client not installed: {e}")
            print("   Please install: pip install oauth2client")
            return False
        except Exception as e:
            print(f"❌ Failed to create oauth2client credentials: {e}")
            return False
        
        # Step 10: Test PyDrive authentication with oauth2client
        print("\nStep 10: Testing PyDrive authentication with oauth2client...")
        try:
            from pydrive2.auth import GoogleAuth
            from pydrive2.drive import GoogleDrive
            
            # Create GoogleAuth and set oauth2client credentials
            gauth = GoogleAuth()
            gauth.credentials = oauth2client_creds  # Use oauth2client credentials
            
            # Create GoogleDrive object
            drive = GoogleDrive(gauth)
            
            # Test connection
            about = drive.GetAbout()
            print("✅ PyDrive authentication successful")
            print(f"👤 User name: {about.get('name', 'Unknown')}")
            print(f"📧 User email: {about.get('user', {}).get('emailAddress', 'Unknown')}")
            
        except Exception as e:
            print(f"❌ PyDrive authentication failed: {e}")
            print(f"Full error details: {type(e).__name__}: {e}")
            import traceback
            print("Traceback:")
            traceback.print_exc()
            return False
        
        print("\n" + "=" * 50)
        print("🎉 ALL AUTHENTICATION STEPS SUCCESSFUL!")
        print("✅ oauth2client conversion works")
        print("✅ PyDrive2 authentication works")
        print("✅ Force sync should now work")
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_authentication()