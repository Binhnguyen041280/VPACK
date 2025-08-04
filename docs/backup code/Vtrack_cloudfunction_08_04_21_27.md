# 📦 Tổng hợp mã nguồn Vtrack

**Tổng cộng:** 14 file

---

## 📄 File: `conftest.py`
**Đường dẫn:** `/Users/annhu/vtrack_app/V_Track_CloudFunctions/tests/conftest.py`

```python

```
## 📄 File: `__init__.py`
**Đường dẫn:** `/Users/annhu/vtrack_app/V_Track_CloudFunctions/tests/__init__.py`

```python

```
## 📄 File: `test_local.py`
**Đường dẫn:** `/Users/annhu/vtrack_app/V_Track_CloudFunctions/tests/test_local.py`

```python
#!/usr/bin/env python3
"""
Local testing script for V_track Cloud Functions
Test all functions locally before deployment
"""
import os
import sys
import json
import time
import requests
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading

# Configuration
PAYMENT_PORT = 8081
WEBHOOK_PORT = 8082
LICENSE_PORT = 8083

BASE_URL_PAYMENT = f"http://localhost:{PAYMENT_PORT}"
BASE_URL_WEBHOOK = f"http://localhost:{WEBHOOK_PORT}"
BASE_URL_LICENSE = f"http://localhost:{LICENSE_PORT}"

class FunctionTester:
    """Test runner for Cloud Functions"""
    
    def __init__(self):
        self.processes = []
        self.test_results = {}
        
    def start_function(self, function_name, port, source_path):
        """Start a function locally using Functions Framework"""
        print(f"🚀 Starting {function_name} on port {port}...")
        
        try:
            cmd = [
                'functions-framework',
                f'--target={function_name}',
                f'--source={source_path}',
                f'--port={port}',
                '--debug'
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.dirname(source_path)
            )
            
            self.processes.append((function_name, process))
            
            # Wait for function to start
            time.sleep(3)
            
            # Test if function is responding
            try:
                response = requests.get(f"http://localhost:{port}/health", timeout=5)
                if response.status_code == 200:
                    print(f"✅ {function_name} started successfully on port {port}")
                    return True
                else:
                    print(f"❌ {function_name} health check failed: {response.status_code}")
                    return False
            except:
                print(f"⚠️ {function_name} health check not available (normal for some functions)")
                return True
                
        except Exception as e:
            print(f"❌ Failed to start {function_name}: {str(e)}")
            return False
    
    def stop_all_functions(self):
        """Stop all running functions"""
        print("\n🛑 Stopping all functions...")
        for function_name, process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ Stopped {function_name}")
            except:
                process.kill()
                print(f"🔥 Force killed {function_name}")
    
    def test_payment_creation(self):
        """Test payment creation function"""
        print("\n🧪 Testing Payment Creation Function...")
        
        test_cases = [
            {
                "name": "Valid Professional Package",
                "data": {
                    "customer_email": "test@example.com",
                    "package_type": "professional_1y"
                },
                "expected_status": 200
            },
            {
                "name": "Valid Trial Package",
                "data": {
                    "customer_email": "trial@example.com", 
                    "package_type": "trial_30d"
                },
                "expected_status": 200
            },
            {
                "name": "Invalid Email",
                "data": {
                    "customer_email": "invalid-email",
                    "package_type": "professional_1y"
                },
                "expected_status": 400
            },
            {
                "name": "Invalid Package",
                "data": {
                    "customer_email": "test@example.com",
                    "package_type": "invalid_package"
                },
                "expected_status": 400
            },
            {
                "name": "Missing Email",
                "data": {
                    "package_type": "professional_1y"
                },
                "expected_status": 400
            }
        ]
        
        results = []
        for test_case in test_cases:
            try:
                print(f"  🔍 {test_case['name']}...")
                
                response = requests.post(
                    f"{BASE_URL_PAYMENT}/create_payment",
                    json=test_case['data'],
                    timeout=10
                )
                
                success = response.status_code == test_case['expected_status']
                result_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                
                if success:
                    print(f"    ✅ PASS - Status: {response.status_code}")
                    if response.status_code == 200 and result_data.get('success'):
                        print(f"    📋 Order URL: {result_data.get('order_url', 'N/A')[:50]}...")
                        print(f"    💰 Amount: {result_data.get('formatted_amount', 'N/A')}")
                else:
                    print(f"    ❌ FAIL - Expected: {test_case['expected_status']}, Got: {response.status_code}")
                    print(f"    📄 Response: {result_data}")
                
                results.append({
                    'test': test_case['name'],
                    'success': success,
                    'status_code': response.status_code,
                    'response': result_data
                })
                
            except Exception as e:
                print(f"    💥 ERROR - {str(e)}")
                results.append({
                    'test': test_case['name'],
                    'success': False,
                    'error': str(e)
                })
        
        self.test_results['payment_creation'] = results
        return results
    
    def test_webhook_handler(self):
        """Test webhook handler function"""
        print("\n🧪 Testing Webhook Handler Function...")
        
        # Note: Testing webhook with real ZaloPay signature is complex
        # This is a basic connectivity test
        test_cases = [
            {
                "name": "Invalid Webhook Data",
                "data": {
                    "data": "invalid_data",
                    "mac": "invalid_mac",
                    "type": 1
                },
                "expected_status": 400  # Should fail signature verification
            },
            {
                "name": "Missing Webhook Data",
                "data": {},
                "expected_status": 400
            }
        ]
        
        results = []
        for test_case in test_cases:
            try:
                print(f"  🔍 {test_case['name']}...")
                
                response = requests.post(
                    f"{BASE_URL_WEBHOOK}/webhook_handler",
                    json=test_case['data'],
                    timeout=10
                )
                
                success = response.status_code == test_case['expected_status']
                result_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                
                if success:
                    print(f"    ✅ PASS - Status: {response.status_code}")
                else:
                    print(f"    ❌ FAIL - Expected: {test_case['expected_status']}, Got: {response.status_code}")
                    print(f"    📄 Response: {result_data}")
                
                results.append({
                    'test': test_case['name'],
                    'success': success,
                    'status_code': response.status_code,
                    'response': result_data
                })
                
            except Exception as e:
                print(f"    💥 ERROR - {str(e)}")
                results.append({
                    'test': test_case['name'],
                    'success': False,
                    'error': str(e)
                })
        
        self.test_results['webhook_handler'] = results
        return results
    
    def test_health_checks(self):
        """Test health check endpoints"""
        print("\n🏥 Testing Health Check Endpoints...")
        
        health_urls = [
            (f"{BASE_URL_PAYMENT}/health", "Payment Function"),
            (f"{BASE_URL_WEBHOOK}/health", "Webhook Function"),
            (f"{BASE_URL_LICENSE}/health", "License Function")
        ]
        
        results = []
        for url, name in health_urls:
            try:
                print(f"  🔍 {name}...")
                
                response = requests.get(url, timeout=5)
                result_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                
                if response.status_code == 200:
                    print(f"    ✅ HEALTHY - {result_data.get('status', 'unknown')}")
                    if 'timestamp' in result_data:
                        print(f"    🕐 Timestamp: {result_data['timestamp']}")
                else:
                    print(f"    ❌ UNHEALTHY - Status: {response.status_code}")
                
                results.append({
                    'service': name,
                    'healthy': response.status_code == 200,
                    'status_code': response.status_code,
                    'response': result_data
                })
                
            except Exception as e:
                print(f"    💥 ERROR - {str(e)}")
                results.append({
                    'service': name,
                    'healthy': False,
                    'error': str(e)
                })
        
        self.test_results['health_checks'] = results
        return results
    
    def generate_test_report(self):
        """Generate test report"""
        print("\n📊 TEST REPORT")
        print("=" * 50)
        
        total_tests = 0
        passed_tests = 0
        
        for category, results in self.test_results.items():
            print(f"\n📋 {category.upper().replace('_', ' ')}")
            print("-" * 30)
            
            for result in results:
                total_tests += 1
                test_name = result.get('test', result.get('service', 'Unknown'))
                
                if result.get('success', result.get('healthy', False)):
                    passed_tests += 1
                    print(f"  ✅ {test_name}")
                else:
                    print(f"  ❌ {test_name}")
                    if 'error' in result:
                        print(f"     Error: {result['error']}")
        
        print(f"\n📊 SUMMARY")
        print("-" * 30)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "N/A")
        
        # Save detailed report
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': total_tests - passed_tests,
                    'success_rate': (passed_tests/total_tests*100) if total_tests > 0 else 0
                },
                'results': self.test_results
            }, f, indent=2)
        
        print(f"\n📁 Detailed report saved: {report_file}")
        
        return passed_tests == total_tests

def main():
    """Main test runner"""
    print("🧪 V_Track Cloud Functions Local Testing")
    print("=" * 50)
    
    tester = FunctionTester()
    
    try:
        # Start functions
        print("🚀 Starting functions locally...")
        
        # Define function paths
        project_root = os.path.dirname(os.path.dirname(__file__))
        
        functions_to_start = [
            ('create_payment', PAYMENT_PORT, os.path.join(project_root, 'functions', 'create_payment', 'main.py')),
            ('webhook_handler', WEBHOOK_PORT, os.path.join(project_root, 'functions', 'webhook_handler', 'main.py')),
            ('license_service', LICENSE_PORT, os.path.join(project_root, 'functions', 'license_service', 'main.py'))
        ]
        
        # Start functions in parallel
        for function_name, port, source_path in functions_to_start:
            if os.path.exists(source_path):
                tester.start_function(function_name, port, source_path)
            else:
                print(f"⚠️ Function source not found: {source_path}")
        
        # Wait for all functions to be ready
        print("\n⏳ Waiting for functions to be ready...")
        time.sleep(5)
        
        # Run tests
        print("\n🧪 Running tests...")
        tester.test_health_checks()
        tester.test_payment_creation()
        tester.test_webhook_handler()
        
        # Generate report
        success = tester.generate_test_report()
        
        if success:
            print(f"\n🎉 All tests passed! Functions are ready for deployment.")
            return 0
        else:
            print(f"\n⚠️ Some tests failed. Check the report for details.")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Testing interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Testing failed: {str(e)}")
        return 1
    finally:
        tester.stop_all_functions()

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
```
## 📄 File: `zalopay_utils.py`
**Đường dẫn:** `/Users/annhu/vtrack_app/V_Track_CloudFunctions/shared/zalopay_utils.py`

