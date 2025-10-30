"""
Camera Health Baseline Capture Module
Captures baseline success rate during Step 4 ROI setup

Purpose:
  - When operator setup ROI with QR trigger
  - Find first TimeGo QR detection
  - Sample 3 seconds from there (15 frames @ 5fps)
  - Calculate success rate (golden standard for later health checks)
  - Save diagnostic metrics for root cause analysis
"""

import cv2
import numpy as np
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List

from modules.db_utils.safe_connection import safe_db_connection
from modules.technician.qr_detector import detect_qr_at_time

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

BASELINE_CONFIG = {
    'sample_duration_sec': 3.0,
    'interval_fps': 5,  # 5fps = 0.2s interval
    'total_frames': 15,  # 3 * 5
    'qr_target_text': 'TimeGo'
}


def find_first_timego_frame(
    video_path: str,
    trigger_roi: dict,
    start_search_sec: float = 0.0,
    max_search_sec: float = 10.0
) -> Optional[float]:
    """
    Scan video to find first frame where TimeGo QR is detected

    Args:
        video_path: Path to video file
        trigger_roi: ROI area {"x": 700, "y": 500, "w": 150, "h": 150}
        start_search_sec: Start scanning from this time
        max_search_sec: Maximum time to scan

    Returns:
        Timestamp (seconds) when first TimeGo detected, or None
    """

    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"[BASELINE] Cannot open video: {video_path}")
            return None

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            logger.error("[BASELINE] Cannot determine FPS")
            cap.release()
            return None

        cap.release()

        # Start searching using WeChat QR detection
        frame_interval = 1.0 / BASELINE_CONFIG['interval_fps']  # 0.2s for 5fps
        current_time = start_search_sec

        logger.info(f"[BASELINE] Searching for TimeGo from {start_search_sec}s to {max_search_sec}s")

        while current_time <= max_search_sec:
            # Use existing detect_qr_at_time from qr_detector
            result = detect_qr_at_time(video_path, current_time, trigger_roi)

            if result.get('success') and result.get('qr_detections'):
                # Check if any detection contains TimeGo
                for qr_det in result['qr_detections']:
                    if BASELINE_CONFIG['qr_target_text'] in qr_det.get('decoded_text', ''):
                        logger.info(f"[BASELINE] ✅ TimeGo found at {current_time:.2f}s")
                        return current_time

            current_time += frame_interval

        logger.warning(f"[BASELINE] TimeGo not found in first {max_search_sec}s")
        return None

    except Exception as e:
        logger.error(f"[BASELINE] Error searching for TimeGo: {e}")
        return None


# ❌ REMOVED: collect_diagnostic_metrics() - No longer needed
# All diagnostic metrics (blur, brightness, contrast, ink, edge) have been removed
# Health check now focuses only on: QR Success Rate + Position


