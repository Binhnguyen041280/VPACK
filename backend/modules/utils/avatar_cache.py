"""
Avatar Cache Service
Cache user avatars locally for offline usage
"""
import os
from pathlib import Path
import hashlib
import requests
from urllib.parse import urlparse
from datetime import datetime, timedelta
import logging
from modules.config.logging_config import get_logger

logger = get_logger(__name__)

class AvatarCache:
    def __init__(self, cache_dir='static/avatars', base_url='http://localhost:8080'):
        self.cache_dir = str(Path(__file__).parent.parent / cache_dir)
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        self.cache_duration = timedelta(days=7)  # Cache for 7 days
        self.base_url = base_url
        
    def _get_cache_filename(self, url, user_email):
        """Generate cache filename based on URL and user email"""
        # Use hash of URL + email to create unique filename
        content = f"{url}_{user_email}".encode('utf-8')
        hash_name = hashlib.md5(content).hexdigest()
        
        # Try to preserve original extension
        parsed_url = urlparse(url)
        path = parsed_url.path
        if '.' in path:
            ext = Path(path).suffix.split('?')[0]  # Remove query params
        else:
            ext = '.jpg'  # Default to jpg
            
        return f"{hash_name}{ext}"
    
    def _is_cache_valid(self, cache_path):
        """Check if cached file exists and is not expired"""
        if not Path(cache_path).exists():
            return False
            
        # Check file age
        file_time = datetime.fromtimestamp(Path(cache_path).stat().st_mtime)
        return datetime.now() - file_time < self.cache_duration
    
    def get_cached_avatar_url(self, original_url, user_email):
        """Get cached avatar URL or download and cache if needed"""
        try:
            cache_filename = self._get_cache_filename(original_url, user_email)
            cache_path = str(Path(self.cache_dir) / cache_filename)
            
            # Check if cache is valid
            if self._is_cache_valid(cache_path):
                logger.debug(f"✅ Using cached avatar: {cache_filename}")
                return f"{self.base_url}/static/avatars/{cache_filename}"
            
            # Download and cache the avatar
            logger.info(f"📥 Downloading avatar from: {original_url}")
            response = requests.get(original_url, timeout=10, stream=True)
            response.raise_for_status()
            
            # Save to cache
            with open(cache_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"💾 Avatar cached as: {cache_filename}")
            return f"{self.base_url}/static/avatars/{cache_filename}"
            
        except Exception as e:
            logger.error(f"❌ Failed to cache avatar: {e}")
            # Return original URL as fallback
            return original_url
    
    def cleanup_expired_cache(self):
        """Remove expired cached avatars"""
        try:
            cleaned_count = 0
            for filename in os.listdir(self.cache_dir):
                cache_path = str(Path(self.cache_dir) / filename)
                if not self._is_cache_valid(cache_path):
                    os.remove(cache_path)
                    cleaned_count += 1
                    
            if cleaned_count > 0:
                logger.info(f"🧹 Cleaned {cleaned_count} expired cached avatars")
                
        except Exception as e:
            logger.error(f"❌ Failed to cleanup avatar cache: {e}")

# Global instance
avatar_cache = AvatarCache()