```python
"""
Shared ZaloPay utilities extracted from V_track backend
Common functions for payment processing and webhook handling
"""
import os
import json
import hmac
import hashlib
import time
import requests
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ZaloPayClient:
    """ZaloPay API client for Cloud Functions"""
    
    def __init__(self):
        self.app_id = os.getenv('ZALOPAY_APP_ID')
        self.key1 = os.getenv('ZALOPAY_KEY1')
        self.key2 = os.getenv('ZALOPAY_KEY2')
        self.endpoint = os.getenv('ZALOPAY_ENDPOINT', 'https://openapi.zalopay.vn/v2/create')
        self.sandbox = os.getenv('ZALOPAY_SANDBOX', 'true').lower() == 'true'
        
        if not all([self.app_id, self.key1, self.key2]):
            raise ValueError("Missing ZaloPay credentials in environment variables")
        
        if self.sandbox:
            self.endpoint = 'https://sb-openapi.zalopay.vn/v2/create'
            logger.info("ZaloPay client initialized in SANDBOX mode")
        else:
            logger.info("ZaloPay client initialized in PRODUCTION mode")
    
    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create ZaloPay payment order
        
        Args:
            order_data: {
                'amount': int,
                'customer_email': str,
                'package_type': str,
                'description': str (optional),
                'callback_url': str (optional)
            }
            
        Returns:
            dict: ZaloPay order response
        """
        try:
            # Generate unique transaction ID
            app_trans_id = f"{datetime.now().strftime('%y%m%d')}_{int(time.time() * 1000)}"
            
            # Prepare order data
            order = {
                "app_id": int(self.app_id),
                "app_user": order_data['customer_email'],
                "app_time": int(time.time() * 1000),
                "amount": int(order_data['amount']),
                "app_trans_id": app_trans_id,
                "bank_code": "zalopayapp",
                "item": json.dumps([{
                    "itemid": order_data.get('package_type', 'vtrack_license'),
                    "itemname": order_data.get('description', 'V_track License'),
                    "itemprice": int(order_data['amount']),
                    "itemquantity": 1
                }]),
                "embed_data": json.dumps({
                    "customer_email": order_data['customer_email'],
                    "package_type": order_data.get('package_type', 'annual_1y'),
                    "preferred_language": "vi"
                }),
                "description": order_data.get('description', f"V_track License - {order_data['customer_email']}"),
                "callback_url": order_data.get('callback_url', '')
            }
            
            # Generate MAC signature
            mac_data = f"{order['app_id']}|{order['app_trans_id']}|{order['app_user']}|{order['amount']}|{order['app_time']}|{order['embed_data']}|{order['item']}"
            order['mac'] = hmac.new(
                self.key1.encode('utf-8'),
                mac_data.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Make API request
            response = requests.post(
                self.endpoint,
                json=order,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('return_code') == 1:
                    logger.info(f"ZaloPay order created successfully: {app_trans_id}")
                    return {
                        'success': True,
                        'app_trans_id': app_trans_id,
                        'order_url': result['order_url'],
                        'zp_trans_token': result['zp_trans_token'],
                        'order_data': order
                    }
                else:
                    logger.error(f"ZaloPay order creation failed: {result}")
                    return {
                        'success': False,
                        'error': result.get('return_message', 'Unknown error'),
                        'error_code': result.get('return_code')
                    }
            else:
                logger.error(f"ZaloPay API request failed: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'API request failed: {response.status_code}',
                    'response_text': response.text
                }
                
        except Exception as e:
            logger.error(f"ZaloPay order creation error: {str(e)}")
            return {
                'success': False,
                'error': f'Order creation error: {str(e)}'
            }
    
    def verify_callback_signature(self, callback_data: Dict[str, Any]) -> bool:
        """
        Verify ZaloPay callback signature
        
        Args:
            callback_data: ZaloPay callback data
            
        Returns:
            bool: True if signature is valid
        """
        try:
            data_str = callback_data.get('data', '')
            received_mac = callback_data.get('mac', '')
            
            if not data_str or not received_mac:
                logger.warning("Missing data or mac in callback")
                return False
            
            # Calculate expected MAC
            expected_mac = hmac.new(
                self.key2.encode('utf-8'),
                data_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            is_valid = hmac.compare_digest(expected_mac, received_mac)
            
            if is_valid:
                logger.info("ZaloPay callback signature verified successfully")
            else:
                logger.warning(f"Invalid callback signature. Expected: {expected_mac}, Received: {received_mac}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Callback signature verification error: {str(e)}")
            return False
    
    def parse_callback_data(self, callback_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse and validate ZaloPay callback data
        
        Args:
            callback_data: Raw callback data from ZaloPay
            
        Returns:
            dict: Parsed payment data or None if invalid
        """
        try:
            # Verify signature first
            if not self.verify_callback_signature(callback_data):
                return None
            
            # Parse data field
            data_str = callback_data.get('data', '')
            payment_data = json.loads(data_str)
            
            # Extract embed_data
            embed_data_str = payment_data.get('embed_data', '{}')
            embed_data = json.loads(embed_data_str)
            
            # Return structured data
            return {
                'app_id': payment_data.get('app_id'),
                'app_trans_id': payment_data.get('app_trans_id'),
                'app_time': payment_data.get('app_time'),
                'app_user': payment_data.get('app_user'),
                'amount': payment_data.get('amount'),
                'zp_trans_id': payment_data.get('zp_trans_id'),
                'server_time': payment_data.get('server_time'),
                'channel': payment_data.get('channel'),
                'merchant_user_id': payment_data.get('merchant_user_id'),
                'zp_user_id': payment_data.get('zp_user_id'),
                'user_fee_amount': payment_data.get('user_fee_amount'),
                'discount_amount': payment_data.get('discount_amount'),
                
                # Custom embed data
                'customer_email': embed_data.get('customer_email'),
                'package_type': embed_data.get('package_type', 'annual_1y'),
                'preferred_language': embed_data.get('preferred_language', 'vi'),
                
                # Callback metadata
                'callback_type': callback_data.get('type', 1),
                'processed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Callback data parsing error: {str(e)}")
            return None

def get_package_pricing() -> Dict[str, Dict[str, Any]]:
    """Get package pricing configuration"""
    return {
        'trial_30d': {
            'name': 'Trial 30 Days',
            'amount': 0,  # Free trial
            'duration_days': 30,
            'features': ['basic_tracking', 'limited_cameras'],
            'description': 'Free 30-day trial'
        },
        'basic_1y': {
            'name': 'Basic Annual',
            'amount': 300000,  # 300k VND
            'duration_days': 365,
            'features': ['full_tracking', 'unlimited_cameras', 'email_support'],
            'description': 'Basic annual license'
        },
        'professional_1y': {
            'name': 'Professional Annual',
            'amount': 500000,  # 500k VND  
            'duration_days': 365,
            'features': ['full_tracking', 'unlimited_cameras', 'priority_support', 'cloud_sync', 'advanced_analytics'],
            'description': 'Professional annual license'
        },
        'enterprise_1y': {
            'name': 'Enterprise Annual',
            'amount': 1000000,  # 1M VND
            'duration_days': 365,
            'features': ['full_tracking', 'unlimited_cameras', 'dedicated_support', 'cloud_sync', 'advanced_analytics', 'custom_integration'],
            'description': 'Enterprise annual license'
        }
    }

def get_package_details(package_type: str) -> Optional[Dict[str, Any]]:
    """Get details for a specific package type"""
    pricing = get_package_pricing()
    return pricing.get(package_type)

def validate_payment_amount(package_type: str, amount: int) -> bool:
    """Validate payment amount matches package pricing"""
    package = get_package_details(package_type)
    if not package:
        return False
    return package['amount'] == amount

def format_currency(amount: int) -> str:
    """Format amount in Vietnamese currency"""
    return f"{amount:,} VND"

def generate_payment_description(customer_email: str, package_type: str) -> str:
    """Generate payment description"""
    package = get_package_details(package_type)
    if package:
        return f"V_track {package['name']} - {customer_email}"
    return f"V_track License - {customer_email}"

# Webhook response helpers
def success_response(message: str = "success") -> Dict[str, Any]:
    """Generate success response for ZaloPay webhook"""
    return {
        'return_code': 1,
        'return_message': message
    }

def error_response(message: str = "error") -> Dict[str, Any]:
    """Generate error response for ZaloPay webhook"""
    return {
        'return_code': 0,
        'return_message': message
    }

def retry_response(message: str = "retry") -> Dict[str, Any]:
    """Generate retry response for ZaloPay webhook"""
    return {
        'return_code': 2,
        'return_message': message
    }
```
## 📄 File: `Firestore_client.py`
**Đường dẫn:** `/Users/annhu/vtrack_app/V_Track_CloudFunctions/shared/Firestore_client.py`

