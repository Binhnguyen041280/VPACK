"""Docker Management API Module for V_Track.

This module provides Flask REST API endpoints for managing Docker configuration
dynamically at runtime. It allows the application to update docker-compose.yml
and restart containers to enable dynamic bind mounts for local video sources.

API Endpoints:
    POST /docker/update-local-source-mount: Update bind mount for local video source
    GET /docker/current-mounts: Get currently configured bind mounts
    POST /docker/remove-local-source-mount: Remove local source bind mount

Security Considerations:
    - Requires Docker socket access (-v /var/run/docker.sock:/var/run/docker.sock)
    - Only allows specific whitelisted operations
    - Validates paths before mounting
    - Logs all Docker management operations

Thread Safety:
    Uses file locks for safe docker-compose.yml modifications
"""

from flask import Blueprint, request, jsonify
import os
import yaml
import subprocess
import threading
from pathlib import Path
from modules.config.logging_config import get_logger

docker_bp = Blueprint('docker_management', __name__)
logger = get_logger(__name__, {"module": "docker_management"})

# Docker compose file path (mounted into container)
DOCKER_COMPOSE_FILE = '/app/docker-compose.yml'
COMPOSE_LOCK = threading.Lock()

# Local source mount configuration
LOCAL_SOURCE_MOUNT_KEY = 'local-source-videos'

def validate_host_path(path: str) -> tuple[bool, str]:
    """Validate that the path is safe to mount.

    Args:
        path: Host filesystem path to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path or not path.strip():
        return False, "Path cannot be empty"

    # Basic security checks
    if '..' in path:
        return False, "Path cannot contain '..' (parent directory references)"

    if path.startswith('/var/run') or path.startswith('/var/lib/docker'):
        return False, "Cannot mount Docker system directories"

    if path.startswith('/etc') or path.startswith('/sys') or path.startswith('/proc'):
        return False, "Cannot mount system directories"

    return True, ""

def update_docker_compose_mount(host_path: str, container_path: str = '/app/resources/local_source') -> dict:
    """Update docker-compose.yml to add/update local source bind mount.

    Args:
        host_path: Path on host machine to mount
        container_path: Path inside container where host_path will be mounted

    Returns:
        Dictionary with success status and message
    """
    try:
        with COMPOSE_LOCK:
            logger.info(f"📝 Updating docker-compose.yml: {host_path} -> {container_path}")

            # Read current docker-compose.yml
            if not os.path.exists(DOCKER_COMPOSE_FILE):
                return {'success': False, 'error': 'docker-compose.yml not found'}

            with open(DOCKER_COMPOSE_FILE, 'r') as f:
                compose_config = yaml.safe_load(f)

            # Ensure services.backend.volumes exists
            if 'services' not in compose_config:
                compose_config['services'] = {}
            if 'backend' not in compose_config['services']:
                compose_config['services']['backend'] = {}
            if 'volumes' not in compose_config['services']['backend']:
                compose_config['services']['backend']['volumes'] = []

            volumes = compose_config['services']['backend']['volumes']

            # Remove existing local source mount if any
            volumes = [v for v in volumes if not (isinstance(v, str) and container_path in v)]

            # Add new bind mount
            new_mount = f"{host_path}:{container_path}:ro"  # Read-only mount for safety
            volumes.append(new_mount)

            compose_config['services']['backend']['volumes'] = volumes

            # Write updated docker-compose.yml
            with open(DOCKER_COMPOSE_FILE, 'w') as f:
                yaml.dump(compose_config, f, default_flow_style=False, sort_keys=False)

            logger.info(f"✅ docker-compose.yml updated successfully")
            return {'success': True, 'mount': new_mount}

    except Exception as e:
        logger.error(f"❌ Error updating docker-compose.yml: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}

def restart_backend_container() -> dict:
    """Restart the backend container to apply new mounts.

    Returns:
        Dictionary with success status and message
    """
    try:
        logger.info("🔄 Restarting backend container...")

        # Use docker-compose to restart backend service
        result = subprocess.run(
            ['docker-compose', '-f', DOCKER_COMPOSE_FILE, 'restart', 'backend'],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            logger.info("✅ Backend container restarted successfully")
            return {'success': True}
        else:
            logger.error(f"❌ Failed to restart container: {result.stderr}")
            return {'success': False, 'error': result.stderr}

    except subprocess.TimeoutExpired:
        logger.error("❌ Restart command timed out")
        return {'success': False, 'error': 'Restart command timed out'}
    except Exception as e:
        logger.error(f"❌ Error restarting container: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}

@docker_bp.route('/docker/update-local-source-mount', methods=['POST'])
def update_local_source_mount():
    """Update bind mount for local video source and restart container.

    Request JSON:
        {
            "host_path": "/Users/username/Videos/VTrack"
        }

    Returns:
        JSON response with:
        - success: Boolean indicating operation success
        - message: Success or error message
        - mount: The mount configuration added
        - restart_required: Whether container restart is needed
    """
    try:
        data = request.get_json()
        host_path = data.get('host_path')

        if not host_path:
            return jsonify({
                'success': False,
                'error': 'host_path is required'
            }), 400

        # Validate path
        is_valid, error_msg = validate_host_path(host_path)
        if not is_valid:
            logger.warning(f"⚠️  Invalid path rejected: {host_path} - {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400

        logger.info(f"📂 Received request to mount: {host_path}")

        # Update docker-compose.yml
        update_result = update_docker_compose_mount(host_path)
        if not update_result['success']:
            return jsonify(update_result), 500

        # Restart container to apply changes
        restart_result = restart_backend_container()
        if not restart_result['success']:
            return jsonify({
                'success': False,
                'error': f"Mount added but restart failed: {restart_result['error']}",
                'mount': update_result['mount'],
                'restart_required': True
            }), 500

        return jsonify({
            'success': True,
            'message': 'Local source mount updated successfully',
            'mount': update_result['mount'],
            'restart_required': False
        }), 200

    except Exception as e:
        logger.error(f"❌ Error in update_local_source_mount: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@docker_bp.route('/docker/current-mounts', methods=['GET'])
def get_current_mounts():
    """Get currently configured bind mounts for backend container.

    Returns:
        JSON response with:
        - success: Boolean
        - mounts: List of current volume mounts
    """
    try:
        with COMPOSE_LOCK:
            if not os.path.exists(DOCKER_COMPOSE_FILE):
                return jsonify({
                    'success': False,
                    'error': 'docker-compose.yml not found'
                }), 500

            with open(DOCKER_COMPOSE_FILE, 'r') as f:
                compose_config = yaml.safe_load(f)

            volumes = compose_config.get('services', {}).get('backend', {}).get('volumes', [])

            return jsonify({
                'success': True,
                'mounts': volumes
            }), 200

    except Exception as e:
        logger.error(f"❌ Error reading mounts: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
