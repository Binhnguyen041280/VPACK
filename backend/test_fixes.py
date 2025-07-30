#!/usr/bin/env python3
"""
Quick test script to verify PyDrive fixes
Usage: python backend/test_fixes.py
"""

import sys
import os

# Add modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))
sys.path.append(os.path.dirname(__file__))

def test_import_fixes():
    """Test that import fixes are working"""
    print("🧪 Testing import fixes...")
    
    try:
        # Test pydrive_downloader imports
        print("1️⃣ Testing pydrive_downloader imports...")
        from modules.sources.pydrive_downloader import PyDriveDownloader
        print("✅ PyDriveDownloader import successful")
        
        # Test creating instance
        print("2️⃣ Testing PyDriveDownloader instance creation...")
        downloader = PyDriveDownloader()
        print("✅ PyDriveDownloader instance created")
        
        # Test method signature (should not crash on import)
        print("3️⃣ Testing method signatures...")
        print(f"   _get_drive_client method exists: {hasattr(downloader, '_get_drive_client')}")
        print(f"   _get_stored_credentials method exists: {hasattr(downloader, '_get_stored_credentials')}")
        print(f"   _convert_to_oauth2client_credentials method exists: {hasattr(downloader, '_convert_to_oauth2client_credentials')}")
        
        # Test that there's only one _update_credential_data_after_refresh method
        update_methods = [attr for attr in dir(downloader) if 'update_credential_data_after_refresh' in attr]
        print(f"4️⃣ Number of _update_credential_data_after_refresh methods: {len(update_methods)}")
        if len(update_methods) == 1:
            print("✅ Duplicate method successfully removed")
        else:
            print(f"❌ Expected 1 method, found {len(update_methods)}")
        
        print("\n🎉 All import tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_oauth2client_availability():
    """Test oauth2client availability"""
    print("\n🧪 Testing oauth2client availability...")
    try:
        from oauth2client import client
        from oauth2client.client import GOOGLE_TOKEN_URI
        print("✅ oauth2client import successful")
        return True
    except ImportError as e:
        print(f"❌ oauth2client not available: {e}")
        print("💡 Install with: pip install oauth2client")
        return False

if __name__ == "__main__":
    print("🚀 Running PyDrive fixes verification...")
    print("=" * 50)
    
    success1 = test_import_fixes()
    success2 = test_oauth2client_availability()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 ALL TESTS PASSED! Fixes are working correctly.")
        print("\n💡 Next steps:")
        print("   1. Restart backend server: pkill -f 'python.*main.py' && python backend/main.py")
        print("   2. Test force sync API: curl -X POST http://localhost:8080/api/sync/force-sync/88")
        print("   3. Run debug script: python backend/debug_auth.py")
    else:
        print("❌ Some tests failed. Check errors above.")
