"""
UI components for license management - NON-BLOCKING VERSION
"""
import logging
from typing import Dict, Any, Optional
import threading
import queue
import time

logger = logging.getLogger(__name__)

class LicenseUI:
    """Non-blocking UI components for license management"""
    
    @staticmethod
    def show_license_input_dialog() -> Optional[str]:
        """Non-blocking license key input - returns None immediately"""
        logger.warning("License key required - please visit web interface at /payment")
        logger.info("License input dialog bypassed to prevent blocking")
        return None
    
    @staticmethod
    def show_license_input_dialog_async(callback=None) -> None:
        """Async license key input dialog with callback"""
        def ui_worker():
            try:
                import tkinter as tk
                from tkinter import simpledialog
                
                # Create root window
                root = tk.Tk()
                root.withdraw()  # Hide main window
                root.attributes('-topmost', True)  # Bring to front
                
                # Show dialog
                license_key = simpledialog.askstring(
                    title="ePACK License",
                    prompt="Enter your license key:",
                    parent=root
                )
                
                root.destroy()
                
                # Call callback if provided
                if callback:
                    callback(license_key)
                    
                return license_key
                
            except Exception as e:
                logger.error(f"Async license input dialog failed: {e}")
                if callback:
                    callback(None)
                return None
        
        # Run in separate thread
        thread = threading.Thread(target=ui_worker, daemon=True, name="LicenseUIDialog")
        thread.start()
    
    @staticmethod
    def show_license_status(license_data: Dict[str, Any]):
        """Show license status without blocking"""
        try:
            expires_at = license_data.get('expires_at', 'Never')
            package_name = license_data.get('package_name', 'Desktop License')
            
            message = f"""License Status: Active
Package: {package_name}
Expires: {expires_at[:10] if expires_at != 'Never' else 'Never'}
Features: Full Access"""
            
            logger.info(f"License Status: {message.replace(chr(10), ' | ')}")
            
        except Exception as e:
            logger.error(f"License status display failed: {e}")
    
    @staticmethod
    def show_expiry_warning(days_remaining: int) -> bool:
        """Show license expiry warning - non-blocking version"""
        message = f"License expires in {days_remaining} days - please renew at /payment"
        logger.warning(message)
        return False  # Don't block for renewal
    
    @staticmethod
    def show_expiry_warning_async(days_remaining: int, callback=None) -> None:
        """Async expiry warning with user choice"""
        def ui_worker():
            try:
                import tkinter as tk
                from tkinter import messagebox
                
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                
                message = f"""License Expiring Soon!

Your license will expire in {days_remaining} days.
Please renew to avoid interruption.

Would you like to renew now?"""
                
                result = messagebox.askyesno("License Expiry Warning", message, parent=root)
                root.destroy()
                
                if callback:
                    callback(result)
                    
                return result
                
            except Exception as e:
                logger.error(f"Async expiry warning failed: {e}")
                if callback:
                    callback(False)
                return False
        
        thread = threading.Thread(target=ui_worker, daemon=True, name="LicenseExpiryWarning")
        thread.start()
    
    @staticmethod
    def show_error_dialog(error_message: str):
        """Show license error - non-blocking version"""
        logger.error(f"License Error: {error_message}")
    
    @staticmethod
    def show_error_dialog_async(error_message: str, callback=None) -> None:
        """Async error dialog"""
        def ui_worker():
            try:
                import tkinter as tk
                from tkinter import messagebox
                
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                
                messagebox.showerror("License Error", error_message, parent=root)
                root.destroy()
                
                if callback:
                    callback(True)
                    
            except Exception as e:
                logger.error(f"Async error dialog failed: {e}")
                if callback:
                    callback(False)
        
        thread = threading.Thread(target=ui_worker, daemon=True, name="LicenseErrorDialog")
        thread.start()

class LicenseUIManager:
    """Manager for handling license UI operations with queue"""
    
    def __init__(self):
        self.ui_queue = queue.Queue()
        self.running = True
        self.ui_thread = None
        
    def start(self):
        """Start UI manager thread"""
        if self.ui_thread is None or not self.ui_thread.is_alive():
            self.running = True
            self.ui_thread = threading.Thread(target=self._ui_worker, daemon=True, name="LicenseUIManager")
            self.ui_thread.start()
            logger.info("License UI Manager started")
    
    def stop(self):
        """Stop UI manager"""
        self.running = False
        try:
            self.ui_queue.put(('stop', None), timeout=1)
        except queue.Full:
            pass
        logger.info("License UI Manager stopped")
    
    def _ui_worker(self):
        """UI worker thread - processes UI requests"""
        while self.running:
            try:
                # Wait for UI requests
                item = self.ui_queue.get(timeout=1)
                if item is None:
                    continue
                    
                action, data = item
                
                if action == 'stop':
                    break
                elif action == 'license_input':
                    self._handle_license_input(data)
                elif action == 'expiry_warning':
                    self._handle_expiry_warning(data)
                elif action == 'error_dialog':
                    self._handle_error_dialog(data)
                    
                self.ui_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"UI worker error: {e}")
    
    def _handle_license_input(self, data):
        """Handle license input request"""
        callback = data.get('callback')
        LicenseUI.show_license_input_dialog_async(callback)
    
    def _handle_expiry_warning(self, data):
        """Handle expiry warning request"""
        days_remaining = data.get('days_remaining', 0)
        callback = data.get('callback')
        LicenseUI.show_expiry_warning_async(days_remaining, callback)
    
    def _handle_error_dialog(self, data):
        """Handle error dialog request"""
        error_message = data.get('error_message', 'Unknown error')
        callback = data.get('callback')
        LicenseUI.show_error_dialog_async(error_message, callback)
    
    def request_license_input(self, callback=None):
        """Request license input dialog"""
        try:
            self.ui_queue.put(('license_input', {'callback': callback}), timeout=1)
        except queue.Full:
            logger.warning("UI queue full - skipping license input request")
    
    def request_expiry_warning(self, days_remaining: int, callback=None):
        """Request expiry warning dialog"""
        try:
            self.ui_queue.put(('expiry_warning', {
                'days_remaining': days_remaining,
                'callback': callback
            }), timeout=1)
        except queue.Full:
            logger.warning("UI queue full - skipping expiry warning")
    
    def request_error_dialog(self, error_message: str, callback=None):
        """Request error dialog"""
        try:
            self.ui_queue.put(('error_dialog', {
                'error_message': error_message,
                'callback': callback
            }), timeout=1)
        except queue.Full:
            logger.warning("UI queue full - skipping error dialog")

# Global UI manager instance
ui_manager = LicenseUIManager()

def get_ui_manager():
    """Get global UI manager instance"""
    return ui_manager