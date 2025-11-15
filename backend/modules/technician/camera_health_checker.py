"""
Camera Health Check Module
Compares current QR detection success rate against baseline
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import cv2
import numpy as np
from modules.db_utils.safe_connection import safe_db_connection
from modules.technician.qr_detector import detect_qr_at_time

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

HEALTH_CHECK_CONFIG = {
    "sample_duration_sec": 3.0,
    "interval_fps": 5,
    "total_frames": 15,
    "qr_target_text": "TimeGo",
}

# Status thresholds - FINAL CONFIRMED
POSITION_OFFSET_THRESHOLDS = {
    "OK": 0.10,  # < 10% of ROI diagonal
    "CAUTION": 0.20,  # 10-20% of ROI diagonal
    "CRITICAL": 1.00,  # > 20% of ROI diagonal
}

QR_READABLE_THRESHOLDS = {
    "OK": 0.85,  # >= 85% success rate
    "CAUTION": 0.70,  # 70-84% success rate
    "CRITICAL": 0.0,  # < 70% success rate
}


def get_baseline_by_camera(camera_name: str) -> Optional[Dict]:
    """Get active baseline for a camera"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, baseline_success_rate, baseline_success_rate_pct,
                       baseline_sample_start_sec, trigger_roi, qr_trigger_bbox
                FROM camera_baseline_samples
                WHERE camera_name = ? AND status = 'active'
                LIMIT 1
            """,
                (camera_name,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            return {
                "id": row[0],
                "baseline_success_rate": row[1],
                "baseline_success_rate_pct": row[2],
                "baseline_sample_start_sec": row[3],
                "trigger_roi": json.loads(row[4]),
                "qr_trigger_bbox": json.loads(row[5]) if row[5] else None,
            }
    except Exception as e:
        logger.error(f"[HEALTH] Error getting baseline: {e}")
        return None


def get_qr_trigger_area(camera_name: str) -> Optional[Dict]:
    """
    Get actual QR trigger area from packing_profiles
    This matches the runtime detection ROI (not the old baseline ROI)

    Returns: {"x": int, "y": int, "w": int, "h": int} or None
    """
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT qr_trigger_area FROM packing_profiles
                WHERE profile_name = ?
                LIMIT 1
            """,
                (camera_name,),
            )

            row = cursor.fetchone()
            if not row or not row[0]:
                logger.warning(f"[HEALTH] No qr_trigger_area found for {camera_name}")
                return None

            # Parse qr_trigger_area from list [x, y, w, h]
            area_list = json.loads(row[0])
            if not isinstance(area_list, list) or len(area_list) != 4:
                logger.warning(
                    f"[HEALTH] Invalid qr_trigger_area format for {camera_name}: {area_list}"
                )
                return None

            # Convert to dict format: {"x": int, "y": int, "w": int, "h": int}
            trigger_roi = {
                "x": int(area_list[0]),
                "y": int(area_list[1]),
                "w": int(area_list[2]),
                "h": int(area_list[3]),
            }

            logger.info(f"[HEALTH] Using qr_trigger_area for {camera_name}: {trigger_roi}")
            return trigger_roi

    except Exception as e:
        logger.error(f"[HEALTH] Error getting qr_trigger_area: {e}")
        return None


# ❌ REMOVED: collect_diagnostic_metrics() - No longer needed
# All diagnostic metrics (blur, brightness, contrast, ink saturation, edge density, etc.) have been removed
# Health check now focuses only on: QR Success Rate + Position Offset


