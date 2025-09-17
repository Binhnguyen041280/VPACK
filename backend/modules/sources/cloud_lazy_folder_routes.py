#!/usr/bin/env python3

"""
Lazy Loading Folder Tree Routes for Google Drive Integration
Separated from main cloud_endpoints.py for better organization
"""

from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin
from google.oauth2.credentials import Credentials
from modules.sources.google_drive_service import GoogleDriveFolderService
from datetime import datetime
import logging
from functools import wraps
import time
from collections import defaultdict
import hashlib
import json
import os
from google.auth.transport.requests import Request
from cryptography.fernet import Fernet
import base64
from .cloud_auth import CloudAuthManager

logger = logging.getLogger(__name__)

# Rate limiting storage
lazy_folder_rate_limit_storage = defaultdict(list)

LAZY_FOLDER_RATE_LIMITS = {
    'folder_discovery': {'calls': 15, 'window': 60},
    'folder_search': {'calls': 10, 'window': 60},
    'folder_info': {'calls': 20, 'window': 60}
}

def lazy_folder_rate_limit(endpoint_type='folder_discovery'):
    """Rate limiting decorator for lazy folder operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            current_time = time.time()
            
            limit_config = LAZY_FOLDER_RATE_LIMITS.get(endpoint_type, {'calls': 15, 'window': 60})
            max_calls = limit_config['calls']
            time_window = limit_config['window']
            
            # Clean old entries
            cutoff_time = current_time - time_window
            lazy_folder_rate_limit_storage[client_ip] = [
                call_time for call_time in lazy_folder_rate_limit_storage[client_ip] 
                if call_time > cutoff_time
            ]
            
            # Check rate limit
            if len(lazy_folder_rate_limit_storage[client_ip]) >= max_calls:
                logger.warning(f"🚫 Lazy folder rate limit exceeded for {client_ip} on {endpoint_type}")
                return jsonify({
                    'success': False,
                    'message': f'Rate limit exceeded. Max {max_calls} calls per {time_window} seconds.',
                    'retry_after': int(time_window - (current_time - lazy_folder_rate_limit_storage[client_ip][0]))
                }), 429
            
            # Record this call
            lazy_folder_rate_limit_storage[client_ip].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_credentials_simple():
    """
    🎯 SIMPLE CREDENTIALS - Bước 3 = manual auth required, but allow after successful auth
    """
    try:
        # Check if this is initial setup (step 3)
        setup_step = session.get('current_setup_step')
        is_video_source_setup = (setup_step == 'video-source')

        logger.info(f"🔍 Setup step check: '{setup_step}' -> is_setup: {is_video_source_setup}")

        if is_video_source_setup:
            # Step 3 setup: Check if user has just authenticated
            session_token = session.get('session_token')
            auth_result = session.get('auth_result')

            if session_token or (auth_result and auth_result.get('credentials')):
                logger.info("🎯 Step 3 setup: Found session token/credentials - allowing folder access")
                # Use the new session-based credential loading
                from .cloud_endpoints import get_credentials_from_session
                credentials = get_credentials_from_session()
                if credentials:
                    return credentials
                else:
                    # Fallback to legacy method
                    return _get_credentials_from_legacy_session()
            else:
                logger.info("🎯 Step 3 setup: No credentials - forcing manual Google Drive auth")
                return None
        else:
            # Setup completed: use saved credentials
            logger.info("🔄 Normal usage - loading saved credentials...")
            return _get_credentials_from_legacy_session()

    except Exception as e:
        logger.error(f"❌ Simple credential error: {e}")
        return None

def _get_credentials_from_legacy_session():
    """Get Google Drive credentials from session data (legacy method)"""
    try:
        auth_result = session.get('auth_result')
        if not auth_result or not auth_result.get('credentials'):
            logger.debug("⚠️ No credentials found in legacy auth_result")
            return None

        cred_data = auth_result['credentials']
        logger.info(f"✅ Found legacy credentials for: {auth_result.get('user_email', 'unknown')}")

        # Create credentials object from session data
        credentials = Credentials(
            token=cred_data.get('token'),
            refresh_token=cred_data.get('refresh_token'),
            token_uri=cred_data.get('token_uri'),
            client_id=cred_data.get('client_id'),
            client_secret=cred_data.get('client_secret'),
            scopes=cred_data.get('scopes')
        )

        # Refresh token if needed
        if credentials.expired and credentials.refresh_token:
            logger.info("🔄 Refreshing expired legacy credentials...")
            credentials.refresh(Request())

            # Update session with new token
            auth_result['credentials']['token'] = credentials.token
            session['auth_result'] = auth_result
            session.permanent = True

        return credentials

    except Exception as e:
        logger.error(f"❌ Error getting legacy session credentials: {e}")
        return None

# Removed complex database fallback - not needed for simple flow

# Removed complex CloudAuthManager integration - keeping it simple

# Create Blueprint for lazy folder routes
lazy_folder_bp = Blueprint('lazy_folders', __name__)

@lazy_folder_bp.route('/list_subfolders', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
@lazy_folder_rate_limit('folder_discovery')
def list_subfolders():
    """
    Get subfolders of a specific parent folder with lazy loading
    
    Request JSON:
    {
        "parent_id": "folder_id_or_root",
        "max_results": 50,
        "include_stats": false
    }
    
    Response:
    {
        "success": true,
        "folders": [...],
        "parent_info": {...},
        "total_count": 25,
        "has_more": false
    }
    """
    try:
        data = request.get_json()
        parent_id = data.get('parent_id', 'root')
        max_results = min(data.get('max_results', 50), 100)  # Cap at 100
        include_stats = data.get('include_stats', False)
        
        logger.info(f"📂 Listing subfolders for parent: {parent_id}")
        
        # Get credentials using simple system
        credentials = get_credentials_simple()
        if not credentials:
            return jsonify({
                'success': False,
                'message': 'No valid Google Drive credentials found. Please authenticate first.',
                'requires_auth': True,
                'error_code': 'CREDENTIALS_NOT_FOUND',
                'suggestion': 'Please re-authenticate with Google Drive'
            }), 401
        
        # Initialize folder service
        folder_service = GoogleDriveFolderService(credentials)
        
        # Get subfolders
        subfolders = folder_service.get_subfolders(parent_id, max_results)
        
        # Enrich folder data with depth and selection info
        enriched_folders = []
        for folder in subfolders:
            # Calculate depth for this folder
            depth = folder_service.calculate_folder_depth(folder['id'])
            
            # Check if folder has subfolders (for expand indicator)
            has_subfolders = folder_service.has_subfolders(folder['id'])
            
            enriched_folder = {
                'id': folder['id'],
                'name': folder['name'],
                'type': 'folder',
                'parent_id': parent_id,
                'depth': depth,
                'selectable': folder_service.is_selectable_folder(depth),
                'has_subfolders': has_subfolders,
                'created': folder.get('created'),
                'modified': folder.get('modified'),
                'path': folder_service.build_folder_path(folder['id'])
            }
            
            # Add statistics if requested
            if include_stats:
                stats = folder_service.get_folder_statistics(folder['id'])
                enriched_folder['stats'] = stats
            
            enriched_folders.append(enriched_folder)
        
        # Get parent folder info
        parent_info = {}
        if parent_id != 'root':
            parent_info = folder_service.get_folder_info(parent_id)
        else:
            parent_info = {
                'id': 'root',
                'name': 'My Drive',
                'depth': 0,
                'path': '/My Drive',
                'selectable': False
            }
        
        response_data = {
            'success': True,
            'folders': enriched_folders,
            'parent_info': parent_info,
            'total_count': len(enriched_folders),
            'has_more': len(enriched_folders) == max_results,  # Might have more if we hit the limit
            'cache_info': folder_service.get_cache_info(),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Found {len(enriched_folders)} subfolders in {parent_id}")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"❌ Error listing subfolders: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to list subfolders: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@lazy_folder_bp.route('/get_depth', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
@lazy_folder_rate_limit('folder_info')
def get_folder_depth():
    """
    Get the depth level of a specific folder
    
    Request JSON:
    {
        "folder_id": "folder_id"
    }
    
    Response:
    {
        "success": true,
        "folder_id": "folder_id",
        "depth": 2,
        "selectable": false,
        "path": "/My Drive/Project/Area"
    }
    """
    try:
        data = request.get_json()
        folder_id = data.get('folder_id')
        
        if not folder_id:
            return jsonify({
                'success': False,
                'message': 'folder_id is required'
            }), 400
        
        # Get credentials using simple system
        credentials = get_credentials_simple()
        if not credentials:
            return jsonify({
                'success': False,
                'message': 'No valid Google Drive credentials found',
                'requires_auth': True
            }), 401
        
        # Initialize folder service
        folder_service = GoogleDriveFolderService(credentials)
        
        # Calculate depth
        depth = folder_service.calculate_folder_depth(folder_id)
        path = folder_service.build_folder_path(folder_id)
        selectable = folder_service.is_selectable_folder(depth)
        
        return jsonify({
            'success': True,
            'folder_id': folder_id,
            'depth': depth,
            'selectable': selectable,
            'path': path,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting folder depth: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to get folder depth: {str(e)}'
        }), 500

@lazy_folder_bp.route('/search', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
@lazy_folder_rate_limit('folder_search')
def search_folders():
    """
    Search for folders by name
    
    Request JSON:
    {
        "query": "camera",
        "max_results": 20
    }
    
    Response:
    {
        "success": true,
        "folders": [...],
        "query": "camera",
        "total_found": 15
    }
    """
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        max_results = min(data.get('max_results', 20), 50)
        
        if not query:
            return jsonify({
                'success': False,
                'message': 'Search query is required'
            }), 400
        
        # Get credentials using simple system
        credentials = get_credentials_simple()
        if not credentials:
            return jsonify({
                'success': False,
                'message': 'No valid Google Drive credentials found',
                'requires_auth': True
            }), 401
        
        # Initialize folder service
        folder_service = GoogleDriveFolderService(credentials)
        
        # Search folders
        search_results = folder_service.search_folders(query, max_results)
        
        return jsonify({
            'success': True,
            'folders': search_results,
            'query': query,
            'total_found': len(search_results),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error searching folders: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to search folders: {str(e)}'
        }), 500

@lazy_folder_bp.route('/get_info', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
@lazy_folder_rate_limit('folder_info')
def get_folder_info():
    """
    Get comprehensive information about a folder
    
    Request JSON:
    {
        "folder_id": "folder_id",
        "include_stats": true
    }
    """
    try:
        data = request.get_json()
        folder_id = data.get('folder_id')
        include_stats = data.get('include_stats', False)
        
        if not folder_id:
            return jsonify({
                'success': False,
                'message': 'folder_id is required'
            }), 400
        
        # Get credentials using simple system
        credentials = get_credentials_simple()
        if not credentials:
            return jsonify({
                'success': False,
                'message': 'No valid Google Drive credentials found',
                'requires_auth': True
            }), 401
        
        # Initialize folder service
        folder_service = GoogleDriveFolderService(credentials)
        
        # Get folder info
        folder_info = folder_service.get_folder_info(folder_id)
        
        if include_stats:
            stats = folder_service.get_folder_statistics(folder_id)
            folder_info['stats'] = stats
        
        return jsonify({
            'success': True,
            'folder_info': folder_info,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting folder info: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to get folder info: {str(e)}'
        }), 500

@lazy_folder_bp.route('/clear_cache', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
@lazy_folder_rate_limit('folder_info')
def clear_folder_cache():
    """Clear Google Drive folder service cache"""
    try:
        # If we have active credentials, clear service cache
        credentials = get_unified_credentials()
        if credentials:
            folder_service = GoogleDriveFolderService(credentials)
            folder_service.clear_cache()
        
        return jsonify({
            'success': True,
            'message': 'Folder service cache cleared successfully',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error clearing folder cache: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to clear folder cache: {str(e)}'
        }), 500

@lazy_folder_bp.route('/breadcrumb', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
@lazy_folder_rate_limit('folder_info')
def get_folder_breadcrumb():
    """
    Get breadcrumb navigation for a folder
    
    Request JSON:
    {
        "folder_id": "folder_id"
    }
    
    Response:
    {
        "success": true,
        "breadcrumb": [
            {"id": "root", "name": "My Drive", "depth": 0},
            {"id": "123", "name": "Project", "depth": 1},
            {"id": "456", "name": "Area", "depth": 2}
        ]
    }
    """
    try:
        data = request.get_json()
        folder_id = data.get('folder_id')
        
        if not folder_id:
            return jsonify({
                'success': False,
                'message': 'folder_id is required'
            }), 400
        
        # Get credentials using simple system
        credentials = get_credentials_simple()
        if not credentials:
            return jsonify({
                'success': False,
                'message': 'No valid Google Drive credentials found',
                'requires_auth': True
            }), 401
        
        # Initialize folder service
        folder_service = GoogleDriveFolderService(credentials)
        
        # Build breadcrumb
        breadcrumb = []
        current_id = folder_id
        
        # Traverse up the hierarchy
        while current_id and current_id != 'root' and len(breadcrumb) < 10:
            try:
                folder_info = folder_service.get_folder_info(current_id)
                breadcrumb.insert(0, {
                    'id': current_id,
                    'name': folder_info.get('name', 'Unknown'),
                    'depth': folder_info.get('depth', 0)
                })
                
                # Get parent
                parents = folder_info.get('parents', [])
                current_id = parents[0] if parents else 'root'
                
            except Exception as e:
                logger.warning(f"⚠️ Error getting folder info for breadcrumb {current_id}: {e}")
                break
        
        # Add root if not already there
        if not breadcrumb or breadcrumb[0]['id'] != 'root':
            breadcrumb.insert(0, {
                'id': 'root',
                'name': 'My Drive',
                'depth': 0
            })
        
        return jsonify({
            'success': True,
            'breadcrumb': breadcrumb,
            'total_levels': len(breadcrumb),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting breadcrumb: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to get breadcrumb: {str(e)}'
        }), 500

@lazy_folder_bp.route('/validate_selection', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
@lazy_folder_rate_limit('folder_info')
def validate_folder_selection():
    """
    Validate if selected folders meet the depth requirements
    
    Request JSON:
    {
        "folder_ids": ["id1", "id2", "id3"]
    }
    
    Response:
    {
        "success": true,
        "valid_selections": [...],
        "invalid_selections": [...],
        "total_valid": 2
    }
    """
    try:
        data = request.get_json()
        folder_ids = data.get('folder_ids', [])
        
        if not folder_ids:
            return jsonify({
                'success': False,
                'message': 'folder_ids array is required'
            }), 400
        
        # Get credentials using simple system
        credentials = get_credentials_simple()
        if not credentials:
            return jsonify({
                'success': False,
                'message': 'No valid Google Drive credentials found',
                'requires_auth': True
            }), 401
        
        # Initialize folder service
        folder_service = GoogleDriveFolderService(credentials)
        
        valid_selections = []
        invalid_selections = []
        
        for folder_id in folder_ids:
            try:
                depth = folder_service.calculate_folder_depth(folder_id)
                selectable = folder_service.is_selectable_folder(depth)
                folder_info = folder_service.get_folder_info(folder_id)
                
                selection_info = {
                    'id': folder_id,
                    'name': folder_info.get('name', 'Unknown'),
                    'depth': depth,
                    'selectable': selectable,
                    'path': folder_info.get('path', ''),
                    'reason': 'Valid camera folder' if selectable else f'Wrong depth (level {depth}, need level 4)'
                }
                
                if selectable:
                    valid_selections.append(selection_info)
                else:
                    invalid_selections.append(selection_info)
                    
            except Exception as e:
                logger.warning(f"⚠️ Error validating folder {folder_id}: {e}")
                invalid_selections.append({
                    'id': folder_id,
                    'name': 'Unknown',
                    'depth': -1,
                    'selectable': False,
                    'path': '',
                    'reason': f'Validation error: {str(e)}'
                })
        
        return jsonify({
            'success': True,
            'valid_selections': valid_selections,
            'invalid_selections': invalid_selections,
            'total_valid': len(valid_selections),
            'total_invalid': len(invalid_selections),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error validating folder selection: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to validate selection: {str(e)}'
        }), 500