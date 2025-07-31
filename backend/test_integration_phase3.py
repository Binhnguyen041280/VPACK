#!/usr/bin/env python3
"""
Simplified Integration Test for VTrack PyDrive
Tests essential functionality only - no over-engineering
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

def test_component_initialization():
    """Test basic component initialization"""
    print("🧪 Testing Simplified Component Initialization...")
    
    try:
        from modules.sources.pydrive_downloader import pydrive_downloader
        from modules.sources.pydrive_core import PyDriveCore
        from modules.sources.pydrive_error_manager import PyDriveErrorManager
        
        # Test Core
        assert hasattr(pydrive_downloader, 'core'), "❌ Core component missing"
        assert isinstance(pydrive_downloader.core, PyDriveCore), "❌ Core not proper type"
        print("✅ PyDriveCore initialized correctly")
        
        # Test ErrorManager (simplified)
        assert hasattr(pydrive_downloader, 'error_manager'), "❌ ErrorManager component missing"
        assert isinstance(pydrive_downloader.error_manager, PyDriveErrorManager), "❌ ErrorManager not proper type"
        print("✅ Simplified PyDriveErrorManager initialized correctly")
        
        # Test essential attributes
        assert hasattr(pydrive_downloader, 'sync_timers'), "❌ sync_timers missing"
        assert hasattr(pydrive_downloader, 'sync_locks'), "❌ sync_locks missing"
        print("✅ Essential attributes present")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization test failed: {e}")
        return False

def test_simplified_error_handling():
    """Test simplified error classification"""
    print("\n🧪 Testing Simplified Error Handling...")
    
    try:
        from modules.sources.error_definitions import classify_error_simple, SIMPLE_USER_MESSAGES
        
        # Test simple error classification
        test_cases = [
            ("Connection timeout", "network"),
            ("OAuth token expired", "auth"),
            ("Quota exceeded", "quota"),
            ("Random error", "other")
        ]
        
        for error_text, expected_type in test_cases:
            result = classify_error_simple(error_text)
            assert result == expected_type, f"❌ Wrong classification: {error_text} → {result}"
            print(f"✅ Error classified: {error_text} → {result}")
        
        # Test user messages exist
        for error_type in ['network', 'auth', 'quota', 'other']:
            assert error_type in SIMPLE_USER_MESSAGES, f"❌ Missing user message for: {error_type}"
            print(f"✅ User message for {error_type}: {SIMPLE_USER_MESSAGES[error_type]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def test_simple_api_methods():
    """Test essential API methods only"""
    print("\n🧪 Testing Simplified API Methods...")
    
    try:
        from modules.sources.pydrive_downloader import pydrive_downloader
        
        # Test simple status method
        status = pydrive_downloader.get_simple_status(999)  # Non-existent source
        assert 'status' in status, "❌ Status format invalid"
        assert 'message' in status, "❌ Message missing"
        print(f"✅ Simple status: {status['status']} - {status['message']}")
        
        # Test backward compatibility functions
        from modules.sources.pydrive_downloader import start_source_sync, stop_source_sync, force_sync_source, get_source_status
        
        print("✅ Backward compatibility functions exist:")
        print("   - start_source_sync")
        print("   - stop_source_sync") 
        print("   - force_sync_source")
        print("   - get_source_status")
        
        return True
        
    except Exception as e:
        print(f"❌ API methods test failed: {e}")
        return False

def test_error_manager_retry():
    """Test simplified retry mechanism"""
    print("\n🧪 Testing Simplified Retry Mechanism...")
    
    try:
        from modules.sources.pydrive_downloader import pydrive_downloader
        
        # Test error counting
        error_count = pydrive_downloader.error_manager.get_error_count(999)
        assert isinstance(error_count, int), "❌ Error count not integer"
        print(f"✅ Error count for source 999: {error_count}")
        
        # Test network connectivity check
        is_connected = pydrive_downloader.error_manager.check_network_connectivity(timeout=2)
        print(f"✅ Network connectivity: {'Connected' if is_connected else 'Disconnected'}")
        
        # Test simple retry wrapper
        def test_operation():
            return {'success': True, 'message': 'Test operation completed'}
        
        result = pydrive_downloader.error_manager.handle_with_retry(test_operation, 999)
        assert result['success'], "❌ Retry mechanism failed"
        print("✅ Retry mechanism works for successful operations")
        
        return True
        
    except Exception as e:
        print(f"❌ Retry mechanism test failed: {e}")
        return False

def test_database_integration():
    """Test simplified database operations"""
    print("\n🧪 Testing Simplified Database Integration...")
    
    try:
        from modules.sources.pydrive_downloader import pydrive_downloader
        
        # Test simple status update
        pydrive_downloader._update_simple_status(999, 'test', 'Integration test message')
        print("✅ Simple status update works")
        
        # Test error status update
        pydrive_downloader._update_error_status(999, 'Test error message')
        print("✅ Error status update works")
        
        # Test success status update
        test_result = {
            'message': 'Test sync completed',
            'files_downloaded': 5,
            'total_size_mb': 25.3
        }
        pydrive_downloader._update_success_status(999, test_result)
        print("✅ Success status update works")
        
        return True
        
    except Exception as e:
        print(f"❌ Database integration test failed: {e}")
        return False

def test_core_business_logic():
    """Test core business logic accessibility"""
    print("\n🧪 Testing Core Business Logic...")
    
    try:
        from modules.sources.pydrive_downloader import pydrive_downloader
        
        # Test core methods accessibility
        assert hasattr(pydrive_downloader.core, 'get_drive_client'), "❌ get_drive_client missing"
        assert hasattr(pydrive_downloader.core, 'sync_source'), "❌ sync_source missing"
        assert hasattr(pydrive_downloader.core, '_sanitize_filename'), "❌ _sanitize_filename missing"
        print("✅ Core business logic methods accessible")
        
        # Test filename sanitization
        sanitized = pydrive_downloader.core._sanitize_filename("test<>file:video.mp4")
        assert '<' not in sanitized and '>' not in sanitized and ':' not in sanitized, "❌ Sanitization failed"
        print(f"✅ Filename sanitization: 'test<>file:video.mp4' → '{sanitized}'")
        
        # Test source config method (should return None for non-existent source)
        config = pydrive_downloader.core._get_source_config(999)
        print(f"✅ Source config method works (returned: {config is None})")
        
        return True
        
    except Exception as e:
        print(f"❌ Core business logic test failed: {e}")
        return False

def test_timer_management():
    """Test simplified timer management"""
    print("\n🧪 Testing Simplified Timer Management...")
    
    try:
        from modules.sources.pydrive_downloader import pydrive_downloader
        
        # Test timer data structures
        assert hasattr(pydrive_downloader, 'sync_timers'), "❌ sync_timers missing"
        assert isinstance(pydrive_downloader.sync_timers, dict), "❌ sync_timers not dict"
        print("✅ Timer data structures present")
        
        # Test scheduling method exists
        assert hasattr(pydrive_downloader, '_schedule_next_sync'), "❌ _schedule_next_sync missing"
        assert hasattr(pydrive_downloader, '_timer_callback'), "❌ _timer_callback missing"
        print("✅ Timer management methods present")
        
        return True
        
    except Exception as e:
        print(f"❌ Timer management test failed: {e}")
        return False

def test_sync_operations():
    """Test sync operation structure"""
    print("\n🧪 Testing Sync Operations...")
    
    try:
        from modules.sources.pydrive_downloader import pydrive_downloader
        
        # Test sync methods exist
        assert hasattr(pydrive_downloader, 'start_auto_sync'), "❌ start_auto_sync missing"
        assert hasattr(pydrive_downloader, 'stop_auto_sync'), "❌ stop_auto_sync missing"
        assert hasattr(pydrive_downloader, 'force_sync_now'), "❌ force_sync_now missing"
        assert hasattr(pydrive_downloader, '_perform_sync'), "❌ _perform_sync missing"
        print("✅ Sync operation methods present")
        
        # Test sync with non-existent source (should fail gracefully)
        result = pydrive_downloader.force_sync_now(999)
        assert 'success' in result, "❌ Sync result format invalid"
        assert isinstance(result['success'], bool), "❌ Success field not boolean"
        print(f"✅ Sync operation handles non-existent source: {result['success']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Sync operations test failed: {e}")
        return False

def run_simplified_tests():
    """Run all simplified integration tests"""
    print("🚀 Starting Simplified PyDriveDownloader Integration Tests")
    print("Focus: Essential functionality, reliability, simplicity")
    print("=" * 70)
    
    tests = [
        test_component_initialization,
        test_simplified_error_handling,
        test_simple_api_methods,
        test_error_manager_retry,
        test_database_integration,
        test_core_business_logic,
        test_timer_management,
        test_sync_operations
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"💥 Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"🧪 TEST RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL SIMPLIFIED INTEGRATION TESTS PASSED!")
        print("✅ Separation of concerns working")
        print("✅ Essential features functional") 
        print("✅ Simplified approach validated")
        print("✅ Ready for production")
        return True
    else:
        print(f"❌ {failed} tests failed - needs investigation")
        return False

if __name__ == "__main__":
    success = run_simplified_tests()
    sys.exit(0 if success else 1)