def run_health_check(camera_name: str, video_path: str) -> Dict:
    """
    Run health check against baseline with 2 metrics only:
    - Metric 1: QR Trigger Readable (success rate >= 85%)
    - Metric 2: Camera Position OK (QR bbox offset < 10% of ROI diagonal)

    Protocol: Same as baseline - use baseline_sample_start_sec + 3 seconds
    """

    logger.info(f"[HEALTH] Starting health check for {camera_name}")

    try:
        # Get baseline
        baseline = get_baseline_by_camera(camera_name)

        if not baseline:
            logger.warning(f"[HEALTH] No baseline found for {camera_name}")
            return {
                "success": False,
                "error": f"No baseline found for {camera_name}",
                "camera_name": camera_name,
                "status": "SKIPPED",
            }

        baseline_start = baseline["baseline_sample_start_sec"]
        baseline_rate = baseline["baseline_success_rate"]
        baseline_rate_pct = baseline["baseline_success_rate_pct"]
        baseline_qr_bbox = baseline.get("qr_trigger_bbox")  # Baseline QR position
        baseline_id = baseline["id"]

        # ✅ Get actual QR trigger area from packing_profiles (matches runtime detection)
        # This ensures health check uses the SAME ROI as the runtime process
        actual_trigger_roi = get_qr_trigger_area(camera_name)
        if actual_trigger_roi:
            trigger_roi = actual_trigger_roi
            logger.info(
                f"[HEALTH] Using actual qr_trigger_area from packing_profiles for {camera_name}"
            )
        else:
            # Fallback to baseline trigger_roi if qr_trigger_area not found
            trigger_roi = baseline["trigger_roi"]
            logger.warning(f"[HEALTH] Fallback to baseline trigger_roi for {camera_name}")

        # Calculate frame parameters
        frame_interval = 1.0 / HEALTH_CHECK_CONFIG["interval_fps"]
        total_frames = HEALTH_CHECK_CONFIG["total_frames"]

        detected_count = 0
        qr_bbox_list = []  # ← Collect QR bboxes for position tracking

        logger.info(
            f"[HEALTH] Sampling from baseline window: {baseline_start:.2f}s to {baseline_start + 3.0:.2f}s"
        )

        # Sample frames using SAME protocol as baseline
        for i in range(total_frames):
            frame_time = baseline_start + i * frame_interval

            try:
                # Detect QR at this time
                result = detect_qr_at_time(video_path, frame_time, trigger_roi)

                if result.get("success") and result.get("qr_detections"):
                    for qr_det in result["qr_detections"]:
                        if HEALTH_CHECK_CONFIG["qr_target_text"] in qr_det.get("decoded_text", ""):
                            detected_count += 1

                            # ← Extract QR bbox (position & size)
                            bbox = qr_det.get("bbox")
                            if bbox:
                                qr_bbox_list.append(bbox)
                            break

            except Exception as e:
                logger.error(f"[HEALTH] Error at {frame_time:.2f}s: {e}")

        # ===================== METRIC 1: QR READABLE =====================
        current_rate = detected_count / total_frames if total_frames > 0 else 0
        current_rate_pct = current_rate * 100

        # ✅ Compare with BASELINE (not fixed threshold)
        degradation_pct = current_rate_pct - baseline_rate_pct  # Negative = degradation

        logger.info(
            f"[HEALTH] QR Success: Baseline={baseline_rate_pct:.1f}%, Current={current_rate_pct:.1f}%, Degradation={degradation_pct:.1f}%"
        )

        # Determine QR Readable status based on degradation
        if degradation_pct >= 0:  # Better or same as baseline
            qr_readable_status = "OK"
        elif degradation_pct >= -15:  # Max 15% degradation acceptable
            qr_readable_status = "CAUTION"
        else:  # More than 15% degradation
            qr_readable_status = "CRITICAL"

        logger.info(
            f"[HEALTH] QR Readable: {degradation_pct:.1f}% degradation → {qr_readable_status}"
        )

        # ===================== METRIC 2: POSITION OFFSET =====================
        avg_qr_bbox = None
        position_offset_pct = None
        position_status = "OK"  # Default

        if qr_bbox_list and baseline_qr_bbox:
            # ✅ Detect được QR → Tính offset bình thường
            # Calculate average current QR position
            avg_qr_bbox = {
                "x": int(np.mean([b["x"] for b in qr_bbox_list])),
                "y": int(np.mean([b["y"] for b in qr_bbox_list])),
                "w": int(np.mean([b["w"] for b in qr_bbox_list])),
                "h": int(np.mean([b["h"] for b in qr_bbox_list])),
            }

            # ✅ Calculate center points from QR BBOX (not trigger ROI)
            baseline_center = (
                baseline_qr_bbox["x"] + baseline_qr_bbox["w"] / 2,
                baseline_qr_bbox["y"] + baseline_qr_bbox["h"] / 2,
            )
            current_center = (
                avg_qr_bbox["x"] + avg_qr_bbox["w"] / 2,
                avg_qr_bbox["y"] + avg_qr_bbox["h"] / 2,
            )

            # ✅ Compare with BASELINE center (not trigger ROI center)
            offset_dx = current_center[0] - baseline_center[0]
            offset_dy = current_center[1] - baseline_center[1]
            offset_distance = np.sqrt(offset_dx**2 + offset_dy**2)

            # Use ROI diagonal for percentage calculation
            roi_diagonal = np.sqrt(trigger_roi["w"] ** 2 + trigger_roi["h"] ** 2)
            position_offset_pct = (offset_distance / roi_diagonal * 100) if roi_diagonal > 0 else 0

            # Determine position status based on offset
            if position_offset_pct < 10:  # < 10% offset = OK
                position_status = "OK"
            elif position_offset_pct < 20:  # 10-20% = CAUTION
                position_status = "CAUTION"
            else:  # > 20% = CRITICAL
                position_status = "CRITICAL"

            logger.info(
                f"[HEALTH] Position: Baseline=({baseline_center[0]:.0f}, {baseline_center[1]:.0f}), Current=({current_center[0]:.0f}, {current_center[1]:.0f})"
            )
            logger.info(
                f"[HEALTH] Position Offset: {offset_distance:.1f}px ({position_offset_pct:.1f}% of ROI diagonal) → {position_status}"
            )

        else:
            # ❌ Không detect QR → Không thể check position → offset = 100% (sai hoàn toàn)
            position_offset_pct = 100.0  # ✅ 100% offset = completely wrong
            position_status = "CRITICAL"  # 100 > 20 → CRITICAL
            logger.info(f"[HEALTH] Position Offset: No QR detected → 100.0% (CRITICAL)")

        # ===================== OVERALL STATUS =====================
        # ✅ QR Readable is PRIMARY metric (controls overall status)
        # Position only affects when QR=OK + Position=CRITICAL → downgrade to CAUTION

        overall_status = qr_readable_status  # Default: follow QR status

        # Special case: QR is OK but Position is CRITICAL (camera drifted badly)
        if qr_readable_status == "OK" and position_status == "CRITICAL":
            overall_status = "CAUTION"  # Downgrade to CAUTION as warning
            logger.info(f"[HEALTH] QR is OK but Position CRITICAL → Downgrade to CAUTION")

        logger.info(
            f"[HEALTH] Overall Status: QR={qr_readable_status}, Pos={position_status} → {overall_status}"
        )

        # Save to database
        check_data = {
            "baseline_id": baseline_id,
            "camera_name": camera_name,
            "video_file": video_path,
            "current_total_frames": total_frames,
            "current_qr_detected_count": detected_count,
            "current_success_rate": current_rate,
            "current_success_rate_pct": current_rate_pct,
            "baseline_success_rate_pct": baseline_rate_pct,
            "success_rate_degradation": degradation_pct,  # Negative if degraded
            "success_rate_degradation_pct": degradation_pct,  # Same as degradation_pct
            "overall_status": overall_status,
            "qr_trigger_bbox": json.dumps(avg_qr_bbox) if avg_qr_bbox else None,
            "qr_position_offset_pct": position_offset_pct,
            "check_timestamp": datetime.now().isoformat(),
        }

        with safe_db_connection() as conn:
            cursor = conn.cursor()

            # Check if health check result already exists for this camera
            cursor.execute(
                "SELECT id FROM camera_health_check_results WHERE camera_name = ?", (camera_name,)
            )
            existing = cursor.fetchone()

            if existing:
                # UPDATE existing health check result for this camera
                logger.info(f"[HEALTH] Updating existing health check result for {camera_name}")
                check_id = existing[0]

                # Build UPDATE statement dynamically
                update_cols = ", ".join([f"{k} = ?" for k in check_data.keys()])
                values = list(check_data.values()) + [check_id]

                cursor.execute(
                    f"UPDATE camera_health_check_results SET {update_cols} WHERE id = ?", values
                )
            else:
                # INSERT new health check result only if not exists (first time)
                logger.info(f"[HEALTH] Creating new health check result for {camera_name}")
                placeholders = ", ".join(["?"] * len(check_data))
                columns = ", ".join(check_data.keys())
                cursor.execute(
                    f"INSERT INTO camera_health_check_results ({columns}) VALUES ({placeholders})",
                    tuple(check_data.values()),
                )

            conn.commit()

        logger.info(f"[HEALTH] ✅ Health check completed: {overall_status}")

        return {
            "success": True,
            "camera_name": camera_name,
            "status": overall_status,
            "check_timestamp": datetime.now().isoformat(),
            "metrics": {
                "qr_readable": {
                    "status": qr_readable_status,
                    "baseline_pct": baseline_rate_pct,
                    "current_pct": current_rate_pct,
                    "degradation_pct": degradation_pct,
                },
                "camera_position": {"status": position_status, "offset_pct": position_offset_pct},
            },
        }

    except Exception as e:
        logger.error(f"[HEALTH] ❌ Error: {e}", exc_info=True)
        return {"success": False, "error": str(e), "camera_name": camera_name, "status": "ERROR"}