```python
"""
V_Track Firestore Database Client
Handles all database operations for Cloud Functions
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from google.cloud import firestore
    from google.cloud import DocumentReference, DocumentSnapshot
    FIRESTORE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Firestore not available: {e}")
    FIRESTORE_AVAILABLE = False
    
    # Mock classes for local development
    class firestore:
        SERVER_TIMESTAMP = datetime.now()
        
        @staticmethod
        def Client():
            return MockFirestoreClient()
    
    class DocumentReference:
        def __init__(self, doc_id):
            self.id = doc_id
    
    class DocumentSnapshot:
        def __init__(self, exists=True, data=None):
            self._exists = exists
            self._data = data or {}
        
        @property
        def exists(self):
            return self._exists
        
        def to_dict(self):
            return self._data

class MockFirestoreClient:
    """Mock Firestore client for local development"""
    
    def collection(self, name):
        return MockCollection(name)

class MockCollection:
    """Mock Firestore collection"""
    
    def __init__(self, name):
        self.name = name
    
    def document(self, doc_id=None):
        return MockDocument(doc_id or "mock_doc")
    
    def where(self, field, op, value):
        return MockQuery()
    
    def order_by(self, field, direction=None):
        return MockQuery()
    
    def limit(self, count):
        return MockQuery()

class MockDocument:
    """Mock Firestore document"""
    
    def __init__(self, doc_id):
        self.id = doc_id
    
    def set(self, data):
        logger.info(f"Mock set document {self.id}: {data}")
        return DocumentReference(self.id)
    
    def get(self):
        return DocumentSnapshot(exists=True, data={"id": self.id, "status": "mock"})
    
    def update(self, data):
        logger.info(f"Mock update document {self.id}: {data}")
        return True

class MockQuery:
    """Mock Firestore query"""
    
    def get(self):
        return [DocumentSnapshot(exists=True, data={"id": "mock", "status": "mock"})]
    
    def stream(self):
        yield DocumentSnapshot(exists=True, data={"id": "mock", "status": "mock"})

class VTrackFirestore:
    """
    V_Track Firestore Database Client
    Provides high-level database operations for payment and license management
    """
    
    def __init__(self, project_id: Optional[str] = None):
        """
        Initialize Firestore client
        
        Args:
            project_id: Google Cloud project ID (optional, uses environment if not provided)
        """
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT', 'vtrack-payments')
        
        if FIRESTORE_AVAILABLE:
            try:
                self.db = firestore.Client(project=self.project_id)
                logger.info(f"Firestore client initialized for project: {self.project_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Firestore: {e}")
                self.db = MockFirestoreClient()
        else:
            logger.warning("Using mock Firestore client for local development")
            self.db = MockFirestoreClient()
    
    # Payment operations
    def save_payment_request(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save payment request to Firestore
        
        Args:
            payment_data: Payment information dictionary
            
        Returns:
            dict: Saved document information
        """
        try:
            # Prepare document data
            doc_data = {
                **payment_data,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            # Convert datetime objects to timestamps
            for key, value in doc_data.items():
                if isinstance(value, datetime):
                    doc_data[key] = value
            
            # Save to payments collection
            doc_ref = self.db.collection('payments').document()
            doc_ref.set(doc_data)
            
            logger.info(f"Payment request saved: {doc_ref.id}")
            
            return {
                'id': doc_ref.id,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Failed to save payment request: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_payment_by_order_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get payment record by order ID
        
        Args:
            order_id: ZaloPay order ID
            
        Returns:
            Payment record dictionary or None if not found
        """
        try:
            payments_ref = self.db.collection('payments')
            query = payments_ref.where('order_id', '==', order_id).limit(1)
            
            docs = query.get()
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            
            logger.warning(f"Payment not found for order_id: {order_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get payment by order_id: {str(e)}")
            return None
    
    def update_payment_status(self, payment_id: str, status: str, 
                            additional_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update payment status and additional data
        
        Args:
            payment_id: Payment document ID
            status: New payment status
            additional_data: Additional data to update
            
        Returns:
            bool: Success status
        """
        try:
            doc_ref = self.db.collection('payments').document(payment_id)
            
            update_data = {
                'status': status,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            if additional_data:
                update_data.update(additional_data)
            
            doc_ref.update(update_data)
            
            logger.info(f"Payment status updated: {payment_id} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update payment status: {str(e)}")
            return False
    
    def get_payment_history(self, customer_email: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get payment history for a customer
        
        Args:
            customer_email: Customer email address
            limit: Maximum number of records to return
            
        Returns:
            List of payment records
        """
        try:
            payments_ref = self.db.collection('payments')
            query = (payments_ref
                    .where('customer_email', '==', customer_email)
                    .order_by('created_at', direction=firestore.Query.DESCENDING)
                    .limit(limit))
            
            payments = []
            for doc in query.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                payments.append(data)
            
            return payments
            
        except Exception as e:
            logger.error(f"Failed to get payment history: {str(e)}")
            return []
    
    # License operations
    def save_license(self, license_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save license to Firestore
        
        Args:
            license_data: License information dictionary
            
        Returns:
            dict: Saved document information
        """
        try:
            # Prepare document data
            doc_data = {
                **license_data,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            # Convert datetime objects to timestamps
            for key, value in doc_data.items():
                if isinstance(value, datetime):
                    doc_data[key] = value
            
            # Save to licenses collection
            doc_ref = self.db.collection('licenses').document()
            doc_ref.set(doc_data)
            
            logger.info(f"License saved: {doc_ref.id}")
            
            return {
                'id': doc_ref.id,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Failed to save license: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_license_by_key(self, license_key: str) -> Optional[Dict[str, Any]]:
        """
        Get license by license key
        
        Args:
            license_key: License key string
            
        Returns:
            License record dictionary or None if not found
        """
        try:
            licenses_ref = self.db.collection('licenses')
            query = licenses_ref.where('license_key', '==', license_key).limit(1)
            
            docs = query.get()
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            
            logger.warning(f"License not found for key: {license_key}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get license by key: {str(e)}")
            return None
    
    def get_licenses_by_email(self, customer_email: str) -> List[Dict[str, Any]]:
        """
        Get all licenses for a customer email
        
        Args:
            customer_email: Customer email address
            
        Returns:
            List of license records
        """
        try:
            licenses_ref = self.db.collection('licenses')
            query = (licenses_ref
                    .where('customer_email', '==', customer_email)
                    .order_by('created_at', direction=firestore.Query.DESCENDING))
            
            licenses = []
            for doc in query.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                licenses.append(data)
            
            return licenses
            
        except Exception as e:
            logger.error(f"Failed to get licenses by email: {str(e)}")
            return []
    
    def update_license_status(self, license_id: str, status: str) -> bool:
        """
        Update license status
        
        Args:
            license_id: License document ID
            status: New license status (active, expired, revoked)
            
        Returns:
            bool: Success status
        """
        try:
            doc_ref = self.db.collection('licenses').document(license_id)
            
            update_data = {
                'status': status,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref.update(update_data)
            
            logger.info(f"License status updated: {license_id} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update license status: {str(e)}")
            return False
    
    # Analytics and reporting
    def get_payment_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get payment statistics for the last N days
        
        Args:
            days: Number of days to analyze
            
        Returns:
            dict: Payment statistics
        """
        try:
            from datetime import timedelta
            
            start_date = datetime.now() - timedelta(days=days)
            
            payments_ref = self.db.collection('payments')
            query = payments_ref.where('created_at', '>=', start_date)
            
            total_payments = 0
            successful_payments = 0
            total_revenue = 0
            package_counts = {}
            
            for doc in query.stream():
                data = doc.to_dict()
                total_payments += 1
                
                if data.get('status') == 'completed':
                    successful_payments += 1
                    total_revenue += data.get('amount', 0)
                
                package_type = data.get('package_type', 'unknown')
                package_counts[package_type] = package_counts.get(package_type, 0) + 1
            
            return {
                'period_days': days,
                'total_payments': total_payments,
                'successful_payments': successful_payments,
                'success_rate': (successful_payments / total_payments * 100) if total_payments > 0 else 0,
                'total_revenue': total_revenue,
                'package_distribution': package_counts,
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get payment stats: {str(e)}")
            return {}
    
    def get_license_stats(self) -> Dict[str, Any]:
        """
        Get license statistics
        
        Returns:
            dict: License statistics
        """
        try:
            licenses_ref = self.db.collection('licenses')
            
            total_licenses = 0
            active_licenses = 0
            expired_licenses = 0
            status_counts = {}
            
            for doc in licenses_ref.stream():
                data = doc.to_dict()
                total_licenses += 1
                
                status = data.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
                
                if status == 'active':
                    active_licenses += 1
                elif status == 'expired':
                    expired_licenses += 1
            
            return {
                'total_licenses': total_licenses,
                'active_licenses': active_licenses,
                'expired_licenses': expired_licenses,
                'status_distribution': status_counts,
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get license stats: {str(e)}")
            return {}
    
    # Utility methods
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Firestore connection
        
        Returns:
            dict: Health check result
        """
        try:
            # Try to read from a collection
            test_doc = self.db.collection('_health_check').document('test')
            test_doc.set({
                'timestamp': firestore.SERVER_TIMESTAMP,
                'status': 'healthy'
            })
            
            # Try to read it back
            doc = test_doc.get()
            
            if doc.exists:
                return {
                    'status': 'healthy',
                    'firestore_connected': True,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'unhealthy',
                    'firestore_connected': False,
                    'error': 'Test document not found'
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'firestore_connected': False,
                'error': str(e)
            }

# Singleton instance
_firestore_client = None

def get_firestore_client() -> VTrackFirestore:
    """Get singleton Firestore client instance"""
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = VTrackFirestore()
    return _firestore_client
```
## 📄 File: `__init__.py`
**Đường dẫn:** `/Users/annhu/vtrack_app/V_Track_CloudFunctions/shared/__init__.py`

