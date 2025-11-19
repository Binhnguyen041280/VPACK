"""
VPACK Desktop Launcher
Khởi động backend + frontend và mở browser tự động
Kiến trúc giống Ollama, LM Studio, GPT4All
"""

import os
import sys
import time
import signal
import logging
import subprocess
import webbrowser
import threading
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import config
import requests

# Setup logging
def setup_logging():
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format=config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("VPACK-Launcher")

logger = setup_logging()

class VPACKLauncher:
    def __init__(self):
        self.backend_process = None
        self.frontend_process = None
        self.running = False
        self.tray_icon = None

    def ensure_directories(self):
        """Create necessary data directories"""
        dirs = [
            config.DATABASE_DIR,
            config.LOGS_DIR,
            config.OUTPUT_DIR,
            config.SESSION_DIR,
            config.INPUT_DIR,
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory: {dir_path}")

    def get_env(self):
        """Get environment variables for subprocesses"""
        env = os.environ.copy()
        env.update(config.DESKTOP_ENV)
        return env

    def start_backend(self):
        """Start Flask backend server"""
        logger.info("Starting backend server...")

        if not config.BACKEND_EXE.exists():
            # Development mode - run Python directly
            backend_dir = config.APP_DIR / "backend"
            cmd = [sys.executable, str(backend_dir / "app.py")]
            cwd = str(backend_dir)
        else:
            # Production mode - run compiled executable
            cmd = [str(config.BACKEND_EXE)]
            cwd = str(config.BACKEND_EXE.parent)

        logger.info(f"Backend command: {' '.join(cmd)}")

        self.backend_process = subprocess.Popen(
            cmd,
            env=self.get_env(),
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )

        # Log backend output in background
        threading.Thread(
            target=self._log_output,
            args=(self.backend_process, "Backend"),
            daemon=True
        ).start()

        return self.wait_for_backend()

    def start_frontend(self):
        """Start Next.js frontend server"""
        logger.info("Starting frontend server...")

        frontend_dir = config.APP_DIR / "frontend"

        if config.NODE_EXE.exists() and config.FRONTEND_SERVER.exists():
            # Production mode - use bundled Node.js
            cmd = [str(config.NODE_EXE), str(config.FRONTEND_SERVER)]
            cwd = str(config.FRONTEND_SERVER.parent)
        else:
            # Development mode - use npm
            if sys.platform == "win32":
                cmd = ["cmd", "/c", "npm", "start"]
            else:
                cmd = ["npm", "start"]
            cwd = str(frontend_dir)

        env = self.get_env()
        env["PORT"] = str(config.FRONTEND_PORT)
        env["NEXT_PUBLIC_API_URL"] = config.BACKEND_URL

        logger.info(f"Frontend command: {' '.join(cmd)}")

        self.frontend_process = subprocess.Popen(
            cmd,
            env=env,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )

        # Log frontend output in background
        threading.Thread(
            target=self._log_output,
            args=(self.frontend_process, "Frontend"),
            daemon=True
        ).start()

        return self.wait_for_frontend()

    def _log_output(self, process, name):
        """Log subprocess output"""
        for line in iter(process.stdout.readline, b''):
            try:
                text = line.decode('utf-8', errors='ignore').strip()
                if text:
                    logger.debug(f"[{name}] {text}")
            except:
                pass

    def wait_for_backend(self):
        """Wait for backend to be ready"""
        logger.info(f"Waiting for backend at {config.HEALTH_CHECK_URL}...")

        start_time = time.time()
        while time.time() - start_time < config.BACKEND_STARTUP_TIMEOUT:
            try:
                response = requests.get(config.HEALTH_CHECK_URL, timeout=2)
                if response.status_code == 200:
                    logger.info("Backend is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass

            # Check if process died
            if self.backend_process.poll() is not None:
                logger.error("Backend process died unexpectedly")
                return False

            time.sleep(config.HEALTH_CHECK_INTERVAL)

        logger.error("Backend startup timeout")
        return False

    def wait_for_frontend(self):
        """Wait for frontend to be ready"""
        logger.info(f"Waiting for frontend at {config.FRONTEND_URL}...")

        start_time = time.time()
        while time.time() - start_time < config.FRONTEND_STARTUP_TIMEOUT:
            try:
                response = requests.get(config.FRONTEND_URL, timeout=2)
                if response.status_code == 200:
                    logger.info("Frontend is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass

            # Check if process died
            if self.frontend_process.poll() is not None:
                logger.error("Frontend process died unexpectedly")
                return False

            time.sleep(config.HEALTH_CHECK_INTERVAL)

        logger.error("Frontend startup timeout")
        return False

    def open_browser(self):
        """Open default browser to frontend URL"""
        logger.info(f"Opening browser at {config.FRONTEND_URL}")
        webbrowser.open(config.FRONTEND_URL)

    def setup_tray(self):
        """Setup system tray icon (optional)"""
        try:
            import pystray
            from PIL import Image

            # Load or create icon
            if config.TRAY_ICON.exists():
                icon_image = Image.open(config.TRAY_ICON)
            else:
                # Create simple icon
                icon_image = Image.new('RGB', (64, 64), color='blue')

            def on_open(icon, item):
                self.open_browser()

            def on_quit(icon, item):
                self.shutdown()
                icon.stop()

            menu = pystray.Menu(
                pystray.MenuItem("Open VPACK", on_open, default=True),
                pystray.MenuItem("Quit", on_quit)
            )

            self.tray_icon = pystray.Icon(
                config.APP_NAME,
                icon_image,
                config.TRAY_TOOLTIP,
                menu
            )

            # Run tray in background thread
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
            logger.info("System tray icon created")

        except ImportError:
            logger.warning("pystray not available, running without tray icon")
        except Exception as e:
            logger.warning(f"Could not create tray icon: {e}")

    def shutdown(self):
        """Gracefully shutdown all processes"""
        logger.info("Shutting down VPACK...")
        self.running = False

        if self.frontend_process:
            logger.info("Stopping frontend...")
            self.frontend_process.terminate()
            try:
                self.frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()

        if self.backend_process:
            logger.info("Stopping backend...")
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()

        logger.info("VPACK shutdown complete")

    def run(self):
        """Main entry point"""
        logger.info(f"Starting {config.APP_NAME} v{config.APP_VERSION}")
        logger.info(f"App directory: {config.APP_DIR}")
        logger.info(f"Data directory: {config.DATA_DIR}")

        # Setup signal handlers
        signal.signal(signal.SIGINT, lambda s, f: self.shutdown())
        signal.signal(signal.SIGTERM, lambda s, f: self.shutdown())

        try:
            # Ensure directories exist
            self.ensure_directories()

            # Start backend
            if not self.start_backend():
                logger.error("Failed to start backend")
                self.shutdown()
                return 1

            # Start frontend
            if not self.start_frontend():
                logger.error("Failed to start frontend")
                self.shutdown()
                return 1

            # Open browser
            self.open_browser()

            # Setup tray icon
            self.setup_tray()

            # Keep running
            self.running = True
            logger.info("VPACK is running. Press Ctrl+C to stop.")

            while self.running:
                # Check if processes are still running
                if self.backend_process.poll() is not None:
                    logger.error("Backend process died")
                    break
                if self.frontend_process.poll() is not None:
                    logger.error("Frontend process died")
                    break
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error: {e}")
            return 1
        finally:
            self.shutdown()

        return 0


def main():
    launcher = VPACKLauncher()
    sys.exit(launcher.run())


if __name__ == "__main__":
    main()
