"""
AI Service Layer for V.PACK
Handles AI configuration, API key management, and QR recovery
Reuses encryption pattern from cloud_auth.py
"""

import base64
import json
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime
from cryptography.fernet import Fernet
import os
from pathlib import Path

# AI SDK imports
try:
    import anthropic
except ImportError:
    logging.warning("Anthropic SDK not installed. Run: pip install anthropic")
    anthropic = None

try:
    import openai
except ImportError:
    logging.warning("OpenAI SDK not installed. Run: pip install openai")
    openai = None

from modules.db_utils.safe_connection import safe_db_connection
from modules.scheduler.db_sync import db_rwlock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== ENCRYPTION KEY MANAGEMENT ====================
# Reuse encryption key from cloud_auth.py

def _load_encryption_key():
    """Load OAuth encryption key for consistent encryption across the app"""
    try:
        keys_dir = str(Path(__file__).parent / '..', '..', '..', 'keys')
        key_path = str(Path(keys_dir) / 'oauth_encryption.key')

        if Path(key_path).exists():
            with open(key_path, 'rb') as f:
                key = f.read()
            logger.info("✅ Using existing OAuth encryption key for AI")
            return key
        else:
            # Generate new key if not exists
            os.makedirs(keys_dir, exist_ok=True)
            key = Fernet.generate_key()
            with open(key_path, 'wb') as f:
                f.write(key)
            os.chmod(key_path, 0o600)
            logger.info("🔑 Generated new encryption key for AI")
            return key
    except Exception as e:
        logger.error(f"❌ Encryption key load error: {e}")
        # Fallback
        env_key = os.getenv('ENCRYPTION_KEY')
        if env_key:
            return env_key.encode() if isinstance(env_key, str) else env_key
        return Fernet.generate_key()

ENCRYPTION_KEY = _load_encryption_key()


