"""
Simple Avatar Downloader
Download user avatars to frontend public folder
"""
import os
from pathlib import Path
import requests
import logging
from modules.config.logging_config import get_logger

logger = get_logger(__name__)

class SimpleAvatarDownloader:
    def __init__(self):
        # Path to frontend public avatars folder
        self.frontend_avatars_dir = str(Path(__file__).parent.parent.parent / 'frontend' / 'public' / 'img' / 'avatars')
        # Ensure directory exists
        Path(self.frontend_avatars_dir).mkdir(parents=True, exist_ok=True)

    def get_user_avatar_filename(self, user_email):
        """Generate filename for user avatar"""
        # Clean email for filename: user_email@gmail.com -> user_email_gmail_com.jpg
        clean_email = user_email.replace('@', '_').replace('.', '_')
        return f"user_{clean_email}.jpg"

    def get_avatar_path(self, user_email):
        """Get local path for user avatar"""
        filename = self.get_user_avatar_filename(user_email)
        return f"/img/avatars/{filename}"

    def download_avatar(self, user_email, avatar_url, max_retries=3):
        """Download avatar to frontend public folder with retry logic"""
        filename = self.get_user_avatar_filename(user_email)
        local_path = str(Path(self.frontend_avatars_dir) / filename)

        # Check if file exists and is valid
        if self._is_avatar_valid(local_path):
            logger.debug(f"✅ Valid avatar already exists: {filename}")
            return self.get_avatar_path(user_email)

        # Try to download with retries
        for attempt in range(max_retries):
            try:
                logger.info(f"📥 Downloading avatar for {user_email} (attempt {attempt + 1}/{max_retries})")
                response = requests.get(avatar_url, timeout=15, stream=True)
                response.raise_for_status()

                # Validate content type
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    raise ValueError(f"Invalid content type: {content_type}")

                # Save to public folder with temp file for atomic write
                temp_path = local_path + '.tmp'
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # Validate downloaded file
                if self._is_avatar_valid(temp_path):
                    # Move temp file to final location
                    if Path(local_path).exists():
                        os.remove(local_path)
                    os.rename(temp_path, local_path)

                    logger.info(f"💾 Avatar saved: {filename} ({Path(local_path).stat().st_size} bytes)")
                    return self.get_avatar_path(user_email)
                else:
                    os.remove(temp_path)
                    raise ValueError("Downloaded file is invalid")

            except Exception as e:
                logger.warning(f"⚠️ Avatar download attempt {attempt + 1} failed for {user_email}: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"❌ All avatar download attempts failed for {user_email}")
                    # Return default avatar path instead of original URL
                    return "/img/avatars/avatar4.png"
                continue

        return "/img/avatars/avatar4.png"

    def _is_avatar_valid(self, file_path):
        """Check if avatar file exists and is valid"""
        try:
            if not Path(file_path).exists():
                return False

            # Check file size (should be > 100 bytes)
            file_size = Path(file_path).stat().st_size
            if file_size < 100:
                logger.warning(f"⚠️ Avatar file too small: {file_path} ({file_size} bytes)")
                return False

            # Check if file is readable
            with open(file_path, 'rb') as f:
                # Read first few bytes to check if it's an image
                header = f.read(16)
                if not header:
                    return False

                # Check for common image file signatures
                image_signatures = [
                    b'\xFF\xD8\xFF',  # JPEG
                    b'\x89\x50\x4E\x47',  # PNG
                    b'GIF87a',  # GIF87a
                    b'GIF89a',  # GIF89a
                    b'\x52\x49\x46\x46',  # WEBP (RIFF header)
                ]

                for sig in image_signatures:
                    if header.startswith(sig):
                        return True

                logger.warning(f"⚠️ Avatar file has unknown format: {file_path}")
                return False

        except Exception as e:
            logger.error(f"❌ Error validating avatar file {file_path}: {e}")
            return False

    def validate_user_avatar(self, user_email):
        """Public method to validate user's avatar exists and is valid"""
        filename = self.get_user_avatar_filename(user_email)
        local_path = str(Path(self.frontend_avatars_dir) / filename)
        return self._is_avatar_valid(local_path)

# Global instance
avatar_downloader = SimpleAvatarDownloader()
