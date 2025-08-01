# backend/modules/payments/license_generator.py

import json
import base64
import hashlib
import os
import platform
import uuid
import logging
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.fernet import Fernet
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class LicenseGenerator:
    """
    Cryptographic license generator for V_track desktop application
    Supports offline validation với RSA digital signatures
    """
    
    def __init__(self):
        self.private_key: Optional[rsa.RSAPrivateKey] = None
        self.public_key: Optional[rsa.RSAPublicKey] = None
        self.fernet_key: Optional[bytes] = None
        
        # Initialize keys
        self._load_or_generate_keys()
        
        logger.info("License generator initialized with cryptographic keys")
    
    def _load_or_generate_keys(self):
        """Load existing keys or generate new ones"""
        try:
            # Paths for key storage
            keys_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'keys')
            os.makedirs(keys_dir, exist_ok=True)
            
            private_key_path = os.path.join(keys_dir, 'license_private_key.pem')
            public_key_path = os.path.join(keys_dir, 'license_public_key.pem')
            fernet_key_path = os.path.join(keys_dir, 'license_fernet_key.key')
            
            # Load or generate RSA keys
            if os.path.exists(private_key_path) and os.path.exists(public_key_path):
                self._load_rsa_keys(private_key_path, public_key_path)
                logger.info("Loaded existing RSA keys")
            else:
                self._generate_rsa_keys(private_key_path, public_key_path)
                logger.info("Generated new RSA keys")
            
            # Load or generate Fernet key
            if os.path.exists(fernet_key_path):
                with open(fernet_key_path, 'rb') as f:
                    self.fernet_key = f.read()
                logger.info("Loaded existing Fernet key")
            else:
                self.fernet_key = Fernet.generate_key()
                with open(fernet_key_path, 'wb') as f:
                    f.write(self.fernet_key)
                logger.info("Generated new Fernet key")
                
        except Exception as e:
            logger.error(f"Key initialization error: {str(e)}")
            raise
    
    def _generate_rsa_keys(self, private_path: str, public_path: str):
        """Generate new RSA key pair"""
        try:
            # Generate private key
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Get public key
            self.public_key = self.private_key.public_key()
            
            # Save private key
            private_pem = self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            with open(private_path, 'wb') as f:
                f.write(private_pem)
            
            # Save public key
            public_pem = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            with open(public_path, 'wb') as f:
                f.write(public_pem)
                
            # Set appropriate permissions (read-only for owner)
            os.chmod(private_path, 0o600)
            os.chmod(public_path, 0o644)
            
        except Exception as e:
            logger.error(f"RSA key generation error: {str(e)}")
            raise
    
    def _load_rsa_keys(self, private_path: str, public_path: str):
        """Load existing RSA keys"""
        try:
            # Load private key
            with open(private_path, 'rb') as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                )
            
            # Load public key
            with open(public_path, 'rb') as f:
                self.public_key = serialization.load_pem_public_key(f.read())
                
        except Exception as e:
            logger.error(f"RSA key loading error: {str(e)}")
            raise
    
    def generate_license(self, license_info: Dict[str, Any]) -> Optional[str]:
        """
        Generate cryptographically signed license key
        
        Args:
            license_info (dict): {
                'customer_email': str,
                'product_type': str,
                'features': list,
                'duration_days': int
            }
            
        Returns:
            str: Base64 encoded signed license key
        """
        try:
            if not self.private_key:
                logger.error("Private key not initialized")
                return None
                
            # Create license data
            license_data = {
                'customer_email': license_info['customer_email'],
                'product_type': license_info.get('product_type', 'desktop'),
                'features': license_info.get('features', ['full_access']),
                'issue_date': datetime.now().isoformat(),
                'expiry_date': (datetime.now() + timedelta(days=license_info.get('duration_days', 365))).isoformat(),
                'license_id': str(uuid.uuid4()),
                'version': '1.0',
                'issuer': 'V_track License System'
            }
            
            # Serialize license data
            license_json = json.dumps(license_data, sort_keys=True, separators=(',', ':'))
            license_bytes = license_json.encode('utf-8')
            
            # Create digital signature using RSA private key
            signature = self.private_key.sign(
                license_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # Create final license package
            license_package = {
                'data': base64.b64encode(license_bytes).decode('ascii'),
                'signature': base64.b64encode(signature).decode('ascii'),
                'algorithm': 'RSA-PSS-SHA256'
            }
            
            # Encode final license key
            license_key = base64.b64encode(
                json.dumps(license_package).encode('utf-8')
            ).decode('ascii')
            
            logger.info(f"Generated license for {license_info['customer_email']}")
            return license_key
            
        except Exception as e:
            logger.error(f"License generation error: {str(e)}")
            return None
    
    def verify_license(self, license_key: str) -> Optional[Dict[str, Any]]:
        """
        Verify license signature and extract data
        
        Args:
            license_key (str): Base64 encoded license key
            
        Returns:
            dict: License data nếu valid, None nếu invalid
        """
        try:
            if not self.public_key:
                logger.error("Public key not initialized")
                return None
                
            # Decode license package
            license_package_json = base64.b64decode(license_key).decode('utf-8')
            license_package = json.loads(license_package_json)
            
            # Extract components
            license_data_b64 = license_package['data']
            signature_b64 = license_package['signature']
            algorithm = license_package.get('algorithm', 'RSA-PSS-SHA256')
            
            # Decode data and signature
            license_data_bytes = base64.b64decode(license_data_b64)
            signature = base64.b64decode(signature_b64)
            
            # Verify signature using RSA public key
            if algorithm == 'RSA-PSS-SHA256':
                self.public_key.verify(
                    signature,
                    license_data_bytes,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")
            
            # Parse license data
            license_data = json.loads(license_data_bytes.decode('utf-8'))
            
            # Additional validation
            expiry_date = datetime.fromisoformat(license_data['expiry_date'])
            if datetime.now() > expiry_date:
                return None  # Expired
            
            logger.info(f"License verified for {license_data['customer_email']}")
            return license_data
            
        except Exception as e:
            logger.warning(f"License verification failed: {str(e)}")
            return None
    
    def generate_machine_fingerprint(self) -> str:
        """
        Generate unique machine fingerprint cho license binding
        
        Returns:
            str: Machine fingerprint hash
        """
        try:
            # Collect machine-specific data
            machine_data = [
                platform.node(),          # Hostname
                platform.machine(),       # Architecture  
                platform.processor(),     # Processor info
                platform.system(),        # OS name
                str(uuid.getnode())        # MAC address
            ]
            
            # Get additional hardware info if available
            try:
                import psutil
                machine_data.append(str(psutil.disk_usage('/').total))  # Disk size
                machine_data.append(str(psutil.virtual_memory().total))  # RAM size
            except ImportError:
                pass  # psutil not available
            
            # Create fingerprint hash
            combined_data = '|'.join(machine_data).encode('utf-8')
            fingerprint = hashlib.sha256(combined_data).hexdigest()[:32]
            
            return fingerprint
            
        except Exception as e:
            logger.error(f"Machine fingerprint generation error: {str(e)}")
            # Fallback fingerprint
            return hashlib.md5(platform.node().encode()).hexdigest()[:16]
    
    def bind_license_to_machine(self, license_key: str, machine_fingerprint: Optional[str] = None) -> Optional[str]:
        """
        Bind license to specific machine
        
        Args:
            license_key (str): Original license key
            machine_fingerprint (str): Machine fingerprint (auto-generated if None)
            
        Returns:
            str: Machine-bound license key
        """
        try:
            if not self.private_key:
                logger.error("Private key not initialized")
                return None
                
            if machine_fingerprint is None:
                machine_fingerprint = self.generate_machine_fingerprint()
            
            # Verify original license
            license_data = self.verify_license(license_key)
            if not license_data:
                return None
            
            # Add machine binding
            license_data['machine_fingerprint'] = machine_fingerprint
            license_data['bound_date'] = datetime.now().isoformat()
            
            # Re-sign with machine binding
            license_json = json.dumps(license_data, sort_keys=True, separators=(',', ':'))
            license_bytes = license_json.encode('utf-8')
            
            signature = self.private_key.sign(
                license_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # Create bound license package
            bound_package = {
                'data': base64.b64encode(license_bytes).decode('ascii'),
                'signature': base64.b64encode(signature).decode('ascii'),
                'algorithm': 'RSA-PSS-SHA256',
                'bound': True
            }
            
            bound_license = base64.b64encode(
                json.dumps(bound_package).encode('utf-8')
            ).decode('ascii')
            
            logger.info(f"License bound to machine {machine_fingerprint[:8]}...")
            return bound_license
            
        except Exception as e:
            logger.error(f"License binding error: {str(e)}")
            return None
    
    def validate_machine_binding(self, license_key: str, current_machine_fingerprint: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate machine-bound license
        
        Args:
            license_key (str): Machine-bound license key
            current_machine_fingerprint (str): Current machine fingerprint
            
        Returns:
            dict: Validation result
        """
        try:
            if current_machine_fingerprint is None:
                current_machine_fingerprint = self.generate_machine_fingerprint()
            
            # Verify license
            license_data = self.verify_license(license_key)
            if not license_data:
                return {'valid': False, 'error': 'Invalid license'}
            
            # Check machine binding
            if 'machine_fingerprint' not in license_data:
                return {'valid': True, 'bound': False}  # Unbound license
            
            stored_fingerprint = license_data['machine_fingerprint']
            
            if stored_fingerprint != current_machine_fingerprint:
                return {
                    'valid': False, 
                    'error': 'Machine fingerprint mismatch',
                    'expected': stored_fingerprint[:8] + '...',
                    'current': current_machine_fingerprint[:8] + '...'
                }
            
            return {
                'valid': True,
                'bound': True,
                'license_data': license_data
            }
            
        except Exception as e:
            logger.error(f"Machine binding validation error: {str(e)}")
            return {'valid': False, 'error': f'Validation error: {str(e)}'}
    
    def get_public_key_pem(self) -> Optional[str]:
        """
        Get public key in PEM format for client distribution
        
        Returns:
            str: Public key PEM string
        """
        try:
            if not self.public_key:
                logger.error("Public key not initialized")
                return None
                
            public_pem = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            return public_pem.decode('ascii')
            
        except Exception as e:
            logger.error(f"Public key export error: {str(e)}")
            return None
    
    def create_license_package_for_distribution(self, license_key: str) -> Optional[Dict[str, Any]]:
        """
        Create complete license package for client distribution
        
        Args:
            license_key (str): Generated license key
            
        Returns:
            dict: Complete license package
        """
        try:
            license_data = self.verify_license(license_key)
            if not license_data:
                return None
            
            public_key_pem = self.get_public_key_pem()
            if not public_key_pem:
                return None
            
            package = {
                'license_key': license_key,
                'public_key': public_key_pem,
                'customer_email': license_data['customer_email'],
                'product_type': license_data['product_type'],
                'features': license_data['features'],
                'expiry_date': license_data['expiry_date'],
                'license_id': license_data['license_id'],
                'instructions': {
                    'installation': [
                        '1. Save this license package to a secure location',
                        '2. Install V_track desktop application',
                        '3. Enter license key when prompted during first run',
                        '4. Application will automatically validate and activate'
                    ],
                    'support': 'support@vtrack.app'
                }
            }
            
            return package
            
        except Exception as e:
            logger.error(f"License package creation error: {str(e)}")
            return None