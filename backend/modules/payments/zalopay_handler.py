# backend/modules/payments/zalopay_handler.py

import hmac
import hashlib
import json
import time
import uuid
import os
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
import requests
from modules.db_utils import get_db_connection

# Tạo Blueprint cho ZaloPay
zalopay_bp = Blueprint('zalopay', __name__)

# Setup logging
logger = logging.getLogger(__name__)

class ZaloPayHandler:
    """
    Core ZaloPay integration handler for V_track license management
    Handles payment creation, verification, and order management
    """
    
    def __init__(self):
        # Load config từ environment variables
        self.app_id = os.getenv('ZALOPAY_APP_ID', '553')  # Default test app_id
        self.key1 = os.getenv('ZALOPAY_KEY1', '9phuAOYhan4urywHTh0ndEXiV3pKHr5Q')  # Test key1
        self.key2 = os.getenv('ZALOPAY_KEY2', 'Iyz2habzyr7AG8SgvoBCbKwKi3UzlLi3')  # Test key2
        self.endpoint = os.getenv('ZALOPAY_ENDPOINT', 'https://sandbox.zalopay.com.vn/v001/tpe/createorder')
        self.query_endpoint = os.getenv('ZALOPAY_QUERY_ENDPOINT', 'https://sandbox.zalopay.com.vn/v001/tpe/getstatusbyapptransid')
        self.environment = os.getenv('ZALOPAY_ENVIRONMENT', 'sandbox')
        self.callback_url = os.getenv('ZALOPAY_CALLBACK_URL', 'http://localhost:8080/webhook/zalopay')
        
        logger.info(f"ZaloPay Handler initialized - Environment: {self.environment}")
    
    def create_order(self, license_info):
        """
        Tạo đơn hàng license trên ZaloPay
        
        Args:
            license_info (dict): Thông tin license {
                'customer_email': string,
                'license_type': string,
                'price': int (VND),
                'features': list,
                'duration_days': int
            }
            
        Returns:
            dict: Kết quả tạo order với payment_url
        """
        try:
            # Generate unique transaction ID
            app_trans_id = f"{datetime.now().strftime('%y%m%d')}_{str(uuid.uuid4())[:8]}"
            
            # Chuẩn bị embed_data (metadata)
            embed_data = {
                "license_type": license_info.get('license_type', 'desktop'),
                "customer_email": license_info.get('customer_email'),
                "features": license_info.get('features', ['full_access']),
                "duration_days": license_info.get('duration_days', 365),
                "v_track_version": "1.0"
            }
            
            # Chuẩn bị item data
            items = [{
                "itemid": "vtrack_license",
                "itemname": f"V_track {license_info.get('license_type', 'Desktop')} License",
                "itemprice": license_info.get('price', 500000),
                "itemquantity": 1
            }]
            
            # Tạo order data
            order_data = {
                "appid": int(self.app_id),
                "apptransid": app_trans_id,
                "appuser": license_info.get('customer_email', 'vtrack_user'),
                "apptime": int(time.time() * 1000),  # milliseconds
                "embeddata": json.dumps(embed_data),
                "item": json.dumps(items),
                "amount": license_info.get('price', 500000),  # VND
                "description": f"V_track License - {license_info.get('customer_email')}",
                "bankcode": "",  # Use ZaloPay wallet
                "callback_url": self.callback_url  # Webhook callback URL
            }
            
            # Tạo MAC signature (FIXED - không include callback_url)
            mac_data = f"{order_data['appid']}|{order_data['apptransid']}|{order_data['appuser']}|{order_data['amount']}|{order_data['apptime']}|{order_data['embeddata']}|{order_data['item']}"
            
            order_data['mac'] = hmac.new(
                self.key1.encode('utf-8'),
                mac_data.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            logger.info(f"Creating ZaloPay order: {app_trans_id}")
            logger.debug(f"Order data sent to ZaloPay: {json.dumps(order_data, indent=2)}")
            
            # Gửi request tới ZaloPay
            response = requests.post(self.endpoint, data=order_data, timeout=30)
            logger.debug(f"Raw ZaloPay response status: {response.status_code}, content: {response.text}")
            
            try:
                result = response.json()
            except ValueError:
                logger.error(f"Invalid JSON response from ZaloPay: {response.text}")
                return {
                    'success': False,
                    'error': 'Invalid response from ZaloPay',
                    'error_code': None
                }
            
            # FIXED: Use correct field names from ZaloPay API
            if result.get('returncode') == 1:
                # Lưu order vào database
                self._store_payment_transaction({
                    'app_trans_id': app_trans_id,
                    'customer_email': license_info.get('customer_email'),
                    'amount': license_info.get('price', 500000),
                    'license_type': license_info.get('license_type', 'desktop'),
                    'embed_data': json.dumps(embed_data),
                    'status': 'pending'
                })
                
                return {
                    'success': True,
                    'payment_url': result.get('orderurl'),
                    'app_trans_id': app_trans_id,
                    'zp_trans_token': result.get('zptranstoken'),
                    'order_id': app_trans_id
                }
            else:
                logger.error(f"ZaloPay order creation failed: {result}")
                return {
                    'success': False,
                    'error': result.get('returnmessage', 'Unknown error'),
                    'error_code': result.get('returncode')
                }
                
        except requests.RequestException as e:
            logger.error(f"ZaloPay API request failed: {str(e)}")
            return {
                'success': False,
                'error': f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Order creation error: {str(e)}")
            return {
                'success': False,
                'error': f"Internal error: {str(e)}"
            }
    
    def verify_callback(self, callback_data):
        """
        Verify ZaloPay callback signature
        
        Args:
            callback_data (dict): Callback data từ ZaloPay
            
        Returns:
            bool: True nếu signature hợp lệ
        """
        try:
            data_str = callback_data.get('data', '')
            received_mac = callback_data.get('mac', '')
            
            if not data_str or not received_mac:
                logger.warning("Missing data or mac in callback")
                return False
            
            # Calculate expected MAC using key2
            calculated_mac = hmac.new(
                self.key2.encode('utf-8'),
                data_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(calculated_mac, received_mac)
            
            if not is_valid:
                logger.warning(f"Invalid callback signature. Expected: {calculated_mac}, Received: {received_mac}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Callback verification error: {e}")
            return False
    
    def query_order_status(self, app_trans_id):
        """
        Query order status từ ZaloPay
        
        Args:
            app_trans_id (str): Transaction ID
            
        Returns:
            dict: Order status info
        """
        try:
            query_data = {
                "appid": int(self.app_id),
                "apptransid": app_trans_id
            }
            
            # Create MAC for query
            mac_data = f"{query_data['appid']}|{query_data['apptransid']}|{self.key1}"
            query_data['mac'] = hmac.new(
                self.key1.encode('utf-8'),
                mac_data.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            response = requests.post(self.query_endpoint, data=query_data, timeout=30)
            logger.debug(f"Raw ZaloPay response status: {response.status_code}, content: {response.text}")
            
            try:
                result = response.json()
            except ValueError:
                logger.error(f"Invalid JSON response from ZaloPay: {response.text}")
                return {
                    'success': False,
                    'error': 'Invalid response from ZaloPay',
                    'error_code': None
                }
            
            logger.info(f"Order status query for {app_trans_id}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Order status query error: {str(e)}")
            return {
                'returncode': -1,
                'returnmessage': f"Query error: {str(e)}"
            }
    
    def _store_payment_transaction(self, transaction_data):
        """
        Store payment transaction in database
        
        Args:
            transaction_data (dict): Transaction info để lưu
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO payment_transactions 
                    (app_trans_id, customer_email, amount, status, payment_data, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    transaction_data['app_trans_id'],
                    transaction_data['customer_email'],
                    transaction_data['amount'],
                    transaction_data['status'],
                    json.dumps(transaction_data),
                    datetime.now()
                ))
                
                conn.commit()
                logger.info(f"Stored payment transaction: {transaction_data['app_trans_id']}")
                
        except Exception as e:
            logger.error(f"Failed to store payment transaction: {str(e)}")
    
    def get_payment_transaction(self, app_trans_id):
        """
        Retrieve payment transaction from database
        
        Args:
            app_trans_id (str): Transaction ID
            
        Returns:
            dict: Transaction data hoặc None
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM payment_transactions 
                    WHERE app_trans_id = ?
                """, (app_trans_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'app_trans_id': row[1],
                        'zalopay_trans_id': row[2],
                        'customer_email': row[3],
                        'amount': row[4],
                        'status': row[5],
                        'payment_data': json.loads(row[6]) if row[6] else {},
                        'created_at': row[7],
                        'completed_at': row[8]
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to get payment transaction: {str(e)}")
            return None

# Initialize handler
zalopay_handler = ZaloPayHandler()

# Flask Routes
@zalopay_bp.route('/create-order', methods=['POST'])
def create_payment_order():
    """API endpoint tạo ZaloPay payment order"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['customer_email', 'license_type', 'price']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate email format
        email = data['customer_email']
        if '@' not in email or '.' not in email:
            return jsonify({
                'success': False,
                'error': 'Invalid email format'
            }), 400
        
        # Validate price
        price = data['price']
        if not isinstance(price, int) or price < 10000:  # Minimum 10,000 VND
            return jsonify({
                'success': False,
                'error': 'Invalid price (minimum 10,000 VND)'
            }), 400
        
        # Create order
        result = zalopay_handler.create_order(data)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Create order error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@zalopay_bp.route('/order-status/<app_trans_id>', methods=['GET'])
def get_order_status(app_trans_id):
    """API endpoint query order status"""
    try:
        # Query từ ZaloPay
        zalopay_status = zalopay_handler.query_order_status(app_trans_id)
        
        # Query từ local database
        local_transaction = zalopay_handler.get_payment_transaction(app_trans_id)
        
        return jsonify({
            'success': True,
            'zalopay_status': zalopay_status,
            'local_transaction': local_transaction
        }), 200
        
    except Exception as e:
        logger.error(f"Order status query error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Query error: {str(e)}'
        }), 500

@zalopay_bp.route('/test-connection', methods=['GET'])
def test_zalopay_connection():
    """Test endpoint để kiểm tra ZaloPay configuration"""
    try:
        config_info = {
            'app_id': zalopay_handler.app_id,
            'environment': zalopay_handler.environment,
            'endpoint': zalopay_handler.endpoint,
            'callback_url': zalopay_handler.callback_url,
            'has_key1': bool(zalopay_handler.key1),
            'has_key2': bool(zalopay_handler.key2),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'message': 'ZaloPay Handler initialized successfully',
            'config': config_info
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Configuration error: {str(e)}'
        }), 500