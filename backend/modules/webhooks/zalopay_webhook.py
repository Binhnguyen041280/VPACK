# backend/modules/webhooks/zalopay_webhook.py

import json
import logging
from datetime import datetime
from modules.db_utils import get_db_connection
from flask import Blueprint, request, jsonify
from modules.payments.zalopay_handler import zalopay_handler
from modules.licensing.license_models import PaymentTransaction, License, EmailLog
from modules.payments.license_generator import LicenseGenerator
from modules.payments.email_sender import EmailSender

# Create webhook blueprint
webhook_bp = Blueprint('webhook', __name__)

# Setup logging
logger = logging.getLogger(__name__)

# Initialize components
license_generator = LicenseGenerator()
email_sender = EmailSender()

@webhook_bp.route('/zalopay', methods=['POST'])
def zalopay_callback():
    """
    ZaloPay payment callback handler
    Xử lý thông báo thanh toán thành công từ ZaloPay
    """
    try:
        # Get callback data
        callback_data = request.get_json()
        
        if not callback_data:
            logger.warning("Empty callback data received")
            return jsonify({
                'return_code': -1,
                'return_message': 'Empty callback data'
            }), 400
        
        logger.info(f"ZaloPay callback received: {callback_data}")
        
        # Verify callback signature
        if not zalopay_handler.verify_callback(callback_data):
            logger.error("Invalid callback signature")
            return jsonify({
                'return_code': -1,
                'return_message': 'Invalid signature'
            }), 400
        
        # Parse payment data
        try:
            payment_data = json.loads(callback_data['data'])
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse callback data: {e}")
            return jsonify({
                'return_code': -1,
                'return_message': 'Invalid data format'
            }), 400
        
        app_trans_id = payment_data.get('app_trans_id')
        zp_trans_id = payment_data.get('zp_trans_id')
        
        if not app_trans_id:
            logger.error("Missing app_trans_id in callback")
            return jsonify({
                'return_code': -1,
                'return_message': 'Missing transaction ID'
            }), 400
        
        logger.info(f"Processing payment callback for transaction: {app_trans_id}")
        
        # Get payment transaction from database
        transaction = PaymentTransaction.get_by_app_trans_id(app_trans_id)
        
        if not transaction:
            logger.error(f"Transaction not found: {app_trans_id}")
            return jsonify({
                'return_code': 0,
                'return_message': 'Transaction not found'
            }), 404
        
        # Check if already processed
        if transaction['status'] == 'completed':
            logger.info(f"Transaction already processed: {app_trans_id}")
            return jsonify({
                'return_code': 1,
                'return_message': 'Already processed'
            })
        
        # Update payment status
        success = PaymentTransaction.update_status(
            app_trans_id=app_trans_id,
            status='completed',
            zalopay_trans_id=zp_trans_id
        )
        
        if not success:
            logger.error(f"Failed to update payment status: {app_trans_id}")
            return jsonify({
                'return_code': 0,
                'return_message': 'Failed to update payment'
            }), 500
        
        # Process license generation and delivery
        license_result = process_license_fulfillment(transaction, payment_data)
        
        if license_result['success']:
            logger.info(f"License fulfillment completed for transaction: {app_trans_id}")
            return jsonify({
                'return_code': 1,
                'return_message': 'success'
            })
        else:
            logger.error(f"License fulfillment failed: {license_result['error']}")
            return jsonify({
                'return_code': 0,
                'return_message': f'License error: {license_result["error"]}'
            }), 500
            
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return jsonify({
            'return_code': 0,
            'return_message': f'Processing error: {str(e)}'
        }), 500

def process_license_fulfillment(transaction, payment_data):
    """
    Process complete license fulfillment workflow:
    1. Generate cryptographic license key
    2. Store license in database
    3. Send license email to customer
    
    Args:
        transaction (dict): Payment transaction data
        payment_data (dict): ZaloPay payment callback data
        
    Returns:
        dict: Success/failure result với details
    """
    try:
        customer_email = transaction['customer_email']
        payment_metadata = transaction.get('payment_data', {})
        
        logger.info(f"Starting license fulfillment for {customer_email}")
        
        # 1. Generate license key
        license_info = {
            'customer_email': customer_email,
            'product_type': payment_metadata.get('license_type', 'desktop'),
            'features': payment_metadata.get('features', ['full_access']),
            'duration_days': payment_metadata.get('duration_days', 365)
        }
        
        license_key = license_generator.generate_license(license_info)
        
        if not license_key:
            return {
                'success': False,
                'error': 'Failed to generate license key'
            }
        
        # 2. Store license in database
        license_id = License.create(
            license_key=license_key,
            customer_email=customer_email,
            payment_transaction_id=transaction['id'],
            product_type=license_info['product_type'],
            features=license_info['features'],
            expires_days=license_info['duration_days']
        )
        
        if not license_id:
            return {
                'success': False,
                'error': 'Failed to store license in database'
            }
        
        # 3. Send license email
        email_result = send_license_email(
            license_id=license_id,
            customer_email=customer_email,
            license_key=license_key,
            license_info=license_info,
            transaction=transaction
        )
        
        if not email_result['success']:
            logger.warning(f"Email delivery failed for license {license_id}: {email_result['error']}")
            # Continue anyway - license is generated, email can be resent
        
        logger.info(f"License fulfillment completed: License ID {license_id}")
        
        return {
            'success': True,
            'license_id': license_id,
            'license_key': license_key,
            'email_sent': email_result['success']
        }
        
    except Exception as e:
        logger.error(f"License fulfillment error: {str(e)}")
        return {
            'success': False,
            'error': f'Fulfillment error: {str(e)}'
        }

