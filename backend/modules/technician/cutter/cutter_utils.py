import os
from datetime import datetime
import ast


def is_reasonable_timestamp(ts):
    """Check if timestamp is valid (greater than year 2020)."""
    return ts and int(ts) > 1577836800000  # After year 2020


def generate_output_filename(event, tracking_codes_filter, output_dir, brand_name="Alan"):
    """Create output filename based on tracking code and time priority: packing_time_start > packing_time_end."""
    tracking_codes_str = event.get("tracking_codes")
    packing_time_start = event.get("packing_time_start")
    packing_time_end = event.get("packing_time_end")

    try:
        tracking_codes = ast.literal_eval(tracking_codes_str) if tracking_codes_str else []
    except (ValueError, SyntaxError) as e:
        print(f"Error parsing tracking_codes_str for event {event.get('event_id')}: {e}")
        tracking_codes = []

    # Select priority tracking code
    if tracking_codes_filter:
        selected_tracking_code = next(
            (code for code in tracking_codes_filter if code in tracking_codes), "NoCode"
        )
    else:
        selected_tracking_code = tracking_codes[-1] if tracking_codes else "NoCode"

    # Priority select time: packing_time_start > packing_time_end > fallback
    timestamp = next(
        (t for t in [packing_time_start, packing_time_end] if is_reasonable_timestamp(t)),
        0,  # Fallback
    )
    try:
        time_str = datetime.fromtimestamp(int(timestamp) / 1000).strftime("%Y%m%d_%H%M")
    except Exception:
        time_str = "19700101_0000"

    return os.path.join(output_dir, f"{brand_name}_{selected_tracking_code}_{time_str}.mp4")


def generate_merged_filename(event_a, event_b, output_dir, brand_name="Alan"):
    """Create merged filename for two incomplete events, time priority: packing_time_start > packing_time_end."""
    tracking_codes_a_str = event_a.get("tracking_codes")
    tracking_codes_b_str = event_b.get("tracking_codes")
    packing_time_start_a = event_a.get("packing_time_start")
    packing_time_end_b = event_b.get("packing_time_end")

    # Select tracking code (priority to event with tracking code)
    try:
        tracking_codes_a = ast.literal_eval(tracking_codes_a_str) if tracking_codes_a_str else []
    except (ValueError, SyntaxError):
        tracking_codes_a = []
    try:
        tracking_codes_b = ast.literal_eval(tracking_codes_b_str) if tracking_codes_b_str else []
    except (ValueError, SyntaxError):
        tracking_codes_b = []

    selected_tracking_code = (
        tracking_codes_b[-1]
        if tracking_codes_b
        else (tracking_codes_a[-1] if tracking_codes_a else "NoCode")
    )

    # Priority select time: packing_time_start > packing_time_end > fallback
    timestamp = next(
        (t for t in [packing_time_start_a, packing_time_end_b] if is_reasonable_timestamp(t)),
        0,  # Fallback
    )
    try:
        time_str = datetime.fromtimestamp(int(timestamp) / 1000).strftime("%Y%m%d_%H%M")
    except Exception:
        time_str = "19700101_0000"

    return os.path.join(output_dir, f"{brand_name}_{selected_tracking_code}_{time_str}.mp4")


def update_event_in_db(cursor, event_id, output_file):
    """Update database for an event."""
    cursor.execute(
        """
        UPDATE events 
        SET is_processed = 1, output_file = ? 
        WHERE event_id = ?
    """,
        (output_file, event_id),
    )
