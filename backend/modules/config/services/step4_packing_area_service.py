"""
Step 4 Packing Area Service Layer for V.PACK Configuration.

Wrapper service for existing packing area/ROI detection logic.
Uses existing packing_profiles table and hand detection functions.
"""

import json
from typing import Dict, Any, Tuple, Optional, List
from ..shared import (
    safe_connection_wrapper,
    validate_packing_area_config,
    sanitize_input,
    log_step_operation
)


class Step4PackingAreaService:
    """Service class for Step 4 Packing Area configuration operations."""
    
    def get_packing_area_config(self) -> Dict[str, Any]:
        """
        Get current packing area configuration from packing_profiles table.
        
        Returns:
            Dict containing current packing area configuration
        """
        try:
            with safe_connection_wrapper() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT profile_name, qr_trigger_area, packing_area
                    FROM packing_profiles
                    ORDER BY id
                """)
                
                rows = cursor.fetchall()
                
                detection_zones = []
                configured_cameras = []
                
                for row in rows:
                    profile_name, qr_trigger_area, packing_area = row

                    # Parse JSON coordinates (handle null/empty values)
                    try:
                        trigger_area = json.loads(qr_trigger_area) if qr_trigger_area else [0, 0, 0, 0]
                        packing_coords = json.loads(packing_area) if packing_area else [0, 0, 0, 0]
                    except json.JSONDecodeError:
                        trigger_area = [0, 0, 0, 0]
                        packing_coords = [0, 0, 0, 0]

                    zone = {
                        "camera_name": profile_name,
                        "packing_area": packing_coords,
                        "trigger_area": trigger_area
                    }
                    
                    detection_zones.append(zone)
                    configured_cameras.append(profile_name)
                
                config = {
                    "detection_zones": detection_zones,
                    "configured_cameras": configured_cameras,
                    "zone_count": len(detection_zones)
                }
                
                log_step_operation("4", "get_packing_area", {"zone_count": len(detection_zones)})
                return config
                
        except Exception as e:
            log_step_operation("4", "get_packing_area", {"error": str(e)}, False)
            
            # Return safe defaults on error
            return {
                "detection_zones": [],
                "configured_cameras": [],
                "zone_count": 0,
                "error": str(e)
            }
    
    def update_packing_area_config(self, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Update packing area configuration using existing packing_profiles logic.
        
        Args:
            data: Packing area configuration data
            
        Returns:
            Tuple of (success: bool, result_data: dict)
        """
        try:
            # Validate input data
            is_valid, validation_error = validate_packing_area_config(data)
            if not is_valid:
                return False, {"error": validation_error}
            
            detection_zones = data.get('detection_zones', [])
            
            updated_zones = []
            
            with safe_connection_wrapper() as conn:
                cursor = conn.cursor()
                
                for zone in detection_zones:
                    camera_name = sanitize_input(zone.get('camera_name', ''), 100)
                    packing_area = zone.get('packing_area', [0, 0, 0, 0])
                    trigger_area = zone.get('trigger_area', [0, 0, 0, 0])

                    # Check if profile exists
                    cursor.execute("SELECT 1 FROM packing_profiles WHERE profile_name = ?", (camera_name,))
                    exists = cursor.fetchone()

                    if exists:
                        # Update existing profile using the same pattern as roi_bp.py
                        cursor.execute('''
                            UPDATE packing_profiles
                            SET qr_trigger_area = ?, packing_area = ?
                            WHERE profile_name = ?
                        ''', (
                            json.dumps(trigger_area),
                            json.dumps(packing_area),
                            camera_name
                        ))
                    else:
                        # Insert new profile with default values matching roi_bp.py
                        cursor.execute('''
                            INSERT INTO packing_profiles (
                                profile_name, qr_trigger_area, packing_area,
                                min_packing_time, jump_time_ratio, scan_mode, fixed_threshold, margin,
                                additional_params, mvd_jump_ratio
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            camera_name,
                            json.dumps(trigger_area),
                            json.dumps(packing_area),
                            10,    # min_packing_time
                            0.5,   # jump_time_ratio
                            "full", # scan_mode
                            20,    # fixed_threshold
                            60,    # margin
                            json.dumps({}), # additional_params
                            None   # mvd_jump_ratio
                        ))

                    updated_zones.append({
                        "camera_name": camera_name,
                        "packing_area": packing_area,
                        "trigger_area": trigger_area,
                        "action": "updated" if exists else "created"
                    })
                
                conn.commit()
            
            result = {
                "detection_zones": updated_zones,
                "zone_count": len(updated_zones),
                "configured_cameras": [zone["camera_name"] for zone in updated_zones],
                "changed": True
            }
            
            log_step_operation("4", "update_packing_area", {
                "zone_count": len(updated_zones),
                "cameras": [zone["camera_name"] for zone in updated_zones]
            })
            
            return True, result
            
        except Exception as e:
            log_step_operation("4", "update_packing_area", {"error": str(e)}, False)
            return False, {"error": f"Failed to update packing area configuration: {str(e)}"}
    
    def get_camera_packing_profile(self, camera_name: str) -> Dict[str, Any]:
        """
        Get packing profile for a specific camera.
        
        Args:
            camera_name: Name of the camera
            
        Returns:
            Dict with camera packing profile data
        """
        try:
            with safe_connection_wrapper() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT profile_name, qr_trigger_area, packing_area,
                           min_packing_time, jump_time_ratio, scan_mode, fixed_threshold, margin
                    FROM packing_profiles WHERE profile_name = ?
                """, (camera_name,))

                row = cursor.fetchone()

                if row:
                    profile_name, qr_trigger_area, packing_area, \
                    min_packing_time, jump_time_ratio, scan_mode, fixed_threshold, margin = row

                    # Parse JSON coordinates
                    try:
                        trigger_area = json.loads(qr_trigger_area) if qr_trigger_area else [0, 0, 0, 0]
                        packing_coords = json.loads(packing_area) if packing_area else [0, 0, 0, 0]
                    except json.JSONDecodeError:
                        trigger_area = [0, 0, 0, 0]
                        packing_coords = [0, 0, 0, 0]

                    return {
                        "camera_name": profile_name,
                        "packing_area": packing_coords,
                        "trigger_area": trigger_area,
                        "settings": {
                            "min_packing_time": min_packing_time,
                            "jump_time_ratio": jump_time_ratio,
                            "scan_mode": scan_mode,
                            "fixed_threshold": fixed_threshold,
                            "margin": margin
                        },
                        "exists": True
                    }
                else:
                    return {
                        "camera_name": camera_name,
                        "packing_area": [0, 0, 0, 0],
                        "trigger_area": [0, 0, 0, 0],
                        "settings": {},
                        "exists": False
                    }
                    
        except Exception as e:
            return {
                "camera_name": camera_name,
                "error": str(e),
                "exists": False
            }
    
    def call_existing_roi_selection(self, video_path: str, camera_id: str, step: str = "packing") -> Dict[str, Any]:
        """
        Call existing ROI selection logic from hand detection module.
        
        Args:
            video_path: Path to video file for ROI selection
            camera_id: Camera identifier
            step: ROI selection step (default: "packing")
            
        Returns:
            Dict with ROI selection result
        """
        try:
            # Import and call existing select_roi function
            from modules.technician.hand_detection import select_roi
            
            result = select_roi(video_path, camera_id, step)
            
            log_step_operation("4", "roi_selection", {
                "camera_id": camera_id,
                "step": step,
                "success": result.get("success", False)
            })
            
            return result
            
        except ImportError as e:
            error_msg = f"Hand detection module not available: {str(e)}"
            log_step_operation("4", "roi_selection", {"error": error_msg}, False)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"ROI selection failed: {str(e)}"
            log_step_operation("4", "roi_selection", {"error": error_msg}, False)
            return {"success": False, "error": error_msg}
    
    def call_existing_roi_finalization(self, video_path: str, camera_id: str, rois: List[Dict]) -> Dict[str, Any]:
        """
        Call existing ROI finalization logic from hand detection module.
        
        Args:
            video_path: Path to video file
            camera_id: Camera identifier
            rois: List of ROI data
            
        Returns:
            Dict with finalization result
        """
        try:
            # Import and call existing finalize_roi function
            from modules.technician.hand_detection import finalize_roi
            
            result = finalize_roi(video_path, camera_id, rois)
            
            log_step_operation("4", "roi_finalization", {
                "camera_id": camera_id,
                "roi_count": len(rois),
                "success": result.get("success", False) if isinstance(result, dict) else True
            })
            
            # Wrap result if needed
            if not isinstance(result, dict):
                return {"success": True, "message": "ROI finalized successfully"}
            
            return result
            
        except ImportError as e:
            error_msg = f"Hand detection module not available: {str(e)}"
            log_step_operation("4", "roi_finalization", {"error": error_msg}, False)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"ROI finalization failed: {str(e)}"
            log_step_operation("4", "roi_finalization", {"error": error_msg}, False)
            return {"success": False, "error": error_msg}

    def get_all_cameras_roi_status(self) -> Dict[str, Any]:
        """
        Get ROI configuration status for all cameras.
        Matches cameras from camera_configurations with packing_profiles.

        Returns:
            Dict containing cameras list with their ROI status:
            {
                "cameras": [
                    {"camera_name": "Cam1", "has_roi": true, "profile_name": "..."},
                    {"camera_name": "Cam2", "has_roi": false}
                ]
            }
        """
        try:
            with safe_connection_wrapper() as conn:
                cursor = conn.cursor()

                # Get all cameras from camera_configurations
                cursor.execute("""
                    SELECT DISTINCT camera_name
                    FROM camera_configurations
                    WHERE is_selected = 1
                    ORDER BY camera_name
                """)

                all_cameras = [row[0] for row in cursor.fetchall()]

                # Get cameras with ROI config from packing_profiles
                # profile_name format: "CameraName_YYYYMMDD_HHMMSS"
                cursor.execute("""
                    SELECT profile_name
                    FROM packing_profiles
                    WHERE packing_area IS NOT NULL
                """)

                configured_profiles = cursor.fetchall()

                # Map camera names to their profiles
                camera_status = []
                for camera_name in all_cameras:
                    # Find matching profile (exact match - no timestamp)
                    matching_profile = None
                    for (profile_name,) in configured_profiles:
                        if profile_name == camera_name:
                            matching_profile = profile_name
                            break

                    camera_status.append({
                        "camera_name": camera_name,
                        "has_roi": matching_profile is not None,
                        "profile_name": matching_profile if matching_profile else None
                    })

                result = {
                    "cameras": camera_status,
                    "total": len(camera_status),
                    "configured": len([c for c in camera_status if c["has_roi"]])
                }

                log_step_operation("4", "get_all_cameras_roi_status", {
                    "total": result["total"],
                    "configured": result["configured"]
                })

                return result

        except Exception as e:
            log_step_operation("4", "get_all_cameras_roi_status", {"error": str(e)}, False)
            return {
                "cameras": [],
                "total": 0,
                "configured": 0,
                "error": str(e)
            }


# Create singleton instance for import
step4_packing_area_service = Step4PackingAreaService()