def send_license_email(license_id, customer_email, license_key, license_info, transaction):
    """
    Send license delivery email to customer
    
    Args:
        license_id (int): License database ID
        customer_email (str): Customer email address
        license_key (str): Generated license key
        license_info (dict): License details
        transaction (dict): Payment transaction data
        
    Returns:
        dict: Email delivery result
    """
    try:
        # Create email log entry
        subject = f"Your V_track {license_info['product_type'].title()} License"
        email_log_id = EmailLog.create(
            license_id=license_id,
            recipient_email=customer_email,
            email_type='license_delivery',
            subject=subject
        )
        
        # Prepare email content
        email_content = {
            'customer_email': customer_email,
            'license_key': license_key,
            'product_type': license_info['product_type'],
            'features': license_info['features'],
            'expires_days': license_info['duration_days'],
            'transaction_id': transaction['app_trans_id'],
            'amount': transaction['amount'],
            'purchase_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Send email
        email_result = email_sender.send_license_email(
            recipient=customer_email,
            subject=subject,
            content=email_content
        )
        
        # Update email log status
        if email_log_id:
            EmailLog.update_status(
                log_id=email_log_id,
                status='sent' if email_result['success'] else 'failed',
                error_message=email_result.get('error')
            )
        
        return email_result
        
    except Exception as e:
        logger.error(f"Email sending error: {str(e)}")
        return {
            'success': False,
            'error': f'Email error: {str(e)}'
        }

@webhook_bp.route('/test-webhook', methods=['POST'])
def test_webhook():
    """Test endpoint để kiểm tra webhook functionality"""
    try:
        data = request.get_json()
        
        # Simulate a test transaction
        test_transaction = {
            'id': 999,
            'app_trans_id': f"TEST_{datetime.now().strftime('%y%m%d_%H%M%S')}",
            'customer_email': data.get('test_email', 'test@example.com'),
            'amount': data.get('amount', 100000),
            'payment_data': {
                'license_type': 'desktop',
                'features': ['full_access'],
                'duration_days': 365
            }
        }
        
        # Test license fulfillment
        result = process_license_fulfillment(test_transaction, {})
        
        return jsonify({
            'success': True,
            'message': 'Webhook test completed',
            'fulfillment_result': result
        }), 200
        
    except Exception as e:
        logger.error(f"Webhook test error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Test error: {str(e)}'
        }), 500

@webhook_bp.route('/resend-license', methods=['POST'])
def resend_license():
    """Resend license email for existing transaction"""
    try:
        data = request.get_json()
        
        license_key = data.get('license_key')
        email = data.get('email')
        
        if not license_key and not email:
            return jsonify({
                'success': False,
                'error': 'Either license_key or email required'
            }), 400
        
        # Find license
        if license_key:
            license_data = License.get_by_key(license_key)
            if not license_data:
                return jsonify({
                    'success': False,
                    'error': 'License not found'
                }), 404
        else:
            licenses = License.get_by_email(email)
            if not licenses:
                return jsonify({
                    'success': False,
                    'error': 'No licenses found for email'
                }), 404
            license_data = licenses[0]  # Get most recent
        
        # Resend email
        license_info = {
            'product_type': license_data['product_type'],
            'features': license_data['features'],
            'duration_days': 365  # Default
        }
        
        email_result = send_license_email(
            license_id=license_data['id'],
            customer_email=license_data['customer_email'],
            license_key=license_data['license_key'],
            license_info=license_info,
            transaction={'app_trans_id': 'RESEND', 'amount': 0}
        )
        
        if email_result['success']:
            return jsonify({
                'success': True,
                'message': 'License email resent successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': email_result['error']
            }), 500
            
    except Exception as e:
        logger.error(f"Resend license error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Resend error: {str(e)}'
        }), 500

@webhook_bp.route('/webhook-status', methods=['GET'])
def webhook_status():
    """Get webhook system status và statistics"""
    try:
        from modules.licensing.license_models import get_license_stats
        
        stats = get_license_stats()
        
        # Recent webhook activity
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Recent payments
            cursor.execute("""
                SELECT COUNT(*) FROM payment_transactions 
                WHERE created_at > datetime('now', '-24 hours')
            """)
            recent_payments = cursor.fetchone()[0]
            
            # Recent emails
            cursor.execute("""
                SELECT COUNT(*) FROM email_logs 
                WHERE sent_at > datetime('now', '-24 hours') AND status = 'sent'
            """)
            recent_emails = cursor.fetchone()[0]
            
            # Failed emails
            cursor.execute("""
                SELECT COUNT(*) FROM email_logs 
                WHERE sent_at > datetime('now', '-24 hours') AND status = 'failed'
            """)
            failed_emails = cursor.fetchone()[0]
        
        return jsonify({
            'success': True,
            'webhook_status': 'operational',
            'stats': stats,
            'recent_activity': {
                'payments_24h': recent_payments,
                'emails_sent_24h': recent_emails,
                'emails_failed_24h': failed_emails
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Webhook status error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Status error: {str(e)}'
        }), 500