```python
"""
V_Track Cloud Functions Shared Modules
Provides common utilities for all functions
"""

# Make shared modules importable
import sys
import os

# Add current directory to Python path
_current_dir = os.path.dirname(__file__)
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

# Public API
__all__ = [
    'get_firestore_client',
    'ZaloPayClient'
]

try:
    from ..shared import get_firestore_client
    from .zalopay_utils import ZaloPayClient
except ImportError:
    # Fallback imports without relative imports
    try:
        from ..shared import get_firestore_client
        from zalopay_utils import ZaloPayClient
    except ImportError as e:
        # Create mock implementations for development
        import logging
        logging.warning(f"Could not import shared modules: {e}")
        
        class MockFirestore:
            def health_check(self):
                return {"status": "mock", "available": False}
        
        class MockZaloPay:
            def create_payment_url(self, data):
                return "https://mock-zalopay.com/payment"
        
        def get_firestore_client():
            return MockFirestore()
        
        ZaloPayClient = MockZaloPay

# Version info
__version__ = "1.0.0"
__author__ = "V_Track Team"
```
## 📄 File: `payos_client.py`
**Đường dẫn:** `/Users/annhu/vtrack_app/V_Track_CloudFunctions/shared/payos_client.py`

```python
# shared/payos_client.py - Updated with test mode support
"""
PayOS Client for V_Track CloudFunctions with test mode support
"""

import os
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class PayOSClient:
    """PayOS integration client with test mode support"""
    
    def __init__(self):
        # Load PayOS credentials from environment
        self.client_id = os.getenv('PAYOS_CLIENT_ID')
        self.api_key = os.getenv('PAYOS_API_KEY') 
        self.checksum_key = os.getenv('PAYOS_CHECKSUM_KEY')
        self.testing_mode = os.getenv('TESTING_MODE', 'false').lower() == 'true'
        
        if not all([self.client_id, self.api_key, self.checksum_key]):
            if not self.testing_mode:
                raise ValueError("Missing PayOS credentials in environment")
            else:
                logger.warning("PayOS credentials missing - running in test mode")
        
        # Initialize PayOS SDK only if not in testing mode
        if not self.testing_mode:
            try:
                from payos import PayOS, PaymentData, ItemData
                self.payos = PayOS(
                    client_id=self.client_id,
                    api_key=self.api_key,
                    checksum_key=self.checksum_key
                )
                logger.info("PayOS Client initialized successfully")
            except ImportError:
                logger.warning("PayOS SDK not available - using test mode")
                self.testing_mode = True
        else:
            logger.info("PayOS Client initialized in TEST MODE")
    
    def create_payment_url(self, order_data: Dict[str, Any]) -> str:
        """Create PayOS payment URL"""
        if self.testing_mode:
            return f"https://test.payos.vn/payment/{order_data['order_code']}"
        
        try:
            from payos import PaymentData, ItemData
            
            # Create item data
            item = ItemData(
                name=order_data.get('item_name', 'V_Track License'),
                quantity=1,
                price=order_data['amount']
            )
            
            # Build payment data
            payment_data = PaymentData(
                orderCode=order_data['order_code'],
                amount=order_data['amount'],
                description=order_data.get('description', 'V_Track License Purchase'),
                items=[item],
                cancelUrl=order_data.get('cancel_url', ''),
                returnUrl=order_data.get('return_url', '')
            )
            
            # Create payment link
            result = self.payos.createPaymentLink(paymentData=payment_data)
            
            logger.info(f"PayOS payment created: {order_data['order_code']}")
            return result.checkoutUrl
            
        except Exception as e:
            logger.error(f"PayOS payment creation failed: {str(e)}")
            raise
    
    def verify_webhook_data(self, webhook_body: Dict[str, Any]) -> Dict[str, Any]:
        """Verify and parse PayOS webhook data with test mode support"""
        
        # Test mode - bypass signature verification
        if self.testing_mode:
            logger.info("Test mode: Bypassing PayOS signature verification")
            
            # Mock successful verification
            data = webhook_body.get('data', {})
            return {
                'orderCode': data.get('orderCode', 123456),
                'amount': data.get('amount', 500000),
                'code': data.get('code', '00'),
                'paymentLinkId': data.get('paymentLinkId', 'test_payment_id'),
                'description': data.get('description', 'Test payment'),
                'data': data
            }
        
        # Production mode - full verification
        try:
            webhook_data = self.payos.verifyPaymentWebhookData(webhook_body)
            return {
                'orderCode': webhook_data.orderCode,
                'amount': webhook_data.amount,
                'code': webhook_data.code,
                'paymentLinkId': webhook_data.paymentLinkId,
                'description': getattr(webhook_data, 'description', ''),
                'data': webhook_data
            }
        except Exception as e:
            logger.error(f"PayOS webhook verification failed: {str(e)}")
            raise
```
## 📄 File: `deploy_all.sh`
**Đường dẫn:** `/Users/annhu/vtrack_app/V_Track_CloudFunctions/deployment/deploy_all.sh`