def check_position_offset(detected_qr_center: tuple, trigger_roi: dict) -> Dict:
    """
    Calculate position offset as % of ROI diagonal

    Args:
        detected_qr_center: (x, y) - detected QR center position
        trigger_roi: {"x": 84, "y": 710, "w": 749, "h": 806}

    Returns:
        {
            'offset_px': float,
            'offset_pct': float,
            'roi_diagonal': float,
            'status': 'OK' / 'CAUTION' / 'CRITICAL'
        }
    """
    try:
        if not detected_qr_center or not trigger_roi:
            return {
                "offset_px": None,
                "offset_pct": None,
                "status": "CRITICAL",
                "error": "Missing position data",
            }

        # Expected center
        expected_x = trigger_roi["x"] + trigger_roi["w"] / 2
        expected_y = trigger_roi["y"] + trigger_roi["h"] / 2

        # Offset
        offset_dx = detected_qr_center[0] - expected_x
        offset_dy = detected_qr_center[1] - expected_y
        offset_distance = np.sqrt(offset_dx**2 + offset_dy**2)

        # ROI diagonal
        roi_diagonal = np.sqrt(trigger_roi["w"] ** 2 + trigger_roi["h"] ** 2)
        offset_pct = (offset_distance / roi_diagonal) if roi_diagonal > 0 else 0

        # Decision
        if offset_pct < POSITION_OFFSET_THRESHOLDS["OK"]:
            status = "OK"
        elif offset_pct < POSITION_OFFSET_THRESHOLDS["CAUTION"]:
            status = "CAUTION"
        else:
            status = "CRITICAL"

        return {
            "offset_px": float(offset_distance),
            "offset_pct": float(offset_pct * 100),  # Convert to %
            "roi_diagonal": float(roi_diagonal),
            "status": status,
        }

    except Exception as e:
        logger.error(f"[HEALTH] Error checking position: {e}")
        return {"offset_px": None, "offset_pct": None, "status": "CRITICAL", "error": str(e)}


