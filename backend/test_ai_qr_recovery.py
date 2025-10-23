#!/usr/bin/env python3
"""
Test Script: AI QR Code Recovery
Tests Claude API's ability to decode blurred/damaged QR codes
Logs results to ai_recovery_logs table
"""

import os
import sys
import base64
import anthropic
from pathlib import Path
from datetime import datetime
import sqlite3

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.db_utils.safe_connection import safe_db_connection
from modules.scheduler.db_sync import db_rwlock
from modules.config.services.ai_service import AIService

# Configuration
TEST_IMAGES_DIR = "/Users/annhu/vtrack_app/V_Track/var/logs/qr_recovery"
USER_EMAIL = "guest@vpack.local"

# Pricing (Claude 3.5 Sonnet - as of 2024)
PRICE_PER_1M_INPUT_TOKENS = 3.0  # $3 per 1M input tokens
PRICE_PER_1M_OUTPUT_TOKENS = 15.0  # $15 per 1M output tokens


def encode_image_to_base64(image_path: str) -> str:
    """Encode image to base64 for Claude API"""
    with open(image_path, 'rb') as f:
        image_data = f.read()
    return base64.standard_b64encode(image_data).decode('utf-8')


def detect_image_media_type(image_path: str) -> str:
    """Detect image MIME type from extension"""
    ext = Path(image_path).suffix.lower()
    media_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
        '.gif': 'image/gif'
    }
    return media_types.get(ext, 'image/jpeg')


def recover_qr_with_claude(image_path: str, api_key: str) -> dict:
    """
    Call Claude API to decode QR code from blurred image

    Args:
        image_path: Path to QR code image
        api_key: Claude API key

    Returns:
        dict: {
            'success': bool,
            'decoded_text': str,
            'input_tokens': int,
            'output_tokens': int,
            'cost_usd': float,
            'error_message': str
        }
    """
    try:
        # Encode image
        image_base64 = encode_image_to_base64(image_path)
        media_type = detect_image_media_type(image_path)

        # Initialize Claude client
        client = anthropic.Anthropic(api_key=api_key)

        # Create message with vision prompt
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_base64,
                        },
                    },
                    {
                        "type": "text",
                        "text": """Analyze this QR code image and extract the encoded text.

Instructions:
1. Carefully examine the QR code pattern
2. If the QR code is blurred or damaged, try your best to decode it
3. Return ONLY the decoded text, nothing else
4. If you cannot decode it, return "DECODE_FAILED"

Format: Just return the tracking code (e.g., "TRACK001" or "MVD12345")"""
                    }
                ],
            }]
        )

        # Extract response
        decoded_text = message.content[0].text.strip()

        # Calculate cost
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens

        cost_usd = (
            (input_tokens / 1_000_000 * PRICE_PER_1M_INPUT_TOKENS) +
            (output_tokens / 1_000_000 * PRICE_PER_1M_OUTPUT_TOKENS)
        )

        # Determine success
        success = decoded_text != "DECODE_FAILED" and len(decoded_text) > 0

        return {
            'success': success,
            'decoded_text': decoded_text,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cost_usd': cost_usd,
            'error_message': None if success else 'Decode failed'
        }

    except anthropic.AuthenticationError:
        return {
            'success': False,
            'decoded_text': None,
            'input_tokens': 0,
            'output_tokens': 0,
            'cost_usd': 0.0,
            'error_message': 'Invalid API key'
        }
    except Exception as e:
        return {
            'success': False,
            'decoded_text': None,
            'input_tokens': 0,
            'output_tokens': 0,
            'cost_usd': 0.0,
            'error_message': str(e)
        }


def log_recovery_result(user_email: str, frame_path: str, result: dict, event_id: str = None):
    """Log recovery result to ai_recovery_logs table"""
    try:
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ai_recovery_logs
                    (user_email, event_id, frame_path, success, decoded_text,
                     cost_usd, input_tokens, output_tokens, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_email,
                    event_id,
                    frame_path,
                    1 if result['success'] else 0,
                    result['decoded_text'],
                    result['cost_usd'],
                    result['input_tokens'],
                    result['output_tokens'],
                    result['error_message']
                ))
                conn.commit()
                print(f"  ✅ Logged to database (ID: {cursor.lastrowid})")
    except Exception as e:
        print(f"  ❌ Failed to log to database: {e}")