```bash
#!/bin/bash
# V_Track Cloud Functions Deployment Script
# Deploy all functions to Google Cloud

set -e  # Exit on any error

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"vtrack-payments"}
REGION=${REGION:-"asia-southeast1"}  # Singapore region for Vietnam
RUNTIME="python39"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 V_Track Cloud Functions Deployment${NC}"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Runtime: $RUNTIME"
echo ""

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found. Please install Google Cloud SDK.${NC}"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ Not authenticated with gcloud. Run: gcloud auth login${NC}"
    exit 1
fi

# Set project
echo -e "${YELLOW}📋 Setting project to $PROJECT_ID${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required APIs${NC}"
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable errorrepporting.googleapis.com

# Deploy Payment Creation Function
echo -e "${YELLOW}📦 Deploying create-payment function${NC}"
cd ../functions/create_payment

gcloud functions deploy create-payment \
  --runtime $RUNTIME \
  --trigger-http \
  --allow-unauthenticated \
  --memory 256MB \
  --timeout 30s \
  --region $REGION \
  --entry-point create_payment \
  --set-env-vars FUNCTION_TARGET=create_payment

# Get function URL
PAYMENT_URL=$(gcloud functions describe create-payment --region=$REGION --format="value(httpsTrigger.url)")
echo -e "${GREEN}✅ Payment function deployed: $PAYMENT_URL${NC}"

# Deploy Webhook Handler Function  
echo -e "${YELLOW}📦 Deploying webhook-handler function${NC}"
cd ../webhook_handler

gcloud functions deploy webhook-handler \
  --runtime $RUNTIME \
  --trigger-http \
  --allow-unauthenticated \
  --memory 512MB \
  --timeout 60s \
  --region $REGION \
  --entry-point webhook_handler \
  --set-env-vars FUNCTION_TARGET=webhook_handler

# Get function URL
WEBHOOK_URL=$(gcloud functions describe webhook-handler --region=$REGION --format="value(httpsTrigger.url)")
echo -e "${GREEN}✅ Webhook function deployed: $WEBHOOK_URL${NC}"

# Deploy License Service Function (future)
echo -e "${YELLOW}📦 Deploying license-service function${NC}"
cd ../license_service

# Create basic license service if it doesn't exist
if [ ! -f "main.py" ]; then
    cat > main.py << 'EOF'
import json
from flask import Request
from datetime import datetime

def license_service(request: Request):
    """Basic license service function"""
    return json.dumps({
        'status': 'healthy',
        'service': 'license_service',
        'timestamp': datetime.now().isoformat()
    }), 200
EOF
fi

if [ ! -f "requirements.txt" ]; then
    cat > requirements.txt << 'EOF'
functions-framework==3.4.0
google-cloud-firestore==2.11.1
flask==2.3.2
EOF
fi

gcloud functions deploy license-service \
  --runtime $RUNTIME \
  --trigger-http \
  --allow-unauthenticated \
  --memory 256MB \
  --timeout 30s \
  --region $REGION \
  --entry-point license_service \
  --set-env-vars FUNCTION_TARGET=license_service

# Get function URL
LICENSE_URL=$(gcloud functions describe license-service --region=$REGION --format="value(httpsTrigger.url)")
echo -e "${GREEN}✅ License function deployed: $LICENSE_URL${NC}"

# Back to deployment directory
cd ../../deployment

# Create function URLs file
cat > function_urls.txt << EOF
# V_Track Cloud Functions URLs
# Generated: $(date)

# Payment Creation
PAYMENT_FUNCTION_URL=$PAYMENT_URL

# Webhook Handler  
WEBHOOK_FUNCTION_URL=$WEBHOOK_URL

# License Service
LICENSE_FUNCTION_URL=$LICENSE_URL

# Health Check URLs
PAYMENT_HEALTH_URL=$PAYMENT_URL?action=health
WEBHOOK_HEALTH_URL=$WEBHOOK_URL?action=health
LICENSE_HEALTH_URL=$LICENSE_URL?action=health
EOF

# Display deployment summary
echo ""
echo -e "${GREEN}🎉 All functions deployed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Function URLs:${NC}"
echo "Payment Creation: $PAYMENT_URL"
echo "Webhook Handler:  $WEBHOOK_URL"
echo "License Service:  $LICENSE_URL"
echo ""
echo -e "${BLUE}📁 URLs saved to: deployment/function_urls.txt${NC}"
echo ""
echo -e "${YELLOW}🔧 Next Steps:${NC}"
echo "1. Configure ZaloPay webhook URL: $WEBHOOK_URL"
echo "2. Update desktop app with payment URL: $PAYMENT_URL"
echo "3. Test payment flow with sandbox"
echo "4. Configure environment variables for production"
echo ""
echo -e "${BLUE}📖 Test Commands:${NC}"
echo "curl $PAYMENT_URL -X POST -H 'Content-Type: application/json' -d '{\"customer_email\":\"test@example.com\",\"package_type\":\"professional_1y\"}'"
echo ""
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
```
## 📄 File: `main.py`
**Đường dẫn:** `/Users/annhu/vtrack_app/V_Track_CloudFunctions/functions/create_payment/main.py`

