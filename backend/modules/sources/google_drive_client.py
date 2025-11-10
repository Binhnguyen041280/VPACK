# Copy the code from the artifact above
#!/usr/bin/env python3
"""
Google Drive Client for VTrack Cloud Integration
Handles authentication, upload, download, and folder management
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleDriveClient:
    """Google Drive API client for VTrack video backup with PyDrive2 compatibility"""
    
    # Google Drive API scopes
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self, source_id=None, credentials_path='google_drive_credentials_web.json', token_path='token.json'):
        """
        Initialize Google Drive client
        
        Args:
            source_id (int): Source ID for loading encrypted credentials
            credentials_path (str): Path to OAuth2 credentials file (fallback)
            token_path (str): Path to store access tokens (fallback)
        """
        self.source_id = source_id
        self.credentials_path = str(Path(__file__).parent / credentials_path)
        self.token_path = str(Path(__file__).parent / token_path)
        self.service = None
        self.creds = None
        self.oauth2client_creds = None  # 🆕 NEW: PyDrive2 compatible credentials
        
        logger.info(f"GoogleDriveClient initialized with source_id: {source_id}")
        logger.info(f"Credentials path: {self.credentials_path}")
        logger.info(f"Token path: {self.token_path}")
    
    def load_credentials_from_storage(self):
        """
        🆕 NEW: Load credentials from encrypted storage (for VTrack integration)
        
        Returns:
            dict: Credential data or None if not found
        """
        if not self.source_id:
            return None
            
        try:
            # Import here to avoid circular imports
            from .cloud_auth import CloudAuthManager
            
            # Load encrypted credentials using CloudAuthManager
            auth_manager = CloudAuthManager()
            
            # Get source config to find user email
            from ...database.sync_database import sync_db
            source = sync_db.get_source(self.source_id)
            if not source:
                logger.error(f"❌ Source {self.source_id} not found")
                return None
                
            config = json.loads(source.get('config', '{}'))
            user_email = config.get('user_email')
            
            if not user_email:
                logger.error(f"❌ No user_email found in source {self.source_id} config")
                return None
            
            # Load credentials from encrypted storage
            tokens_dir = str(Path(__file__).parent / 'tokens')
            token_filename = f"google_drive_{hashlib.md5(user_email.encode()).hexdigest()[:16]}.json"
            token_path = str(Path(tokens_dir) / token_filename)
            
            if not Path(token_path).exists():
                logger.error(f"❌ Token file not found: {token_path}")
                return None
            
            # Load and decrypt credentials
            with open(token_path, 'r') as f:
                storage_data = json.load(f)
            
            encrypted_data = storage_data.get('encrypted_data')
            if not encrypted_data:
                logger.error("❌ No encrypted_data found in token file")
                return None
            
            # Decrypt credentials
            decrypted_data = auth_manager.decrypt_credentials(encrypted_data)
            if not decrypted_data:
                logger.error("❌ Failed to decrypt credentials")
                return None
            
            logger.info("✅ Credentials loaded from encrypted storage")
            return decrypted_data
            
        except Exception as e:
            logger.error(f"❌ Failed to load credentials from storage: {e}")
            return None
    
    def create_oauth2client_credentials(self, credential_data):
        """
        🆕 NEW: Convert google-auth credentials to oauth2client format for PyDrive2
        
        Args:
            credential_data (dict): Decrypted credential data
            
        Returns:
            oauth2client.client.OAuth2Credentials: PyDrive2 compatible credentials
        """
        try:
            # Import oauth2client
            from oauth2client import client
            from oauth2client.client import GOOGLE_TOKEN_URI
            import httplib2
            
            # Extract required data
            access_token = credential_data.get('token')
            refresh_token = credential_data.get('refresh_token')
            client_id = credential_data.get('client_id')
            client_secret = credential_data.get('client_secret')
            token_uri = credential_data.get('token_uri', GOOGLE_TOKEN_URI)
            
            # Handle token expiry
            token_expiry = None
            if credential_data.get('expires_at'):
                from datetime import datetime
                token_expiry = datetime.fromisoformat(credential_data['expires_at'].replace('Z', '+00:00'))
            
            logger.info("🔄 Converting to oauth2client credentials...")
            logger.info(f"   Client ID: {client_id[:20]}..." if client_id else "   No client_id")
            logger.info(f"   Has refresh token: {bool(refresh_token)}")
            logger.info(f"   Has access token: {bool(access_token)}")
            logger.info(f"   Token expiry: {token_expiry}")
            
            # Create oauth2client credentials object
            oauth2client_creds = client.OAuth2Credentials(
                access_token=access_token,
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                token_expiry=token_expiry,
                token_uri=token_uri,
                user_agent="VTrack-GoogleDrive-Client/1.0"
            )
            
            # Refresh token if expired
            if oauth2client_creds.access_token_expired and refresh_token:
                logger.info("🔄 Refreshing expired access token...")
                http = httplib2.Http()
                oauth2client_creds.refresh(http)
                logger.info("✅ Access token refreshed successfully")
            
            logger.info("✅ oauth2client credentials created successfully")
            return oauth2client_creds
            
        except Exception as e:
            logger.error(f"❌ Failed to create oauth2client credentials: {e}")
            return None
    
    def authenticate(self):
        """
        Authenticate with Google Drive API using OAuth2
        Priority: 1) Encrypted storage (VTrack) 2) Local token file (fallback)
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            # Method 1: Try loading from encrypted storage (VTrack integration)
            if self.source_id:
                logger.info("🔐 Attempting to load credentials from encrypted storage...")
                credential_data = self.load_credentials_from_storage()
                
                if credential_data:
                    # Create oauth2client credentials for PyDrive2
                    self.oauth2client_creds = self.create_oauth2client_credentials(credential_data)
                    
                    if self.oauth2client_creds:
                        # Also create google-auth credentials for Drive API v3
                        from google.oauth2.credentials import Credentials
                        self.creds = Credentials(
                            token=credential_data.get('token'),
                            refresh_token=credential_data.get('refresh_token'),
                            token_uri=credential_data.get('token_uri'),
                            client_id=credential_data.get('client_id'),
                            client_secret=credential_data.get('client_secret'),
                            scopes=credential_data.get('scopes', self.SCOPES)
                        )
                        
                        # Build Drive service
                        self.service = build('drive', 'v3', credentials=self.creds)
                        logger.info("✅ Authentication successful using encrypted storage")
                        return True
            
            # Method 2: Fallback to local token file
            logger.info("🔄 Falling back to local token file authentication...")
            
            # Load existing token if available
            if Path(self.token_path).exists():
                from google.oauth2.credentials import Credentials
                self.creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
            
            # If no valid credentials, start OAuth flow
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    logger.info("🔄 Refreshing expired credentials...")
                    from google.auth.transport.requests import Request
                    self.creds.refresh(Request())
                else:
                    logger.info("🌐 Starting OAuth2 authentication flow...")
                    from google_auth_oauthlib.flow import InstalledAppFlow
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES)
                    self.creds = flow.run_local_server(port=0)
                
                # Save credentials for next time
                with open(self.token_path, 'w') as token:
                    token.write(self.creds.to_json())
                logger.info("✅ Credentials saved successfully")
            
            # Build Drive service
            self.service = build('drive', 'v3', credentials=self.creds)
            logger.info("✅ Fallback authentication successful")
            return True
            
        except FileNotFoundError:
            logger.error(f"❌ Credentials file not found: {self.credentials_path}")
            return False
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            return False
    
    def get_pydrive_auth(self):
        """
        🆕 NEW: Get PyDrive2 compatible authentication object
        
        Returns:
            GoogleAuth: PyDrive2 GoogleAuth object or None
        """
        try:
            if not self.oauth2client_creds:
                logger.error("❌ No oauth2client credentials available. Run authenticate() first.")
                return None
            
            # Import PyDrive2
            from pydrive2.auth import GoogleAuth
            
            # Create GoogleAuth object
            gauth = GoogleAuth()
            
            # Set credentials directly
            gauth.credentials = self.oauth2client_creds
            
            # Set authenticated flag
            gauth.authenticated = True
            
            logger.info("✅ PyDrive2 GoogleAuth object created successfully")
            return gauth
            
        except ImportError:
            logger.error("❌ PyDrive2 not installed. Run: pip install PyDrive2")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to create PyDrive2 auth: {e}")
            return None
    
    def test_pydrive_connection(self):
        """
        🆕 NEW: Test PyDrive2 connection
        
        Returns:
            dict: Test result
        """
        try:
            gauth = self.get_pydrive_auth()
            if not gauth:
                return {"success": False, "message": "Failed to get PyDrive2 auth"}
            
            # Import PyDrive2
            from pydrive2.drive import GoogleDrive
            
            # Create drive object
            drive = GoogleDrive(gauth)
            
            # Test connection with GetAbout()
            about = drive.GetAbout()
            
            user_email = about.get('user', {}).get('emailAddress', 'Unknown')
            quota = about.get('quotaBytesTotal', 'Unknown')
            used = about.get('quotaBytesUsed', 'Unknown')
            
            logger.info(f"✅ PyDrive2 connection successful: {user_email}")
            
            return {
                "success": True,
                "message": f"PyDrive2 connected successfully: {user_email}",
                "user_email": user_email,
                "quota_total": quota,
                "quota_used": used
            }
            
        except Exception as e:
            logger.error(f"❌ PyDrive2 connection test failed: {e}")
            return {"success": False, "message": f"PyDrive2 connection failed: {str(e)}"}
    
    def test_connection(self):
        """
        Test Google Drive API connection (both regular API and PyDrive2)
        
        Returns:
            dict: Connection test result
        """
        try:
            if not self.service:
                if not self.authenticate():
                    return {"success": False, "message": "Authentication failed"}
            
            # Test regular Drive API v3
            about = self.service.about().get(fields='user, storageQuota').execute()
            user_email = about.get('user', {}).get('emailAddress', 'Unknown')
            
            # Storage info
            quota = about.get('storageQuota', {})
            total_gb = int(quota.get('limit', 0)) / (1024**3) if quota.get('limit') else 'Unlimited'
            used_gb = int(quota.get('usage', 0)) / (1024**3)
            
            logger.info(f"✅ Connected to Google Drive API v3: {user_email}")
            
            # Test PyDrive2 connection if oauth2client credentials available
            pydrive_result = None
            if self.oauth2client_creds:
                pydrive_result = self.test_pydrive_connection()
            
            return {
                "success": True,
                "message": f"Connected to Google Drive: {user_email}",
                "user_email": user_email,
                "storage_total_gb": total_gb,
                "storage_used_gb": round(used_gb, 2),
                "pydrive2_compatible": pydrive_result.get("success", False) if pydrive_result else False,
                "pydrive2_message": pydrive_result.get("message", "Not tested") if pydrive_result else "oauth2client credentials not available"
            }
            
        except HttpError as e:
            logger.error(f"❌ Google Drive API error: {e}")
            return {"success": False, "message": f"API error: {e}"}
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return {"success": False, "message": f"Connection failed: {str(e)}"}
    
    def create_folder(self, folder_name, parent_folder_id='root'):
        """
        Create folder in Google Drive
        
        Args:
            folder_name (str): Name of folder to create
            parent_folder_id (str): Parent folder ID ('root' for root directory)
            
        Returns:
            str: Created folder ID, None if failed
        """
        try:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder_id]
            }
            
            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            
            logger.info(f"✅ Folder created: {folder_name} (ID: {folder_id})")
            return folder_id
            
        except HttpError as e:
            logger.error(f"❌ Failed to create folder {folder_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Folder creation error: {e}")
            return None
    
    def find_folder(self, folder_name, parent_folder_id='root'):
        """
        Find folder by name in Google Drive
        
        Args:
            folder_name (str): Name of folder to find
            parent_folder_id (str): Parent folder ID to search in
            
        Returns:
            str: Folder ID if found, None otherwise
        """
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_folder_id}' in parents"
            results = self.service.files().list(q=query, fields='files(id, name)').execute()
            folders = results.get('files', [])
            
            if folders:
                folder_id = folders[0]['id']
                logger.info(f"✅ Found folder: {folder_name} (ID: {folder_id})")
                return folder_id
            else:
                logger.info(f"📁 Folder not found: {folder_name}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Folder search error: {e}")
            return None
    
    def get_or_create_folder(self, folder_name, parent_folder_id='root'):
        """
        Get existing folder or create new one
        
        Args:
            folder_name (str): Name of folder
            parent_folder_id (str): Parent folder ID
            
        Returns:
            str: Folder ID
        """
        folder_id = self.find_folder(folder_name, parent_folder_id)
        if not folder_id:
            folder_id = self.create_folder(folder_name, parent_folder_id)
        return folder_id
    
    def upload_file(self, file_path, folder_id='root', custom_name=None):
        """
        Upload file to Google Drive
        
        Args:
            file_path (str): Local file path to upload
            folder_id (str): Google Drive folder ID to upload to
            custom_name (str): Custom name for uploaded file
            
        Returns:
            dict: Upload result with file ID and metadata
        """
        try:
            if not Path(file_path).exists():
                return {"success": False, "message": f"File not found: {file_path}"}
            
            file_name = custom_name or Path(file_path).name
            file_size = Path(file_path).stat().st_size
            
            logger.info(f"📤 Uploading {file_name} ({file_size} bytes) to Google Drive...")
            
            # File metadata
            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            
            # Create media upload
            media = MediaFileUpload(file_path, resumable=True)
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, size, createdTime'
            ).execute()
            
            file_id = file.get('id')
            upload_size = file.get('size')
            created_time = file.get('createdTime')
            
            logger.info(f"✅ Upload successful: {file_name}")
            logger.info(f"   File ID: {file_id}")
            logger.info(f"   Size: {upload_size} bytes")
            
            return {
                "success": True,
                "message": f"File uploaded successfully: {file_name}",
                "file_id": file_id,
                "file_name": file_name,
                "file_size": upload_size,
                "created_time": created_time,
                "drive_url": f"https://drive.google.com/file/d/{file_id}/view"
            }
            
        except HttpError as e:
            logger.error(f"❌ Upload failed: {e}")
            return {"success": False, "message": f"Upload failed: {e}"}
        except Exception as e:
            logger.error(f"❌ Upload error: {e}")
            return {"success": False, "message": f"Upload error: {str(e)}"}
    
    def upload_video(self, video_path, camera_name=None):
        """
        Upload video file with organized folder structure
        
        Args:
            video_path (str): Path to video file
            camera_name (str): Camera name for folder organization
            
        Returns:
            dict: Upload result
        """
        try:
            # Create VTrack main folder
            vtrack_folder_id = self.get_or_create_folder("VTrack_Videos")
            
            # Create camera folder if specified
            if camera_name:
                camera_folder_id = self.get_or_create_folder(camera_name, vtrack_folder_id)
                upload_folder_id = camera_folder_id
            else:
                upload_folder_id = vtrack_folder_id
            
            # Generate custom filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_name = Path(video_path).stem
            extension = Path(video_path).suffix
            custom_name = f"{original_name}_{timestamp}{extension}"
            
            # Upload file
            result = self.upload_file(video_path, upload_folder_id, custom_name)
            
            if result["success"]:
                result["folder_structure"] = f"VTrack_Videos/{camera_name or 'General'}"
                
            return result
            
        except Exception as e:
            logger.error(f"❌ Video upload error: {e}")
            return {"success": False, "message": f"Video upload failed: {str(e)}"}
    
    def list_files(self, folder_id='root', limit=10):
        """
        List files in Google Drive folder
        
        Args:
            folder_id (str): Folder ID to list files from
            limit (int): Maximum number of files to return
            
        Returns:
            list: List of file metadata
        """
        try:
            query = f"'{folder_id}' in parents"
            results = self.service.files().list(
                q=query,
                pageSize=limit,
                fields='files(id, name, size, createdTime, mimeType)'
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"📋 Found {len(files)} files in folder")
            
            return files
            
        except Exception as e:
            logger.error(f"❌ File listing error: {e}")
            return []
    
    def download_file(self, file_id, download_path):
        """
        Download file from Google Drive
        
        Args:
            file_id (str): Google Drive file ID
            download_path (str): Local path to save file
            
        Returns:
            dict: Download result
        """
        try:
            # Get file metadata
            file_metadata = self.service.files().get(fileId=file_id).execute()
            file_name = file_metadata.get('name')
            
            logger.info(f"📥 Downloading {file_name} from Google Drive...")
            
            # Download file content
            request = self.service.files().get_media(fileId=file_id)
            
            with open(download_path, 'wb') as file:
                downloader = MediaIoBaseDownload(file, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    if status:
                        logger.info(f"Download progress: {int(status.progress() * 100)}%")
            
            logger.info(f"✅ Download completed: {download_path}")
            
            return {
                "success": True,
                "message": f"File downloaded successfully: {file_name}",
                "file_name": file_name,
                "local_path": download_path
            }
            
        except Exception as e:
            logger.error(f"❌ Download error: {e}")
            return {"success": False, "message": f"Download failed: {str(e)}"}
    
    def delete_file(self, file_id):
        """
        Delete file from Google Drive
        
        Args:
            file_id (str): Google Drive file ID
            
        Returns:
            dict: Deletion result
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"✅ File deleted: {file_id}")
            
            return {
                "success": True,
                "message": f"File deleted successfully: {file_id}"
            }
            
        except Exception as e:
            logger.error(f"❌ Delete error: {e}")
            return {"success": False, "message": f"Delete failed: {str(e)}"}


def test_google_drive_client():
    """
    Test function for Google Drive client
    """
    print("🔧 Testing Google Drive Client...")
    
    # Initialize client
    client = GoogleDriveClient()
    
    # Test authentication
    print("\n1. Testing authentication...")
    auth_result = client.authenticate()
    print(f"Authentication: {'✅ Success' if auth_result else '❌ Failed'}")
    
    if not auth_result:
        return
    
    # Test connection
    print("\n2. Testing connection...")
    conn_result = client.test_connection()
    print(f"Connection: {'✅ Success' if conn_result['success'] else '❌ Failed'}")
    print(f"Message: {conn_result['message']}")
    
    if conn_result['success']:
        print(f"User: {conn_result.get('user_email', 'Unknown')}")
        print(f"Storage: {conn_result.get('storage_used_gb', 0):.2f}GB used")
    
    # Test folder creation
    print("\n3. Testing folder creation...")
    vtrack_folder_id = client.get_or_create_folder("VTrack_Test")
    if vtrack_folder_id:
        print(f"✅ VTrack_Test folder ready: {vtrack_folder_id}")
    
    # Test file listing
    print("\n4. Testing file listing...")
    files = client.list_files(limit=5)
    print(f"✅ Found {len(files)} files in root directory")
    
    print("\n🎉 Google Drive Client test completed!")


if __name__ == "__main__":
    test_google_drive_client()