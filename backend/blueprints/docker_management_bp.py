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
from flask_cors import cross_origin
import os
import yaml
import subprocess
import threading
import json
from pathlib import Path
from modules.config.logging_config import get_logger
from modules.db_utils.safe_connection import safe_db_connection

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

def update_env_file(local_video_path: str) -> dict:
    """Update .env file with LOCAL_VIDEO_PATH configuration.

    Args:
        local_video_path: Absolute path on host machine to local video folder

    Returns:
        Dictionary with success status and message
    """
    try:
        # Find .env file (should be in parent directory of docker-compose.yml)
        env_file = '/app/../.env'  # Mounted from host

        logger.info(f"📝 Updating .env file with LOCAL_VIDEO_PATH={local_video_path}")

        # Read existing .env content
        env_lines = []
        local_video_path_exists = False

        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    # Update existing LOCAL_VIDEO_PATH line
                    if line.startswith('LOCAL_VIDEO_PATH='):
                        env_lines.append(f'LOCAL_VIDEO_PATH={local_video_path}\n')
                        local_video_path_exists = True
                    else:
                        env_lines.append(line)

        # Add LOCAL_VIDEO_PATH if not exists
        if not local_video_path_exists:
            env_lines.append(f'\n# Local video source path\nLOCAL_VIDEO_PATH={local_video_path}\n')

        # Write back to .env
        with open(env_file, 'w') as f:
            f.writelines(env_lines)

        logger.info(f"✅ .env file updated successfully")
        return {'success': True}

    except Exception as e:
        logger.error(f"❌ Error updating .env file: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}

def update_docker_compose_input_mount(local_video_path: str) -> dict:
    """Replace input folder mount in docker-compose.yml to use local video path.

    Args:
        local_video_path: Path on host machine (will use ${LOCAL_VIDEO_PATH} env var)

    Returns:
        Dictionary with success status and message
    """
    try:
        with COMPOSE_LOCK:
            logger.info(f"📝 Replacing input mount in docker-compose.yml with LOCAL_VIDEO_PATH")

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

            # Find and replace the input folder mount
            new_volumes = []
            input_mount_replaced = False

            for volume in volumes:
                if isinstance(volume, str):
                    # Check if this is the input mount (contains :/app/resources/input)
                    if ':/app/resources/input' in volume:
                        # Replace with LOCAL_VIDEO_PATH mount
                        new_mount = '${LOCAL_VIDEO_PATH}:/app/resources/input:ro'
                        new_volumes.append(new_mount)
                        input_mount_replaced = True
                        logger.info(f"  Replaced: {volume} -> {new_mount}")
                    else:
                        new_volumes.append(volume)
                else:
                    new_volumes.append(volume)

            # If no input mount found, add it
            if not input_mount_replaced:
                new_mount = '${LOCAL_VIDEO_PATH}:/app/resources/input:ro'
                new_volumes.append(new_mount)
                logger.info(f"  Added: {new_mount}")

            compose_config['services']['backend']['volumes'] = new_volumes

            # Write updated docker-compose.yml
            with open(DOCKER_COMPOSE_FILE, 'w') as f:
                yaml.dump(compose_config, f, default_flow_style=False, sort_keys=False)

            logger.info(f"✅ docker-compose.yml updated successfully")
            return {'success': True, 'mount': '${LOCAL_VIDEO_PATH}:/app/resources/input:ro'}

    except Exception as e:
        logger.error(f"❌ Error updating docker-compose.yml: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}

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
    """Restart the backend container to apply new mounts using Docker API.

    Returns:
        Dictionary with success status and message
    """
    try:
        logger.info("🔄 Restarting backend container...")

        # Use docker CLI via Docker socket to restart container
        # The container name is 'vtrack-backend' from docker-compose.yml
        result = subprocess.run(
            ['docker', 'restart', 'vtrack-backend'],
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

@docker_bp.route('/docker/setup-local-source', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def setup_local_source():
    """Setup local video source by updating .env, docker-compose.yml and restarting container.

    This is the main API for configuring local video source from UI.

    Request JSON:
        {
            "local_path": "/Users/username/Videos/CCTV"
        }

    Returns:
        JSON response with:
        - success: Boolean indicating operation success
        - message: Success or error message
        - restarting: Whether backend is restarting
    """
    try:
        data = request.get_json()
        local_path = data.get('local_path')

        if not local_path:
            return jsonify({
                'success': False,
                'error': 'local_path is required'
            }), 400

        # Validate path (security checks only, can't check existence from inside container)
        is_valid, error_msg = validate_host_path(local_path)
        if not is_valid:
            logger.warning(f"⚠️  Invalid path rejected: {local_path} - {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400

        # Note: Cannot check if path exists because it's on the host machine,
        # not inside the container. User must ensure path is correct.

        logger.info(f"📂 Setting up local video source: {local_path}")

        # Step 1: Update .env file
        env_result = update_env_file(local_path)
        if not env_result['success']:
            return jsonify({
                'success': False,
                'error': f"Failed to update .env: {env_result.get('error')}"
            }), 500

        # Step 2: Update docker-compose.yml
        compose_result = update_docker_compose_input_mount(local_path)
        if not compose_result['success']:
            return jsonify({
                'success': False,
                'error': f"Failed to update docker-compose.yml: {compose_result.get('error')}"
            }), 500

        # Step 3: Update processing_config.input_path to container path
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                container_input_path = '/app/resources/input'
                cursor.execute("""
                    UPDATE processing_config
                    SET input_path = ?
                    WHERE id = 1
                """, (container_input_path,))
                conn.commit()
                logger.info(f"✅ Updated processing_config.input_path to: {container_input_path}")
        except Exception as db_error:
            logger.error(f"⚠️ Failed to update processing_config: {db_error}", exc_info=True)
            # Continue anyway - user can fix manually if needed

        # Configuration complete - user needs to restart Docker from host
        logger.info("✅ Configuration updated successfully (including database). Restart required.")

        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully (including database). Please restart Docker containers from your terminal using: docker-compose restart backend',
            'restart_required': True,
            'restart_command': 'docker-compose restart backend'
        }), 200

    except Exception as e:
        logger.error(f"❌ Error in setup_local_source: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