def main():
    """Main test function"""
    print("=" * 70)
    print("🧪 AI QR Recovery Test Script")
    print("=" * 70)
    print()

    # Get API key from database
    print("📋 Loading AI configuration...")
    config = AIService.get_ai_config(USER_EMAIL)

    if not config.get('ai_enabled'):
        print("❌ AI is not enabled. Please enable it in the UI first.")
        return

    if not config.get('has_custom_key'):
        print("❌ No API key configured. Please add API key in the UI first.")
        return

    # Decrypt API key
    with db_rwlock.gen_rlock():
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT encrypted_api_key FROM ai_config WHERE user_email = ?", (USER_EMAIL,))
            result = cursor.fetchone()
            if not result or not result[0]:
                print("❌ No encrypted API key found in database")
                return

            api_key = AIService.decrypt_api_key(result[0])
            if not api_key:
                print("❌ Failed to decrypt API key")
                return

    print(f"✅ API key loaded: {api_key[:10]}...")
    print(f"✅ Provider: {config['api_provider']}")
    print()

    # Find test images
    image_dir = Path(TEST_IMAGES_DIR)
    if not image_dir.exists():
        print(f"❌ Test directory not found: {TEST_IMAGES_DIR}")
        print(f"📝 Please create directory and add 3 QR code images:")
        print(f"   mkdir -p {TEST_IMAGES_DIR}")
        print(f"   # Then add: qr_test_1.jpg, qr_test_2.jpg, qr_test_3.jpg")
        return

    # Get image files
    image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    test_images = [
        f for f in image_dir.iterdir()
        if f.suffix.lower() in image_extensions
    ]

    if not test_images:
        print(f"❌ No images found in {TEST_IMAGES_DIR}")
        print(f"📝 Please add QR code images with extensions: {', '.join(image_extensions)}")
        return

    print(f"📁 Found {len(test_images)} test images")
    print()

    # Process each image
    total_cost = 0.0
    successful = 0
    failed = 0

    for i, image_path in enumerate(test_images, 1):
        print(f"🔍 Processing image {i}/{len(test_images)}: {image_path.name}")
        print(f"   File size: {image_path.stat().st_size / 1024:.1f} KB")

        # Call Claude API
        print("   📡 Calling Claude API...")
        result = recover_qr_with_claude(str(image_path), api_key)

        # Display result
        if result['success']:
            print(f"   ✅ SUCCESS: {result['decoded_text']}")
            successful += 1
        else:
            print(f"   ❌ FAILED: {result['error_message']}")
            failed += 1

        print(f"   💰 Cost: ${result['cost_usd']:.6f}")
        print(f"   📊 Tokens: {result['input_tokens']} in, {result['output_tokens']} out")

        # Log to database
        event_id = f"TEST_EVENT_{i:03d}"
        log_recovery_result(USER_EMAIL, str(image_path), result, event_id)

        total_cost += result['cost_usd']
        print()

    # Summary
    print("=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    print(f"Total images processed: {len(test_images)}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success rate: {(successful / len(test_images) * 100):.1f}%")
    print(f"💰 Total cost: ${total_cost:.6f}")
    print(f"💵 Average cost per image: ${(total_cost / len(test_images)):.6f}")
    print()

    # Show database stats
    print("📊 Database Stats:")
    stats = AIService.get_usage_stats(USER_EMAIL)
    print(f"   Total recoveries: {stats['total_recoveries']}")
    print(f"   Successful: {stats['successful']}")
    print(f"   Failed: {stats['failed']}")
    print(f"   Total cost: ${stats['total_cost_usd']:.6f}")
    print()

    print("✅ Test completed! Check results in UI: Account → AI Usage")


if __name__ == "__main__":
    main()