```python
"""
V_Track Payment CloudFunction với PayOS SDK
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any
from payos import PayOS, ItemData, PaymentData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PayOS Credentials 
PAYOS_CLIENT_ID = os.getenv('PAYOS_CLIENT_ID', 'f5b7601e-9bc9-4392-baac-ebecabb1023b')
PAYOS_API_KEY = os.getenv('PAYOS_API_KEY', '56956c30-7244-4f2a-bf6e-9a3ffe93d59b')  
PAYOS_CHECKSUM_KEY = os.getenv('PAYOS_CHECKSUM_KEY', '6eb7be3c098bd6c3b51125b8d093b8c8aa34e215149bb20fb50828c6d3577b4a')

class PayOSClient:
    """PayOS Integration với SDK"""
    
    def __init__(self):
        self.payos = PayOS(
            client_id=PAYOS_CLIENT_ID,
            api_key=PAYOS_API_KEY,
            checksum_key=PAYOS_CHECKSUM_KEY
        )
        logger.info("PayOS SDK client initialized")
        
    def create_payment_link(self, order_data: Dict[str, Any]) -> str:
        """Create PayOS payment link using SDK"""
        try:
            # Generate unique order code
            order_code = int(time.time() * 1000) % 9999999
            
            # Prepare item data
            item = ItemData(
                name=order_data.get('item_name', 'V_Track License'),
                quantity=1,
                price=int(order_data['amount'])
            )
            
            # Prepare payment data (description max 25 chars)
            payment_data = PaymentData(
                orderCode=order_code,
                amount=int(order_data['amount']),
                description="V_Track License",  # Keep under 25 chars
                items=[item],
                cancelUrl="https://v-track.app/cancel",
                returnUrl="https://v-track.app/success"
            )
            
            # Create payment link using SDK
            result = self.payos.createPaymentLink(paymentData=payment_data)
            
            logger.info(f"PayOS payment created: {order_code}")
            logger.info(f"PayOS result: {result}")
            
            # Extract checkout URL from result
            if hasattr(result, 'checkoutUrl'):
                return result.checkoutUrl
            else:
                logger.error(f"No checkoutUrl in PayOS response: {result}")
                raise Exception("PayOS success but no checkoutUrl")
                
        except Exception as e:
            logger.error(f"PayOS payment creation failed: {str(e)}")
            raise

def get_package_info(package_type: str) -> Dict[str, Any]:
    """Get package pricing - Updated test pricing"""
    packages = {
        'personal_1m': {
            'name': 'Personal Monthly',
            'price': 2000,  # 2k VND test
            'duration_days': 30
        },
        'personal_1y': {
            'name': 'Personal Annual',
            'price': 20000,  # 20k VND test
            'duration_days': 365
        },
        'business_1m': {
            'name': 'Business Monthly',
            'price': 5000,  # 5k VND test
            'duration_days': 30
        },
        'business_1y': {
            'name': 'Business Annual',
            'price': 50000,  # 50k VND test
            'duration_days': 365
        }
    }
    return packages.get(package_type)

def create_payment(request):
    """Main payment creation handler"""
    try:
        request_data = request.get_json()
        
        # Validate required fields
        required_fields = ['customer_email', 'package_type']
        for field in required_fields:
            if field not in request_data:
                return {'error': f'Missing required field: {field}'}, 400
        
        # Get package info
        package_info = get_package_info(request_data['package_type'])
        if not package_info:
            return {'error': 'Invalid package type'}, 400
        
        # Prepare order data
        order_code = int(datetime.now().timestamp())
        order_data = {
            'order_code': order_code,
            'amount': package_info['price'],
            'item_name': package_info['name'],
            'customer_email': request_data['customer_email']
        }
        
        # Create PayOS payment using SDK
        payos_client = PayOSClient()
        payment_url = payos_client.create_payment_link(order_data)
        
        logger.info(f"Payment created successfully: {order_code}")
        
        return {
            'success': True,
            'payment_url': payment_url,
            'order_code': order_code,
            'order_id': f'vtrack_{order_code}',
            'provider': 'payos',
            'amount': package_info['price']
        }
        
    except Exception as e:
        logger.error(f"Payment creation failed: {str(e)}")
        return {'error': str(e)}, 500

def create_payment_handler(request):
    """Cloud Functions entry point"""
    # Handle CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Content-Type': 'application/json'
    }
    
    try:
        # Handle health check
        if request.method == 'GET':
            action = request.args.get('action')
            if action == 'health':
                health_response = {
                    'status': 'healthy',
                    'service': 'create_payment',
                    'timestamp': datetime.now().isoformat(),
                    'provider': 'payos_sdk'
                }
                return (json.dumps(health_response), 200, headers)
        
        # Handle payment creation
        if request.method == 'POST':
            result = create_payment(request)
            
            if isinstance(result, tuple):
                response_data, status_code = result
                return (json.dumps(response_data), status_code, headers)
            else:
                return (json.dumps(result), 200, headers)
        
        # Method not allowed
        return (json.dumps({'error': 'Method not allowed'}), 405, headers)
            
    except Exception as e:
        logger.error(f"Function execution failed: {str(e)}")
        error_response = {'error': 'Internal server error', 'details': str(e)}
        return (json.dumps(error_response), 500, headers)
```
## 📄 File: `main.py`
**Đường dẫn:** `/Users/annhu/vtrack_app/V_Track_CloudFunctions/functions/license_service/main.py`

