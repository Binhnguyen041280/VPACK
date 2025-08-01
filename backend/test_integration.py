#!/usr/bin/env python3
"""
Test script for V_track ZaloPay integration
Run comprehensive tests to verify all components work
"""

import requests
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from modules.payments.license_generator import LicenseGenerator
from modules.licensing.license_models import License

# Set up environment
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv('environment/.env.development')
    print("✅ Environment variables loaded")
except ImportError:
    print("⚠️ python-dotenv not installed, using OS environment")

def test_flask_server():
    """Test Flask server is running"""
    try:
        # Try different ports
        ports = [8080, 5000]
        for port in ports:
            try:
                response = requests.get(f'http://localhost:{port}/health', timeout=5)
                if response.status_code == 200:
                    print(f"✅ Flask server is running on port {port}")
                    return True, port
            except requests.ConnectionError:
                continue
        
        print("❌ Cannot connect to Flask server on any port")
        return False, None
    except Exception as e:
        print(f"❌ Flask server test error: {str(e)}")
        return False, None

def test_zalopay_config(port: int = 8080):
    """Test ZaloPay configuration"""
    try:
        response = requests.get(f'http://localhost:{port}/api/payment/test-connection', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ ZaloPay configuration:", data.get('config', {}).get('environment', 'Unknown'))
            return True
        else:
            print(f"❌ ZaloPay configuration error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ ZaloPay test failed: {str(e)}")
        return False

def test_license_generation():
    """Test license generation"""
    try:
        print("🔍 Testing license generation module import...")
        
        print("✅ LicenseGenerator imported successfully")
        
        # Test initialization
        try:
            generator = LicenseGenerator()
            print("✅ LicenseGenerator initialized")
        except Exception as e:
            print(f"❌ Initialization error: {str(e)}")
            return False
        
        # Generate test license
        license_info = {
            'customer_email': 'test@example.com',
            'product_type': 'desktop',
            'features': ['full_access'],
            'duration_days': 365
        }
        
        print("🔍 Generating test license...")
        license_key = generator.generate_license(license_info)
        
        if license_key:
            print("✅ License key generated")
            
            # Verify license
            print("🔍 Verifying license...")
            license_data = generator.verify_license(license_key)
            if license_data:
                print("✅ License generation and verification working")
                print(f"   License ID: {license_data.get('license_id', 'N/A')}")
                return True
            else:
                print("❌ License verification failed")
                return False
        else:
            print("❌ License generation failed")
            return False
            
    except Exception as e:
        print(f"❌ License test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_email_system(port: int = 8080):
    """Test email system configuration"""
    try:
        response = requests.get(f'http://localhost:{port}/api/license/config', timeout=10)
        if response.status_code == 200:
            config = response.json().get('config', {}).get('email', {})
            if config.get('smtp_configured'):
                print("✅ Email system configured")
                return True
            else:
                print("⚠️ Email system not configured (but system working)")
                return True  # Not a blocker
        else:
            print("❌ Cannot check email configuration")
            return False
    except Exception as e:
        print(f"❌ Email test failed: {str(e)}")
        return False

def test_payment_creation(port: int = 8080):
    """Test payment order creation"""
    try:
        payment_data = {
            'customer_email': 'test@example.com',
            'license_type': 'desktop',
            'price': 500000
        }
        
        response = requests.post(
            f'http://localhost:{port}/api/payment/create-order',
            json=payment_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Payment order creation working")
                print(f"   Order ID: {result.get('app_trans_id', 'N/A')}")
                return True
            else:
                print("❌ Payment creation failed:", result.get('error', 'Unknown error'))
                return False
        else:
            print(f"❌ Payment API error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Payment test failed: {str(e)}")
        return False

def test_database_connection():
    """Test database connection and tables"""
    try:
        print("🔍 Testing database connection...")
        
        from modules.licensing.license_models import init_license_db, get_license_stats
        print("✅ Database models imported")
        
        # Test database initialization
        try:
            init_license_db()
            print("✅ Database tables initialized/verified")
        except Exception as e:
            print(f"❌ Database initialization error: {str(e)}")
            return False
        
        # Test basic database operation
        try:
            stats = get_license_stats()
            if stats is not None:
                print("✅ Database operations working")
                print(f"   Total licenses: {stats.get('total_licenses', 0)}")
                return True
            else:
                print("❌ Database stats query failed")
                return False
        except Exception as e:
            print(f"❌ Database operation error: {str(e)}")
            return False
            
    except Exception as e:
        print(f"❌ Database test failed: {str(e)}")
        return False

def main():
    """Run all integration tests"""
    print("🧪 V_track ZaloPay Integration Test Suite")
    print("=" * 60)
    print(f"🕒 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Working directory: {os.getcwd()}")
    print("=" * 60)
    
    # Test Flask server first to get port
    print("\n🔍 Testing Flask Server...")
    server_running, port = test_flask_server()
    
    if not server_running:
        print("❌ Flask server not running. Please start the server first:")
        print("   cd backend && python app.py")
        sys.exit(1)
    
    # Ensure port is not None
    if port is None:
        port = 8080  # Default fallback
    
    # Define tests with discovered port
    tests = [
        ("Database Connection", test_database_connection),
        ("License Generation", test_license_generation),
        ("ZaloPay Config", lambda: test_zalopay_config(port)),
        ("Email System", lambda: test_email_system(port)),
        ("Payment Creation", lambda: test_payment_creation(port))
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        print("-" * 40)
        result = test_func()
        results.append((test_name, result))
        print("-" * 40)
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name:25} {status}")
        if result:
            passed += 1
    
    print("=" * 60)
    print(f"🎯 Final Summary: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! V_track ZaloPay integration is ready!")
        print("\n📋 Next Steps:")
        print("   1. Register ZaloPay merchant account")
        print("   2. Update production environment variables")
        print("   3. Configure SMTP email settings")
        print("   4. Deploy to production")
        return 0
    else:
        print("⚠️ Some tests failed. Check configuration and try again.")
        print("\n🔧 Troubleshooting:")
        print("   1. Make sure Flask server is running: python backend/app.py")
        print("   2. Check environment variables in environment/.env.development")
        print("   3. Verify all modules are installed: pip install -r requirements.txt")
        print("   4. Check database permissions and file paths")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)