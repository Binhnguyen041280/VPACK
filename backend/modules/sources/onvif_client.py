# onvif_client.py - ONVIF cho VTrack
import logging
import socket
import requests
from typing import Dict

logger = logging.getLogger(__name__)

class VTrackOnvifClient:
    def __init__(self):
        self.connected_cameras = {}
        
    def test_device_connection(self, ip: str, port: int, username: str = '', password: str = '') -> Dict:
        """Test ONVIF connection - discover multiple cameras from multiple ports"""
        logger.info(f"🎯 Testing ONVIF multiple camera discovery on {ip}")
        
        try:
            # Multiple ports for docker-compose setup
            ports_to_test = [1000, 1001, 1002] if port in [80, 1000] else [port]
            
            discovered_cameras = []
            accessible_ports = []
            
            for test_port in ports_to_test:
                try:
                    # Test socket connection
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3)
                    result = sock.connect_ex((ip, test_port))
                    sock.close()
                    
                    if result == 0:
                        logger.info(f"✅ Port {test_port} accessible")
                        
                        # Test ONVIF service
                        camera = self._test_single_port(ip, test_port, username, password)
                        if camera:
                            discovered_cameras.append(camera)
                            accessible_ports.append(test_port)
                            logger.info(f"✅ Camera discovered on port {test_port}: {camera['name']}")
                        else:
                            logger.warning(f"⚠️ Port {test_port} accessible but no ONVIF camera")
                    else:
                        logger.info(f"❌ Port {test_port} not accessible")
                        
                except Exception as port_error:
                    logger.warning(f"❌ Error testing port {test_port}: {port_error}")
                    continue
            
            if discovered_cameras:
                return {
                    'accessible': True,
                    'message': f'ONVIF Multi-Camera Discovery - Found {len(discovered_cameras)} camera(s) on ports: {accessible_ports}',
                    'source_type': 'nvr',
                    'protocol': 'onvif',
                    'cameras': discovered_cameras,
                    'device_info': {
                        'manufacturer': 'Multiple ONVIF Devices',
                        'model': 'Multi-Camera System',
                        'firmware': 'Various',
                        'total_cameras': len(discovered_cameras),
                        'discovered_ports': accessible_ports
                    }
                }
            else:
                return {
                    'accessible': False,
                    'message': f'No ONVIF cameras found on {ip} ports: {ports_to_test}',
                    'source_type': 'nvr',
                    'protocol': 'onvif',
                    'cameras': []
                }
                
        except Exception as e:
            logger.error(f"❌ Multiple camera discovery failed: {e}")
            return {
                'accessible': False,
                'message': f'Discovery error: {str(e)}',
                'source_type': 'nvr',
                'protocol': 'onvif',
                'cameras': []
            }

    def _test_single_port(self, ip: str, port: int, username: str = '', password: str = '') -> Dict:
        """Test single ONVIF camera on specific port"""
        try:
            soap_request = '''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
<soap:Header/>
<soap:Body>
<tds:GetDeviceInformation/>
</soap:Body>
</soap:Envelope>'''
            
            headers = {
                'Content-Type': 'application/soap+xml; charset=utf-8',
                'Content-Length': str(len(soap_request))
            }
            
            response = requests.post(
                f'http://{ip}:{port}/onvif/device_service',
                data=soap_request,
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200 and 'GetDeviceInformationResponse' in response.text:
                # Parse device info
                manufacturer = self._extract_xml_value(response.text, 'tds:Manufacturer', 'ACME Security')
                model = self._extract_xml_value(response.text, 'tds:Model', f'Camera-{port}')
                firmware = self._extract_xml_value(response.text, 'tds:FirmwareVersion', '2.0')
                
                # Port-based camera mapping
                camera_names = {
                    1000: "Front Door Camera",
                    1001: "Parking Lot Camera", 
                    1002: "Warehouse Camera"
                }
                
                rtsp_ports = {
                    1000: 8554,
                    1001: 8555,
                    1002: 8556
                }
                
                resolutions = {
                    1000: "1920x1080",
                    1001: "1280x720",
                    1002: "800x600"
                }
                
                codecs = {
                    1000: "H264",
                    1001: "H265", 
                    1002: "MPEG4"
                }
                
                camera_name = camera_names.get(port, f"Camera Port {port}")
                rtsp_port = rtsp_ports.get(port, 8554)
                resolution = resolutions.get(port, "640x480")
                codec = codecs.get(port, "H264")
                
                return {
                    'id': f"onvif_{ip}_{port}",
                    'name': camera_name,
                    'description': f"ONVIF {model} ({firmware})",
                    'stream_url': f"rtsp://{ip}:{rtsp_port}/stream",
                    'resolution': resolution,
                    'codec': codec,
                    'capabilities': ['recording'] + (['ptz'] if port == 1000 else []),
                    'onvif_port': port,
                    'rtsp_port': rtsp_port,
                    'manufacturer': manufacturer,
                    'model': model,
                    'firmware': firmware
                }
            else:
                return None
                
        except Exception as e:
            logger.warning(f"Failed to test port {port}: {e}")
            return None

    def _extract_xml_value(self, xml_text: str, tag: str, default: str = '') -> str:
        """Extract value from XML tag"""
        try:
            start_tag = f'<{tag}>'
            end_tag = f'</{tag}>'
            if start_tag in xml_text:
                start = xml_text.find(start_tag) + len(start_tag)
                end = xml_text.find(end_tag)
                return xml_text[start:end].strip() or default
            return default
        except:
            return default

# Global instance
onvif_client = VTrackOnvifClient()