def evaluate_camera_health_checklist(camera_name: str, video_path: str) -> Dict:
    """
    Evaluate camera health: 2-item checklist

    Item 1: QR Trigger Readable (success rate >= 85%)
    Item 2: Position Offset (< 10% of ROI diagonal)

    Returns:
        {
            'camera_name': str,
            'items': [
                {
                    'name': 'QR Trigger Readable',
                    'status': 'YES' / 'WEAK' / 'NO',
                    'success_rate_pct': float,
                    'detected': int,
                    'total': int,
                    'action': 'OK' / 'Replace QR Label'
                },
                {
                    'name': 'Camera Position OK',
                    'status': 'YES' / 'WEAK' / 'NO',
                    'offset_px': float,
                    'offset_pct': float,
                    'action': 'OK' / 'Adjust Camera'
                }
            ],
            'overall_status': 'OK' / 'CRITICAL',
            'overall_rate_pct': float (0, 50, or 100)
        }
    """

    logger.info(f"[HEALTH] Evaluating 2-item checklist for {camera_name}")

    baseline = get_baseline_by_camera(camera_name)
    if not baseline:
        return {"success": False, "error": f"No baseline for {camera_name}"}

    trigger_roi = baseline["trigger_roi"]
    baseline_start = baseline["baseline_sample_start_sec"]

    # ============ ITEM 1: QR READABLE ============
    total_frames = HEALTH_CHECK_CONFIG["total_frames"]
    detected_count = 0
    detected_qr_position = None

    for i in range(total_frames):
        frame_time = baseline_start + i * (1.0 / HEALTH_CHECK_CONFIG["interval_fps"])

        try:
            result = detect_qr_at_time(video_path, frame_time, trigger_roi)

            if result.get("success") and result.get("qr_detections"):
                for qr_det in result["qr_detections"]:
                    if HEALTH_CHECK_CONFIG["qr_target_text"] in qr_det.get("decoded_text", ""):
                        detected_count += 1
                        # Save first detected position for Item 2
                        if detected_qr_position is None and "bbox" in qr_det:
                            bbox = qr_det["bbox"]
                            detected_qr_position = (
                                (bbox[0] + bbox[2]) / 2,  # center x
                                (bbox[1] + bbox[3]) / 2,  # center y
                            )
                        break
        except Exception as e:
            logger.error(f"[HEALTH] Error at frame {i}: {e}")

    qr_success_rate = detected_count / total_frames if total_frames > 0 else 0

    # Determine QR status
    if qr_success_rate >= QR_READABLE_THRESHOLDS["OK"]:
        qr_status = "YES"
        qr_action = "OK"
    elif qr_success_rate >= QR_READABLE_THRESHOLDS["CAUTION"]:
        qr_status = "WEAK"
        qr_action = "Monitor"
    else:
        qr_status = "NO"
        qr_action = "Replace QR Label"

    item1 = {
        "name": "QR Trigger Readable",
        "status": qr_status,
        "success_rate_pct": qr_success_rate * 100,
        "detected": detected_count,
        "total": total_frames,
        "action": qr_action,
    }

    # ============ ITEM 2: POSITION OFFSET ============
    if detected_qr_position:
        position_result = check_position_offset(detected_qr_position, trigger_roi)

        if position_result.get("status") == "OK":
            position_status = "YES"
            position_action = "OK"
        elif position_result.get("status") == "CAUTION":
            position_status = "WEAK"
            position_action = "Monitor"
        else:
            position_status = "NO"
            position_action = "Adjust Camera"

        item2 = {
            "name": "Camera Position OK",
            "status": position_status,
            "offset_px": position_result.get("offset_px"),
            "offset_pct": position_result.get("offset_pct"),
            "action": position_action,
        }
    else:
        # Could not detect QR position, so can't check position
        item2 = {
            "name": "Camera Position OK",
            "status": "UNKNOWN",
            "offset_px": None,
            "offset_pct": None,
            "action": "Cannot determine (no QR detected)",
        }

    # ============ OVERALL EVALUATION ============
    ok_count = 0
    if item1["status"] == "YES":
        ok_count += 1
    if item2["status"] == "YES":
        ok_count += 1

    if ok_count == 2:
        overall_status = "OK"
        overall_rate = 100
    elif ok_count == 1:
        overall_status = "CRITICAL"
        overall_rate = 50
    else:
        overall_status = "CRITICAL"
        overall_rate = 0

    return {
        "success": True,
        "camera_name": camera_name,
        "items": [item1, item2],
        "overall_status": overall_status,
        "overall_rate_pct": overall_rate,
    }


