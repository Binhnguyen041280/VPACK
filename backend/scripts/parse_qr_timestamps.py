#!/usr/bin/env python3
"""
Parse QR timestamps from log files and populate qr_detections table

This script reads log files that contain QR detection timestamps with bounding boxes,
calculates relative timestamps, and stores them in the database for the Magnifying Glass feature.

Log format: timestamp,state,tracking_code,bbox:[x,y,w,h]
Example: 350,On,SPXVN053052444843,bbox:[450,230,180,180]
"""

import re
import sqlite3
from typing import List, Tuple, Optional
from modules.db_utils.safe_connection import safe_db_connection
from modules.scheduler.db_sync import db_rwlock
from modules.config.logging_config import get_logger

logger = get_logger(__name__, {})


def parse_log_file(log_file_path: str) -> List[Tuple[int, str, int, int, int, int]]:
    """
    Parse QR detections with bbox from a log file.

    Args:
        log_file_path: Path to the log file

    Returns:
        List of tuples: (timestamp, tracking_code, bbox_x, bbox_y, bbox_w, bbox_h)
    """
    qr_detections = []

    # Regex pattern to match: timestamp,On,TRACKING_CODE,bbox:[x,y,w,h]
    pattern = r"^(\d+),On,([A-Z0-9]+),bbox:\[(\d+),(\d+),(\d+),(\d+)\]$"

    try:
        with open(log_file_path, "r") as f:
            for line in f:
                line = line.strip()

                # Skip comments and empty lines
                if line.startswith("#") or not line:
                    continue

                match = re.match(pattern, line)
                if match:
                    timestamp = int(match.group(1))
                    tracking_code = match.group(2)
                    bbox_x = int(match.group(3))
                    bbox_y = int(match.group(4))
                    bbox_w = int(match.group(5))
                    bbox_h = int(match.group(6))

                    qr_detections.append((timestamp, tracking_code, bbox_x, bbox_y, bbox_w, bbox_h))
                    logger.debug(
                        f"Parsed QR: {tracking_code} at {timestamp}s, bbox=({bbox_x},{bbox_y},{bbox_w},{bbox_h})"
                    )

        logger.info(f"Parsed {len(qr_detections)} QR detections from {log_file_path}")
        return qr_detections

    except FileNotFoundError:
        logger.error(f"Log file not found: {log_file_path}")
        return []
    except Exception as e:
        logger.error(f"Error parsing log file {log_file_path}: {str(e)}")
        return []


def get_events_with_logs() -> List[Tuple[int, int, str]]:
    """
    Get all events with their processed log files.

    Returns:
        List of tuples: (event_id, event_ts, log_file_path)
    """
    with db_rwlock.gen_rlock():
        with safe_db_connection() as conn:
            cursor = conn.cursor()

            # Join events with processed_logs to get log file paths
            cursor.execute(
                """
                SELECT DISTINCT
                    e.event_id,
                    e.ts,
                    pl.log_file
                FROM events e
                INNER JOIN processed_logs pl ON pl.log_file LIKE '%' || e.camera_name || '%'
                WHERE pl.is_processed = 1
                  AND e.ts IS NOT NULL
                ORDER BY e.event_id
            """
            )

            results = cursor.fetchall()
            logger.info(f"Found {len(results)} events with processed logs")
            return results


def populate_qr_detections():
    """
    Main function to parse log files and populate qr_detections table.
    """
    logger.info("Starting QR detections population...")

    events = get_events_with_logs()

    if not events:
        logger.warning("No events with processed logs found")
        return

    total_inserted = 0

    with db_rwlock.gen_wlock():
        with safe_db_connection() as conn:
            cursor = conn.cursor()

            # Clear existing qr_detections (optional - comment out to keep existing data)
            cursor.execute("DELETE FROM qr_detections")
            logger.info("Cleared existing qr_detections table")

            for event_id, event_ts, log_file in events:
                logger.info(f"Processing event {event_id}, ts={event_ts}, log={log_file}")

                # Parse QR detections from log file
                qr_detections = parse_log_file(log_file)

                if not qr_detections:
                    continue

                # Insert into database with relative timestamps
                for log_timestamp, tracking_code, bbox_x, bbox_y, bbox_w, bbox_h in qr_detections:
                    # Calculate relative timestamp: log_timestamp - event.ts
                    relative_timestamp = log_timestamp - event_ts

                    # Skip if relative timestamp is negative (shouldn't happen)
                    if relative_timestamp < 0:
                        logger.warning(
                            f"Skipping negative relative timestamp: {relative_timestamp}s for event {event_id}"
                        )
                        continue

                    try:
                        cursor.execute(
                            """
                            INSERT INTO qr_detections
                            (event_id, timestamp_seconds, tracking_code, bbox_x, bbox_y, bbox_w, bbox_h)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                event_id,
                                relative_timestamp,
                                tracking_code,
                                bbox_x,
                                bbox_y,
                                bbox_w,
                                bbox_h,
                            ),
                        )

                        total_inserted += 1
                        logger.debug(
                            f"Inserted QR detection: event={event_id}, rel_ts={relative_timestamp}s, code={tracking_code}"
                        )

                    except sqlite3.IntegrityError as e:
                        logger.error(
                            f"Integrity error inserting QR detection for event {event_id}: {e}"
                        )
                        continue

            conn.commit()

    logger.info(f"✅ QR detections population completed! Inserted {total_inserted} records.")

    # Print summary
    with db_rwlock.gen_rlock():
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM qr_detections")
            total_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT event_id) FROM qr_detections")
            events_count = cursor.fetchone()[0]

            logger.info(f"📊 Summary: {total_count} QR detections across {events_count} events")


if __name__ == "__main__":
    populate_qr_detections()
