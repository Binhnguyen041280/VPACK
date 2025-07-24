# nvr_client.py - Fixed Authentication for ZM v1.34.26
import requests
import logging
import socket
import random
import json
import os
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from .onvif_client import onvif_client

class NVRClient:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.base_url = None
        # 🆕 JWT Token storage
        self.access_token = None
        self.auth_credentials = None
    
    def _authenticate_zoneminder(self, username: str, password: str) -> bool:
        """🔧 DEBUG: ZoneMinder authentication with detailed logging"""
        try:
            auth_data = {
                'user': username,
                'pass': password
            }
            
            login_url = f"{self.base_url}/host/login.json"
            self.logger.info(f"🔐 Attempting login to: {login_url}")
            self.logger.info(f"🔐 Login data: user={username}, pass=***")
            
            response = self.session.post(login_url, data=auth_data, timeout=10)
            
            self.logger.info(f"🔐 Login response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"🔐 Login response data: {json.dumps(data, indent=2)}")
                
                # 🎯 PRIORITY: Use auth credentials (works with current ZM config)
                if 'credentials' in data and data.get('credentials'):
                    self.auth_credentials = data['credentials']  # "auth=abc123"
                    self.logger.info(f"✅ ZoneMinder auth hash successful: {self.auth_credentials}")
                    return True
                
                # Fallback: JWT token (if ZM configured differently)
                elif 'access_token' in data and data.get('access_token'):
                    self.access_token = data['access_token']
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.access_token}'
                    })
                    self.logger.info("✅ ZoneMinder JWT authentication successful")
                    return True
                
                # Simple success
                elif data.get('success', False):
                    self.logger.info("✅ ZoneMinder basic auth successful")
                    return True
                
                else:
                    self.logger.error("❌ ZoneMinder authentication failed - no valid response")
                    return False
            else:
                self.logger.error(f"❌ ZoneMinder auth request failed: {response.status_code}")
                self.logger.error(f"❌ Response text: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ ZoneMinder authentication error: {e}")
            return False
    
    def _make_authenticated_request(self, url: str, **kwargs):
        """🔧 DEBUG: Make request with detailed logging"""
        
        self.logger.info(f"🌐 Making request to: {url}")
        
        # Priority: Auth credentials (current working method)
        if self.auth_credentials:
            separator = '&' if '?' in url else '?'
            auth_url = f"{url}{separator}{self.auth_credentials}"
            self.logger.info(f"🔑 Using auth hash URL: {auth_url}")
            response = self.session.get(auth_url, **kwargs)
            self.logger.info(f"🌐 Auth hash response status: {response.status_code}")
            if response.status_code != 200:
                self.logger.error(f"❌ Auth hash response error: {response.text[:200]}")
            return response
        
        # Fallback: JWT token
        elif self.access_token:
            self.logger.info(f"🔑 Using JWT token in headers")
            response = self.session.get(url, **kwargs)
            self.logger.info(f"🌐 JWT response status: {response.status_code}")
            return response
        
        # No auth - try direct request
        else:
            self.logger.info(f"🔓 No auth - direct request")
            response = self.session.get(url, **kwargs)
            self.logger.info(f"🌐 Direct response status: {response.status_code}")
            return response

    def _discover_zoneminder_real(self, url: str, config: dict) -> dict:
        """🔧 FIXED: Auth first, then version check"""
        self.base_url = f"http://{url}/zm/api"
        username = config.get('username', '')
        password = config.get('password', '')
        
        self.logger.info(f"🎯 === ZONEMINDER DISCOVERY START ===")
        self.logger.info(f"🎯 Base URL: {self.base_url}")
        self.logger.info(f"🎯 Username: {username}")
        self.logger.info(f"🎯 Password provided: {'Yes' if password else 'No'}")
        
        try:
            # Step 1: Authentication FIRST (if credentials provided)
            if username and password:
                self.logger.info(f"🔐 Step 1: Authenticating with credentials")
                auth_success = self._authenticate_zoneminder(username, password)
                if not auth_success:
                    error_msg = "ZoneMinder authentication failed"
                    self.logger.error(f"❌ {error_msg}")
                    return self._error_response(error_msg)
            elif username or password:
                error_msg = "Both username and password required for authentication"
                self.logger.error(f"❌ {error_msg}")
                return self._error_response(error_msg)
            else:
                self.logger.info(f"🔓 Step 1: No credentials provided - skipping auth")
            
            # Step 2: Test connectivity & get version (AFTER auth)
            self.logger.info(f"📡 Step 2: Testing version endpoint")
            version_response = self._make_authenticated_request(f"{self.base_url}/host/getVersion.json", timeout=10)
            if version_response.status_code != 200:
                error_msg = f"ZoneMinder API not accessible. Status: {version_response.status_code}"
                self.logger.error(f"❌ {error_msg}")
                return self._error_response(error_msg)
            
            version_data = version_response.json()
            zm_version = version_data.get('version', 'Unknown')
            api_version = version_data.get('apiversion', 'Unknown')
            
            self.logger.info(f"✅ ZoneMinder version: {zm_version}, API: {api_version}")
            
            # Step 3: Get real monitors with authentication
            self.logger.info(f"📹 Step 3: Getting monitors")
            monitors_response = self._make_authenticated_request(f"{self.base_url}/monitors.json", timeout=10)
            if monitors_response.status_code != 200:
                if monitors_response.status_code == 401:
                    error_msg = "Authentication required but failed. Check username/password."
                    self.logger.error(f"❌ {error_msg}")
                    return self._error_response(error_msg)
                else:
                    error_msg = f"Failed to get monitors. Status: {monitors_response.status_code}"
                    self.logger.error(f"❌ {error_msg}")
                    return self._error_response(error_msg)
            
            monitors_data = monitors_response.json()
            monitors = monitors_data.get('monitors', [])
            
            self.logger.info(f"✅ Found {len(monitors)} monitors")
            
            if not monitors:
                error_msg = "No monitors found in ZoneMinder"
                self.logger.error(f"❌ {error_msg}")
                return self._error_response(error_msg)
            
            # Step 4: Process real monitor data
            cameras = []
            for monitor_data in monitors:
                monitor = monitor_data.get('Monitor', {})
                monitor_status = monitor_data.get('Monitor_Status', {})
                
                monitor_id = monitor.get('Id')
                monitor_name = monitor.get('Name', f"Monitor_{monitor_id}")
                
                camera_info = {
                    "id": f"zm_monitor_{monitor_id}",
                    "name": monitor_name,
                    "description": f"ZM {monitor_name} ({monitor.get('Function', 'Record')})",
                    "zm_id": monitor_id,
                    "status": monitor_status.get('Status', 'Unknown'),
                    "resolution": f"{monitor.get('Width', 'Unknown')}x{monitor.get('Height', 'Unknown')}",
                    "function": monitor.get('Function', 'Record'),
                    "enabled": monitor.get('Enabled') == '1',
                    "type": monitor.get('Type', 'Unknown'),
                    "fps": {
                        "capture": float(monitor_status.get('CaptureFPS', '0.00')),
                        "analysis": float(monitor_status.get('AnalysisFPS', '0.00'))
                    },
                    "capabilities": self._get_zm_capabilities(monitor)
                }
                
                # Add path information
                monitor_path = monitor.get('Path', '')
                if monitor.get('Type') == 'File' and monitor_path:
                    camera_info['file_path'] = monitor_path
                elif monitor_path.startswith('rtsp://') or monitor_path.startswith('http://'):
                    camera_info['stream_url'] = monitor_path
                
                cameras.append(camera_info)
                
                self.logger.info(f"📹 Found ZM monitor: {monitor_name} (ID: {monitor_id}, Status: {camera_info['status']})")
            
            # Step 5: Get system information
            self.logger.info(f"🔧 Step 5: Getting system info")
            system_info = self._get_zoneminder_system_info()
            
            success_result = {
                "accessible": True,
                "message": f"ZoneMinder connection successful - Discovered {len(cameras)} camera(s)",
                "source_type": "nvr",
                "protocol": "zoneminder",
                "cameras": cameras,
                "device_info": {
                    "manufacturer": "ZoneMinder",
                    "model": "Open Source NVR",
                    "firmware": zm_version,
                    "api_version": api_version,
                    "disk_usage": system_info.get('disk_usage', 'Unknown'),
                    "total_cameras": len(cameras),
                    "api_url": self.base_url,
                    "auth_method": "Auth Hash" if self.auth_credentials else ("JWT Token" if self.access_token else "No Auth")
                }
            }
            
            self.logger.info(f"🎯 === ZONEMINDER DISCOVERY SUCCESS ===")
            return success_result
            
        except requests.exceptions.RequestException as e:
            error_msg = f"ZoneMinder API connection failed: {str(e)}"
            self.logger.error(f"❌ Request error: {error_msg}")
            return self._error_response(error_msg)
        except Exception as e:
            error_msg = f"ZoneMinder discovery failed: {str(e)}"
            self.logger.error(f"❌ Unexpected error: {error_msg}")
            return self._error_response(error_msg)
    
    def _get_zoneminder_system_info(self) -> dict:
        """🔧 FIXED: Get ZoneMinder system information with auth"""
        system_info = {}
        
        try:
            # Get disk usage with authentication
            disk_response = self._make_authenticated_request(f"{self.base_url}/host/getDiskPercent.json", timeout=5)
            if disk_response.status_code == 200:
                disk_data = disk_response.json()
                usage = disk_data.get('usage', {})
                total_usage = usage.get('Total', {}).get('space', 'Unknown')
                system_info['disk_usage'] = f"{total_usage}% used" if total_usage != 'Unknown' else 'Unknown'
                
                self.logger.info(f"ZoneMinder disk usage: {system_info['disk_usage']}")
            
        except Exception as e:
            self.logger.warning(f"Failed to get ZoneMinder system info: {e}")
            system_info['disk_usage'] = 'Unknown'
        
        return system_info
    
    def test_connection_and_discover_cameras(self, source_data: dict) -> dict:
        """
        Universal NVR connection test and camera discovery
        Supports: ZoneMinder (Real), ONVIF (Mock), RTSP, etc.
        """
        url = source_data.get('path', '')
        config = source_data.get('config', {})
        protocol = config.get('protocol', 'onvif').lower()
        username = config.get('username', '')
        password = config.get('password', '')
        
        self.logger.info(f"Testing NVR connection to {url} using {protocol}")
        
        try:
            # Basic validation
            if not url:
                return self._error_response("NVR URL is required")
            
            # Extract host for network check
            host = self._extract_host(url)
            
            # Network connectivity check
            if not self._check_network_connectivity(host):
                return self._error_response(f"Cannot reach NVR at {host}. Check network connectivity.")
            
            # Protocol-specific discovery
            if protocol == 'zoneminder':
                return self._discover_zoneminder_real(url, config)
            elif protocol == 'onvif':
                return self._discover_onvif_real(url, config)
            elif protocol == 'rtsp':
                return self._discover_rtsp_mock(url, config)
            elif protocol == 'hikvision':
                return self._discover_vendor_mock(url, config, 'hikvision')
            elif protocol == 'dahua':
                return self._discover_vendor_mock(url, config, 'dahua')
            else:
                return self._discover_generic_mock(url, config)
                
        except Exception as e:
            self.logger.error(f"NVR connection test failed: {e}")
            return self._error_response(f"Connection test failed: {str(e)}")
    
    # ... (rest of the methods remain the same)
    
    def _get_zm_capabilities(self, monitor: dict) -> List[str]:
        """Get ZoneMinder monitor capabilities"""
        capabilities = []
        
        function = monitor.get('Function', '')
        if function in ['Record', 'Mocord']:
            capabilities.append('recording')
        if function in ['Monitor', 'Modect', 'Mocord']:
            capabilities.append('monitoring')
        if function in ['Modect', 'Mocord']:
            capabilities.append('motion_detection')
        
        if monitor.get('Controllable') == '1':
            capabilities.append('ptz')
        
        if monitor.get('RecordAudio') == '1':
            capabilities.append('audio')
            
        return capabilities
    
    def _extract_host(self, url: str) -> str:
        """Extract hostname/IP from URL"""
        url = url.replace('http://', '').replace('https://', '').replace('rtsp://', '')
        host = url.split(':')[0].split('/')[0]
        return host
    
    def _check_network_connectivity(self, host: str) -> bool:
        """Check network connectivity"""
        try:
            socket.gethostbyname(host)
            return True
        except socket.gaierror:
            # For local IPs and localhost, assume reachable
            if host.startswith('192.168.') or host.startswith('10.') or host.startswith('172.') or host in ['localhost', '127.0.0.1']:
                return True
            return False
    
    def _error_response(self, message: str) -> dict:
        """Standard error response"""
        return {
            "accessible": False,
            "message": message,
            "source_type": "nvr",
            "cameras": [],
            "device_info": {}
        }
    
    # Mock implementations for other protocols
    def _discover_onvif_mock(self, url: str, config: dict) -> dict:
        """Mock ONVIF discovery (for other NVR types)"""
        if not config.get('username') or not config.get('password'):
            return self._error_response("Username and password are required for ONVIF")
        
        host = self._extract_host(url)
        num_cameras = random.randint(2, 6)
        cameras = []
        
        camera_names = ["Front Door", "Parking", "Warehouse", "Office", "Storage", "Loading"]
        
        for i in range(num_cameras):
            cameras.append({
                "id": f"onvif_profile_{i+1}",
                "name": camera_names[i] if i < len(camera_names) else f"Camera {i+1}",
                "description": f"ONVIF Camera {i+1}",
                "stream_url": f"rtsp://{host}:554/stream{i+1}",
                "resolution": random.choice(["1920x1080", "1280x720", "2560x1440"]),
                "codec": random.choice(["H264", "H265"]),
                "capabilities": ["recording"] + (["ptz"] if i < 2 else [])
            })
        
        return {
            "accessible": True,
            "message": f"ONVIF connection successful - Discovered {num_cameras} cameras",
            "source_type": "nvr",
            "protocol": "onvif",
            "cameras": cameras,
            "device_info": {
                "manufacturer": "Generic ONVIF",
                "model": f"NVR-{num_cameras}CH",
                "firmware": f"V{random.randint(2,5)}.{random.randint(0,9)}.0"
            }
        }
    
    def _discover_rtsp_mock(self, url: str, config: dict) -> dict:
        """Mock RTSP discovery"""
        if not config.get('username') or not config.get('password'):
            return self._error_response("Username and password are required for RTSP")
        
        return {
            "accessible": True,
            "message": "RTSP connection successful - Found 2 streams",
            "source_type": "nvr",
            "protocol": "rtsp",
            "cameras": [
                {"id": "rtsp_1", "name": "Main Stream", "stream_url": f"rtsp://{url}/stream1"},
                {"id": "rtsp_2", "name": "Sub Stream", "stream_url": f"rtsp://{url}/stream2"}
            ],
            "device_info": {"manufacturer": "Generic RTSP", "model": "RTSP Server"}
        }
    
    def _discover_vendor_mock(self, url: str, config: dict, vendor: str) -> dict:
        """Mock vendor-specific discovery"""
        return {
            "accessible": False,
            "message": f"{vendor.title()} API integration coming soon. Use ONVIF protocol for now.",
            "source_type": "nvr",
            "protocol": vendor,
            "cameras": [],
            "device_info": {}
        }
    
    def _discover_generic_mock(self, url: str, config: dict) -> dict:
        """Mock generic discovery"""
        return {
            "accessible": False,
            "message": "Generic HTTP API not implemented. Try ONVIF, RTSP, or ZoneMinder protocols.",
            "source_type": "nvr",
            "protocol": "generic",
            "cameras": [],
            "device_info": {}
        }
    def _discover_onvif_real(self, url: str, config: dict) -> dict:
        """Real ONVIF discovery"""
        try:
            host = self._extract_host(url)
            port = int(config.get('port', 80))
            username = config.get('username', '')
            password = config.get('password', '')
            
            response = onvif_client.test_device_connection(host, port, username, password)
            
            # Validate cameras is array
            if 'cameras' in response and not isinstance(response['cameras'], list):
                response['cameras'] = [response['cameras']]
            
            # Handle multiple cameras and generate IDs
            if 'cameras' in response:
                for i, camera in enumerate(response['cameras']):
                    camera['id'] = f"onvif_{host}_channel_{i+1}"
            
            return response
            
        except Exception as e:
            return self._error_response(f"ONVIF lỗi: {str(e)}")