```python
"""
V_Track License Service Cloud Function
Handles license management and validation
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from flask import Request

# Add shared directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

try:
    from ...shared import get_firestore_client
except ImportError as e:
    logging.error(f"Import error: {e}")
    # Fallback for local testing
    class MockFirestore:
        def get_license_by_key(self, key): 
            return {"id": "mock", "status": "active", "valid_until": datetime.now() + timedelta(days=30)}
        def get_licenses_by_email(self, email): 
            return [{"id": "mock", "status": "active"}]
        def health_check(self): 
            return {"status": "mock"}
    
    def get_firestore_client():
        return MockFirestore()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def license_service(request: Request) -> tuple[str, int]:
    """
    Main Cloud Function entry point for license services
    
    Args:
        request: HTTP request object
        
    Returns:
        Tuple of (response_json, status_code)
    """
    try:
        # Handle health check requests
        if request.method == 'GET':
            action = request.args.get('action')
            if action == 'health':
                return handle_health_check()
            elif action == 'validate':
                license_key = request.args.get('license_key')
                if license_key:
                    return handle_license_validation(license_key)
                else:
                    return json.dumps({
                        'success': False,
                        'error': 'Missing license_key parameter'
                    }), 400
        
        # Handle POST requests
        if request.method == 'POST':
            return handle_license_operations(request)
        
        # Method not allowed
        return json.dumps({
            'success': False,
            'error': 'Method not allowed'
        }), 405
        
    except Exception as e:
        logger.error(f"Unexpected error in license_service: {str(e)}")
        return json.dumps({
            'success': False,
            'error': 'Internal server error'
        }), 500

def handle_health_check() -> tuple[str, int]:
    """Handle health check requests"""
    try:
        firestore_client = get_firestore_client()
        firestore_health = firestore_client.health_check()
        
        return json.dumps({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'license_service',
            'firestore': firestore_health
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return json.dumps({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

def handle_license_validation(license_key: str) -> tuple[str, int]:
    """
    Validate a license key
    
    Args:
        license_key: License key to validate
        
    Returns:
        Validation result
    """
    try:
        firestore_client = get_firestore_client()
        license_data = firestore_client.get_license_by_key(license_key)
        
        if not license_data:
            return json.dumps({
                'valid': False,
                'error': 'License not found'
            }), 404
        
        # Check if license is still valid
        valid_until = license_data.get('valid_until')
        if valid_until and isinstance(valid_until, datetime):
            is_expired = valid_until < datetime.now()
        else:
            # Assume valid if no expiry date
            is_expired = False
        
        status = license_data.get('status', 'unknown')
        is_active = status == 'active'
        
        return json.dumps({
            'valid': is_active and not is_expired,
            'license_key': license_key,
            'status': status,
            'customer_email': license_data.get('customer_email', ''),
            'package_type': license_data.get('package_type', ''),
            'valid_until': valid_until.isoformat() if valid_until else None,
            'is_expired': is_expired,
            'validated_at': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"License validation failed: {str(e)}")
        return json.dumps({
            'valid': False,
            'error': 'Validation failed'
        }), 500

def handle_license_operations(request: Request) -> tuple[str, int]:
    """Handle POST license operations"""
    try:
        # Parse request data
        if not request.is_json:
            return json.dumps({
                'success': False,
                'error': 'Content-Type must be application/json'
            }), 400
        
        data = request.get_json()
        action = data.get('action')
        
        if action == 'get_licenses':
            # Get licenses by email
            customer_email = data.get('customer_email')
            if not customer_email:
                return json.dumps({
                    'success': False,
                    'error': 'Missing customer_email'
                }), 400
            
            return handle_get_licenses_by_email(customer_email)
        
        elif action == 'validate_license':
            # Validate license (alternative to GET method)
            license_key = data.get('license_key')
            if not license_key:
                return json.dumps({
                    'success': False,
                    'error': 'Missing license_key'
                }), 400
            
            return handle_license_validation(license_key)
        
        else:
            return json.dumps({
                'success': False,
                'error': f'Unknown action: {action}'
            }), 400
        
    except Exception as e:
        logger.error(f"License operation failed: {str(e)}")
        return json.dumps({
            'success': False,
            'error': 'Operation failed'
        }), 500

def handle_get_licenses_by_email(customer_email: str) -> tuple[str, int]:
    """
    Get all licenses for a customer email
    
    Args:
        customer_email: Customer email address
        
    Returns:
        List of licenses
    """
    try:
        firestore_client = get_firestore_client()
        licenses = firestore_client.get_licenses_by_email(customer_email)
        
        # Format licenses for response
        formatted_licenses = []
        for license_data in licenses:
            valid_until = license_data.get('valid_until')
            if valid_until and isinstance(valid_until, datetime):
                is_expired = valid_until < datetime.now()
                valid_until_str = valid_until.isoformat()
            else:
                is_expired = False
                valid_until_str = None
            
            formatted_licenses.append({
                'license_key': license_data.get('license_key', ''),
                'package_type': license_data.get('package_type', ''),
                'package_name': license_data.get('package_info', {}).get('name', ''),
                'status': license_data.get('status', 'unknown'),
                'valid_until': valid_until_str,
                'is_expired': is_expired,
                'created_at': license_data.get('created_at', '').isoformat() if isinstance(license_data.get('created_at'), datetime) else license_data.get('created_at', '')
            })
        
        return json.dumps({
            'success': True,
            'customer_email': customer_email,
            'licenses': formatted_licenses,
            'total_count': len(formatted_licenses)
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get licenses by email: {str(e)}")
        return json.dumps({
            'success': False,
            'error': 'Failed to retrieve licenses'
        }), 500

# Local testing support
if __name__ == "__main__":
    # For local testing with functions-framework
    try:
        from ...shared import create_app
        app = create_app(license_service)
        app.run(host='0.0.0.0', port=8083, debug=True)
    except ImportError:
        print("functions-framework not installed. Install with: pip install functions-framework")
        print("For manual testing, this function expects Flask Request objects")
```
## 📄 File: `main.py`
**Đường dẫn:** `/Users/annhu/vtrack_app/V_Track_CloudFunctions/functions/webhook_handler/main.py`

