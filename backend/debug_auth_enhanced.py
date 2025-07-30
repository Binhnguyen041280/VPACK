#!/usr/bin/env python3
"""
Enhanced authentication debugging script for V_track
Usage: python backend/debug_auth_enhanced.py
"""

import sys
import os
import json
import hashlib

# Add modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))
sys.path.append(os.path.dirname(__file__))

def test_encryption_keys():
    """Test encryption key consistency"""
    print("🔐 Testing encryption keys...")
    
    # Test 1: Check environment variable
    env_key = os.getenv('ENCRYPTION_KEY')
    print(f"🔑 ENCRYPTION_KEY env var: {'SET' if env_key else 'NOT SET'}")
    
    if env_key:
        print(f"   Key length: {len(env_key)} chars")
        print(f"   Key type: {type(env_key)}")
    else:
        print("⚠️  WARNING: No ENCRYPTION_KEY environment variable!")
        print("   This means a new key is generated each time!")
    
    # Test 2: Import and check actual key used
    try:
        from modules.sources.cloud_endpoints import ENCRYPTION_KEY
        print(f"🔑 Actual ENCRYPTION_KEY: {len(ENCRYPTION_KEY)} bytes")
        print(f"   Key (first 16 chars): {ENCRYPTION_KEY[:16] if isinstance(ENCRYPTION_KEY, bytes) else 'Not bytes'}")
        return ENCRYPTION_KEY
    except Exception as e:
        print(f"❌ Error importing ENCRYPTION_KEY: {e}")
        return None

def test_manual_decryption(encryption_key=None):
    """Test manual decryption with different approaches"""
    print("\n🔓 Testing manual decryption...")
    
    try:
        # Load the encrypted file
        tokens_dir = os.path.join(os.path.dirname(__file__), 'modules', 'sources', 'tokens')
        token_filepath = os.path.join(tokens_dir, 'google_drive_2146a5516664cebd.json')
        
        with open(token_filepath, 'r') as f:
            encrypted_storage = json.load(f)
        
        encrypted_data = encrypted_storage['encrypted_data']
        print(f"📦 Loaded encrypted data: {len(encrypted_data)} characters")
        
        # Test current encryption key
        if encryption_key:
            try:
                from cryptography.fernet import Fernet
                import base64
                
                fernet = Fernet(encryption_key)
                encrypted_bytes = base64.b64decode(encrypted_data.encode())
                decrypted_data = fernet.decrypt(encrypted_bytes)
                credential_data = json.loads(decrypted_data.decode())
                
                print("✅ Decryption with current key: SUCCESS")
                print(f"🔐 Credential keys: {list(credential_data.keys())}")
                return True
                
            except Exception as e:
                print(f"❌ Decryption with current key: FAILED")
                print(f"   Error: {e}")
                return False
        else:
            print("❌ No encryption key available for testing")
            return False
            
    except Exception as e:
        print(f"❌ Manual decryption test failed: {e}")
        return False

def fix_encryption_key_issue():
    """Generate and set a persistent encryption key"""
    print("\n🔧 Generating persistent encryption key...")
    
    try:
        from cryptography.fernet import Fernet
        
        # Generate new key
        new_key = Fernet.generate_key()
        print(f"🔑 Generated new key: {new_key}")
        
        # Create .env file or print instruction
        env_file_path = os.path.join(os.path.dirname(__file__), '.env')
        
        env_content = f"ENCRYPTION_KEY={new_key.decode()}\n"
        
        # Check if .env exists
        if os.path.exists(env_file_path):
            print(f"📄 .env file exists at: {env_file_path}")
            with open(env_file_path, 'r') as f:
                existing_content = f.read()
            
            if 'ENCRYPTION_KEY' in existing_content:
                print("⚠️  ENCRYPTION_KEY already exists in .env file")
                print("   Manual action required:")
                print(f"   Update ENCRYPTION_KEY={new_key.decode()}")
            else:
                # Append to existing .env
                with open(env_file_path, 'a') as f:
                    f.write(f"\n{env_content}")
                print(f"✅ Added ENCRYPTION_KEY to existing .env file")
        else:
            # Create new .env file
            with open(env_file_path, 'w') as f:
                f.write(env_content)
            print(f"✅ Created new .env file with ENCRYPTION_KEY")
        
        print("\n📋 Next steps:")
        print("1. Restart the backend server")
        print("2. Re-authenticate from frontend to generate new credentials")
        print("3. Test sync again")
        
        return new_key
        
    except Exception as e:
        print(f"❌ Error generating encryption key: {e}")
        return None

def main():
    print("🔍 Enhanced Authentication Debugging")
    print("=" * 50)
    
    # Test encryption keys
    encryption_key = test_encryption_keys()
    
    # Test manual decryption
    decryption_success = test_manual_decryption(encryption_key)
    
    if not decryption_success:
        print("\n❌ DECRYPTION FAILED!")
        print("This confirms the encryption key mismatch issue.")
        
        # Offer to fix
        response = input("\n🔧 Would you like to generate a persistent encryption key? (y/n): ")
        if response.lower() in ['y', 'yes']:
            fix_encryption_key_issue()
        else:
            print("Manual fix required:")
            print("1. Set ENCRYPTION_KEY environment variable")
            print("2. Or restart backend and re-authenticate")
    else:
        print("\n✅ DECRYPTION SUCCESSFUL!")
        print("The encryption key is working correctly.")
        print("The issue might be elsewhere in the authentication flow.")

if __name__ == "__main__":
    main()