class AIService:
    """Service layer for AI configuration and QR recovery"""

    @staticmethod
    def encrypt_api_key(api_key: str) -> Optional[str]:
        """
        Encrypt API key using Fernet (AES-256)
        Reuses encryption pattern from cloud_auth.py (lines 170-179)
        """
        try:
            fernet = Fernet(ENCRYPTION_KEY)
            encrypted_data = fernet.encrypt(api_key.encode())
            return base64.b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"❌ API key encryption error: {e}")
            return None

    @staticmethod
    def decrypt_api_key(encrypted_key: str) -> Optional[str]:
        """
        Decrypt API key
        Reuses decryption pattern from cloud_auth.py (lines 181-190)
        """
        try:
            fernet = Fernet(ENCRYPTION_KEY)
            encrypted_bytes = base64.b64decode(encrypted_key.encode())
            decrypted_data = fernet.decrypt(encrypted_bytes)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"❌ API key decryption error: {e}")
            return None

    @staticmethod
    def get_ai_config(user_email: str) -> Dict:
        """
        Get AI configuration for user

        Args:
            user_email: User email address

        Returns:
            dict: {
                'ai_enabled': bool,
                'api_provider': str,
                'has_custom_key': bool,
                'masked_key': str  # First 10 chars only
            }
        """
        try:
            with db_rwlock.gen_rlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT ai_enabled, api_provider, encrypted_api_key
                        FROM ai_config WHERE user_email = ?
                    """, (user_email,))
                    result = cursor.fetchone()

                    if result:
                        ai_enabled, api_provider, encrypted_key = result

                        # Decrypt and mask key
                        masked_key = ""
                        has_custom_key = bool(encrypted_key)
                        if encrypted_key:
                            decrypted = AIService.decrypt_api_key(encrypted_key)
                            if decrypted:
                                masked_key = decrypted[:10] + "..." if len(decrypted) > 10 else decrypted

                        return {
                            'ai_enabled': bool(ai_enabled),
                            'api_provider': api_provider or 'claude',
                            'has_custom_key': has_custom_key,
                            'masked_key': masked_key
                        }
                    else:
                        # Return default config
                        return {
                            'ai_enabled': False,
                            'api_provider': 'claude',
                            'has_custom_key': False,
                            'masked_key': ''
                        }
        except Exception as e:
            logger.error(f"❌ Get AI config error: {e}")
            return {
                'ai_enabled': False,
                'api_provider': 'claude',
                'has_custom_key': False,
                'masked_key': '',
                'error': str(e)
            }

    @staticmethod
    def update_ai_config(user_email: str, ai_enabled: bool, api_provider: str, api_key: str = '') -> Tuple[bool, Dict]:
        """
        Update AI configuration

        Args:
            user_email: User email
            ai_enabled: Enable/disable AI
            api_provider: 'claude' or 'openai'
            api_key: API key (will be encrypted)

        Returns:
            tuple: (success: bool, result: dict)
        """
        try:
            # Encrypt API key if provided
            encrypted_key = None
            if api_key:
                encrypted_key = AIService.encrypt_api_key(api_key)
                if not encrypted_key:
                    return False, {'error': 'Failed to encrypt API key'}

            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()

                    # Check if config exists
                    cursor.execute("SELECT user_email FROM ai_config WHERE user_email = ?", (user_email,))
                    exists = cursor.fetchone()

                    if exists:
                        # Update existing
                        if encrypted_key:
                            cursor.execute("""
                                UPDATE ai_config
                                SET ai_enabled = ?, api_provider = ?, encrypted_api_key = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE user_email = ?
                            """, (ai_enabled, api_provider, encrypted_key, user_email))
                        else:
                            cursor.execute("""
                                UPDATE ai_config
                                SET ai_enabled = ?, api_provider = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE user_email = ?
                            """, (ai_enabled, api_provider, user_email))
                    else:
                        # Insert new
                        cursor.execute("""
                            INSERT INTO ai_config (user_email, ai_enabled, api_provider, encrypted_api_key)
                            VALUES (?, ?, ?, ?)
                        """, (user_email, ai_enabled, api_provider, encrypted_key))

                    conn.commit()

            logger.info(f"✅ Updated AI config for {user_email}")
            return True, {
                'message': 'Configuration updated successfully',
                'ai_enabled': ai_enabled,
                'api_provider': api_provider
            }

        except Exception as e:
            logger.error(f"❌ Update AI config error: {e}")
            return False, {'error': str(e)}

    @staticmethod
    def test_claude_key(api_key: str) -> Tuple[bool, str]:
        """
        Test Claude API key with actual API call

        Args:
            api_key: Claude API key

        Returns:
            tuple: (success: bool, message: str)
        """
        if not anthropic:
            return False, "Anthropic SDK not installed"

        try:
            client = anthropic.Anthropic(api_key=api_key)

            # Minimal test call
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )

            logger.info(f"✅ Claude API key validated successfully")
            return True, "Claude API key is valid"

        except anthropic.AuthenticationError:
            logger.warning("⚠️ Invalid Claude API key")
            return False, "Invalid Claude API key"
        except anthropic.RateLimitError:
            logger.warning("⚠️ Claude rate limit exceeded")
            return False, "Rate limit exceeded - but key is valid"
        except Exception as e:
            logger.error(f"❌ Claude API test error: {e}")
            return False, f"API test failed: {str(e)}"

    @staticmethod
    def test_openai_key(api_key: str) -> Tuple[bool, str]:
        """
        Test OpenAI API key with actual API call

        Args:
            api_key: OpenAI API key

        Returns:
            tuple: (success: bool, message: str)
        """
        if not openai:
            return False, "OpenAI SDK not installed"

        try:
            client = openai.OpenAI(api_key=api_key)

            # Minimal test call
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Cheapest model for testing
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10
            )

            logger.info(f"✅ OpenAI API key validated successfully")
            return True, "OpenAI API key is valid"

        except openai.AuthenticationError:
            logger.warning("⚠️ Invalid OpenAI API key")
            return False, "Invalid OpenAI API key"
        except openai.RateLimitError:
            logger.warning("⚠️ OpenAI rate limit exceeded")
            return False, "Rate limit exceeded - but key is valid"
        except Exception as e:
            logger.error(f"❌ OpenAI API test error: {e}")
            return False, f"API test failed: {str(e)}"

    @staticmethod
    def get_usage_stats(user_email: str) -> Dict:
        """
        Get AI usage statistics for user

        Args:
            user_email: User email

        Returns:
            dict: Usage statistics
        """
        try:
            with db_rwlock.gen_rlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT
                            COUNT(*) as total,
                            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                            SUM(cost_usd) as total_cost,
                            SUM(input_tokens) as total_input_tokens,
                            SUM(output_tokens) as total_output_tokens
                        FROM ai_recovery_logs WHERE user_email = ?
                    """, (user_email,))
                    result = cursor.fetchone()

                    total = result[0] or 0
                    successful = result[1] or 0
                    total_cost = result[2] or 0.0
                    total_input_tokens = result[3] or 0
                    total_output_tokens = result[4] or 0

                    return {
                        'total_recoveries': total,
                        'successful': successful,
                        'failed': total - successful,
                        'success_rate': (successful / total * 100) if total > 0 else 0,
                        'total_cost_usd': round(total_cost, 6),
                        'avg_cost_per_recovery': round((total_cost / total), 6) if total > 0 else 0,
                        'total_input_tokens': total_input_tokens,
                        'total_output_tokens': total_output_tokens
                    }
        except Exception as e:
            logger.error(f"❌ Get usage stats error: {e}")
            return {
                'total_recoveries': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 0,
                'total_cost_usd': 0,
                'avg_cost_per_recovery': 0,
                'error': str(e)
            }

    @staticmethod
    def get_recovery_logs(user_email: str, limit: int = 50) -> list:
        """
        Get recent recovery logs

        Args:
            user_email: User email
            limit: Max number of logs

        Returns:
            list: Recovery logs
        """
        try:
            with db_rwlock.gen_rlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id, event_id, frame_path, success, decoded_text, cost_usd,
                               input_tokens, output_tokens, error_message, created_at
                        FROM ai_recovery_logs
                        WHERE user_email = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (user_email, limit))

                    logs = []
                    for row in cursor.fetchall():
                        logs.append({
                            'id': row[0],
                            'event_id': row[1],
                            'frame_path': row[2],
                            'success': bool(row[3]),
                            'decoded_text': row[4],
                            'cost_usd': row[5],
                            'input_tokens': row[6],
                            'output_tokens': row[7],
                            'error_message': row[8],
                            'created_at': row[9]
                        })

                    return logs
        except Exception as e:
            logger.error(f"❌ Get recovery logs error: {e}")
            return []