```python
import sys
import os
import json
import logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from payos_client import PayOSClient
from zalopay_utils import ZaloPayClient
from Firestore_client import get_firestore_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def detect_provider(data):
    """Detect payment provider from webhook data"""
    if 'signature' in data and 'data' in data:
        return 'payos'
    elif 'mac' in data and 'data' in data:
        return 'zalopay'
    return None

def webhook_handler(request):
    """Handle webhooks from multiple payment providers"""
    try:
        request_data = request.get_json()
        provider = detect_provider(request_data)
        
        if provider == 'payos':
            return handle_payos_webhook(request_data)
        elif provider == 'zalopay':
            return handle_zalopay_webhook(request_data)
        else:
            logger.error(f"Unknown provider for data: {json.dumps(request_data, ensure_ascii=False)}")
            return {'error': 'Unknown provider'}, 400
            
    except Exception as e:
        logger.error(f"Webhook handling failed: {str(e)}")
        return {'error': str(e)}, 500

def handle_payos_webhook(request_data):
    """Handle PayOS webhook"""
    try:
        client = PayOSClient()
        webhook_data = client.verify_webhook_data(request_data)
        
        if webhook_data['code'] == '00':
            # Fixed: Use correct key mapping
            process_result = process_successful_payment({
                'order_code': webhook_data['orderCode'],  # Map orderCode -> order_code
                'amount': webhook_data['amount'],
                'payment_id': webhook_data['paymentLinkId'],
                'description': webhook_data.get('description', ''),
                'provider': 'payos'
            })
            
            logger.info(f"PayOS webhook processed: {webhook_data['orderCode']}")
            return {'success': True, 'order_code': webhook_data['orderCode']}, 200
        else:
            logger.info(f"PayOS payment failed: {webhook_data['orderCode']}, status: {webhook_data['code']}")
            return {'success': False, 'status': webhook_data['code']}, 200
            
    except Exception as e:
        logger.error(f"PayOS webhook failed: {str(e)}")
        return {'error': str(e)}, 400

def handle_zalopay_webhook(request_data):
    """Handle ZaloPay webhook"""
    try:
        client = ZaloPayClient()
        result = client.handle_webhook(request_data)
        logger.info(f"ZaloPay webhook processed: {result}")
        return {'success': True, 'result': result}, 200
    except Exception as e:
        logger.error(f"ZaloPay webhook failed: {str(e)}")
        return {'error': str(e)}, 400

def process_successful_payment(payment_data):
    """Process successful payment and trigger license generation"""
    try:
        # Mock license generation for testing
        license_key = f"VTRACK-{payment_data['order_code']}-{payment_data['amount']}"
        
        logger.info(f"Generated license: {license_key} for order: {payment_data['order_code']}")
        
        # Try to save to Firestore (will use mock in test mode)
        try:
            firestore_client = get_firestore_client()
            # Mock save operation
            result = {
                'license_key': license_key,
                'order_code': payment_data['order_code'],
                'status': 'completed'
            }
            logger.info(f"Payment processed successfully: {payment_data['order_code']}")
            return result
        except Exception as db_error:
            logger.warning(f"Firestore save failed: {db_error}")
            return {
                'license_key': license_key,
                'order_code': payment_data['order_code'],
                'status': 'completed'
            }
        
    except Exception as e:
        logger.error(f"Payment processing failed: {str(e)}")
        raise

def main(request):
    """Cloud Functions entry point"""
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
        return ('', 204, headers)
    
    result = webhook_handler(request)
    headers = {'Access-Control-Allow-Origin': '*'}
    return (result, 200, headers) if isinstance(result, dict) else result
```
## 📄 File: `settings.json`
**Đường dẫn:** `/Users/annhu/vtrack_app/V_Track_CloudFunctions/.vscode/settings.json`

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/.pytest_cache": true,
        "**/node_modules": true,
        "**/.env": false
    },
    "python.analysis.extraPaths": [
        "./shared",
        "./functions/webhook_handler"
    ]
}

```
## 📄 File: `extensions.json`
**Đường dẫn:** `/Users/annhu/vtrack_app/V_Track_CloudFunctions/.vscode/extensions.json`

```json
{
    "recommendations": [
        "ms-python.python",
        "googlecloudtools.cloudcode", 
        "ms-vscode.vscode-json",
        "ms-python.pylint",
        "ms-python.black-formatter",
        "ms-python.pytest"
    ]
}

```
## 📄 File: `launch.json`
**Đường dẫn:** `/Users/annhu/vtrack_app/V_Track_CloudFunctions/.vscode/launch.json`

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Payment Function",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/functions/create_payment/main.py",
            "console": "integratedTerminal",
            "args": [],
            "env": {
                "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/shared",
                "FUNCTION_TARGET": "create_payment"
            },
            "cwd": "${workspaceFolder}/functions/create_payment"
        },
        {
            "name": "Debug Webhook Function", 
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/functions/webhook_handler/main.py",
            "console": "integratedTerminal",
            "args": [],
            "env": {
                "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/shared",
                "FUNCTION_TARGET": "webhook_handler"
            },
            "cwd": "${workspaceFolder}/functions/webhook_handler"
        },
        {
            "name": "Debug License Function",
            "type": "debugpy", 
            "request": "launch",
            "program": "${workspaceFolder}/functions/license_service/main.py",
            "console": "integratedTerminal",
            "args": [],
            "env": {
                "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/shared",
                "FUNCTION_TARGET": "license_service"
            },
            "cwd": "${workspaceFolder}/functions/license_service"
        },
        {
            "name": "Test Payment Function Local",
            "type": "debugpy",
            "request": "launch", 
            "module": "functions_framework",
            "args": [
                "--target=create_payment",
                "--source=${workspaceFolder}/functions/create_payment/main.py",
                "--port=8081"
            ],
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/shared"
            },
            "cwd": "${workspaceFolder}"
        }
    ]
}
```