def capture_baseline_from_step4(
    camera_name: str,
    video_path: str,
    trigger_roi: dict,
    packing_profile_id: Optional[int] = None,
    sample_start_sec: float = 0.0
) -> Dict:
    """
    Capture baseline during Step 4 ROI setup

    Protocol:
      1. Find first frame where TimeGo is detected
      2. From that frame, sample 3 seconds (15 frames @ 5fps)
      3. Count TimeGo detection success
      4. Collect diagnostic metrics
      5. Save to database

    Args:
        camera_name: Camera identifier
        video_path: Path to uploaded video (Step 4)
        trigger_roi: QR trigger area {"x": 700, "y": 500, "w": 150, "h": 150}
        packing_profile_id: ID of packing profile (optional)
        sample_start_sec: Where to start searching (default: 0.0)

    Returns:
        {
            'success': bool,
            'baseline_id': int or None,
            'baseline_success_rate': float,
            'baseline_success_rate_pct': float,
            'detected_frames': int,
            'total_frames': int,
            'error': str or None
        }
    """

    logger.info(f"[BASELINE] Starting capture for camera: {camera_name}")

    try:
        # Step 1: Find first TimeGo detection
        first_timego_time = find_first_timego_frame(video_path, trigger_roi, sample_start_sec)

        if first_timego_time is None:
            logger.warning(f"[BASELINE] TimeGo not found - skipping baseline capture")
            return {
                'success': False,
                'baseline_id': None,
                'error': 'TimeGo QR not found in video',
                'baseline_success_rate': 0,
                'baseline_success_rate_pct': 0,
                'detected_frames': 0,
                'total_frames': 0
            }

        logger.info(f"[BASELINE] First TimeGo found at {first_timego_time:.2f}s")

        # Step 2: Sample 3 seconds from first detection
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {
                'success': False,
                'baseline_id': None,
                'error': 'Cannot open video',
                'baseline_success_rate': 0,
                'baseline_success_rate_pct': 0,
                'detected_frames': 0,
                'total_frames': 0
            }

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps / BASELINE_CONFIG['interval_fps'])

        # Baseline window: [first_timego, first_timego + 3]
        baseline_start_frame = int(first_timego_time * fps)
        baseline_duration_sec = BASELINE_CONFIG['sample_duration_sec']
        total_frames = BASELINE_CONFIG['total_frames']

        x, y, w, h = trigger_roi['x'], trigger_roi['y'], trigger_roi['w'], trigger_roi['h']

        detected_count = 0
        diagnostic_metrics_list = []

        logger.info(f"[BASELINE] Sampling {total_frames} frames from {first_timego_time:.2f}s")

        # Step 3: Process each frame using detect_qr_at_time
        cap.release()  # Don't need manual frame reading anymore

        qr_bbox_list = []  # ← List to store detected QR bboxes

        for i in range(total_frames):
            frame_time = first_timego_time + i * (1.0 / BASELINE_CONFIG['interval_fps'])

            try:
                # Use detect_qr_at_time to detect QR at this timestamp
                result = detect_qr_at_time(video_path, frame_time, trigger_roi)

                # Detect TimeGo and extract bbox
                qr_found = False
                if result.get('success') and result.get('qr_detections'):
                    for qr_det in result['qr_detections']:
                        if BASELINE_CONFIG['qr_target_text'] in qr_det.get('decoded_text', ''):
                            qr_found = True
                            detected_count += 1

                            # ← Extract QR bbox (position & size)
                            bbox = qr_det.get('bbox')
                            if bbox:
                                qr_bbox_list.append(bbox)
                            break

                # ❌ REMOVED: diagnostic metrics collection
                # Only track QR detection now, not blur/brightness/contrast/ink/edge

            except Exception as e:
                logger.error(f"[BASELINE] Error processing frame at {frame_time:.2f}s: {e}")

        # Step 4: Calculate success rate
        success_rate = detected_count / total_frames if total_frames > 0 else 0
        success_rate_pct = success_rate * 100

        logger.info(f"[BASELINE] Success rate: {detected_count}/{total_frames} = {success_rate_pct:.1f}%")

        # ← Calculate average QR bbox (position & size)
        avg_qr_bbox = None
        if qr_bbox_list:
            avg_qr_bbox = {
                'x': int(np.mean([b['x'] for b in qr_bbox_list])),
                'y': int(np.mean([b['y'] for b in qr_bbox_list])),
                'w': int(np.mean([b['w'] for b in qr_bbox_list])),
                'h': int(np.mean([b['h'] for b in qr_bbox_list]))
            }
            logger.info(f"[BASELINE] Average QR bbox: {avg_qr_bbox}")

        # ❌ REMOVED: avg_metrics calculation for diagnostics

        # Step 5: Save to database
        baseline_data = {
            'camera_name': camera_name,
            'packing_profile_id': packing_profile_id,
            'setup_video_path': video_path,
            'baseline_sample_start_sec': first_timego_time,
            'baseline_sample_duration_sec': baseline_duration_sec,
            'total_frames': total_frames,
            'qr_detected_count': detected_count,
            'baseline_success_rate': success_rate,
            'baseline_success_rate_pct': success_rate_pct,
            'trigger_roi': json.dumps(trigger_roi),
            'qr_trigger_bbox': json.dumps(avg_qr_bbox) if avg_qr_bbox else None,
            'status': 'active'
        }

        with safe_db_connection() as conn:
            cursor = conn.cursor()

            # Check if baseline already exists for this camera
            cursor.execute(
                "SELECT id FROM camera_baseline_samples WHERE camera_name = ? AND status = 'active'",
                (camera_name,)
            )
            existing = cursor.fetchone()

            if existing:
                # UPDATE existing baseline (preserve baseline_id for foreign keys)
                logger.info(f"[BASELINE] Updating existing baseline for {camera_name}")
                baseline_id = existing[0]

                # Build UPDATE statement dynamically
                update_cols = ', '.join([f"{k} = ?" for k in baseline_data.keys()])
                values = list(baseline_data.values()) + [baseline_id]

                cursor.execute(
                    f"UPDATE camera_baseline_samples SET {update_cols} WHERE id = ?",
                    values
                )
            else:
                # INSERT new baseline only if not exists (first time)
                logger.info(f"[BASELINE] Creating new baseline for {camera_name}")
                placeholders = ', '.join(['?'] * len(baseline_data))
                columns = ', '.join(baseline_data.keys())
                cursor.execute(
                    f"INSERT INTO camera_baseline_samples ({columns}) VALUES ({placeholders})",
                    tuple(baseline_data.values())
                )
                baseline_id = cursor.lastrowid

            conn.commit()

        logger.info(f"[BASELINE] ✅ Baseline saved: ID={baseline_id}, Rate={success_rate_pct:.1f}%")

        return {
            'success': True,
            'baseline_id': baseline_id,
            'baseline_success_rate': success_rate,
            'baseline_success_rate_pct': success_rate_pct,
            'detected_frames': detected_count,
            'total_frames': total_frames,
            'first_timego_sec': first_timego_time
        }

    except Exception as e:
        logger.error(f"[BASELINE] ❌ Error capturing baseline: {e}", exc_info=True)
        return {
            'success': False,
            'baseline_id': None,
            'error': str(e),
            'baseline_success_rate': 0,
            'baseline_success_rate_pct': 0,
            'detected_frames': 0,
            'total_frames': 0
        }


# Utility function to get baseline
def get_baseline_by_camera(camera_name: str) -> Optional[Dict]:
    """Get active baseline for a camera"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, baseline_success_rate, baseline_success_rate_pct,
                       baseline_sample_start_sec, trigger_roi, qr_trigger_bbox
                FROM camera_baseline_samples
                WHERE camera_name = ? AND status = 'active'
                LIMIT 1
            """, (camera_name,))

            row = cursor.fetchone()
            if not row:
                return None

            return {
                'id': row[0],
                'baseline_success_rate': row[1],
                'baseline_success_rate_pct': row[2],
                'baseline_sample_start_sec': row[3],
                'trigger_roi': json.loads(row[4]),
                'qr_trigger_bbox': json.loads(row[5]) if row[5] else None
            }
    except Exception as e:
        logger.error(f"[BASELINE] Error getting baseline: {e}")
        return None
