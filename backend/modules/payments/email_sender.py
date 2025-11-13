# backend/modules/payments/email_sender.py

import smtplib
import ssl
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from jinja2 import Environment, FileSystemLoader
import json
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class EmailSender:
    """
    Automated email sender for V_track license delivery
    Supports HTML templates, attachments, và retry logic
    """

    def __init__(self):
        # SMTP Configuration từ environment variables
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.sender_name = os.getenv("SENDER_NAME", "V_track License System")
        self.sender_email = self.smtp_username

        # Template configuration
        template_dir = os.path.join(os.path.dirname(__file__), "..", "..", "templates", "email")
        os.makedirs(template_dir, exist_ok=True)

        self.jinja_env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)

        # Create default templates if not exist
        self._ensure_email_templates(template_dir)

        logger.info(f"Email sender initialized - SMTP: {self.smtp_host}:{self.smtp_port}")

    def _ensure_email_templates(self, template_dir):
        """Ensure email templates exist"""
        try:
            license_template_path = os.path.join(template_dir, "license_delivery.html")

            if not os.path.exists(license_template_path):
                default_template = self._get_default_license_template()
                with open(license_template_path, "w", encoding="utf-8") as f:
                    f.write(default_template)
                logger.info("Created default license email template")

        except Exception as e:
            logger.error(f"Template creation error: {str(e)}")

    def _get_default_license_template(self):
        """Get default HTML email template"""
        return """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your V_track License</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background-color: #f4f4f4; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        .header { text-align: center; border-bottom: 2px solid #0066CC; padding-bottom: 20px; margin-bottom: 30px; }
        .logo { font-size: 28px; font-weight: bold; color: #0066CC; }
        .license-box { background: #f8f9fa; border: 2px solid #0066CC; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center; }
        .license-key { font-family: monospace; font-size: 14px; background: white; padding: 15px; border-radius: 5px; word-break: break-all; margin: 10px 0; border: 1px solid #ddd; }
        .instructions { background: #e7f3ff; border-left: 4px solid #0066CC; padding: 15px; margin: 20px 0; }
        .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666; }
        .btn { display: inline-block; background: #0066CC; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 10px 0; }
        .warning { color: #d63384; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">V_TRACK</div>
            <h2>Your License Key is Ready!</h2>
        </div>
        
        <p>Dear Valued Customer,</p>
        
        <p>Thank you for purchasing <strong>V_track {{ product_type|title }} License</strong>! Your license has been generated and is ready for activation.</p>
        
        <div class="license-box">
            <h3>🔑 Your License Key</h3>
            <div class="license-key">{{ license_key }}</div>
            <p class="warning">⚠️ Please save this license key securely</p>
        </div>
        
        <div class="instructions">
            <h3>📋 Activation Instructions</h3>
            <ol>
                <li><strong>Download V_track:</strong> <a href="https://vtrack.app/download" class="btn">Download Now</a></li>
                <li><strong>Install the application</strong> on your computer</li>
                <li><strong>Launch V_track</strong> for the first time</li>
                <li><strong>Enter your license key</strong> when prompted</li>
                <li><strong>Complete activation</strong> and start using V_track!</li>
            </ol>
        </div>
        
        <div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 15px; margin: 20px 0;">
            <h4>📊 Your License Details:</h4>
            <ul style="list-style: none; padding-left: 0;">
                <li><strong>Product:</strong> V_track {{ product_type|title }}</li>
                <li><strong>Features:</strong> {{ features|join(', ')|title }}</li>
                <li><strong>Valid until:</strong> {{ expiry_date[:10] }}</li>
                <li><strong>Transaction ID:</strong> {{ transaction_id }}</li>
                <li><strong>Amount:</strong> {{ "{:,}".format(amount) }} VND</li>
                <li><strong>Purchase Date:</strong> {{ purchase_date }}</li>
            </ul>
        </div>
        
        <div style="background: #d1ecf1; border: 1px solid #bee5eb; border-radius: 5px; padding: 15px; margin: 20px 0;">
            <h4>💡 Need Help?</h4>
            <p>If you encounter any issues during installation or activation:</p>
            <ul>
                <li>📧 Email us: <a href="mailto:support@vtrack.app">support@vtrack.app</a></li>
                <li>📖 Check documentation: <a href="https://docs.vtrack.app">docs.vtrack.app</a></li>
                <li>🎥 Watch setup videos: <a href="https://vtrack.app/tutorials">vtrack.app/tutorials</a></li>
            </ul>
        </div>
        
        <div class="footer">
            <p><strong>V_track License System</strong><br>
            Automated license delivery - Secure & Reliable</p>
            <p style="font-size: 12px; color: #999;">
                This email was sent automatically. Please do not reply to this address.<br>
                If you did not purchase this license, please contact our support team immediately.
            </p>
        </div>
    </div>
</body>
</html>"""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _send_email_with_retry(self, message):
        """Send email với retry logic"""
        try:
            # Create secure connection
            context = ssl.create_default_context()

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_username, self.smtp_password)

                # Send email
                text = message.as_string()
                server.sendmail(self.sender_email, message["To"], text)

            return {"success": True}

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {str(e)}")
            raise Exception(f"Email authentication failed: {str(e)}")
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"Recipient refused: {str(e)}")
            raise Exception(f"Invalid recipient email: {str(e)}")
        except Exception as e:
            logger.error(f"Email sending error: {str(e)}")
            raise

    def send_license_email(self, recipient, subject, content):
        """
        Send license delivery email

        Args:
            recipient (str): Recipient email address
            subject (str): Email subject
            content (dict): Email content data

        Returns:
            dict: Sending result
        """
        try:
            if not self.smtp_username or not self.smtp_password:
                return {"success": False, "error": "SMTP credentials not configured"}

            # Render email template
            template = self.jinja_env.get_template("license_delivery.html")
            html_content = template.render(**content)

            # Create email message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.sender_name} <{self.sender_email}>"
            message["To"] = recipient

            # Add HTML content
            html_part = MIMEText(html_content, "html", "utf-8")
            message.attach(html_part)

            # Add plain text fallback
            text_content = self._create_text_fallback(content)
            text_part = MIMEText(text_content, "plain", "utf-8")
            message.attach(text_part)

            # Send email with retry
            result = self._send_email_with_retry(message)

            logger.info(f"License email sent successfully to {recipient}")
            return result

        except Exception as e:
            logger.error(f"Failed to send license email to {recipient}: {str(e)}")
            return {"success": False, "error": str(e)}

    def _create_text_fallback(self, content):
        """Create plain text version of email"""
        text_content = f"""
V_TRACK LICENSE DELIVERY

Dear Customer,

Thank you for purchasing V_track {content.get('product_type', 'Desktop')} License!

YOUR LICENSE KEY:
{content.get('license_key', 'N/A')}

ACTIVATION INSTRUCTIONS:
1. Download V_track from: https://vtrack.app/download
2. Install the application on your computer
3. Launch V_track for the first time
4. Enter your license key when prompted
5. Complete activation and start using V_track!

LICENSE DETAILS:
- Product: V_track {content.get('product_type', 'Desktop')}
- Features: {', '.join(content.get('features', []))}
- Valid until: {content.get('expiry_date', 'N/A')[:10]}
- Transaction ID: {content.get('transaction_id', 'N/A')}
- Amount: {content.get('amount', 0):,} VND
- Purchase Date: {content.get('purchase_date', 'N/A')}

NEED HELP?
Email: support@vtrack.app
Documentation: https://docs.vtrack.app

---
V_track License System
Automated license delivery
        """
        return text_content.strip()

    def send_test_email(self, recipient, test_content=None):
        """Send test email để kiểm tra SMTP configuration"""
        try:
            if test_content is None:
                test_content = {
                    "customer_email": recipient,
                    "license_key": "TEST-LICENSE-KEY-123456789",
                    "product_type": "desktop",
                    "features": ["full_access", "priority_support"],
                    "expiry_date": "2025-12-31",
                    "transaction_id": "TEST_TRANSACTION",
                    "amount": 500000,
                    "purchase_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }

            subject = "V_track License Test Email"

            result = self.send_license_email(
                recipient=recipient, subject=subject, content=test_content
            )

            return result

        except Exception as e:
            logger.error(f"Test email failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def send_license_with_attachment(self, recipient, subject, content, license_package):
        """
        Send license email với license file attachment

        Args:
            recipient (str): Recipient email
            subject (str): Email subject
            content (dict): Email content
            license_package (dict): Complete license package

        Returns:
            dict: Sending result
        """
        try:
            # Render email template
            template = self.jinja_env.get_template("license_delivery.html")
            html_content = template.render(**content)

            # Create email message
            message = MIMEMultipart()
            message["Subject"] = subject
            message["From"] = f"{self.sender_name} <{self.sender_email}>"
            message["To"] = recipient

            # Add HTML content
            html_part = MIMEText(html_content, "html", "utf-8")
            message.attach(html_part)

            # Add license package as JSON attachment
            license_json = json.dumps(license_package, indent=2)
            license_attachment = MIMEApplication(license_json.encode("utf-8"), _subtype="json")
            license_attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=f"vtrack_license_{content.get('customer_email', 'user')}.json",
            )
            message.attach(license_attachment)

            # Send email
            result = self._send_email_with_retry(message)

            logger.info(f"License email with attachment sent to {recipient}")
            return result

        except Exception as e:
            logger.error(f"Failed to send email with attachment: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_email_config_status(self):
        """Get current email configuration status"""
        return {
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "smtp_username": self.smtp_username,
            "smtp_configured": bool(self.smtp_username and self.smtp_password),
            "sender_name": self.sender_name,
            "templates_available": ["license_delivery.html"],
        }