def get_latest_health_check(camera_name: str) -> Optional[Dict]:
    """Get latest health check result for a camera (2-metrics format)"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, current_success_rate_pct, baseline_success_rate_pct,
                       qr_position_offset_pct, overall_status, check_timestamp
                FROM camera_health_check_results
                WHERE camera_name = ?
                ORDER BY check_timestamp DESC
                LIMIT 1
            """,
                (camera_name,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            current_pct = row[1]
            baseline_pct = row[2]
            position_offset_pct = row[3]
            status = row[4]
            timestamp = row[5]

            # Calculate QR degradation for display
            degradation_pct = current_pct - baseline_pct

            return {
                "id": row[0],
                "current_success_rate_pct": current_pct,
                "baseline_success_rate_pct": baseline_pct,
                "degradation_pct": degradation_pct,  # ✅ Match FE expectation
                "position_offset_pct": position_offset_pct,
                "status": status,
                "timestamp": timestamp,
            }
    except Exception as e:
        logger.error(f"[HEALTH] Error getting latest check: {e}")
        return None


# ==================== RUNTIME HEALTH CHECK FUNCTIONS ====================


def should_run_health_check(camera_name: str) -> bool:
    """
    Check if 2-hour interval has passed since last health check.

    Returns: True if should run check (first check or >2h since last)
    """
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()

            # Query last check timestamp
            # NOTE: check_type may not be set by run_health_check(), so we query all records
            cursor.execute(
                """
                SELECT check_timestamp FROM camera_health_check_results
                WHERE camera_name = ?
                ORDER BY check_timestamp DESC LIMIT 1
            """,
                (camera_name,),
            )

            result = cursor.fetchone()
            if not result:
                logger.info(f"[HEALTH] {camera_name}: First health check ever")
                return True  # First check ever

            # Check if 2 hours passed
            last_check_str = result[0]
            last_check = datetime.fromisoformat(last_check_str)
            now = datetime.now()
            hours_passed = (now - last_check).total_seconds() / 3600

            should_run = hours_passed >= 2.0

            if should_run:
                logger.info(
                    f"[HEALTH] {camera_name}: 2h interval passed ({hours_passed:.1f}h) - running check"
                )
            else:
                logger.debug(
                    f"[HEALTH] {camera_name}: Last check was {hours_passed:.1f}h ago - skipping"
                )

            return should_run

    except Exception as e:
        logger.error(f"[HEALTH] Error checking interval for {camera_name}: {e}")
        return False
